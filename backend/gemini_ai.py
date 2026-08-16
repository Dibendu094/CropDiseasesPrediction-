"""
AgriCare AI — Gemini Vision fallback module
===========================================
When a user selects "Other / Unknown Crop", the offline PyTorch model (trained
on 14 fixed crops) cannot help. This module hands the leaf photo to Google's
Gemini Vision AI, which identifies *any* crop, diagnoses the disease, and returns
a full farmer-friendly treatment plan in the SAME structured shape the rest of
the app uses — so the UI, PDF export and history all render it identically.

Public API
----------
    detect_unknown_crop(image_path: str) -> dict

Returns a dict with `success=True` and the unified report fields on success, or
`success=False` and a user-friendly `error` message on failure. It never raises.
"""

import os
import re
import io
import json
import time
import mimetypes
from datetime import datetime

import config

# Pillow is used to downscale large photos before upload (faster + avoids timeouts).
try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

# Google's modern, supported Vision SDK (`google-genai`). Optional — the app runs
# fine without it as long as nobody uses the unknown-crop path.
try:
    from google import genai
    from google.genai import types
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False

LOG_PREFIX = "[Gemini]"
DISCLAIMER = ("AI-generated recommendations. Please confirm with your local "
             "agricultural expert or Krishi Vigyan Kendra before large-scale use.")

# Prompt: force a strict JSON contract so parsing is reliable.
PROMPT = """You are an expert agronomist and plant pathologist helping a farmer.
Look at this crop leaf image carefully and identify the crop and any disease.

Respond with ONLY a valid JSON object (no markdown, no code fences, no extra
text) using EXACTLY this schema:

{
  "crop": "English crop name",
  "crop_hindi": "Hindi name in Devanagari, or empty string",
  "disease": "English disease name (use 'Healthy' if the plant looks healthy)",
  "is_healthy": true or false,
  "confidence": a number 0-100 (your certainty),
  "cause": "one short sentence on what causes this problem",
  "affected_parts": ["Leaves", "Stem", ...],
  "symptoms": ["short visible symptom", "..."],
  "organic_remedy": ["simple organic step a farmer can do", "..."],
  "chemical_spray": ["specific product + dosage per litre + how to apply", "..."],
  "preventive_measures": ["practical prevention tip", "..."],
  "best_time_to_spray": "e.g. Early morning 6-9 AM or after 4 PM",
  "fertilizers": [{"name": "fertilizer", "purpose": "why it helps"}],
  "safety_tips": ["safety precaution while spraying", "..."]
}

Rules:
- Use simple language a farmer with basic literacy can understand.
- Prefer commonly available Indian agricultural products for chemical sprays.
- Give 3-5 items in each list where possible.
- If the plant is healthy, still fill symptoms/organic_remedy with care tips.
- If you cannot identify the crop at all, set "crop" to "Unknown" and
  "disease" to "Unable to identify".
"""


def _log(message):
    """Timestamped stderr-style log for debugging Gemini calls."""
    print(f"{LOG_PREFIX} {datetime.now().isoformat(timespec='seconds')} {message}")


def _prepare_image(image_path, original_mime):
    """Load the image and, if it is large, downscale + re-encode it as JPEG so the
    upload is small and fast. Returns (image_bytes, mime_type)."""
    with open(image_path, 'rb') as fh:
        raw = fh.read()

    if not _PIL_AVAILABLE:
        return raw, (original_mime or 'image/jpeg')

    try:
        img = Image.open(io.BytesIO(raw))
        img = img.convert('RGB')
        # Cap the longest side at 1024px — plenty for disease diagnosis.
        max_side = 1024
        if max(img.size) > max_side:
            img.thumbnail((max_side, max_side), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85, optimize=True)
        return buf.getvalue(), 'image/jpeg'
    except Exception as e:  # noqa: BLE001 — fall back to the original bytes
        _log(f"image resize skipped: {e}")
        return raw, (original_mime or 'image/jpeg')


def _confidence_level(score):
    if score >= 90:
        return "High"
    if score >= 70:
        return "Medium"
    return "Low"


def _extract_json(text):
    """Pull the first JSON object out of the model's reply, tolerating stray
    prose or ```json fences."""
    if not text:
        return None
    # Strip code fences if present.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    # Otherwise grab the outermost brace span.
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or end < start:
        return None
    candidate = text[start:end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # Last resort: remove trailing commas and retry.
        cleaned = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None


def _as_list(value):
    """Normalise a field that should be a list of strings."""
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if value:
        return [str(value).strip()]
    return []


def _normalise(data):
    """Coerce a parsed Gemini JSON object into the app's unified report shape."""
    crop = str(data.get('crop', 'Unknown') or 'Unknown').strip()
    disease = str(data.get('disease', 'Unknown') or 'Unknown').strip()

    if crop.lower() == 'unknown' or disease.lower().startswith('unable'):
        return {
            'success': False,
            'error': ("Unable to identify crop from image. Try uploading a "
                     "clearer close-up photo of the leaves.")
        }

    is_healthy = bool(data.get('is_healthy', 'healthy' in disease.lower()))

    try:
        confidence = float(data.get('confidence', 80))
    except (TypeError, ValueError):
        confidence = 80.0
    confidence = max(0.0, min(100.0, confidence))

    fertilizers = []
    for f in data.get('fertilizers', []) or []:
        if isinstance(f, dict):
            name = str(f.get('name', '')).strip()
            purpose = str(f.get('purpose', '')).strip()
            if name:
                fertilizers.append({'name': name, 'purpose': purpose})
        elif str(f).strip():
            fertilizers.append({'name': str(f).strip(), 'purpose': ''})

    return {
        'success': True,
        'source': 'Gemini Vision AI',
        'source_short': 'gemini',
        'crop': crop,
        'crop_hindi': str(data.get('crop_hindi', '') or '').strip(),
        'disease': disease,
        'confidence': round(confidence, 2),
        'confidence_level': _confidence_level(confidence),
        'is_healthy': is_healthy,
        'description': str(data.get('description', '') or '').strip(),
        'cause': str(data.get('cause', '') or '').strip(),
        'affected_parts': _as_list(data.get('affected_parts')),
        'symptoms': _as_list(data.get('symptoms')),
        'organic_remedy': _as_list(data.get('organic_remedy')),
        'chemical_spray': _as_list(data.get('chemical_spray')),
        'preventive_measures': _as_list(data.get('preventive_measures')),
        'best_time_to_spray': str(data.get('best_time_to_spray', '') or '').strip(),
        'fertilizers': fertilizers,
        'safety_tips': _as_list(data.get('safety_tips')),
        'disclaimer': DISCLAIMER,
    }


def _model_chain():
    """Models to try, in order: the configured one first, then the fallbacks.

    Google retires hosted model ids on a rolling basis and returns 503 when a
    model is briefly saturated, so pinning a single id makes the unknown-crop
    path fail for reasons that have nothing to do with the user's photo.
    """
    chain = []
    for name in [config.GEMINI_MODEL] + list(config.GEMINI_FALLBACK_MODELS):
        if name and name not in chain:
            chain.append(name)
    return chain


def _classify_error(exc):
    """Map an SDK exception to (kind, friendly_message).

    kind is 'retry' for transient conditions worth another attempt, 'next_model'
    when this particular model is unusable, or 'fatal' to stop immediately.
    """
    detail = str(exc).lower()

    if 'quota' in detail or 'resource_exhausted' in detail or '429' in detail:
        return 'next_model', (
            'Gemini quota reached for this key. Create a fresh key at '
            'https://aistudio.google.com/app/apikey, make sure the Gemini API is '
            'enabled, then update GEMINI_API_KEY in .env.'
        )
    # Auth problems are fatal — no other model will fix them.
    if ('api key' in detail or 'api_key' in detail or 'unauthenticated' in detail
            or 'permission_denied' in detail or '401' in detail or '403' in detail):
        return 'fatal', 'Gemini API key is invalid or unauthorized. Check GEMINI_API_KEY in .env.'
    # A retired or unknown model id — try the next one in the chain.
    if 'not_found' in detail or '404' in detail or 'no longer available' in detail:
        return 'next_model', (
            'The configured Gemini model is no longer available. '
            'Update GEMINI_MODEL in .env to a current model.'
        )
    # Overloaded / temporarily unavailable — worth retrying.
    if ('503' in detail or 'unavailable' in detail or 'overloaded' in detail
            or 'high demand' in detail or '500' in detail or 'internal' in detail):
        return 'retry', 'Gemini AI service is busy right now. Please try again in a moment.'
    if 'timeout' in detail or 'deadline' in detail:
        return 'retry', 'Detection timed out. Please try again in a moment.'
    return 'next_model', 'Gemini AI service temporarily unavailable. Please try again later.'


def _generate(client, model, image_bytes, send_mime):
    """One generate_content call against a specific model."""
    return client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=send_mime),
            PROMPT,
        ],
        config=types.GenerateContentConfig(
            # Ask the model to return JSON directly for reliable parsing.
            response_mime_type='application/json',
            temperature=0.2,
        ),
    )


def detect_unknown_crop(image_path):
    """Identify an unknown crop + disease from a leaf image via Gemini Vision.

    Tries each model in the configured chain, retrying transient failures with a
    short backoff, so an overloaded or retired model degrades to the next one
    instead of surfacing as an error.

    Returns a unified report dict. Never raises — all failures come back as
    {'success': False, 'error': <friendly message>}.
    """
    if not config.GEMINI_ENABLED:
        return {
            'success': False,
            'error': ("Unknown-crop detection is not configured. Add your "
                     "GEMINI_API_KEY to the .env file to enable it.")
        }

    if not _SDK_AVAILABLE:
        return {
            'success': False,
            'error': ("Gemini library not installed. Run: "
                     "pip install google-genai")
        }

    if not os.path.exists(image_path):
        return {'success': False, 'error': 'Uploaded image could not be found.'}

    # Validate the image before spending an API call.
    mime, _ = mimetypes.guess_type(image_path)
    if not mime or not mime.startswith('image/'):
        mime = 'image/jpeg'
    size = os.path.getsize(image_path)
    if size == 0:
        return {'success': False, 'error': 'The uploaded image is empty.'}
    if size > 16 * 1024 * 1024:
        return {'success': False, 'error': 'Image too large (max 16 MB).'}

    try:
        client = genai.Client(
            api_key=config.GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=60000),  # milliseconds
        )
        image_bytes, send_mime = _prepare_image(image_path, mime)
    except Exception as e:  # noqa: BLE001 — client construction / image read
        _log(f"SETUP ERROR: {e}")
        return {'success': False,
                'error': 'Could not prepare the image for analysis. Please try again.'}

    last_error = 'Gemini AI service temporarily unavailable. Please try again later.'

    for model in _model_chain():
        for attempt in range(max(1, config.GEMINI_MAX_RETRIES + 1)):
            try:
                _log(f"Sending image ({len(image_bytes)} bytes, {send_mime}; "
                     f"original {size}) to {model} (attempt {attempt + 1})")
                response = _generate(client, model, image_bytes, send_mime)

                raw = getattr(response, 'text', None) or ''
                _log(f"Received {len(raw)} chars from {model}")

                parsed = _extract_json(raw)
                if not parsed:
                    _log(f"Failed to parse JSON from {model} response")
                    last_error = ("Could not read the AI response. Please try again "
                                  "with a clearer image.")
                    break            # a parse failure won't fix itself on retry

                result = _normalise(parsed)
                if result.get('success'):
                    result['model_used'] = model
                return result

            except Exception as e:  # noqa: BLE001 — classify, then retry or move on
                kind, message = _classify_error(e)
                last_error = message
                _log(f"ERROR from {model} ({kind}): {str(e)[:200]}")

                if kind == 'fatal':
                    return {'success': False, 'error': message}
                if kind == 'retry' and attempt < config.GEMINI_MAX_RETRIES:
                    time.sleep(1.5 * (attempt + 1))   # linear backoff
                    continue
                break                # try the next model in the chain

    return {'success': False, 'error': last_error}
