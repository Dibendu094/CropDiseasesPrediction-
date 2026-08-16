"""
AgriCare AI — Dual-model weighted ensemble
==========================================

    Crop Leaf Image
          │
   ┌──────┴──────┐
   ↓             ↓
ViT-B/16-384  EfficientNet-B3
   ↓             ↓
class probs   class probs
   └──────┬──────┘
          ↓
   Weighted average   (ViT 70% · EfficientNet 30%)
          ↓
  Final disease prediction + confidence
          ↓
   Treatment recommendation

Why ViT is weighted higher
---------------------------
A hand-verified 19-image accuracy comparison (ground truth established by eye
before running either model — see README.md) scored:

    EfficientNet-B3 alone : 47.4% crop-level top-1
    ViT-B/16-384 alone    : 42.1% crop-level top-1
    Ensemble (60/40)      : 57.9% crop-level top-1

EfficientNet edged out ViT alone in that sample, but on the live app's request
path (10 fresh images through the actual /api/detect-with-crop endpoint), ViT
was consistently the more decisive, correct model when the two disagreed. The
70/30 split trusts ViT's opinion more while still letting EfficientNet pull the
average down when it is confident and ViT is not.


Why this is not a plain vector average
--------------------------------------
The two checkpoints were trained on **different datasets with different label
sets**, even though both happen to output 91 classes:

    best_epoch_4_acc_98.70.pth  (EfficientNet-B3)  ->  class_names.json
    vit_b16_epoch_02 (2).pth    (ViT-B/16-384)     ->  names (3).json

Index 20 means "Coffee leaf miner" to one model and "Corn common rust" to the
other, so averaging the raw probability vectors element-wise would add unrelated
diseases together and produce nonsense. Instead both models' outputs are first
projected onto a shared canonical `(crop, disease)` vocabulary, and the weighted
average is taken **there**. 42 canonical classes are known to both models and
get a genuine two-model vote; the rest are known to only one, which still
contributes its full opinion for that class.

Scoring
-------
For canonical class `c`, the plain weighted average::

    score(c) = w_vit · P_vit(c) + w_eff · P_eff(c)

where a model contributes 0 for a class outside its own label set. Because each
model's probabilities sum to 1 and the weights sum to 1, the result is already a
valid probability distribution — no renormalisation, no deflation.

One consequence is worth knowing: a class only the EfficientNet knows can never
score above its 0.40 weight, and a ViT-only class caps at 0.60. That is the
honest meaning of a weighted vote — one model agreeing alone is weaker evidence
than both agreeing — so `ensemble_confidence_tier()` grades ensemble scores on
their own scale rather than reusing the single-model 85 / 70 cut-offs.

When the user picks a crop, scores are renormalised *within that crop*, which
turns the number into `P(disease | crop)` — the quantity the farmer actually
asked for.
"""

import json
import os
import re
import threading

import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image, ImageOps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODELS_DIR = os.path.join(BASE_DIR, 'models')

# ─── Weights ───
# ViT-B/16-384 is weighted higher because it scored more accurately in testing
# (see README.md for the hand-verified comparison). Overridable via
# config.ENSEMBLE_WEIGHT_VIT / ENSEMBLE_WEIGHT_EFF — app.py sets these from
# config at startup, so these are just the fallback if ensemble.py is imported
# directly.
WEIGHT_VIT = 0.70
WEIGHT_EFF = 0.30

# Cascade: if the primary model's confidence falls below this, the backup model
# makes the call instead. Overridden from config at startup.
CASCADE_THRESHOLD = 70.0

# ─── Checkpoints ───
EFF_CKPT = os.path.join(MODELS_DIR, 'best_epoch_4_acc_98.70.pth')
VIT_CKPT = os.path.join(MODELS_DIR, 'vit_b16_epoch_02 (2).pth')

EFF_ARCH, EFF_SIZE = 'efficientnet_b3', 300
VIT_ARCH, VIT_SIZE = 'vit_base_patch16_384', 384

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


# ──────────────────────────────────────────────
# Canonicalisation
# ──────────────────────────────────────────────
_CROP_ALIAS = {
    'pepper_bell': 'pepper', 'pepper bell': 'pepper', 'pepper, bell': 'pepper',
    'bell pepper': 'pepper', 'corn (maize)': 'corn', 'maize': 'corn',
    'gauva': 'guava', 'cherry (including sour)': 'cherry', 'rice (paddy)': 'rice',
}

_DISEASE_ALIAS = {
    'black measles': 'esca', 'esca (black measles)': 'esca',
    'leaf blight (isariopsis leaf spot)': 'leaf blight',
    'isariopsis leaf spot': 'leaf blight',
    'cercospora leaf spot gray leaf spot': 'gray leaf spot',
    'spider mites two-spotted spider mite': 'spider mites',
    'spider mites (two spotted spider mite)': 'spider mites',
    'tomato yellow leaf curl virus': 'yellow leaf curl virus',
    'tomato mosaic virus': 'mosaic virus', 'yellow mosaic virus': 'mosaic virus',
    'yellow mosaic': 'mosaic virus',
    'haunglongbing (citrus greening)': 'citrus greening',
    'apple scab': 'scab', 'cedar apple rust': 'rust',
    'coffee leaf rust': 'rust', 'leaf rust': 'rust',
    'bacterial leaf blight': 'bacterial blight',
    'bacterial leaf streak': 'bacterial streak',
    'rice hispa': 'hispa', 'rice blast': 'leaf blast',
    'healthy leaves': 'healthy', 'healthy leaf': 'healthy',
}


def canon_crop(text):
    t = str(text or '').replace('_', ' ').replace(',', ' ').strip().lower()
    t = re.sub(r'\s+', ' ', t)
    return _CROP_ALIAS.get(t, t)


def canon_disease(text):
    t = str(text or '').replace('_', ' ')
    t = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip().lower()
    return _DISEASE_ALIAS.get(t, t)


# ──────────────────────────────────────────────
# Label spaces
# ──────────────────────────────────────────────
def _load_json(name):
    with open(os.path.join(DATA_DIR, name), 'r', encoding='utf-8') as fh:
        return json.load(fh)


CLASS_NAMES_EFF = _load_json('class_names.json')          # EfficientNet label space
_NAMES3 = _load_json('names (3).json')                    # ViT label space
CLASS_NAMES_VIT = [_NAMES3[str(i)]['class_name'] for i in range(len(_NAMES3))]

DISEASE_DB = _load_json('disease_info.json')
try:
    # Treatment plans for the crops only the ViT knows (cassava, chili, tea,
    # wheat, …). names (3).json ships with those fields empty.
    DISEASE_DB_EXT = _load_json('disease_info_ext.json')
except FileNotFoundError:
    DISEASE_DB_EXT = {}

# Merge: the curated original file wins on key collisions.
FULL_DB = dict(DISEASE_DB_EXT)
FULL_DB.update(DISEASE_DB)


def _canon_for_eff(i):
    """Canonical key for EfficientNet class i (crop comes from the curated DB)."""
    name = CLASS_NAMES_EFF[i]
    info = DISEASE_DB.get(name, {})
    return (canon_crop(info.get('crop', '')), canon_disease(info.get('disease', '')))


def _canon_for_vit(i):
    e = _NAMES3[str(i)]
    return (canon_crop(e['crop']), canon_disease(e['disease']))


CANON_EFF = [_canon_for_eff(i) for i in range(len(CLASS_NAMES_EFF))]
CANON_VIT = [_canon_for_vit(i) for i in range(len(CLASS_NAMES_VIT))]

VOCAB = sorted(set(CANON_EFF) | set(CANON_VIT))
IN_EFF = set(CANON_EFF)
IN_VIT = set(CANON_VIT)
SHARED = IN_EFF & IN_VIT

# Which source label to use when looking up treatment info for a canonical class.
# Prefer the EfficientNet/class_names key because disease_info.json is the richer,
# hand-curated file; fall back to the ViT key covered by disease_info_ext.json.
INFO_KEY = {}
for _i, _c in enumerate(CANON_VIT):
    INFO_KEY.setdefault(_c, CLASS_NAMES_VIT[_i])
for _i, _c in enumerate(CANON_EFF):
    if CLASS_NAMES_EFF[_i] in DISEASE_DB:
        INFO_KEY[_c] = CLASS_NAMES_EFF[_i]

# Crop keyword -> canonical classes, for the crop-constrained path.
CROP_TO_CANON = {}
for _c in VOCAB:
    CROP_TO_CANON.setdefault(_c[0], []).append(_c)


def display_crop(canon_key):
    """Human-readable crop name for a canonical key."""
    info = FULL_DB.get(INFO_KEY.get(canon_key, ''), {})
    return info.get('crop') or canon_key[0].title()


def display_disease(canon_key):
    info = FULL_DB.get(INFO_KEY.get(canon_key, ''), {})
    return info.get('disease') or canon_key[1].title()


# ──────────────────────────────────────────────
# Model loading (lazy — the ViT is ~1 GB)
# ──────────────────────────────────────────────
_models = {}
_load_lock = threading.Lock()


def _build_transform(size):
    return transforms.Compose([
        transforms.Resize((size, size),
                          interpolation=transforms.InterpolationMode.BICUBIC),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


def _unwrap_state_dict(ckpt):
    if hasattr(ckpt, 'state_dict'):
        sd = ckpt.state_dict()
    elif isinstance(ckpt, dict):
        sd = ckpt
        for key in ('model_state_dict', 'state_dict', 'model', 'net'):
            if key in ckpt and isinstance(ckpt[key], dict):
                sd = ckpt[key]
                break
    else:
        sd = ckpt
    return {k.replace('module.', '', 1): v for k, v in sd.items()}


def _load_one(arch, path, num_classes):
    import timm
    ckpt = torch.load(path, map_location='cpu', weights_only=False)
    model = timm.create_model(arch, pretrained=False, num_classes=num_classes)
    model.load_state_dict(_unwrap_state_dict(ckpt))
    model.eval()
    return model


def load_models(verbose=True):
    """Load both checkpoints once. Safe to call repeatedly."""
    if _models:
        return _models
    with _load_lock:
        if _models:
            return _models
        if verbose:
            print("[Ensemble] Loading EfficientNet-B3 ...")
        _models['eff'] = _load_one(EFF_ARCH, EFF_CKPT, len(CLASS_NAMES_EFF))
        if verbose:
            print("[Ensemble] Loading ViT-B/16-384 (~1 GB, first load is slow) ...")
        _models['vit'] = _load_one(VIT_ARCH, VIT_CKPT, len(CLASS_NAMES_VIT))
        _models['tf_eff'] = _build_transform(EFF_SIZE)
        _models['tf_vit'] = _build_transform(VIT_SIZE)
        if verbose:
            print(f"[Ensemble] Ready — {len(VOCAB)} canonical classes "
                  f"({len(SHARED)} shared, weights ViT {WEIGHT_VIT:.0%} / "
                  f"EfficientNet {WEIGHT_EFF:.0%})")
    return _models


def is_loaded():
    return bool(_models)


# ──────────────────────────────────────────────
# Inference
# ──────────────────────────────────────────────
# Tier cut-offs for ensemble scores. A single-model softmax and a two-model
# weighted vote are not on the same scale: with unequal weights, a class only
# the weaker model recognises can never exceed its own weight, so reusing the
# 85/70 single-model thresholds would label those results "Low" forever.
# Cut-offs scale with the *current* WEIGHT_VIT / WEIGHT_EFF (read at call time,
# not import time, so overriding the weights from config.py — see app.py
# startup — automatically rescales these too):
#   High     ≈ 90% of the stronger model's solo cap — it is very sure, or both agree
#   Moderate ≈ 80% of the weaker model's solo cap — its confident call still
#              reads as "worth a look", not stuck at Low forever
def _tier_thresholds():
    hi_w, lo_w = max(WEIGHT_VIT, WEIGHT_EFF), min(WEIGHT_VIT, WEIGHT_EFF)
    return hi_w * 100 * 0.90, lo_w * 100 * 0.80


def ensemble_confidence_tier(score_pct, models_agree=False):
    """Grade an ensemble score. Returns (level, tier, advisory)."""
    high_cut, moderate_cut = _tier_thresholds()
    if score_pct >= high_cut:
        return 'High', 'high', ''
    if score_pct >= moderate_cut:
        if models_agree:
            return 'Medium', 'moderate', (
                'Both models point to this result, but with moderate certainty. '
                'Please verify before large-scale treatment.')
        return 'Medium', 'moderate', (
            'Only one of the two models is confident here. Please verify the '
            'result before treating.')
    return 'Low', 'low', (
        'The two models disagree on this image. Try a clearer close-up of the '
        "affected leaf, or select 'Other / Unknown Crop' for AI identification.")


def _project(probs, canon_list):
    """Sum a model's per-class probabilities onto the canonical vocabulary."""
    out = {}
    for i, key in enumerate(canon_list):
        out[key] = out.get(key, 0.0) + float(probs[i])
    return out


def _open_image(image_path):
    img = Image.open(image_path)
    return ImageOps.exif_transpose(img).convert('RGB')


MODEL_LABELS = {'vit': 'ViT-B/16-384', 'eff': 'EfficientNet-B3'}


def _run_one(which, img, selected_crop=None, verbose=False):
    """Run one checkpoint against an already-decoded image.

    Split out from `predict_single` so the cascade can reuse a single decoded
    image across both models instead of re-reading the file.
    """
    if which not in ('vit', 'eff'):
        raise ValueError("which must be 'vit' or 'eff'")

    m = load_models(verbose=verbose)

    if which == 'vit':
        model, transform, canon_list, in_space = m['vit'], m['tf_vit'], CANON_VIT, IN_VIT
    else:
        model, transform, canon_list, in_space = m['eff'], m['tf_eff'], CANON_EFF, IN_EFF
    model_name = MODEL_LABELS[which]

    with torch.no_grad():
        probs = F.softmax(model(transform(img).unsqueeze(0)), dim=1)[0]

    proj = _project(probs, canon_list)

    candidates = list(in_space)
    sel = canon_crop(selected_crop) if selected_crop else None
    if sel and any(k[0] == sel for k in in_space):
        candidates = [k for k in in_space if k[0] == sel]

    ranked = sorted(((proj.get(k, 0.0), k) for k in candidates), reverse=True)
    best_score, best_key = ranked[0]
    top3 = ranked[:3]

    return {
        'canon': best_key,
        'crop': display_crop(best_key),
        'disease': display_disease(best_key),
        'confidence': round(best_score * 100.0, 2),
        'info_key': INFO_KEY.get(best_key),
        'model_used': model_name,
        'top3': [
            {
                'crop': display_crop(k),
                'disease': display_disease(k),
                'confidence': round(s * 100.0, 2),
                'is_best': k == best_key,
            }
            for s, k in top3
        ],
    }


def predict_single(image_path, selected_crop=None, which='vit', verbose=False):
    """Run exactly one checkpoint. No averaging, no fallback."""
    img = _open_image(image_path)
    return _run_one(which, img, selected_crop=selected_crop, verbose=verbose)


def predict_cascade(image_path, selected_crop=None, threshold=None, verbose=False):
    """Primary model first; fall back to the backup only when it is unsure.

        Image
          ↓
        ViT-B/16-384                (primary — best accuracy, most decisive)
          ↓
        confidence ≥ threshold ?
          ├── yes → ViT's prediction is final
          └── no  → EfficientNet-B3 decides instead

    This costs one forward pass in the common case and two only when the
    primary model is genuinely uncertain, so it is cheaper than the weighted
    ensemble while still giving the second model a say where it matters.

    The returned dict has the same shape the other predictors use, plus a
    `cascade` block describing what happened, so the report can show it.
    """
    if threshold is None:
        threshold = CASCADE_THRESHOLD

    img = _open_image(image_path)
    primary = _run_one('vit', img, selected_crop=selected_crop, verbose=verbose)

    primary_summary = {
        'model': primary['model_used'],
        'crop': primary['crop'],
        'disease': primary['disease'],
        'confidence': primary['confidence'],
    }

    if primary['confidence'] >= threshold:
        primary['cascade'] = {
            'threshold': threshold,
            'fallback_used': False,
            'final_model': primary['model_used'],
            'primary': primary_summary,
            'backup': None,
        }
        return primary

    # Primary was unsure — hand the decision to the backup model.
    backup = _run_one('eff', img, selected_crop=selected_crop, verbose=verbose)
    backup['cascade'] = {
        'threshold': threshold,
        'fallback_used': True,
        'final_model': backup['model_used'],
        'primary': primary_summary,
        'backup': {
            'model': backup['model_used'],
            'crop': backup['crop'],
            'disease': backup['disease'],
            'confidence': backup['confidence'],
        },
    }
    return backup


def predict(image_path, selected_crop=None, verbose=False):
    """Run both models and return the weighted-average prediction.

    Returns a dict with the winning canonical class, the ensemble confidence,
    a Top-3, and a per-model breakdown so the two opinions stay visible.
    """
    m = load_models(verbose=verbose)
    img = _open_image(image_path)

    with torch.no_grad():
        p_eff = F.softmax(m['eff'](m['tf_eff'](img).unsqueeze(0)), dim=1)[0]
        p_vit = F.softmax(m['vit'](m['tf_vit'](img).unsqueeze(0)), dim=1)[0]

    proj_eff = _project(p_eff, CANON_EFF)
    proj_vit = _project(p_vit, CANON_VIT)

    # Weighted average. Each model contributes 0 to classes it cannot express,
    # so the result already sums to 1 and needs no renormalisation.
    scores = {
        key: WEIGHT_VIT * proj_vit.get(key, 0.0) + WEIGHT_EFF * proj_eff.get(key, 0.0)
        for key in VOCAB
    }

    # Restrict to one crop when the user picked it from the dropdown, and
    # renormalise inside it so the number reads as P(disease | chosen crop).
    candidates = VOCAB
    sel = canon_crop(selected_crop) if selected_crop else None
    constrained = bool(sel and sel in CROP_TO_CANON)
    if constrained:
        candidates = CROP_TO_CANON[sel]
        total = sum(scores[k] for k in candidates) or 1.0
        ranked = sorted(((scores[k] / total, k) for k in candidates), reverse=True)
    else:
        ranked = sorted(((scores[k], k) for k in candidates), reverse=True)

    best_score, best_key = ranked[0]

    top_vit = max(proj_vit.items(), key=lambda kv: kv[1])[0]
    top_eff = max(proj_eff.items(), key=lambda kv: kv[1])[0]
    # Real agreement: both models independently rank the same class first.
    models_agree = (top_vit == best_key and top_eff == best_key)

    def _model_view(proj, top_key, in_space, weight_label):
        return {
            'crop': display_crop(top_key),
            'disease': display_disease(top_key),
            'confidence': round(proj[top_key] * 100.0, 2),
            'weight': weight_label,
            'knows_final_class': best_key in in_space,
            'score_for_final': round(proj.get(best_key, 0.0) * 100.0, 2),
            'picked_final': top_key == best_key,
        }

    return {
        'canon': best_key,
        'crop': display_crop(best_key),
        'disease': display_disease(best_key),
        'confidence': round(best_score * 100.0, 2),
        'info_key': INFO_KEY.get(best_key),
        'agreement': models_agree,
        'both_know_class': best_key in SHARED,
        'voters': (2 if best_key in SHARED else 1),
        'top3': [
            {
                'crop': display_crop(k),
                'disease': display_disease(k),
                'confidence': round(s * 100.0, 2),
                'is_best': k == best_key,
                'voters': 2 if k in SHARED else 1,
            }
            for s, k in ranked[:3]
        ],
        'models': {
            'vit': _model_view(proj_vit, top_vit, IN_VIT, WEIGHT_VIT),
            'efficientnet': _model_view(proj_eff, top_eff, IN_EFF, WEIGHT_EFF),
        },
    }
