"""
Treatment recommendation engine.

Loads the existing `disease_info.json` treatment database (keyed by raw class
name) and turns a classifier result into a farmer-friendly recommendation with
organic + chemical options, severity-based guidance, and preventive measures.
"""

import json

from .config import CONFIG
from .utils import get_logger

log = get_logger()


def _severity_from_confidence(confidence, is_healthy):
    """Rough severity heuristic from model confidence.

    Confidence is a proxy for how strongly the visual pattern matches a disease;
    it is NOT a measured infection level, so we label it as an estimate.
    """
    if is_healthy:
        return "none"
    if confidence >= 85:
        return "severe"
    if confidence >= 60:
        return "moderate"
    return "mild"


_SEVERITY_ADVICE = {
    "mild": "Early / low signal. Start with organic measures and monitor the "
            "crop every 2-3 days before using chemical sprays.",
    "moderate": "Clear infection. Combine organic care with a targeted "
                "chemical spray and remove affected leaves promptly.",
    "severe": "Strong infection signal. Apply the recommended chemical spray "
              "without delay, isolate/prune affected plants, and re-inspect daily.",
    "none": "The leaf appears healthy. Keep following good preventive practice.",
}


class TreatmentAdvisor:
    """Maps disease predictions to structured treatment recommendations."""

    def __init__(self, db_path=None):
        self.db_path = db_path or CONFIG["treatment_db_path"]
        with open(self.db_path, "r", encoding="utf-8") as f:
            self.db = json.load(f)
        log.info("Loaded %d treatment entries from %s",
                 len(self.db), self.db_path)

    def _lookup(self, class_name):
        """Find a treatment record by exact then case-insensitive class name."""
        if class_name in self.db:
            return self.db[class_name]
        lower = {k.lower(): v for k, v in self.db.items()}
        return lower.get(class_name.lower())

    def recommend(self, prediction):
        """Build a recommendation dict from a `DiseaseClassifier.predict` result.

        Returns disease context, symptoms, organic + chemical options, severity
        guidance, preventive measures, and farmer-friendly step-by-step advice.
        """
        class_name = prediction.get("class_name", "")
        confidence = prediction.get("confidence", 0.0)
        is_healthy = prediction.get("is_healthy", False)
        info = self._lookup(class_name)

        severity = _severity_from_confidence(confidence, is_healthy)
        rec = {
            "class_name": class_name,
            "crop": prediction.get("crop"),
            "disease": prediction.get("disease"),
            "confidence": confidence,
            "is_healthy": is_healthy,
            "severity_estimate": severity,
            "severity_note": _SEVERITY_ADVICE[severity],
            "treatment_found": info is not None,
        }

        if info is None:
            rec["message"] = (
                f"No treatment record for '{class_name}'. Consult a local "
                f"agricultural extension officer for crop-specific guidance.")
            rec["organic_treatment"] = []
            rec["chemical_treatment"] = []
            rec["preventive_measures"] = []
            rec["symptoms"] = []
            rec["farmer_instructions"] = self._farmer_steps(rec, info)
            return rec

        rec.update({
            "cause": info.get("cause", ""),
            "affected_parts": info.get("affected_parts", []),
            "symptoms": info.get("symptoms", []),
            "organic_treatment": info.get("organic_remedy", []),
            "chemical_treatment": info.get("chemical_spray", []),
            "preventive_measures": info.get("preventive_measures")
                                   or info.get("prevention", []),
            "best_time_to_spray": info.get("best_time_to_spray", ""),
            "fertilizers": info.get("fertilizers", []),
        })
        rec["farmer_instructions"] = self._farmer_steps(rec, info)
        return rec

    @staticmethod
    def _farmer_steps(rec, info):
        """Compose short, plain-language numbered steps for a farmer."""
        if rec["is_healthy"]:
            steps = [
                "Your crop looks healthy — no treatment needed right now.",
                "Keep watering and fertilising as usual.",
                "Check leaves once a week for early spots or discolouration.",
            ]
            if info and info.get("preventive_measures"):
                steps.append("Prevention tip: " + info["preventive_measures"][0])
            return steps

        steps = [rec["severity_note"]]
        if rec.get("organic_treatment"):
            steps.append("Organic option: " + rec["organic_treatment"][0])
        if rec.get("chemical_treatment") and rec["severity_estimate"] != "mild":
            steps.append("Chemical option: " + rec["chemical_treatment"][0])
        if rec.get("best_time_to_spray"):
            steps.append("Spray timing: " + rec["best_time_to_spray"])
        if rec.get("preventive_measures"):
            steps.append("To prevent spread: " + rec["preventive_measures"][0])
        steps.append("Wear gloves/mask when spraying and keep children away "
                     "until the spray dries.")
        return steps

    def detect_and_recommend(self, classifier, image, apply_bg_removal=True):
        """Convenience: run inference then attach a treatment recommendation."""
        prediction = classifier.predict(image, apply_bg_removal=apply_bg_removal)
        prediction["recommendation"] = self.recommend(prediction)
        return prediction
