# Crop Disease Detection System (with Background Removal)

A self-contained Python package that reuses this project's **existing** trained
model and treatment database. No training is performed — it loads the shipped
timm **EfficientNet-B3** checkpoint (`best_epoch_4_acc_98.70.pth`, 91 classes),
removes image backgrounds, classifies leaf disease, and recommends treatment.

## Folder structure

```
crop_disease_system/
├── __init__.py          # package exports
├── config.py            # paths (point at the parent project), thresholds, HSV ranges
├── preprocessing.py     # HSV background removal, morphology, contours, batch, visualize
├── model_loader.py      # loads the EXISTING checkpoint (.pth/.pt/.pkl), validates it
├── classifier.py        # DiseaseClassifier: inference, top-3, timestamp, image path
├── treatment.py         # TreatmentAdvisor: organic/chemical, severity, farmer steps
├── realtime.py          # webcam loop: FPS, overlay, CSV log, confidence threshold
├── evaluation.py        # precision/recall/F1, confusion matrix, ROC-AUC, bg-removal impact
├── utils.py             # logging, matplotlib visualization, JSON/CSV export
├── main.py              # command-line entry point
├── requirements.txt
├── outputs/             # generated results (created on first run)
└── logs/                # system.log
```

## Install

```bash
pip install -r crop_disease_system/requirements.txt
```

The package expects these files in the **parent** project directory (already
present here): `best_epoch_4_acc_98.70.pth`, `class_names.json`,
`disease_info.json`. Override any path via environment variables
(`CDS_MODEL_PATH`, `CDS_CLASS_NAMES`, `CDS_TREATMENT_DB`, `CDS_DEVICE`).

## Command-line usage

```bash
# Background removal on one image (add --show for a before/after figure)
python -m crop_disease_system.main bgremove path/to/leaf.jpg --show

# Batch background removal: raw folder -> clean folder
python -m crop_disease_system.main bgremove-batch ./raw ./clean

# Detect disease + treatment recommendation for one image
python -m crop_disease_system.main detect path/to/leaf.jpg

# Batch detect a folder (exports outputs/detect_batch.json and .csv)
python -m crop_disease_system.main detect-batch ./images

# Real-time webcam detection (q=quit, b=toggle background removal)
python -m crop_disease_system.main webcam --threshold 50

# Evaluate a class-per-folder test set
python -m crop_disease_system.main evaluate ./test

# Compare accuracy WITH vs WITHOUT background removal
python -m crop_disease_system.main compare ./test
```

## Python API

```python
from crop_disease_system import DiseaseClassifier, TreatmentAdvisor
from crop_disease_system.preprocessing import remove_background, visualize_before_after

clf = DiseaseClassifier()          # loads the existing model once
advisor = TreatmentAdvisor()       # loads disease_info.json

result = advisor.detect_and_recommend(clf, "leaf.jpg")
print(result["crop"], result["disease"], result["confidence"])
for step in result["recommendation"]["farmer_instructions"]:
    print("•", step)

visualize_before_after("leaf.jpg")  # original | mask | background removed
```

## Evaluation test-set layout

```
test/
├── Apple___Apple_scab/   img1.jpg ...
├── Tomato___healthy/     imgA.jpg ...
└── ...                   (folder names must match class_names.json)
```

`evaluate` writes a JSON classification report, a confusion-matrix PNG, and a
ROC-AUC PNG to `outputs/`. `compare` runs the whole thing twice (with and
without background removal) and reports the accuracy delta.

## Notes

- **Severity** is estimated from model confidence as a rough proxy, not a
  measured infection level — the output labels it as an estimate.
- Background removal falls back to the original image when the HSV mask captures
  almost no leaf pixels, so the model is never fed a blank frame.
- Single-word labels without a crop separator (e.g. `Brown Spot`) parse with
  disease `Unknown`, matching the existing project's `inference.py` behaviour.
```
