"""
Evaluation metrics + background-removal impact analysis.

Expects a test directory organized one sub-folder per class:

    test_dir/
        Apple___Apple_scab/   img1.jpg ...
        Tomato___healthy/     imgA.jpg ...

Folder names must match entries in class_names.json. Produces per-class
precision/recall/F1, a confusion matrix, ROC-AUC curves, and a side-by-side
comparison of accuracy with vs. without background removal.
"""

import os
import glob

import numpy as np

from .config import CONFIG, OUTPUT_DIR
from .classifier import DiseaseClassifier
from .utils import get_logger, export_json

log = get_logger()

_IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def _gather_samples(test_dir, class_names):
    """Collect (image_path, true_index) pairs from a class-per-folder layout."""
    name_to_idx = {n: i for i, n in enumerate(class_names)}
    samples = []
    skipped = set()
    for folder in sorted(os.listdir(test_dir)):
        fpath = os.path.join(test_dir, folder)
        if not os.path.isdir(fpath):
            continue
        if folder not in name_to_idx:
            skipped.add(folder)
            continue
        for p in glob.glob(os.path.join(fpath, "*")):
            if p.lower().endswith(_IMG_EXTS):
                samples.append((p, name_to_idx[folder]))
    if skipped:
        log.warning("Skipped %d folders not in class_names: %s",
                    len(skipped), sorted(skipped)[:10])
    log.info("Collected %d test samples across %d classes.",
             len(samples), len({s[1] for s in samples}))
    return samples


def _predict_indices(classifier, samples, apply_bg_removal):
    """Return (y_true, y_pred, y_scores) arrays over all samples."""
    n_classes = len(classifier.class_names)
    y_true, y_pred, y_scores = [], [], []
    for path, true_idx in samples:
        try:
            import cv2
            import torch
            import torch.nn.functional as F
            from .preprocessing import preprocess_for_model

            model_input = preprocess_for_model(path, apply_bg_removal=apply_bg_removal)
            tensor = classifier._to_tensor(model_input)
            with torch.no_grad():
                probs = F.softmax(classifier.model(tensor), dim=1)[0].cpu().numpy()
            y_true.append(true_idx)
            y_pred.append(int(probs.argmax()))
            y_scores.append(probs)
        except Exception as exc:  # noqa: BLE001
            log.error("Eval inference failed on %s: %s", path, exc)
    return np.array(y_true), np.array(y_pred), np.array(y_scores)


def evaluate(test_dir, classifier=None, apply_bg_removal=True,
             save_prefix="eval"):
    """Full evaluation: classification report, confusion matrix, ROC-AUC."""
    from sklearn.metrics import (classification_report, confusion_matrix,
                                 accuracy_score)

    classifier = classifier or DiseaseClassifier()
    samples = _gather_samples(test_dir, classifier.class_names)
    if not samples:
        raise RuntimeError(f"No test samples found under {test_dir}")

    y_true, y_pred, y_scores = _predict_indices(classifier, samples, apply_bg_removal)
    present = sorted(set(y_true.tolist()) | set(y_pred.tolist()))
    target_names = [classifier.class_names[i] for i in present]

    report = classification_report(
        y_true, y_pred, labels=present, target_names=target_names,
        output_dict=True, zero_division=0)
    accuracy = accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred, labels=present)

    log.info("Accuracy (%s bg-removal): %.4f",
             "with" if apply_bg_removal else "without", accuracy)

    # Save artifacts.
    cm_path = os.path.join(OUTPUT_DIR, f"{save_prefix}_confusion_matrix.png")
    _plot_confusion_matrix(cm, target_names, cm_path)

    roc_path = os.path.join(OUTPUT_DIR, f"{save_prefix}_roc_auc.png")
    macro_auc = _plot_roc_auc(y_true, y_scores, present, target_names, roc_path)

    report_path = export_json(
        {"accuracy": accuracy, "macro_roc_auc": macro_auc,
         "background_removed": apply_bg_removal, "report": report},
        os.path.join(OUTPUT_DIR, f"{save_prefix}_report.json"))

    return {
        "accuracy": accuracy,
        "macro_roc_auc": macro_auc,
        "report": report,
        "confusion_matrix_path": cm_path,
        "roc_auc_path": roc_path,
        "report_path": report_path,
        "n_samples": len(samples),
    }


def compare_background_removal(test_dir, classifier=None, save_prefix="compare"):
    """Run evaluation with AND without background removal, then report the delta."""
    classifier = classifier or DiseaseClassifier()
    log.info("=== Comparison: background removal impact ===")
    with_bg = evaluate(test_dir, classifier, apply_bg_removal=True,
                       save_prefix=f"{save_prefix}_with_bg")
    without_bg = evaluate(test_dir, classifier, apply_bg_removal=False,
                          save_prefix=f"{save_prefix}_without_bg")

    delta = with_bg["accuracy"] - without_bg["accuracy"]
    summary = {
        "accuracy_with_bg_removal": with_bg["accuracy"],
        "accuracy_without_bg_removal": without_bg["accuracy"],
        "accuracy_delta": delta,
        "macro_auc_with_bg_removal": with_bg["macro_roc_auc"],
        "macro_auc_without_bg_removal": without_bg["macro_roc_auc"],
        "verdict": ("Background removal improved accuracy"
                    if delta > 0 else
                    "Background removal did not improve accuracy" if delta < 0
                    else "No change"),
        "n_samples": with_bg["n_samples"],
    }
    path = export_json(summary, os.path.join(
        OUTPUT_DIR, f"{save_prefix}_summary.json"))
    log.info("Comparison summary: with=%.4f without=%.4f delta=%+.4f",
             with_bg["accuracy"], without_bg["accuracy"], delta)
    summary["summary_path"] = path
    return summary


# ─────────────────────────────────────────────────────────────
# Plotting
# ─────────────────────────────────────────────────────────────
def _plot_confusion_matrix(cm, labels, save_path):
    import matplotlib.pyplot as plt

    n = len(labels)
    fig, ax = plt.subplots(figsize=(max(6, n * 0.5), max(5, n * 0.5)))
    im = ax.imshow(cm, cmap="Blues")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=90, fontsize=7)
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("Confusion Matrix")
    if n <= 25:  # annotate cells only when it stays legible
        for i in range(n):
            for j in range(n):
                ax.text(j, i, cm[i, j], ha="center", va="center",
                        fontsize=6,
                        color="white" if cm[i, j] > cm.max() / 2 else "black")
    plt.tight_layout()
    plt.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close()
    log.info("Saved confusion matrix -> %s", save_path)


def _plot_roc_auc(y_true, y_scores, present, labels, save_path):
    """One-vs-rest ROC per class; returns macro-average AUC."""
    from sklearn.metrics import roc_curve, auc
    from sklearn.preprocessing import label_binarize
    import matplotlib.pyplot as plt

    y_bin = label_binarize(y_true, classes=present)
    scores = y_scores[:, present]     # keep only columns for present classes
    if y_bin.shape[1] == 1:           # binary edge-case -> expand to 2 columns
        y_bin = np.hstack([1 - y_bin, y_bin])
        scores = np.hstack([1 - scores, scores])

    plt.figure(figsize=(8, 7))
    aucs = []
    for i, label in enumerate(labels):
        if y_bin[:, i].sum() == 0:    # class absent in ground truth
            continue
        fpr, tpr, _ = roc_curve(y_bin[:, i], scores[:, i])
        a = auc(fpr, tpr)
        aucs.append(a)
        if len(labels) <= 12:         # avoid an unreadable legend for many classes
            plt.plot(fpr, tpr, lw=1.3, label=f"{label} (AUC={a:.2f})")

    plt.plot([0, 1], [0, 1], "k--", lw=1)
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    macro = float(np.mean(aucs)) if aucs else float("nan")
    plt.title(f"ROC-AUC (one-vs-rest)  |  macro AUC = {macro:.3f}")
    if len(labels) <= 12:
        plt.legend(fontsize=7, loc="lower right")
    plt.tight_layout()
    plt.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close()
    log.info("Saved ROC-AUC -> %s (macro AUC=%.3f)", save_path, macro)
    return macro
