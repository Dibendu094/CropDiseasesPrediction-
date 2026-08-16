"""
Central configuration for the Crop Disease Detection System.

All paths default to the parent project directory so the package reuses the
existing model checkpoint, class list, and treatment database without copying
anything. Override any value via the `CONFIG` dict or environment variables.
"""

import os

# ── Directories ──
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(PACKAGE_DIR)          # the existing project root
OUTPUT_DIR = os.path.join(PACKAGE_DIR, "outputs")
LOG_DIR = os.path.join(PACKAGE_DIR, "logs")

for _d in (OUTPUT_DIR, LOG_DIR):
    os.makedirs(_d, exist_ok=True)


def _first_existing(*paths):
    """Return the first path that exists, else the first candidate."""
    for p in paths:
        if p and os.path.exists(p):
            return p
    return paths[0]


CONFIG = {
    # ── Existing assets (reused, never modified) ──
    "model_path": _first_existing(
        os.environ.get("CDS_MODEL_PATH"),
        os.path.join(PROJECT_DIR, "best_epoch_4_acc_98.70.pth"),
        os.path.join(PROJECT_DIR, "best_model.pth"),
    ),
    "class_names_path": _first_existing(
        os.environ.get("CDS_CLASS_NAMES"),
        os.path.join(PROJECT_DIR, "class_names.json"),
    ),
    "treatment_db_path": _first_existing(
        os.environ.get("CDS_TREATMENT_DB"),
        os.path.join(PROJECT_DIR, "disease_info.json"),
    ),

    # ── Runtime ──
    "device": os.environ.get("CDS_DEVICE", "cpu"),        # "cpu" or "cuda"
    "model_input_size": 224,                              # timm EfficientNet-B3 input

    # ── Preprocessing / background removal ──
    "target_size": 256,                                   # resize for storage/display
    "gaussian_kernel": 5,                                 # odd; edge smoothing
    "morph_kernel": 5,                                    # close/open structuring element
    "morph_iterations": 2,
    # HSV green-leaf range (H 0-179, S/V 0-255 in OpenCV). Two ranges cover
    # healthy green through yellowed/brown diseased tissue.
    "hsv_lower_green": (25, 30, 30),
    "hsv_upper_green": (95, 255, 255),
    "hsv_lower_brown": (5, 30, 20),      # diseased/senescent yellow-brown
    "hsv_upper_brown": (25, 255, 255),
    "min_contour_area_frac": 0.01,       # ignore contours smaller than 1% of image

    # ── Inference ──
    "top_k": 3,
    "confidence_threshold": 40.0,        # % below which a prediction is "uncertain"

    # ── ImageNet normalization (matches how the model was trained) ──
    "imagenet_mean": (0.485, 0.456, 0.406),
    "imagenet_std": (0.229, 0.224, 0.225),
}
