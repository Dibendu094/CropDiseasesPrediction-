"""
Utility functions: logging, visualization, and JSON/CSV export.
"""

import os
import csv
import json
import logging
from datetime import datetime

import numpy as np

from .config import CONFIG, LOG_DIR

_LOGGERS = {}


def get_logger(name="crop_disease_system"):
    """Return a configured logger that writes to both console and a file."""
    if name in _LOGGERS:
        return _LOGGERS[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        stream = logging.StreamHandler()
        stream.setFormatter(fmt)
        logger.addHandler(stream)

        file_path = os.path.join(LOG_DIR, "system.log")
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    _LOGGERS[name] = logger
    return logger


log = get_logger()


# ─────────────────────────────────────────────────────────────
# Serialization helpers
# ─────────────────────────────────────────────────────────────
def _json_safe(obj):
    """Recursively convert numpy types so json.dump won't choke."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def export_json(data, path):
    """Write `data` to `path` as pretty UTF-8 JSON."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_json_safe(data), f, indent=2, ensure_ascii=False)
    log.info("Exported JSON -> %s", path)
    return path


def export_csv(rows, path, fieldnames=None):
    """Write a list of dicts to CSV. Infers columns from the first row."""
    if not rows:
        log.warning("export_csv called with no rows; nothing written.")
        return None
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fieldnames = fieldnames or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    log.info("Exported CSV (%d rows) -> %s", len(rows), path)
    return path


def append_csv_row(row, path, fieldnames):
    """Append a single dict as a CSV row, writing a header if the file is new."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    new_file = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def timestamp():
    """Human-readable timestamp for logs and output records."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────────────────────────────────────────
# Visualization
# ─────────────────────────────────────────────────────────────
def show_image(image_bgr, title="Image", save_path=None):
    """Display a single BGR image with matplotlib (converts to RGB)."""
    import cv2
    import matplotlib.pyplot as plt

    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    plt.figure(figsize=(5, 5))
    plt.imshow(rgb)
    plt.title(title)
    plt.axis("off")
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=120, bbox_inches="tight")
        log.info("Saved figure -> %s", save_path)
    plt.show()
    plt.close()


def grid_images(images_bgr, titles=None, save_path=None, cols=3):
    """Display several BGR images in a grid."""
    import cv2
    import matplotlib.pyplot as plt

    n = len(images_bgr)
    cols = min(cols, n)
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 4 * rows))
    axes = np.atleast_1d(axes).ravel()
    for i, ax in enumerate(axes):
        if i < n:
            ax.imshow(cv2.cvtColor(images_bgr[i], cv2.COLOR_BGR2RGB))
            if titles:
                ax.set_title(titles[i])
        ax.axis("off")
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=120, bbox_inches="tight")
        log.info("Saved figure -> %s", save_path)
    plt.show()
    plt.close()
