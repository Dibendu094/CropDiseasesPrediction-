"""
AgriCare AI — Crop Disease Detection Backend
Flask application with PyTorch EfficientNet-B0 inference
"""

import os
import json
import re
import uuid
from datetime import datetime

import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image, ImageOps
from flask import (
    Flask, request, jsonify, render_template, send_from_directory,
    session, redirect, url_for,
)

import config
import db
import auth
import gemini_ai
import ensemble
from auth import login_required, current_user

# ──────────────────────────────────────────────
# App Configuration
# ──────────────────────────────────────────────
# Project layout:
#   <root>/backend/   → this file, models, data, python modules
#   <root>/frontend/  → templates + static assets
#   <root>/uploads/   → images users have uploaded
# Paths are derived from __file__ so the app runs from any working directory.
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')

app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, 'templates'),
    static_folder=os.path.join(FRONTEND_DIR, 'static'),
)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload
app.config['UPLOAD_FOLDER'] = os.path.join(PROJECT_ROOT, 'uploads')

# Session / auth config
app.secret_key = config.FLASK_SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    # A separately-hosted frontend (Vercel -> Render) makes the session cookie
    # cross-site, which browsers only accept as SameSite=None + Secure.
    SESSION_COOKIE_SAMESITE='None' if config.CROSS_SITE_COOKIES else 'Lax',
    SESSION_COOKIE_SECURE=config.CROSS_SITE_COOKIES,
)

# CORS, only when the UI is served from another origin.
if config.CORS_ORIGINS:
    @app.after_request
    def _cors(resp):
        origin = request.headers.get('Origin', '').rstrip('/')
        if origin in config.CORS_ORIGINS:
            resp.headers['Access-Control-Allow-Origin'] = origin
            resp.headers['Access-Control-Allow-Credentials'] = 'true'
            resp.headers['Vary'] = 'Origin'
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
        return resp

    @app.route('/<path:_any>', methods=['OPTIONS'])
    @app.route('/', methods=['OPTIONS'])
    def _preflight(_any=None):
        return ('', 204)

    print(f"[AgriCare AI] CORS enabled for: {', '.join(config.CORS_ORIGINS)}")

# Expose the current user + feature flags to every template.
@app.context_processor
def inject_globals():
    return {
        'current_user': current_user(),
        'gemini_enabled': config.GEMINI_ENABLED,
        'google_client_id': config.GOOGLE_CLIENT_ID,
        'google_auth_enabled': config.GOOGLE_AUTH_ENABLED,
    }

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
BASE_DIR = BACKEND_DIR
DATA_DIR = os.path.join(BACKEND_DIR, 'data')
MODELS_DIR = os.path.join(BACKEND_DIR, 'models')

# Crops the offline model can diagnose (shown in the dropdown). Anything else
# routes to the Gemini Vision fallback via "other". Kept in sync with the crops
# present in class_names.json / disease_info.json.
# The crop list lives in crops.py so the static frontend build can read it
# without importing torch. See backend/crops.py.
from crops import KNOWN_CROPS

# Create uploads directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Ensure the user registry exists (per-user schemas are created on signup).
# Falls back to a local SQLite file when the cloud database is unreachable, so
# sign-in and history keep working instead of returning 500s.
try:
    _backend = db.init_registry()
    if _backend == 'postgres':
        print("[AgriCare AI] Storage ready: Postgres.")
    else:
        print(f"[AgriCare AI] Storage ready: local SQLite ({config.SQLITE_PATH}).")
        if db.backend_error():
            print(f"   Postgres unavailable — {db.backend_error()}")
except Exception as e:
    print(f"[AgriCare AI] WARNING: could not initialize storage: {e}")

if config.FLASK_SECRET_KEY_IS_EPHEMERAL:
    print("[AgriCare AI] WARNING: FLASK_SECRET_KEY is not set — using a temporary "
          "key. Sessions will be lost on restart.")

# ──────────────────────────────────────────────
# Load Model & Data
# ──────────────────────────────────────────────
# On a fresh host (Render, a new clone) backend/models/ is empty because the
# checkpoints are too large for git. Fetch them if MODEL_URL_* is configured.
try:
    import model_store
    model_store.ensure_models()
except Exception as _e:
    print(f"[AgriCare AI] WARNING: model fetch step failed: {_e}")

print("[AgriCare AI] Loading model...")

# Load class names
with open(os.path.join(DATA_DIR, 'class_names.json'), 'r', encoding='utf-8') as f:
    CLASS_NAMES = json.load(f)

# Load disease info database (contains Hindi/Unicode text — force UTF-8)
with open(os.path.join(DATA_DIR, 'disease_info.json'), 'r', encoding='utf-8') as f:
    DISEASE_DB = json.load(f)

NUM_CLASSES = len(CLASS_NAMES)
print(f"   Classes loaded: {NUM_CLASSES}")

# Trained weights. The active checkpoint is a timm EfficientNet-B3 training
# checkpoint (weights nested under "model_state_dict"). The loader below is
# robust: it unwraps training checkpoints and auto-detects the EfficientNet
# variant (B0/B2/B3/B4) from the classifier's input feature size, so swapping
# the model file keeps working as long as the class count matches.
MODEL_PATH = os.path.join(MODELS_DIR, 'best_epoch_4_acc_98.70.pth')
if not os.path.exists(MODEL_PATH):          # fall back to the legacy filename
    MODEL_PATH = os.path.join(MODELS_DIR, 'best_model.pth')

_ckpt = torch.load(MODEL_PATH, map_location=torch.device('cpu'), weights_only=False)

# Unwrap: full model object, training checkpoint dict, or a plain state_dict.
if hasattr(_ckpt, 'state_dict'):
    state_dict = _ckpt.state_dict()
elif isinstance(_ckpt, dict):
    state_dict = _ckpt
    for _k in ('model_state_dict', 'state_dict', 'model', 'net'):
        if _k in _ckpt and isinstance(_ckpt[_k], dict):
            state_dict = _ckpt[_k]
            break
else:
    state_dict = _ckpt

# Strip any "module." prefix left over from DataParallel training.
state_dict = {k.replace('module.', '', 1): v for k, v in state_dict.items()}

# Sanity-check the checkpoint's class count against class_names.json.
_ckpt_classes = None
for _key in ('classifier.bias', 'classifier.weight', 'fc.weight'):
    if _key in state_dict and hasattr(state_dict[_key], 'shape'):
        _ckpt_classes = state_dict[_key].shape[0]
        break
if _ckpt_classes is not None and _ckpt_classes != NUM_CLASSES:
    print(f"[AgriCare AI] WARNING: checkpoint has {_ckpt_classes} classes but "
          f"class_names.json has {NUM_CLASSES}. Predictions will be mislabeled — "
          f"make sure class_names.json matches the trained model.")

if any(k.startswith('features.') for k in state_dict.keys()):
    # torchvision-trained EfficientNet-B0 (legacy path)
    from torchvision import models
    model = models.efficientnet_b0(weights=None)
    model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, NUM_CLASSES)
    model.load_state_dict(state_dict)
else:
    # timm-trained EfficientNet — auto-pick the variant by classifier width.
    try:
        import timm
    except ImportError:
        raise ImportError(
            "The 'timm' library is required to load this model. "
            "Install it with: pip install timm"
        )
    _in_feat = None
    if 'classifier.weight' in state_dict and hasattr(state_dict['classifier.weight'], 'shape'):
        _in_feat = state_dict['classifier.weight'].shape[1]
    _ARCH_BY_FEAT = {1280: 'efficientnet_b0', 1408: 'efficientnet_b2',
                     1536: 'efficientnet_b3', 1792: 'efficientnet_b4'}
    MODEL_ARCH = _ARCH_BY_FEAT.get(_in_feat, 'efficientnet_b3')
    model = timm.create_model(MODEL_ARCH, pretrained=False, num_classes=NUM_CLASSES)
    model.load_state_dict(state_dict)
    print(f"   Architecture: timm {MODEL_ARCH} (classifier in_features={_in_feat})")

model.eval()
print(f"[AgriCare AI] Model loaded successfully! ({os.path.basename(MODEL_PATH)})")

# ──────────────────────────────────────────────
# Best-accuracy model (see config.PREDICTION_MODEL for the comparison notes)
# ──────────────────────────────────────────────
# The ViT-B/16-384 / EfficientNet-B3 checkpoints are loaded up front rather
# than on the first request. If loading fails, the app falls back to the
# original single EfficientNet model loaded above.
BEST_MODEL_READY = False
if config.PREDICTION_MODEL in ('cascade', 'vit', 'efficientnet', 'ensemble'):
    try:
        ensemble.WEIGHT_VIT = config.ENSEMBLE_WEIGHT_VIT
        ensemble.WEIGHT_EFF = config.ENSEMBLE_WEIGHT_EFF
        ensemble.CASCADE_THRESHOLD = config.CASCADE_THRESHOLD
        ensemble.load_models()
        BEST_MODEL_READY = True
        _label = {'cascade': f'Cascade — ViT-B/16-384 first, EfficientNet-B3 as backup '
                             f'below {config.CASCADE_THRESHOLD:.0f}% confidence',
                  'vit': 'ViT-B/16-384 (best accuracy — see config.py)',
                  'efficientnet': 'EfficientNet-B3',
                  'ensemble': f'Ensemble (ViT {config.ENSEMBLE_WEIGHT_VIT:.0%} '
                              f'+ EfficientNet {config.ENSEMBLE_WEIGHT_EFF:.0%})'}[config.PREDICTION_MODEL]
        print(f"[AgriCare AI] Prediction model: {_label}")
    except Exception as e:
        print(f"[AgriCare AI] WARNING: could not load the ViT/ensemble models ({e}). "
              f"Falling back to the single EfficientNet model.")

# ──────────────────────────────────────────────
# Image Preprocessing Pipeline
# ──────────────────────────────────────────────
# EfficientNet-B3's native input resolution is ~300px with bicubic resizing.
# The model was trained at this resolution, so feeding it 224px bilinear images
# (the old setting) blurred fine lesion detail and depressed confidence. Using
# 300x300 bicubic restores the training-time distribution and materially lifts
# prediction confidence.
MODEL_INPUT_SIZE = 300
transform = transforms.Compose([
    transforms.Resize((MODEL_INPUT_SIZE, MODEL_INPUT_SIZE),
                      interpolation=transforms.InterpolationMode.BICUBIC),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def split_class_name(class_name):
    """Split a class label into (crop, disease). Handles both 'Crop___Disease'
    and single-underscore labels like 'Rice_BrownSpot'."""
    if '___' in class_name:
        crop, disease = class_name.split('___', 1)
    elif '_' in class_name:
        crop, disease = class_name.split('_', 1)
    else:
        crop, disease = class_name, 'Unknown'
    crop = crop.replace('_', ' ').replace(',', ', ')
    # Split CamelCase disease names (e.g. 'BrownSpot' -> 'Brown Spot')
    disease = disease.replace('_', ' ')
    disease = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', disease)
    return crop, disease


# ──────────────────────────────────────────────
# Confidence policy (graceful low-confidence, never block)
# ──────────────────────────────────────────────
# Three-tier confidence policy (never blocks — advisory only):
#   ≥ 85%      → High     : show disease, confidence, treatment, prevention.
#   70–84.99%  → Moderate : same, plus a "please verify" note.
#   < 70%      → Low      : show Top-3 + treatment for the top one, plus guidance.
HIGH_CONFIDENCE_MIN = 85.0
LOW_CONFIDENCE_THRESHOLD = 70.0
MODERATE_MESSAGE = "Moderate confidence. Please verify the result."
LOW_MESSAGE = ("Low confidence. Try a clearer image or select 'Other / Unknown Crop' "
               "for better identification.")


# Aliases so the dropdown value and the disease-DB crop name canonicalise the same.
_CROP_ALIASES = {
    'bell pepper': 'pepper', 'corn (maize)': 'corn', 'maize': 'corn',
    'rice (paddy)': 'rice', 'paddy': 'rice',
}


def _canon_crop(text):
    """Reduce a crop name or UI value to a simple lowercase keyword for matching
    (e.g. 'Corn (Maize)' → 'corn', 'Bell Pepper' → 'pepper')."""
    t = str(text or '').replace('_', ' ')
    t = t.split('(')[0].split(',')[0].strip().lower()
    return _CROP_ALIASES.get(t, t)


def crop_disease_for(class_name):
    """Return (crop, disease) preferring the curated disease DB (which knows the
    correct crop even for prefix-less labels like 'Anthracnose'), falling back
    to string parsing of the raw class name."""
    info = DISEASE_DB.get(class_name)
    if info:
        crop = info.get('crop')
        disease = info.get('disease')
        if crop and disease:
            return crop, disease
    return split_class_name(class_name)


# Map each crop keyword to the class indices it owns — powers the strict filter.
# Built from the disease DB's crop field so prefix-less classes route correctly.
CROP_INDEX = {}
for _i, _cls in enumerate(CLASS_NAMES):
    _c, _ = crop_disease_for(_cls)
    CROP_INDEX.setdefault(_canon_crop(_c), []).append(_i)


# ──────────────────────────────────────────────
# Duplicate-label merging
# ──────────────────────────────────────────────
# The model was trained on several merged public datasets, so a few real-world
# diseases appear under two different class labels — e.g. 'Leaf Blast' and
# 'Leaf_Blast' are both Rice leaf blast, 'Black Rot' and 'Grape___Black_rot' are
# both Grape black rot. The network splits its softmax mass across both logits,
# which (a) understates confidence for the correct answer and (b) prints the
# same disease twice in the Top-3. Summing the duplicates back together fixes
# both: probability for one real class belongs in one bucket.
CLASS_GROUPS = {}        # (crop_canon, disease_canon) -> [class indices]
for _i, _cls in enumerate(CLASS_NAMES):
    _c, _d = crop_disease_for(_cls)
    CLASS_GROUPS.setdefault((_canon_crop(_c), _d.strip().lower()), []).append(_i)

GROUP_OF = {}            # class index -> group key
for _key, _idxs in CLASS_GROUPS.items():
    for _i in _idxs:
        GROUP_OF[_i] = _key

_MERGED = {k: v for k, v in CLASS_GROUPS.items() if len(v) > 1}
if _MERGED:
    print(f"   Merged {len(_MERGED)} duplicate label pair(s): "
          + ", ".join(f"{'/'.join(k)}" for k in list(_MERGED)[:6]))


def _grouped_scores(raw_probs, allowed=None):
    """Collapse duplicate labels and rank the results.

    Returns a list of (summed_probability, representative_class_index) sorted
    high to low. `allowed` restricts scoring to one crop's class indices.
    """
    indices = allowed if allowed is not None else range(NUM_CLASSES)
    totals, reps = {}, {}
    for i in indices:
        key = GROUP_OF[i]
        p = float(raw_probs[i])
        totals[key] = totals.get(key, 0.0) + p
        # Represent the group with its single strongest label.
        if key not in reps or p > float(raw_probs[reps[key]]):
            reps[key] = i
    return sorted(((totals[k], reps[k]) for k in totals),
                  key=lambda t: t[0], reverse=True)


def _disease_result(predicted_class, confidence_score, top3):
    """Assemble the full treatment-report dict for a prediction.

    Always returns a usable report (never blocks). The three-tier confidence
    fields (tier + advisory) tell the UI how strongly to caveat the result.
    """
    crop_name, disease_name = crop_disease_for(predicted_class)
    disease_data = DISEASE_DB.get(predicted_class, {})
    is_healthy = disease_data.get('is_healthy', 'healthy' in predicted_class.lower())

    if confidence_score >= HIGH_CONFIDENCE_MIN:
        confidence_level = 'High'
        confidence_tier = 'high'
        advisory = ''
    elif confidence_score >= LOW_CONFIDENCE_THRESHOLD:
        confidence_level = 'Medium'
        confidence_tier = 'moderate'
        advisory = MODERATE_MESSAGE
    else:
        confidence_level = 'Low'
        confidence_tier = 'low'
        advisory = LOW_MESSAGE

    return {
        'success': True,
        'is_unsure': False,
        'confidence_tier': confidence_tier,       # 'high' | 'moderate' | 'low'
        'advisory_message': advisory,
        'low_confidence': confidence_tier == 'low',
        'source': 'PyTorch Model (Offline)',
        'source_short': 'pytorch',
        'class_name': predicted_class,
        'crop': disease_data.get('crop', crop_name),
        'crop_hindi': disease_data.get('crop_hindi', ''),
        'disease': disease_data.get('disease', disease_name),
        'confidence': round(confidence_score, 2),
        'confidence_level': confidence_level,
        'is_healthy': is_healthy,
        'description': disease_data.get('description', ''),
        'symptoms': disease_data.get('symptoms', []),
        'cause': disease_data.get('cause', ''),
        'affected_parts': disease_data.get('affected_parts', []),
        'treatment': disease_data.get('treatment', []),
        'organic_remedy': disease_data.get('organic_remedy', []),
        'chemical_spray': disease_data.get('chemical_spray', []),
        'preventive_measures': disease_data.get('preventive_measures',
                                                disease_data.get('prevention', [])),
        'best_time_to_spray': disease_data.get('best_time_to_spray', ''),
        'safety_tips': disease_data.get('safety_tips', []),
        'prevention': disease_data.get('prevention', []),
        'fertilizers': disease_data.get('fertilizers', []),
        'farmer_tips': disease_data.get('farmer_tips', []),
        'top3': top3
    }


def predict_image(image_path, selected_crop=None):
    """Run inference and ALWAYS return a best prediction + Top-3 + treatment.

    • If `selected_crop` is a known crop, the best class is chosen from within
      that crop's classes (so the dropdown still constrains the diagnosis), and
      the Top-3 are that crop's most likely diseases.
    • Confidence is the honest raw softmax probability of the best class (never
      renormalised/inflated), so a wrong crop naturally reads as low confidence.
    • Confidence < LOW_CONFIDENCE_THRESHOLD only sets a soft advisory flag — the
      result is never blocked or hidden. There is NO crop-mismatch warning.
    """
    image = Image.open(image_path)
    # Honour the EXIF orientation tag before anything else — phone photos are
    # commonly stored rotated, and feeding a sideways leaf to the model costs
    # real accuracy.
    image = ImageOps.exif_transpose(image).convert('RGB')
    input_tensor = transform(image).unsqueeze(0)

    with torch.no_grad():
        outputs = model(input_tensor)
        raw_probs = F.softmax(outputs, dim=1)[0]   # (num_classes,), honest probs

    sel_canon = _canon_crop(selected_crop) if selected_crop else None
    allowed = CROP_INDEX.get(sel_canon) if sel_canon else None

    # Rank with duplicate labels merged — restricted to the selected crop's
    # diseases when one was chosen, otherwise across every class.
    ranked = _grouped_scores(raw_probs, allowed)[:3]

    best_prob, best_idx = ranked[0]
    best_class = CLASS_NAMES[best_idx]
    confidence_score = best_prob * 100.0

    top3 = []
    for p, idx in ranked:
        c, d = crop_disease_for(CLASS_NAMES[idx])
        top3.append({
            'class_name': CLASS_NAMES[idx],
            'crop': c,
            'disease': d,
            'confidence': round(p * 100.0, 2),
            'is_best': idx == best_idx,
        })

    result = _disease_result(best_class, confidence_score, top3)
    return result


# ──────────────────────────────────────────────
# Dual-model ensemble path (ViT 60% + EfficientNet 40%)
# ──────────────────────────────────────────────
def _tier_for_single_model(confidence_score):
    """Confidence policy for a single full-strength softmax model — same
    85/70 cut-offs the original EfficientNet-only path used, since a solo
    model's probability is not weight-capped the way an ensemble vote is."""
    if confidence_score >= HIGH_CONFIDENCE_MIN:
        return 'High', 'high', ''
    if confidence_score >= LOW_CONFIDENCE_THRESHOLD:
        return 'Medium', 'moderate', MODERATE_MESSAGE
    return 'Low', 'low', LOW_MESSAGE


def predict_image_best(image_path, selected_crop=None):
    """Run the configured best-accuracy model (see config.PREDICTION_MODEL)
    and build the report. 'vit' / 'efficientnet' run one checkpoint alone;
    'ensemble' runs the weighted average of both.

    Either way, the winning class's treatment content is looked up through
    `info_key`, which resolves into the curated disease DB or the extended one
    written for the crops only the ViT's label space knows about.
    """
    mode = config.PREDICTION_MODEL

    if mode == 'cascade':
        out = ensemble.predict_cascade(image_path, selected_crop=selected_crop)
        confidence_score = out['confidence']
        # Whichever model answered, the number is that model's own softmax, so
        # the single-model 85/70 tiers apply.
        confidence_level, confidence_tier, advisory = _tier_for_single_model(confidence_score)
        casc = out['cascade']
        source = (f"{casc['final_model']} — "
                  + ("backup model (primary was under "
                     f"{casc['threshold']:.0f}% confident)" if casc['fallback_used']
                     else "primary model"))
        source_short = 'cascade'
        ensemble_block = None
        cascade_block = casc

    elif mode == 'ensemble':
        out = ensemble.predict(image_path, selected_crop=selected_crop)
        confidence_score = out['confidence']
        confidence_level, confidence_tier, advisory = ensemble.ensemble_confidence_tier(
            confidence_score, models_agree=out['agreement'])
        source = (f"Dual-Model Ensemble (ViT-B/16 {ensemble.WEIGHT_VIT:.0%} "
                  f"+ EfficientNet-B3 {ensemble.WEIGHT_EFF:.0%})")
        source_short = 'ensemble'
        ensemble_block = {
            'weights': {'vit': ensemble.WEIGHT_VIT, 'efficientnet': ensemble.WEIGHT_EFF},
            'models_agree': out['agreement'],
            'both_know_class': out['both_know_class'],
            'voters': out['voters'],
            'vit': out['models']['vit'],
            'efficientnet': out['models']['efficientnet'],
        }
        cascade_block = None
    else:
        which = 'vit' if mode == 'vit' else 'eff'
        out = ensemble.predict_single(image_path, selected_crop=selected_crop, which=which)
        confidence_score = out['confidence']
        confidence_level, confidence_tier, advisory = _tier_for_single_model(confidence_score)
        source = f"{out['model_used']} (best-accuracy model — see config.PREDICTION_MODEL)"
        source_short = mode
        ensemble_block = None
        cascade_block = None

    info = ensemble.FULL_DB.get(out['info_key'], {})
    is_healthy = info.get('is_healthy', 'healthy' in str(out['disease']).lower())

    return {
        'success': True,
        'is_unsure': False,
        'confidence_tier': confidence_tier,
        'advisory_message': advisory,
        'low_confidence': confidence_tier == 'low',
        'source': source,
        'source_short': source_short,
        'class_name': out['info_key'],
        'crop': info.get('crop', out['crop']),
        'crop_hindi': info.get('crop_hindi', ''),
        'disease': info.get('disease', out['disease']),
        'confidence': confidence_score,
        'confidence_level': confidence_level,
        'is_healthy': is_healthy,
        'description': info.get('description', ''),
        'symptoms': info.get('symptoms', []),
        'cause': info.get('cause', ''),
        'affected_parts': info.get('affected_parts', []),
        'treatment': info.get('treatment', []),
        'organic_remedy': info.get('organic_remedy', []),
        'chemical_spray': info.get('chemical_spray', []),
        'preventive_measures': info.get('preventive_measures',
                                        info.get('prevention', [])),
        'best_time_to_spray': info.get('best_time_to_spray', ''),
        'safety_tips': info.get('safety_tips', []),
        'prevention': info.get('prevention', []),
        'fertilizers': info.get('fertilizers', []),
        'farmer_tips': info.get('farmer_tips', []),
        'top3': out['top3'],
        # Only populated in 'ensemble' mode — the UI hides this panel otherwise.
        'ensemble': ensemble_block,
        # Only populated in 'cascade' mode: which model answered, and why.
        'cascade': cascade_block,
    }


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────
@app.route('/')
@app.route('/detect')
def detect_page():
    """The app is a single page: crop → photo → diagnosis.

    Both `/` and `/detect` render it so existing links and bookmarks keep
    working. Guests and signed-in users both get in; the difference is the
    daily quota (see QUOTAS below).
    """
    return render_template('detect.html', known_crops=KNOWN_CROPS)


@app.route('/history')
@login_required
def history_page():
    """Serve the signed-in user's private scan history page."""
    return render_template('history.html')


# ──────────────────────────────────────────────
# Authentication Routes
# ──────────────────────────────────────────────
@app.route('/auth')
def auth_page():
    """Serve the combined sign-in / sign-up page. If already signed in, go to /detect."""
    if current_user():
        return redirect(url_for('detect_page'))
    next_url = request.args.get('next', '/detect')
    return render_template('auth.html', next=next_url)


@app.route('/signup', methods=['POST'])
def signup():
    """Handle sign-up form submission."""
    data = request.get_json(silent=True) or {}
    full_name = data.get('full_name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    success, message, user = auth.register_user(full_name, email, password)
    if not success:
        return jsonify({'success': False, 'error': message}), 400

    # Auto-login the new user
    session['user'] = user
    session['just_logged_in'] = True
    session.permanent = True

    # NOTE: auth.register_user() has already called db.create_user() with the
    # real password hash and provisioned the user's schema. Calling it again
    # here would re-run the INSERT ... ON CONFLICT DO UPDATE with an empty
    # hash and wipe the stored one, making every new account unable to log in.

    try:
        db.update_last_login(user['id'])
    except Exception:
        pass

    return jsonify({'success': True, 'redirect': data.get('next') or '/detect'})


@app.route('/login', methods=['POST'])
def login():
    """Handle sign-in form submission."""
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip()
    password = data.get('password', '')

    user = auth.authenticate_user(email, password)
    if not user:
        return jsonify({'success': False, 'error': 'Invalid email or password.'}), 401

    session['user'] = user
    session['just_logged_in'] = True
    session.permanent = True

    try:
        db.update_last_login(user['id'])
    except Exception:
        pass

    return jsonify({'success': True, 'redirect': data.get('next') or '/detect'})


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle forgot-password form display and submission."""
    if request.method == 'GET':
        return render_template('forgot_password.html')

    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip()

    success, message, token = auth.generate_reset_token(email)
    if not success:
        return jsonify({'success': False, 'error': message}), 500

    # In a real app, send the reset link via email.
    # For this local setup, we return the token so the frontend can show it.
    reset_link = None
    if token:
        reset_link = f"/reset-password/{token}"

    return jsonify({
        'success': True,
        'message': message,
        'reset_link': reset_link,  # only present in local/dev mode
    })


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset form display and submission."""
    if request.method == 'GET':
        return render_template('reset_password.html', token=token)

    data = request.get_json(silent=True) or {}
    password = data.get('password', '')

    success, message = auth.reset_password(token, password)
    if not success:
        return jsonify({'success': False, 'error': message}), 400

    return jsonify({'success': True, 'message': message})


@app.route('/logout')
def logout():
    """Clear the session and return home."""
    session.clear()
    return redirect(url_for('detect_page'))


@app.route('/api/me')
def api_me():
    """Return the current user, one-time toast status, and today's quota usage."""
    user = current_user()
    just_logged_in = session.pop('just_logged_in', False) if user else False
    return jsonify({
        'user': user,
        'just_logged_in': just_logged_in,
        'usage': usage_snapshot(user),
    })


@app.route('/auth/google', methods=['POST'])
def google_login():
    """Sign in with a Google ID token issued by Google Identity Services.

    The browser gets the token from Google's button, posts it here, and we
    verify the signature and audience server-side before trusting any of it —
    never decode-without-verify, or anyone could forge a session.
    """
    if not config.GOOGLE_AUTH_ENABLED:
        return jsonify({'success': False,
                        'error': 'Google sign-in is not configured on this server.'}), 400

    data = request.get_json(silent=True) or {}
    token = (data.get('credential') or '').strip()
    if not token:
        return jsonify({'success': False, 'error': 'Missing Google credential.'}), 400

    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        info = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), config.GOOGLE_CLIENT_ID
        )
    except ImportError:
        return jsonify({'success': False,
                        'error': 'Server is missing the google-auth library.'}), 500
    except ValueError as e:
        # Bad signature, wrong audience, or expired token.
        print(f"[AgriCare AI] Google token rejected: {e}")
        return jsonify({'success': False, 'error': 'Google sign-in failed. Please try again.'}), 401

    email = (info.get('email') or '').strip().lower()
    if not email or not info.get('email_verified', False):
        return jsonify({'success': False,
                        'error': 'Your Google account has no verified email address.'}), 400

    full_name = (info.get('name') or email.split('@')[0]).strip()
    picture = info.get('picture', '')

    # Reuse the account if this email already signed up locally, otherwise make one.
    try:
        existing = db.get_user_by_email(email)
        if existing:
            user_id = existing['user_id']
            full_name = existing.get('full_name') or full_name
        else:
            user_id = str(uuid.uuid4())
        # Passing '' for the hash leaves any existing password untouched
        # (db.create_user guards it with NULLIF) and provisions this user's
        # private schema in Supabase on first sign-in.
        db.create_user(user_id, full_name, email, '')
        # Persist the Google profile (name + avatar) so it survives new sessions.
        db.save_google_profile(user_id, full_name, picture)
    except Exception as e:
        print(f"[AgriCare AI] Google sign-in storage error: {e}")
        return jsonify({'success': False,
                        'error': 'Could not set up your account. Please try again.'}), 500

    session['user'] = {'id': user_id, 'email': email,
                       'full_name': full_name, 'picture': picture}
    session['just_logged_in'] = True
    session.permanent = True

    return jsonify({'success': True, 'redirect': data.get('next') or '/'})


@app.route('/api/history')
@login_required
def api_history():
    """Return the signed-in user's private detection history."""
    try:
        rows = db.get_detections(current_user()['id'])
        return jsonify({'success': True, 'history': rows})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/history/<int:detection_id>', methods=['DELETE'])
@login_required
def delete_history_item(detection_id):
    """Delete a specific detection from the signed-in user's history."""
    try:
        deleted = db.delete_detection(current_user()['id'], detection_id)
        if deleted:
            return jsonify({'success': True, 'message': 'Scan deleted from history.'})
        return jsonify({'success': False, 'error': 'Record not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _quota_for(user):
    """Daily allowances for the current visitor."""
    if user:
        return config.DAILY_SCANS_SIGNED_IN, config.DAILY_GEMINI_SIGNED_IN
    return config.DAILY_SCANS_GUEST, config.DAILY_GEMINI_GUEST


def _usage_keys():
    """Session keys for today's counters (they roll over automatically because
    the date is part of the key)."""
    today = datetime.now().strftime('%Y-%m-%d')
    return f"scans_{today}", f"gemini_{today}"


def usage_snapshot(user):
    """Current usage + limits, for the UI to show remaining scans."""
    scans_key, gemini_key = _usage_keys()
    scan_limit, gemini_limit = _quota_for(user)
    scans_used = session.get(scans_key, 0)
    gemini_used = session.get(gemini_key, 0)
    return {
        'signed_in': bool(user),
        'scans_used': scans_used,
        'scans_limit': scan_limit,
        'scans_left': max(0, scan_limit - scans_used),
        'gemini_used': gemini_used,
        'gemini_limit': gemini_limit,
        'gemini_left': max(0, gemini_limit - gemini_used),
    }


def _check_and_bump_rate_limit(user, uses_gemini=False):
    """Enforce the daily scan cap (and the stricter Gemini sub-cap).

    Signed-in users get more headroom than guests; the AI "unknown crop" path
    is capped separately for everyone because each call costs an API request.
    Returns an error response tuple when a limit is hit, otherwise None.
    """
    scans_key, gemini_key = _usage_keys()
    scan_limit, gemini_limit = _quota_for(user)

    scans_used = session.get(scans_key, 0)
    if scans_used >= scan_limit:
        who = 'signed-in' if user else 'guest'
        extra = '' if user else ' Sign in with Google for a higher daily limit.'
        return jsonify({
            'success': False,
            'error': f'Daily limit reached ({scan_limit} scans per day for {who} users).{extra}',
            'limit_reached': True,
            'usage': usage_snapshot(user),
        }), 429

    if uses_gemini:
        gemini_used = session.get(gemini_key, 0)
        if gemini_used >= gemini_limit:
            return jsonify({
                'success': False,
                'error': (f'Daily unlisted-crop identification limit reached ({gemini_limit} per day). '
                          f'You can still diagnose the listed crops from the dropdown.'),
                'limit_reached': True,
                'usage': usage_snapshot(user),
            }), 429
        session[gemini_key] = gemini_used + 1

    session[scans_key] = scans_used + 1
    return None


def _run_detection(crop_selected):
    """Shared detection pipeline used by both /predict and /api/detect-with-crop.

    Saves the uploaded image, routes to the offline PyTorch model or the Gemini
    Vision fallback based on `crop_selected`, persists to history, and returns a
    Flask JSON response.
    """
    user = current_user()

    # Decide the route first — the Gemini path has its own, stricter daily cap.
    use_gemini = str(crop_selected).strip().lower() in ('other', 'other / unknown crop', 'unknown')

    limited = _check_and_bump_rate_limit(user, uses_gemini=use_gemini)
    if limited is not None:
        return limited

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'error': 'Invalid file type. Please upload JPG, JPEG, or PNG images.'
        }), 400

    # Save the uploaded file.
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        if use_gemini:
            # Unknown / other crop → Gemini Vision AI fallback.
            result = gemini_ai.detect_unknown_crop(filepath)
            if not result.get('success'):
                # Detection failed — return the friendly error (HTTP 200 so the
                # frontend can display it inline without treating it as a crash).
                return jsonify(result), 200
        elif BEST_MODEL_READY:
            # Known crop → the configured best-accuracy model, constrained to
            # the chosen crop (see config.PREDICTION_MODEL).
            result = predict_image_best(filepath, selected_crop=crop_selected)
        else:
            # Best model unavailable → the original single EfficientNet model.
            result = predict_image(filepath, selected_crop=crop_selected)

        result['image_url'] = f'/uploads/{filename}'
        result['crop_selected'] = crop_selected
        result['usage'] = usage_snapshot(user)

        # Persist to the signed-in user's private database — but never store an
        # "Unknown / Unsure" result (it has no diagnosis worth keeping).
        if user and not result.get('is_unsure'):
            try:
                db.save_detection(user['id'], result)
            except Exception as e:
                print(f"[AgriCare AI] WARNING: could not save detection: {e}")

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Prediction failed: {str(e)}'
        }), 500


@app.route('/api/crops')
def api_crops():
    """Return the known-crop list for the selector, plus whether Gemini fallback
    is available for the 'Other / Unknown Crop' option."""
    return jsonify({
        'crops': KNOWN_CROPS,
        'gemini_enabled': config.GEMINI_ENABLED,
        'prediction_model': config.PREDICTION_MODEL if BEST_MODEL_READY else 'efficientnet-legacy',
        'ensemble_weights': ({'vit': ensemble.WEIGHT_VIT, 'efficientnet': ensemble.WEIGHT_EFF}
                             if (BEST_MODEL_READY and config.PREDICTION_MODEL == 'ensemble') else None),
    })


@app.route('/predict', methods=['POST'])
def predict():
    """Legacy endpoint — runs the offline PyTorch model on the uploaded image."""
    return _run_detection(request.form.get('crop_selected', ''))


@app.route('/api/detect-with-crop', methods=['POST'])
def detect_with_crop():
    """Crop-aware detection. Routes known crops to PyTorch and the
    'Other / Unknown Crop' option to the Gemini Vision fallback."""
    return _run_detection(request.form.get('crop_selected', ''))


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded images."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/api/diseases')
def get_all_diseases():
    """Return the full disease library grouped by crop, including treatment plans."""
    library = {}
    for class_name, info in DISEASE_DB.items():
        # Use the curated DB's crop field — plain string-splitting files
        # prefix-less labels like "Anthracnose" under a crop of that name.
        crop, _ = crop_disease_for(class_name)
        if crop not in library:
            library[crop] = []

        # Include all info such as treatments, symptoms, etc.
        disease_entry = info.copy()
        disease_entry['class_name'] = class_name
        disease_entry['crop'] = crop

        library[crop].append(disease_entry)
    return jsonify(library)


@app.route('/api/disease/<path:class_name>')
def get_disease_info(class_name):
    """Return detailed info for a specific disease."""
    if class_name in DISEASE_DB:
        info = DISEASE_DB[class_name].copy()
        info['class_name'] = class_name
        return jsonify(info)
    return jsonify({'error': 'Disease not found'}), 404


# ──────────────────────────────────────────────
# Error handlers
# ──────────────────────────────────────────────
# The frontend calls response.json() on every reply, so an HTML error page from
# Flask surfaces as an unhelpful "Unexpected token <" in the browser console.
# API routes therefore always answer with JSON.
def _wants_json():
    return (request.path.startswith('/api/')
            or request.path.startswith('/predict')
            or 'application/json' in (request.headers.get('Accept') or ''))


@app.errorhandler(413)
def too_large(_e):
    msg = 'Image is too large. Please upload a file under 16 MB.'
    if _wants_json():
        return jsonify({'success': False, 'error': msg}), 413
    return msg, 413


@app.errorhandler(404)
def not_found(e):
    if _wants_json():
        return jsonify({'success': False, 'error': 'Endpoint not found.'}), 404
    return e, 404


@app.errorhandler(500)
def server_error(_e):
    if _wants_json():
        return jsonify({
            'success': False,
            'error': 'Something went wrong on the server. Please try again.'
        }), 500
    return 'Internal server error', 500


# ──────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────
if __name__ == '__main__':
    # PORT is overridable so the app can share a machine with other services.
    port = int(os.environ.get('PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', '1').lower() not in ('0', 'false', 'no')
    print("\n[AgriCare AI] Server is running!")
    print(f"   Open http://localhost:{port} in your browser\n")
    app.run(debug=debug, host='0.0.0.0', port=port)
