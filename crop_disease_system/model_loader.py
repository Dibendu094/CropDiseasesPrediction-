"""
Load the project's EXISTING trained checkpoint.

The active checkpoint (`best_epoch_4_acc_98.70.pth`) is a timm EfficientNet-B3
training checkpoint with 91 output classes and a 1536-wide classifier. The
loader below is robust: it unwraps full-model objects, training checkpoints
(weights nested under "model_state_dict"), and plain state_dicts, then
auto-detects the EfficientNet variant from the classifier width.
"""

import json

import torch

from .config import CONFIG
from .utils import get_logger

log = get_logger()

# classifier in_features -> timm architecture
_ARCH_BY_FEAT = {
    1280: "efficientnet_b0",
    1408: "efficientnet_b2",
    1536: "efficientnet_b3",
    1792: "efficientnet_b4",
}


def load_class_names(path=None):
    """Load the ordered list of class labels used at training time."""
    path = path or CONFIG["class_names_path"]
    with open(path, "r", encoding="utf-8") as f:
        names = json.load(f)
    log.info("Loaded %d class names from %s", len(names), path)
    return names


def _extract_state_dict(ckpt):
    """Unwrap whatever torch.load returned into a flat state_dict."""
    if hasattr(ckpt, "state_dict"):          # a full model object was pickled
        return ckpt.state_dict()
    if isinstance(ckpt, dict):
        for key in ("model_state_dict", "state_dict", "model", "net"):
            if key in ckpt and isinstance(ckpt[key], dict):
                return ckpt[key]
    return ckpt


def validate_model(model, num_classes, device):
    """Sanity-check the model with a dummy forward pass before real inference."""
    model.eval()
    with torch.no_grad():
        dummy = torch.zeros(1, 3, CONFIG["model_input_size"],
                            CONFIG["model_input_size"], device=device)
        out = model(dummy)
    if out.shape[-1] != num_classes:
        raise RuntimeError(
            f"Model output width {out.shape[-1]} != {num_classes} classes.")
    log.info("Model validation OK (output shape %s).", tuple(out.shape))
    return True


def load_model(model_path=None, class_names=None, device=None):
    """Build the architecture, load existing weights, and return an eval model.

    Supports .pth / .pt checkpoints (torchvision or timm EfficientNet). For
    .pkl-pickled full model objects, torch.load restores the object directly.
    """
    model_path = model_path or CONFIG["model_path"]
    device = device or CONFIG["device"]
    class_names = class_names or load_class_names()
    num_classes = len(class_names)

    log.info("Loading model: %s (device=%s)", model_path, device)
    ckpt = torch.load(model_path, map_location=torch.device(device),
                      weights_only=False)

    # A fully-pickled model object: use it as-is (still validate below).
    if hasattr(ckpt, "eval") and not isinstance(ckpt, dict):
        model = ckpt.to(device)
        model.eval()
        validate_model(model, num_classes, device)
        return model

    state_dict = _extract_state_dict(ckpt)
    state_dict = {k.replace("module.", "", 1): v for k, v in state_dict.items()}

    # Warn (don't crash) on a class-count mismatch.
    ckpt_classes = None
    for key in ("classifier.weight", "classifier.1.weight", "fc.weight"):
        w = state_dict.get(key)
        if hasattr(w, "shape"):
            ckpt_classes = w.shape[0]
            break
    if ckpt_classes is not None and ckpt_classes != num_classes:
        log.warning("Checkpoint has %d classes but class list has %d — "
                    "labels may be misaligned.", ckpt_classes, num_classes)

    from torchvision import models

    if any(k.startswith("features.") for k in state_dict):
        # torchvision-trained EfficientNet-B0 (legacy path)
        model = models.efficientnet_b0(weights=None)
        model.classifier[1] = torch.nn.Linear(
            model.classifier[1].in_features, num_classes)
        model.load_state_dict(state_dict)
        arch = "torchvision efficientnet_b0"
    else:
        # timm-trained EfficientNet — pick the variant by classifier width.
        import timm
        in_feat = 1536
        w = state_dict.get("classifier.weight")
        if hasattr(w, "shape"):
            in_feat = w.shape[1]
        arch = _ARCH_BY_FEAT.get(in_feat, "efficientnet_b3")
        model = timm.create_model(arch, pretrained=False, num_classes=num_classes)
        model.load_state_dict(state_dict)
        arch = f"timm {arch} (in_features={in_feat})"

    model.to(device)
    model.eval()
    log.info("Architecture: %s", arch)
    validate_model(model, num_classes, device)
    return model
