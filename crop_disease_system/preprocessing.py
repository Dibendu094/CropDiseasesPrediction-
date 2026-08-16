"""
Data preprocessing + HSV background removal.

Pipeline
--------
1. Load image (JPG/PNG) as BGR.
2. Gaussian blur for edge smoothing.
3. HSV threshold to isolate leaf-coloured pixels (green + yellow/brown).
4. Morphological CLOSE then OPEN to fill holes and drop speckle.
5. Keep the largest contour(s) -> a clean leaf mask.
6. Composite the leaf onto a white background.
7. Resize / normalize for storage (256) or for the model (224).

Everything works on numpy BGR arrays (OpenCV convention) so it plugs straight
into the classifier and the webcam loop.
"""

import os
import glob

import cv2
import numpy as np

from .config import CONFIG
from .utils import get_logger

log = get_logger()

_IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def load_image(path):
    """Load an image file as a BGR numpy array. Raises on failure."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image not found: {path}")
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not decode image (unsupported/corrupt): {path}")
    return image


def _leaf_mask(image_bgr):
    """Build a binary leaf mask via HSV thresholding + morphology + contours."""
    cfg = CONFIG
    k = cfg["gaussian_kernel"]
    blurred = cv2.GaussianBlur(image_bgr, (k, k), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    # Two colour bands: healthy green and diseased yellow/brown tissue.
    green = cv2.inRange(hsv, np.array(cfg["hsv_lower_green"]),
                        np.array(cfg["hsv_upper_green"]))
    brown = cv2.inRange(hsv, np.array(cfg["hsv_lower_brown"]),
                        np.array(cfg["hsv_upper_brown"]))
    mask = cv2.bitwise_or(green, brown)

    # Morphology: CLOSE fills interior gaps, OPEN removes background speckle.
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (cfg["morph_kernel"], cfg["morph_kernel"]))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel,
                            iterations=cfg["morph_iterations"])
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel,
                            iterations=cfg["morph_iterations"])

    # Contour selection: keep only sufficiently large blobs (the leaf).
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    clean = np.zeros_like(mask)
    if contours:
        img_area = image_bgr.shape[0] * image_bgr.shape[1]
        min_area = cfg["min_contour_area_frac"] * img_area
        kept = [c for c in contours if cv2.contourArea(c) >= min_area]
        if not kept:  # nothing passed the threshold -> keep the single largest
            kept = [max(contours, key=cv2.contourArea)]
        cv2.drawContours(clean, kept, -1, 255, thickness=cv2.FILLED)
        mask = clean

    # Feather the edge slightly so the composite isn't jagged.
    mask = cv2.GaussianBlur(mask, (k, k), 0)
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    return mask


def remove_background(image, white_background=True, return_mask=False):
    """Remove the background from a leaf image.

    Parameters
    ----------
    image : str path or BGR numpy array.
    white_background : composite the leaf onto white (True) or black (False).
    return_mask : also return the binary mask.

    Returns
    -------
    result_bgr  (and mask if return_mask=True)
    """
    if isinstance(image, str):
        image = load_image(image)

    mask = _leaf_mask(image)
    coverage = float((mask > 0).mean())

    # Fallback: if the mask captured almost nothing (odd lighting / non-leaf),
    # return the original so we never feed an all-white frame to the model.
    if coverage < 0.02:
        log.warning("Leaf mask covered only %.1f%% of the image; "
                    "returning original (background not removed).", coverage * 100)
        result = image.copy()
    else:
        bg_value = 255 if white_background else 0
        background = np.full_like(image, bg_value)
        mask3 = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR).astype(bool)
        result = np.where(mask3, image, background)

    if return_mask:
        return result, mask
    return result


def resize_normalize(image_bgr, size=None):
    """Resize to a square `size` and return float32 in [0, 1]."""
    size = size or CONFIG["target_size"]
    resized = cv2.resize(image_bgr, (size, size), interpolation=cv2.INTER_AREA)
    return resized.astype(np.float32) / 255.0


def preprocess_for_model(image, apply_bg_removal=True):
    """Full path from raw image to a normalized tensor-ready BGR array (224).

    Returns a BGR uint8 image at the model's input size (background removed by
    default). The classifier converts this to a normalized torch tensor.
    """
    if isinstance(image, str):
        image = load_image(image)
    processed = remove_background(image) if apply_bg_removal else image
    size = CONFIG["model_input_size"]
    return cv2.resize(processed, (size, size), interpolation=cv2.INTER_AREA)


# ─────────────────────────────────────────────────────────────
# Batch processing
# ─────────────────────────────────────────────────────────────
def batch_remove_background(input_dir, output_dir, white_background=True):
    """Run background removal over every image in a directory.

    Returns a list of {input, output, success, error} records.
    """
    os.makedirs(output_dir, exist_ok=True)
    paths = [p for p in glob.glob(os.path.join(input_dir, "*"))
             if p.lower().endswith(_IMG_EXTS)]
    log.info("Batch background removal: %d images from %s", len(paths), input_dir)

    records = []
    for p in paths:
        rec = {"input": p, "output": None, "success": False, "error": None}
        try:
            result = remove_background(p, white_background=white_background)
            out_path = os.path.join(output_dir, os.path.basename(p))
            cv2.imwrite(out_path, result)
            rec.update(output=out_path, success=True)
        except Exception as exc:  # noqa: BLE001 — report per-file, keep going
            rec["error"] = str(exc)
            log.error("Failed on %s: %s", p, exc)
        records.append(rec)
    ok = sum(r["success"] for r in records)
    log.info("Batch complete: %d/%d succeeded.", ok, len(records))
    return records


# ─────────────────────────────────────────────────────────────
# Visualization
# ─────────────────────────────────────────────────────────────
def visualize_before_after(image, save_path=None, white_background=True):
    """Show original | mask | background-removed side by side."""
    import matplotlib.pyplot as plt

    if isinstance(image, str):
        title = os.path.basename(image)
        image = load_image(image)
    else:
        title = "image"

    result, mask = remove_background(
        image, white_background=white_background, return_mask=True)

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    axes[0].imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    axes[0].set_title(f"Original\n{title}")
    axes[1].imshow(mask, cmap="gray")
    axes[1].set_title("Leaf Mask (HSV + morphology)")
    axes[2].imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
    axes[2].set_title("Background Removed")
    for ax in axes:
        ax.axis("off")
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=120, bbox_inches="tight")
        log.info("Saved before/after -> %s", save_path)
    plt.show()
    plt.close()
    return result
