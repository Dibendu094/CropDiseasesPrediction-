"""
predict.py — Robust inference pipeline for the 42-class Plant Disease model
=============================================================================
Standalone, copy-paste-ready module. Works with MobileNetV3 (the architecture
you're training) or any other torchvision classifier that outputs 42 logits
for a 224x224 RGB input — swap the `arch` argument in `load_model()`.

Covers:
  1. parse_label()      — safe crop/disease parsing for every label format
                           in class_names.json (___, single "_", spaces).
  2. get_transform()     — PIL RGB → Resize(224,224) → Tensor → ImageNet norm.
  3. model.eval() + torch.no_grad() enforced inside predict().
  4. selected_crop filter — masks out every other crop's logits so argmax can
                           only land inside the chosen crop.
  5. confidence threshold — max probability < 50% => "Unsure / Low Confidence
                           Prediction" instead of a (possibly wrong) disease.

Quick start
-----------
    from predict import load_class_names, build_crop_index, load_model, predict

    class_names = load_class_names("class_names.json")
    crop_index  = build_crop_index(class_names)
    model       = load_model("best_model.pth", num_classes=len(class_names),
                              arch="mobilenet_v3_large")

    result = predict(model, "leaf.jpg", class_names, crop_index,
                      selected_crop="Raspberry")
    print(result)
"""

import re
import json

import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
CONFIDENCE_THRESHOLD = 50.0   # percent — below this => Unsure / Low Confidence
UNSURE_LABEL = "Unsure / Low Confidence Prediction"


# ─────────────────────────────────────────────────────────────
# 1. Safe label parsing
# ─────────────────────────────────────────────────────────────
def parse_label(label):
    """Safely split a raw class label into (crop, disease).

    Handles every shape found in class_names.json:
      "Apple___Apple_scab"                              -> ("Apple", "Apple Scab")
      "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot"
                                                          -> ("Corn (maize)", "Cercospora Leaf Spot Gray Leaf Spot")
      "Pepper,_bell___Bacterial_spot"                    -> ("Pepper, Bell", "Bacterial Spot")
      "Rice_BrownSpot"                                   -> ("Rice", "Brown Spot")   # single underscore
      "Rice_Healthy"                                     -> ("Rice", "Healthy")
      "SomethingWithNoSeparator"                          -> ("SomethingWithNoSeparator", "Unknown")
    """
    if not isinstance(label, str) or not label.strip():
        return "Unknown", "Unknown"

    if "___" in label:
        crop_raw, disease_raw = label.split("___", 1)
    elif "_" in label:
        # Single-underscore labels (Rice_BrownSpot, Rice_Healthy, Rice_Hispa, ...):
        # the first token is always the crop.
        crop_raw, disease_raw = label.split("_", 1)
    else:
        crop_raw, disease_raw = label, "Unknown"

    return _tidy(crop_raw), _tidy(disease_raw)


def _tidy(token):
    """Underscores -> spaces, split CamelCase, collapse whitespace, title-case."""
    text = token.replace("_", " ")
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)      # BrownSpot -> Brown Spot
    text = re.sub(r"\s+", " ", text).strip()
    words = [w if any(c.isupper() for c in w[1:]) else w.capitalize()
             for w in text.split(" ") if w]
    return " ".join(words)


def _canon_crop(text):
    """Reduce a crop name / UI value to a simple lowercase matching key,
    e.g. 'Corn (maize)' -> 'corn', 'Pepper, Bell' -> 'pepper'."""
    t = str(text or "").replace("_", " ")
    t = t.split("(")[0].split(",")[0]
    return t.strip().lower()


# ─────────────────────────────────────────────────────────────
# 2. Preprocessing
# ─────────────────────────────────────────────────────────────
def get_transform():
    """Resize(224,224) -> ToTensor -> ImageNet Normalize (matches training)."""
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


_TRANSFORM = get_transform()


def load_class_names(path="class_names.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_crop_index(class_names):
    """{'apple': [0,1,2,3], 'rice': [24,25,26,27], ...} — class indices per crop."""
    index = {}
    for i, label in enumerate(class_names):
        crop, _ = parse_label(label)
        index.setdefault(_canon_crop(crop), []).append(i)
    return index


# ─────────────────────────────────────────────────────────────
# 3 & 4 & 5. Inference: eval + no_grad + crop filter + confidence threshold
# ─────────────────────────────────────────────────────────────
@torch.no_grad()
def predict(model, image_path, class_names, crop_index=None,
            selected_crop=None, device="cpu",
            confidence_threshold=CONFIDENCE_THRESHOLD,
            min_crop_mass_pct=10.0, topk=3):
    """Run one image through the model and return a structured result dict.

    Parameters
    ----------
    model                : nn.Module producing len(class_names) logits.
    image_path            : path to the leaf photo.
    class_names           : list[str], SAME ORDER the model was trained on.
    crop_index            : output of build_crop_index() (built automatically
                             if omitted, but pass it in once and reuse it).
    selected_crop          : optional UI value, e.g. "Tomato", "Raspberry".
                             When given and recognised, the model's logits for
                             every OTHER crop are masked to -inf, so it can
                             ONLY choose a class belonging to this crop.
                             If not passed / not recognised -> normal argmax
                             over all 42 classes.
    confidence_threshold   : percent; below this (after any masking) the
                             result becomes "Unsure".
    min_crop_mass_pct      : percent; IMPORTANT GUARD (see note below). Set to
                             None / 0 to disable and match a plain post-mask
                             threshold exactly.
    topk                   : number of alternate predictions to report.

    Why min_crop_mass_pct matters
    ------------------------------
    Masking logits down to only the selected crop's classes and then checking
    the POST-mask confidence is not enough on its own. softmax over a single
    remaining class always outputs 100% — mathematically, not because the
    image actually matches. Crops with just one class in this dataset
    (Raspberry, Blueberry, Soybean — "___healthy" only, no disease class)
    trigger this exactly: a diseased Raspberry leaf gets masked down to
    "Raspberry___healthy" and reports 100% confidence no matter what the leaf
    actually shows.
    `min_crop_mass_pct` fixes this by checking, BEFORE masking, how much of the
    model's raw probability the selected crop holds in total. If a diseased
    Raspberry leaf's true best match is "Grape___Esca" at 97%, Raspberry's raw
    share is ~0% — far below the floor — so the result is flagged "Unsure"
    instead of falsely reporting "Raspberry — Healthy" at 100%.

    Returns
    -------
    {
        "crop": str,
        "disease": str,
        "confidence_score": float,      # 0-100
        "is_unsure": bool,
        "unsure_reason": str | None,    # "low_confidence" | "crop_mismatch" | None
        "crop_filtered": bool,          # True if selected_crop was applied
        "class_name": str | None,       # None when unsure
        "top_k": [ {class_name, crop, disease, confidence_score}, ... ]
    }
    """
    model.eval()
    model.to(device)

    if crop_index is None:
        crop_index = build_crop_index(class_names)

    # ── Preprocess ──
    image = Image.open(image_path).convert("RGB")
    input_tensor = _TRANSFORM(image).unsqueeze(0).to(device)

    # ── Forward pass (eval mode + no_grad already enforced) ──
    logits = model(input_tensor)   # (1, num_classes)
    raw_probs = F.softmax(logits, dim=1)   # un-masked — needed for the mass check

    # ── Optional crop filter: mask out every class NOT in the selected crop ──
    crop_filtered = False
    allowed = None
    if selected_crop:
        key = _canon_crop(selected_crop)
        allowed = crop_index.get(key)
        if allowed:
            # Raw share of probability the model puts on this crop BEFORE masking.
            allowed_idx = torch.tensor(allowed, dtype=torch.long)
            crop_mass_pct = float(raw_probs[0, allowed_idx].sum().item()) * 100.0

            if min_crop_mass_pct and crop_mass_pct < min_crop_mass_pct:
                best_idx = int(torch.argmax(raw_probs, dim=1).item())
                best_crop, _ = parse_label(class_names[best_idx])
                return {
                    "crop": _tidy(selected_crop),
                    "disease": UNSURE_LABEL,
                    "confidence_score": round(crop_mass_pct, 2),
                    "is_unsure": True,
                    "unsure_reason": "crop_mismatch",
                    "crop_filtered": True,
                    "class_name": None,
                    "top_k": [],
                    "note": (f"This leaf doesn't look like {selected_crop}; the model's "
                            f"best guess overall is {best_crop}."),
                }

            mask = torch.full_like(logits, float("-inf"))
            mask[0, allowed] = 0.0
            logits = logits + mask
            crop_filtered = True
        # If the selected crop isn't recognised, fall through to plain argmax
        # over the full, unmasked logits (documented fallback behaviour).

    probs = F.softmax(logits, dim=1)
    confidence, pred_idx = torch.max(probs, dim=1)
    confidence_score = round(float(confidence.item()) * 100.0, 2)
    pred_idx = int(pred_idx.item())
    predicted_label = class_names[pred_idx]

    # ── Top-k alternatives (within the allowed set if filtered) ──
    k = min(topk, probs.size(1) if not allowed else len(allowed))
    topk_probs, topk_idx = torch.topk(probs, k, dim=1)
    top_k = []
    for p, idx in zip(topk_probs[0].tolist(), topk_idx[0].tolist()):
        c, d = parse_label(class_names[idx])
        top_k.append({
            "class_name": class_names[idx],
            "crop": c,
            "disease": d,
            "confidence_score": round(p * 100.0, 2),
        })

    # ── Confidence threshold: below this, don't report a (possibly wrong) disease ──
    if confidence_score < confidence_threshold:
        crop, _ = parse_label(predicted_label)
        return {
            "crop": crop,
            "disease": UNSURE_LABEL,
            "confidence_score": confidence_score,
            "is_unsure": True,
            "unsure_reason": "low_confidence",
            "crop_filtered": crop_filtered,
            "class_name": None,
            "top_k": top_k,
        }

    crop, disease = parse_label(predicted_label)
    return {
        "crop": crop,
        "disease": disease,
        "confidence_score": confidence_score,
        "is_unsure": False,
        "unsure_reason": None,
        "crop_filtered": crop_filtered,
        "class_name": predicted_label,
        "top_k": top_k,
    }


# ─────────────────────────────────────────────────────────────
# Model loading — MobileNetV3 by default; a couple of common alternates too
# ─────────────────────────────────────────────────────────────
def load_model(weights_path, num_classes, arch="mobilenet_v3_large", device="cpu"):
    """Build the architecture, load your trained weights, return an eval-ready model."""
    from torchvision import models

    state = torch.load(weights_path, map_location=device, weights_only=False)
    if hasattr(state, "state_dict"):     # a full model object was saved, not a state_dict
        state = state.state_dict()

    if arch == "mobilenet_v3_large":
        model = models.mobilenet_v3_large(weights=None)
        model.classifier[3] = torch.nn.Linear(model.classifier[3].in_features, num_classes)
    elif arch == "mobilenet_v3_small":
        model = models.mobilenet_v3_small(weights=None)
        model.classifier[3] = torch.nn.Linear(model.classifier[3].in_features, num_classes)
    elif arch == "efficientnet_b0":
        model = models.efficientnet_b0(weights=None)
        model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, num_classes)
    else:
        raise ValueError(f"Unsupported arch: {arch!r}")

    model.load_state_dict(state)
    model.eval()
    model.to(device)
    return model


# ─────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    samples = [
        "Apple___Apple_scab",
        "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
        "Pepper,_bell___Bacterial_spot",
        "Rice_BrownSpot",
        "Rice_Healthy",
        "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    ]
    print("parse_label() checks:")
    for s in samples:
        print(f"  {s:55s} -> {parse_label(s)}")

    class_names = load_class_names("class_names.json")
    crop_index = build_crop_index(class_names)
    print("\nCrops discovered:", sorted(crop_index.keys()))
    print("Raspberry class indices:", crop_index.get("raspberry"),
          "(only 'healthy' exists — no disease class for this crop)")
