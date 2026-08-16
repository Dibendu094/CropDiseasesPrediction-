"""
Command-line entry point for the Crop Disease Detection System.

Examples
--------
    # Background removal on one image, save before/after figure:
    python -m crop_disease_system.main bgremove leaf.jpg --show

    # Batch background removal:
    python -m crop_disease_system.main bgremove-batch ./raw ./clean

    # Detect + recommend treatment for one image:
    python -m crop_disease_system.main detect leaf.jpg

    # Batch detect a folder, export JSON + CSV:
    python -m crop_disease_system.main detect-batch ./images

    # Real-time webcam detection:
    python -m crop_disease_system.main webcam

    # Evaluate a class-per-folder test set:
    python -m crop_disease_system.main evaluate ./test

    # Compare accuracy with vs. without background removal:
    python -m crop_disease_system.main compare ./test
"""

import os
import argparse

from .config import CONFIG, OUTPUT_DIR
from .utils import get_logger, export_json, export_csv, timestamp

log = get_logger()


def _print_prediction(pred):
    print("\n" + "=" * 60)
    print(f"  Image      : {pred.get('image_path')}")
    print(f"  Time       : {pred.get('timestamp')}")
    print(f"  Prediction : {pred['crop']} — {pred['disease']}")
    print(f"  Confidence : {pred['confidence']:.2f}%  ({pred['confidence_level']})")
    if pred.get("uncertain"):
        print("  NOTE       : low confidence — treat result as uncertain.")
    print("  Top 3:")
    for i, tp in enumerate(pred["top_predictions"], 1):
        print(f"    {i}. {tp['crop']} — {tp['disease']}: {tp['confidence']:.2f}%")
    rec = pred.get("recommendation")
    if rec:
        print("-" * 60)
        print(f"  Severity   : {rec['severity_estimate']}")
        print("  Advice for the farmer:")
        for step in rec["farmer_instructions"]:
            print(f"    • {step}")
    print("=" * 60 + "\n")


def cmd_bgremove(args):
    from .preprocessing import remove_background, visualize_before_after
    import cv2
    if args.show:
        visualize_before_after(args.image)
    result = remove_background(args.image)
    out = args.output or os.path.join(
        OUTPUT_DIR, "bgremoved_" + os.path.basename(args.image))
    cv2.imwrite(out, result)
    print(f"Saved background-removed image -> {out}")


def cmd_bgremove_batch(args):
    from .preprocessing import batch_remove_background
    records = batch_remove_background(args.input_dir, args.output_dir)
    export_json(records, os.path.join(OUTPUT_DIR, "bgremove_batch.json"))
    ok = sum(r["success"] for r in records)
    print(f"Batch background removal: {ok}/{len(records)} succeeded -> {args.output_dir}")


def cmd_detect(args):
    from .classifier import DiseaseClassifier
    from .treatment import TreatmentAdvisor
    clf = DiseaseClassifier()
    advisor = TreatmentAdvisor()
    pred = advisor.detect_and_recommend(
        clf, args.image, apply_bg_removal=not args.no_bg)
    _print_prediction(pred)
    out = export_json(pred, os.path.join(
        OUTPUT_DIR, f"detection_{timestamp().replace(':', '-').replace(' ', '_')}.json"))
    print(f"Full result saved -> {out}")


def cmd_detect_batch(args):
    from .classifier import DiseaseClassifier
    from .treatment import TreatmentAdvisor
    clf = DiseaseClassifier()
    advisor = TreatmentAdvisor()
    results = clf.predict_batch(args.input_dir, apply_bg_removal=not args.no_bg)
    rows = []
    for pred in results:
        if pred.get("success"):
            pred["recommendation"] = advisor.recommend(pred)
            rows.append({
                "image_path": pred["image_path"],
                "timestamp": pred["timestamp"],
                "crop": pred["crop"],
                "disease": pred["disease"],
                "confidence": pred["confidence"],
                "severity": pred["recommendation"]["severity_estimate"],
            })
    export_json(results, os.path.join(OUTPUT_DIR, "detect_batch.json"))
    if rows:
        export_csv(rows, os.path.join(OUTPUT_DIR, "detect_batch.csv"))
    print(f"Processed {len(results)} images -> outputs/detect_batch.json / .csv")


def cmd_webcam(args):
    from .realtime import run_webcam
    run_webcam(camera_index=args.camera, threshold=args.threshold,
               apply_bg_removal=not args.no_bg)


def cmd_evaluate(args):
    from .evaluation import evaluate
    result = evaluate(args.test_dir, apply_bg_removal=not args.no_bg)
    print(f"\nAccuracy: {result['accuracy']:.4f} | "
          f"macro ROC-AUC: {result['macro_roc_auc']:.4f} | "
          f"samples: {result['n_samples']}")
    print(f"Artifacts in {OUTPUT_DIR}")


def cmd_compare(args):
    from .evaluation import compare_background_removal
    summary = compare_background_removal(args.test_dir)
    print("\n" + "=" * 60)
    print(f"  With bg removal   : {summary['accuracy_with_bg_removal']:.4f}")
    print(f"  Without bg removal: {summary['accuracy_without_bg_removal']:.4f}")
    print(f"  Delta             : {summary['accuracy_delta']:+.4f}")
    print(f"  Verdict           : {summary['verdict']}")
    print("=" * 60)


def build_parser():
    p = argparse.ArgumentParser(
        prog="crop_disease_system",
        description="Crop Disease Detection System with Background Removal")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("bgremove", help="Background removal on one image")
    a.add_argument("image")
    a.add_argument("--output")
    a.add_argument("--show", action="store_true", help="Show before/after figure")
    a.set_defaults(func=cmd_bgremove)

    a = sub.add_parser("bgremove-batch", help="Background removal on a folder")
    a.add_argument("input_dir")
    a.add_argument("output_dir")
    a.set_defaults(func=cmd_bgremove_batch)

    a = sub.add_parser("detect", help="Detect disease + recommend treatment")
    a.add_argument("image")
    a.add_argument("--no-bg", action="store_true", help="Skip background removal")
    a.set_defaults(func=cmd_detect)

    a = sub.add_parser("detect-batch", help="Detect a folder of images")
    a.add_argument("input_dir")
    a.add_argument("--no-bg", action="store_true")
    a.set_defaults(func=cmd_detect_batch)

    a = sub.add_parser("webcam", help="Real-time webcam detection")
    a.add_argument("--camera", type=int, default=0)
    a.add_argument("--threshold", type=float, default=CONFIG["confidence_threshold"])
    a.add_argument("--no-bg", action="store_true")
    a.set_defaults(func=cmd_webcam)

    a = sub.add_parser("evaluate", help="Evaluate a class-per-folder test set")
    a.add_argument("test_dir")
    a.add_argument("--no-bg", action="store_true")
    a.set_defaults(func=cmd_evaluate)

    a = sub.add_parser("compare", help="Compare accuracy with/without bg removal")
    a.add_argument("test_dir")
    a.set_defaults(func=cmd_compare)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
