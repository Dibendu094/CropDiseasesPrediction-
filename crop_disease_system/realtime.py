"""
Real-time webcam disease detection.

Opens a webcam stream, runs background-removal + classification every few
frames, overlays the disease name / confidence / FPS, and logs qualifying
detections (above a confidence threshold) to a CSV file.

Run:
    python -m crop_disease_system.realtime
Press 'q' to quit, 'b' to toggle background removal.
"""

import os
import time

import cv2

from .config import CONFIG, OUTPUT_DIR
from .classifier import DiseaseClassifier
from .utils import get_logger, append_csv_row, timestamp

log = get_logger()

_CSV_FIELDS = ["timestamp", "crop", "disease", "confidence",
               "confidence_level", "background_removed"]


def run_webcam(classifier=None, camera_index=0, threshold=None,
               infer_every=5, csv_path=None, apply_bg_removal=True):
    """Start the real-time detection loop.

    Parameters
    ----------
    classifier      : a DiseaseClassifier (created if None).
    camera_index    : OpenCV camera id (0 = default webcam).
    threshold       : min confidence % to display/log (defaults to config).
    infer_every     : run the model every N frames (keeps FPS high).
    csv_path        : detection log location.
    apply_bg_removal: preprocess frames with background removal.
    """
    classifier = classifier or DiseaseClassifier()
    threshold = threshold if threshold is not None else CONFIG["confidence_threshold"]
    csv_path = csv_path or os.path.join(OUTPUT_DIR, "realtime_detections.csv")

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        log.error("Could not open camera index %s.", camera_index)
        raise RuntimeError(f"Webcam {camera_index} unavailable.")

    log.info("Webcam started. threshold=%.0f%% infer_every=%d. "
             "Press 'q' to quit, 'b' to toggle background removal.",
             threshold, infer_every)

    frame_count = 0
    last_pred = None
    prev_time = time.time()
    fps = 0.0
    last_logged = None   # avoid logging the same detection every frame

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                log.warning("Frame grab failed; stopping.")
                break
            frame_count += 1

            # FPS (exponential smoothing).
            now = time.time()
            dt = now - prev_time
            prev_time = now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt)

            # Run inference periodically, not every frame.
            if frame_count % infer_every == 0:
                try:
                    last_pred = classifier.predict(
                        frame, apply_bg_removal=apply_bg_removal)
                except Exception as exc:  # noqa: BLE001
                    log.error("Inference error: %s", exc)
                    last_pred = None

            _draw_overlay(frame, last_pred, fps, threshold, apply_bg_removal)

            # Log qualifying detections (deduplicated by disease name).
            if (last_pred and last_pred["confidence"] >= threshold
                    and not last_pred["is_healthy"]
                    and last_pred["class_name"] != last_logged):
                append_csv_row({
                    "timestamp": timestamp(),
                    "crop": last_pred["crop"],
                    "disease": last_pred["disease"],
                    "confidence": last_pred["confidence"],
                    "confidence_level": last_pred["confidence_level"],
                    "background_removed": apply_bg_removal,
                }, csv_path, _CSV_FIELDS)
                last_logged = last_pred["class_name"]

            cv2.imshow("Crop Disease Detection (q=quit, b=toggle bg)", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("b"):
                apply_bg_removal = not apply_bg_removal
                log.info("Background removal -> %s", apply_bg_removal)
    finally:
        cap.release()
        cv2.destroyAllWindows()
        log.info("Webcam stopped. Detections logged to %s", csv_path)
    return csv_path


def _draw_overlay(frame, pred, fps, threshold, bg_on):
    """Draw FPS + prediction banner onto the frame in place."""
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 70), (0, 0, 0), -1)
    cv2.putText(frame, f"FPS: {fps:4.1f}", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.putText(frame, f"BG removal: {'ON' if bg_on else 'OFF'}", (140, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    if pred is None:
        text = "Analyzing..."
        color = (200, 200, 200)
    elif pred["confidence"] < threshold:
        text = f"Uncertain ({pred['confidence']:.0f}%)"
        color = (0, 165, 255)
    else:
        color = (0, 255, 0) if pred["is_healthy"] else (0, 0, 255)
        text = f"{pred['crop']} - {pred['disease']} ({pred['confidence']:.0f}%)"
    cv2.putText(frame, text, (10, 55),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)


if __name__ == "__main__":
    run_webcam()
