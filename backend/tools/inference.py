"""
AgriCare AI — Plant disease inference (architecture-agnostic)
=============================================================
Clean, reusable inference helpers for a 42-class PlantVillage-style model.

Highlights
----------
1. `parse_class_name()`   — safely splits a raw label into (crop, disease),
                            handling `___`, single-underscore Rice labels, and
                            multi-word disease names with spaces.
2. `get_transform()`      — Resize 224x224 → Tensor → ImageNet normalization.
3. `predict()`            — runs the model under `.eval()` + `torch.no_grad()`
                            and returns {crop, disease, confidence_score, ...}.
4. Optional crop filter   — if the UI pre-selects a crop, the logits of every
                            other crop are masked to -inf so `argmax` can only
                            choose a disease that belongs to the chosen crop.
                            This is the fix for "wrong crop" predictions.

Usage
-----
    from inference import load_class_names, build_crop_index, get_transform, predict
    import torch

    class_names = load_class_names("class_names.json")
    crop_index  = build_crop_index(class_names)
    model       = load_model("best_model.pth", num_classes=len(class_names))

    # Free prediction (model decides the crop):
    print(predict(model, "leaf.jpg", class_names, crop_index))

    # Forced crop (user picked "Tomato" in the UI):
    print(predict(model, "leaf.jpg", class_names, crop_index, selected_crop="Tomato"))
"""

import re
import json

import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


# ─────────────────────────────────────────────────────────────
# 1. Class-name parsing
# ─────────────────────────────────────────────────────────────
def parse_class_name(class_name):
    """Split a raw class label into a clean (crop, disease) pair.

    Handles every label format in the dataset:
      • Triple underscore : "Apple___Apple_scab"                -> ("Apple", "Apple Scab")
      • Parentheses       : "Corn_(maize)___Common_rust_"       -> ("Corn (Maize)", "Common Rust")
      • Comma in crop     : "Pepper,_bell___Bacterial_spot"     -> ("Pepper, Bell", "Bacterial Spot")
      • Spaces in disease : "...___Cercospora_leaf_spot Gray_leaf_spot"
                                                                -> (..., "Cercospora Leaf Spot Gray Leaf Spot")
      • Single underscore : "Rice_BrownSpot"                    -> ("Rice", "Brown Spot")
      • Single underscore : "Rice_Healthy"                      -> ("Rice", "Healthy")
      • No separator      : "Something"                         -> ("Something", "Unknown")
    """
    if "___" in class_name:
        crop_raw, disease_raw = class_name.split("___", 1)
    elif "_" in class_name:
        # Single-underscore labels (e.g. Rice_BrownSpot): first token is the crop.
        crop_raw, disease_raw = class_name.split("_", 1)
    else:
        crop_raw, disease_raw = class_name, "Unknown"

    crop = _prettify(crop_raw)
    disease = _prettify(disease_raw)
    return crop, disease


def _prettify(text):
    """Turn a raw token like 'Corn_(maize)' or 'BrownSpot' into readable text."""
    # Underscores → spaces (but keep spaces that are already there).
    text = text.replace("_", " ")
    # Split CamelCase (BrownSpot -> Brown Spot); works for the Rice_* labels.
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    # Nicely capitalise the maize/measles tokens inside parentheses too.
    text = re.sub(r"\s+", " ", text).strip()
    # Title-case words but preserve short tokens and existing capitals sensibly.
    words = []
    for w in text.split(" "):
        if not w:
            continue
        # Keep tokens that already contain a capital (e.g. acronyms) as-is,
        # otherwise title-case them.
        words.append(w if any(c.isupper() for c in w[1:]) else w.capitalize())
    return " ".join(words)


def crop_key(class_name):
    """Return a canonical, comparison-friendly crop keyword for a raw label.

    e.g. "Corn_(maize)___..." -> "corn", "Pepper,_bell___..." -> "pepper",
         "Cherry_(including_sour)___..." -> "cherry", "Rice_BrownSpot" -> "rice".
    """
    crop, _ = parse_class_name(class_name)
    return _canon(crop)


def _canon(text):
    """Reduce a crop name to a simple lowercase keyword for matching UI values."""
    t = text.replace("_", " ")
    t = t.split("(")[0]   # drop "(maize)" / "(including sour)"
    t = t.split(",")[0]   # drop ", bell"
    return t.strip().lower()


# ─────────────────────────────────────────────────────────────
# 2. Class list + crop → indices map (for the optional filter)
# ─────────────────────────────────────────────────────────────
def load_class_names(path="class_names.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_crop_index(class_names):
    """Map each canonical crop keyword to the list of class indices it owns.

    { 'apple': [0,1,2,3], 'rice': [24,25,26,27], 'tomato': [...], ... }
    """
    index = {}
    for i, name in enumerate(class_names):
        index.setdefault(crop_key(name), []).append(i)
    return index


# ─────────────────────────────────────────────────────────────
# 3. Preprocessing
# ─────────────────────────────────────────────────────────────
def get_transform():
    """Resize → Tensor → ImageNet normalization (matches training)."""
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


_TRANSFORM = get_transform()


# ─────────────────────────────────────────────────────────────
# 4. Inference
# ─────────────────────────────────────────────────────────────
@torch.no_grad()
def predict(model, image_path, class_names, crop_index=None,
            selected_crop=None, device="cpu", temperature=1.0, topk=3):
    """Run inference on one image and return a structured result.

    Parameters
    ----------
    model         : a loaded nn.Module producing `len(class_names)` logits.
    image_path    : path to the leaf image.
    class_names   : list[str] of the 42 labels (same order as training).
    crop_index    : dict from build_crop_index() (required to use selected_crop).
    selected_crop : optional UI crop (e.g. "Tomato", "Rice", "Corn"). When given,
                    only that crop's classes are considered — this prevents the
                    model from returning a disease from the wrong crop.
    device        : "cpu" or "cuda".
    temperature   : <1.0 sharpens confidence, >1.0 softens it. 1.0 = raw softmax.
    topk          : how many alternative predictions to return.

    Returns
    -------
    dict with: success, crop, disease, class_name, confidence_score,
               confidence_level, is_healthy, crop_filtered, top_k[]
    """
    model.eval()
    model.to(device)

    # ── Preprocess ──
    image = Image.open(image_path).convert("RGB")
    tensor = _TRANSFORM(image).unsqueeze(0).to(device)   # (1, 3, 224, 224)

    # ── Forward pass ──
    logits = model(tensor)                               # (1, num_classes)
    logits = logits / max(temperature, 1e-6)

    # ── Optional crop filtering: mask out other crops' logits ──
    crop_filtered = False
    allowed = None
    if selected_crop and str(selected_crop).strip().lower() not in ("", "other", "unknown"):
        if crop_index is None:
            crop_index = build_crop_index(class_names)
        allowed = crop_index.get(_canon(selected_crop))
        if allowed:
            mask = torch.full_like(logits, float("-inf"))
            mask[0, allowed] = 0.0
            logits = logits + mask        # non-allowed classes become -inf
            crop_filtered = True
        # If the crop isn't in our label set, we silently fall back to the full
        # model output rather than masking everything away.

    # ── Probabilities over the (possibly filtered) logits ──
    probs = F.softmax(logits, dim=1)
    confidence, pred_idx = torch.max(probs, dim=1)
    pred_idx = int(pred_idx.item())
    confidence_score = round(float(confidence.item()) * 100.0, 2)

    predicted_class = class_names[pred_idx]
    crop, disease = parse_class_name(predicted_class)

    # ── Top-k alternatives (within the allowed set if filtered) ──
    k = min(topk, probs.size(1) if allowed is None else len(allowed))
    topk_probs, topk_idx = torch.topk(probs, k, dim=1)
    top_k = []
    for p, idx in zip(topk_probs[0].tolist(), topk_idx[0].tolist()):
        c, d = parse_class_name(class_names[idx])
        top_k.append({
            "class_name": class_names[idx],
            "crop": c,
            "disease": d,
            "confidence_score": round(p * 100.0, 2),
        })

    return {
        "success": True,
        "crop": crop,
        "disease": disease,
        "class_name": predicted_class,
        "confidence_score": confidence_score,
        "confidence_level": _confidence_level(confidence_score),
        "is_healthy": "healthy" in predicted_class.lower(),
        "crop_filtered": crop_filtered,
        "top_k": top_k,
    }


def _confidence_level(score):
    if score >= 90:
        return "High"
    if score >= 70:
        return "Medium"
    return "Low"


# ─────────────────────────────────────────────────────────────
# 5. Model loading (MobileNetV3 example — swap for your architecture)
# ─────────────────────────────────────────────────────────────
def load_model(weights_path, num_classes, arch="mobilenet_v3_large", device="cpu"):
    """Build the architecture, load weights, and return an eval-ready model.

    Supports a plain state_dict OR a fully-pickled model object. Adjust `arch`
    to match how you trained (this repo's own best_model.pth is efficientnet_b0).
    """
    from torchvision import models

    state = torch.load(weights_path, map_location=device, weights_only=False)
    if hasattr(state, "state_dict"):        # a full model object was saved
        state = state.state_dict()

    if arch == "mobilenet_v3_large":
        model = models.mobilenet_v3_large(weights=None)
        in_features = model.classifier[3].in_features
        model.classifier[3] = torch.nn.Linear(in_features, num_classes)
    elif arch == "mobilenet_v3_small":
        model = models.mobilenet_v3_small(weights=None)
        in_features = model.classifier[3].in_features
        model.classifier[3] = torch.nn.Linear(in_features, num_classes)
    elif arch == "efficientnet_b0":
        model = models.efficientnet_b0(weights=None)
        in_features = model.classifier[1].in_features
        model.classifier[1] = torch.nn.Linear(in_features, num_classes)
    else:
        raise ValueError(f"Unsupported arch: {arch}")

    model.load_state_dict(state)
    model.eval()
    model.to(device)
    return model


# ─────────────────────────────────────────────────────────────
# Quick self-test
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    names = load_class_names("class_names.json")
    idx = build_crop_index(names)

    # Parsing sanity check across all label shapes.
    for sample in ["Apple___Apple_scab", "Rice_BrownSpot", "Rice_Healthy",
                   "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
                   "Pepper,_bell___Bacterial_spot",
                   "Tomato___Tomato_Yellow_Leaf_Curl_Virus"]:
        print(f"{sample:55s} -> {parse_class_name(sample)}")

    print("\nCrops discovered:", sorted(idx.keys()))
    print("Tomato class indices:", idx.get("tomato"))
