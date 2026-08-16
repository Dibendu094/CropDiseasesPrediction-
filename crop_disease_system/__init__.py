"""
Crop Disease Detection System (with Background Removal)
=======================================================
A self-contained package that reuses the project's existing trained
timm EfficientNet-B3 checkpoint and treatment database to:

  * remove image backgrounds (HSV + morphology + contours),
  * classify crop-leaf diseases (top-3 + confidence),
  * recommend organic / chemical treatments (severity-aware),
  * run real-time webcam detection with a CSV log,
  * evaluate a test set (precision/recall/F1, confusion matrix, ROC-AUC),
  * and export results to JSON / CSV.

Public entry points are re-exported here for convenience.
"""

from .config import CONFIG
from .preprocessing import (
    remove_background,
    preprocess_for_model,
    visualize_before_after,
    batch_remove_background,
)
from .model_loader import load_model, load_class_names
from .classifier import DiseaseClassifier
from .treatment import TreatmentAdvisor
from .utils import get_logger, export_json, export_csv

__all__ = [
    "CONFIG",
    "remove_background",
    "preprocess_for_model",
    "visualize_before_after",
    "batch_remove_background",
    "load_model",
    "load_class_names",
    "DiseaseClassifier",
    "TreatmentAdvisor",
    "get_logger",
    "export_json",
    "export_csv",
]

__version__ = "1.0.0"
