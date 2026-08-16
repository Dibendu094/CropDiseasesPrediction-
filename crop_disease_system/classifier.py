"""
Disease classification using the existing model.

`DiseaseClassifier` wraps model loading, background-removal preprocessing, and
inference into one object. It returns a structured result with the top-3
predictions, confidence percentages, a prediction timestamp, and the image path.
"""

import os
import re
import glob

import cv2
import numpy as np
import torch
import torch.nn.functional as F

from .config import CONFIG
from .model_loader import load_model, load_class_names
from .preprocessing import preprocess_for_model, load_image
from .utils import get_logger, timestamp

log = get_logger()

_IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def parse_class_name(class_name):
    """Split a raw label into a readable (crop, disease) pair.

    Handles `Apple___Apple_scab`, `Corn_(maize)___Common_rust_`,
    `Pepper,_bell___Bacterial_spot`, single-word labels, and CamelCase.
    """
    if "___" in class_name:
        crop_raw, disease_raw = class_name.split("___", 1)
    elif "_" in class_name:
        crop_raw, disease_raw = class_name.split("_", 1)
    else:
        crop_raw, disease_raw = class_name, "Unknown"
    return _prettify(crop_raw), _prettify(disease_raw)


def _prettify(text):
    text = text.replace("_", " ")
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)   # BrownSpot -> Brown Spot
    text = re.sub(r"\s+", " ", text).strip()
    words = []
    for w in text.split(" "):
        if not w:
            continue
        words.append(w if any(c.isupper() for c in w[1:]) else w.capitalize())
    return " ".join(words)


def _confidence_level(score):
    if score >= 90:
        return "High"
    if score >= 70:
        return "Medium"
    return "Low"


class DiseaseClassifier:
    """Load-once, predict-many disease classifier."""

    def __init__(self, model_path=None, class_names_path=None, device=None):
        self.device = device or CONFIG["device"]
        self.class_names = load_class_names(class_names_path)
        self.model = load_model(model_path, self.class_names, self.device)
        mean = torch.tensor(CONFIG["imagenet_mean"]).view(3, 1, 1)
        std = torch.tensor(CONFIG["imagenet_std"]).view(3, 1, 1)
        self._mean = mean.to(self.device)
        self._std = std.to(self.device)

    # ── tensor prep ──
    def _to_tensor(self, image_bgr):
        """BGR uint8 (model input size) -> normalized (1,3,H,W) tensor."""
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        tensor = torch.from_numpy(rgb).permute(2, 0, 1)      # (3,H,W)
        tensor = (tensor.to(self.device) - self._mean) / self._std
        return tensor.unsqueeze(0)

    @torch.no_grad()
    def predict(self, image, apply_bg_removal=True, top_k=None,
                image_path=None):
        """Classify one image and return a structured result dict.

        `image` may be a file path or a BGR numpy array. Background removal is
        applied by default before inference.
        """
        top_k = top_k or CONFIG["top_k"]
        if isinstance(image, str):
            image_path = image_path or image
            image = load_image(image)

        model_input = preprocess_for_model(image, apply_bg_removal=apply_bg_removal)
        tensor = self._to_tensor(model_input)

        logits = self.model(tensor)
        probs = F.softmax(logits, dim=1)[0]
        conf, idx = torch.max(probs, dim=0)
        idx = int(idx.item())
        confidence = round(float(conf.item()) * 100.0, 2)

        predicted_class = self.class_names[idx]
        crop, disease = parse_class_name(predicted_class)

        k = min(top_k, probs.numel())
        top_probs, top_idx = torch.topk(probs, k)
        top_predictions = []
        for p, i in zip(top_probs.tolist(), top_idx.tolist()):
            c, d = parse_class_name(self.class_names[i])
            top_predictions.append({
                "class_name": self.class_names[i],
                "crop": c,
                "disease": d,
                "confidence": round(p * 100.0, 2),
            })

        return {
            "success": True,
            "timestamp": timestamp(),
            "image_path": image_path,
            "background_removed": apply_bg_removal,
            "class_name": predicted_class,
            "crop": crop,
            "disease": disease,
            "confidence": confidence,
            "confidence_level": _confidence_level(confidence),
            "is_healthy": "healthy" in predicted_class.lower(),
            "uncertain": confidence < CONFIG["confidence_threshold"],
            "top_predictions": top_predictions,
        }

    def predict_batch(self, input_dir, apply_bg_removal=True):
        """Classify every image in a directory; returns a list of result dicts."""
        paths = [p for p in glob.glob(os.path.join(input_dir, "*"))
                 if p.lower().endswith(_IMG_EXTS)]
        log.info("Batch inference over %d images in %s", len(paths), input_dir)
        results = []
        for p in paths:
            try:
                results.append(self.predict(p, apply_bg_removal=apply_bg_removal))
            except Exception as exc:  # noqa: BLE001
                log.error("Inference failed on %s: %s", p, exc)
                results.append({"success": False, "image_path": p,
                                "error": str(exc), "timestamp": timestamp()})
        return results
