"""
AgriCare AI — Configuration loader
Reads environment variables from `.env` (via python-dotenv) and exposes them
as plain module-level constants used across the app.

Nothing here is fatal at import time: the app is designed to boot and serve
detections even when the cloud database or the Gemini key are missing, so
optional settings degrade to safe local defaults instead of raising.
"""

import os
import secrets
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

# Load variables from a local .env file if present (no-op in production if the
# platform injects them directly).
# .env lives at the project root, one level above backend/.
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))


def _optional(name, default=''):
    """Fetch an optional env var, trimmed."""
    return (os.environ.get(name) or default).strip()


# ─── Flask ───
# A missing secret key used to crash the app at import. Generate an ephemeral
# one instead so a fresh clone runs immediately; sessions simply reset on
# restart until a real key is set in .env.
FLASK_SECRET_KEY = _optional('FLASK_SECRET_KEY')
FLASK_SECRET_KEY_IS_EPHEMERAL = False
if not FLASK_SECRET_KEY or FLASK_SECRET_KEY == 'change-me':
    FLASK_SECRET_KEY = secrets.token_hex(32)
    FLASK_SECRET_KEY_IS_EPHEMERAL = True

# ─── Storage backend ───
# 'auto'     → try Postgres, fall back to a local SQLite file if unreachable
# 'postgres' → require Postgres (fail loudly)
# 'sqlite'   → always use the local SQLite file
DB_BACKEND = (_optional('DB_BACKEND', 'auto')).lower()

# Local SQLite file used by the 'sqlite' backend and the 'auto' fallback.
SQLITE_PATH = _optional(
    'SQLITE_PATH',
    os.path.join(PROJECT_ROOT, 'agricare_local.db')
)

# ─── Postgres / Supabase (optional) ───
# Direct connection used for per-user schema provisioning. If the host is not
# configured or cannot be reached, the app falls back to SQLite automatically.
DB_HOST = _optional('DB_HOST')
DB_CONFIG = {
    'host': DB_HOST,
    'port': int(_optional('DB_PORT', '5432') or 5432),
    'dbname': _optional('DB_NAME', 'postgres'),
    'user': _optional('DB_USER'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'sslmode': _optional('DB_SSLMODE', 'require'),
}
POSTGRES_CONFIGURED = bool(DB_HOST and DB_CONFIG['user'])

# ─── Google Gemini Vision AI (optional fallback for unknown crops) ───
# Not required for the app to run — known crops work fully offline via the
# PyTorch model. Only the "Other / Unknown Crop" path needs this key.
GEMINI_API_KEY = _optional('GEMINI_API_KEY')
GEMINI_MODEL = _optional('GEMINI_MODEL', 'gemini-flash-lite-latest')

# Models tried in order when the primary is overloaded (503) or retired (404).
# Google rotates hosted model names, so a single hard-coded id goes stale and
# silently breaks the unknown-crop path; the chain keeps it working.
GEMINI_FALLBACK_MODELS = [
    m.strip() for m in _optional(
        'GEMINI_FALLBACK_MODELS',
        'gemini-flash-lite-latest,gemini-flash-latest,gemini-3.5-flash-lite,gemini-3.5-flash'
    ).split(',') if m.strip()
]

# How many times to retry a transient (503 / overloaded) Gemini response.
GEMINI_MAX_RETRIES = int(_optional('GEMINI_MAX_RETRIES', '2') or 2)

# Treat the shipped placeholder as "not configured".
_PLACEHOLDERS = {'', 'YOUR_GEMINI_API_KEY_HERE', 'change-me'}
GEMINI_ENABLED = GEMINI_API_KEY not in _PLACEHOLDERS


# ─── Prediction model ───
# Which checkpoint(s) power the known-crop prediction path:
#   'cascade'      → ViT first; if it is less than CASCADE_THRESHOLD% confident,
#                    EfficientNet-B3 makes the final call (default)
#   'vit'          → ViT-B/16-384 alone
#   'efficientnet' → EfficientNet-B3 alone
#   'ensemble'     → weighted average of both (see ENSEMBLE_WEIGHT_* below)
#
# A hand-verified 29-image accuracy comparison scored ViT-B/16-384 and
# EfficientNet-B3 in an exact tie (58.6% crop-level top-1 each). ViT was chosen
# as the tie-break winner: it is markedly more decisive when correct (75.7% vs
# 61.8% average confidence), which matters for the app's three-tier confidence
# policy. EfficientNet-B3 is roughly 2.6x faster per image if response time
# matters more than decisiveness for your deployment.
PREDICTION_MODEL = _optional('PREDICTION_MODEL', 'cascade').lower()
if PREDICTION_MODEL not in ('cascade', 'vit', 'efficientnet', 'ensemble'):
    PREDICTION_MODEL = 'cascade'

ENSEMBLE_WEIGHT_VIT = float(_optional('ENSEMBLE_WEIGHT_VIT', '0.70') or 0.70)
ENSEMBLE_WEIGHT_EFF = float(_optional('ENSEMBLE_WEIGHT_EFF', '0.30') or 0.30)

# Cascade mode: ViT decides unless it is less than this confident, in which
# case EfficientNet-B3 makes the final call.
CASCADE_THRESHOLD = float(_optional('CASCADE_THRESHOLD', '70') or 70)


# ─── Local Auth ───
# Password policy: minimum length and must contain at least one digit.
PASSWORD_MIN_LENGTH = 6
PASSWORD_REQUIRES_DIGIT = True

# ─── CORS (only needed when the frontend is hosted separately) ───
# Comma-separated origins allowed to call the API with credentials, e.g.
#   CORS_ORIGINS=https://crop-disease-prediction.vercel.app
# Leave empty for the normal single-origin deployment where Flask serves the UI.
CORS_ORIGINS = [o.strip().rstrip('/') for o in
                (_optional('CORS_ORIGINS', '') or '').split(',') if o.strip()]

# A cross-site session cookie must be SameSite=None and Secure, or the browser
# drops it. Only switch to that when a separate frontend origin is configured.
CROSS_SITE_COOKIES = bool(CORS_ORIGINS)


# ─── Google Sign-In (optional) ───
# Create an OAuth 2.0 Web Client at https://console.cloud.google.com/apis/credentials
# and add your app origin (e.g. http://localhost:5000) to "Authorized JavaScript
# origins". Without a client id the Google button is hidden and the app falls
# back to email/password sign-in.
GOOGLE_CLIENT_ID = _optional('GOOGLE_CLIENT_ID')
GOOGLE_AUTH_ENABLED = bool(GOOGLE_CLIENT_ID)

# ─── Daily usage quotas ───
# Total scans per calendar day, and how many of those may use the Gemini
# "Other / Unknown Crop" path (which costs an API call).
DAILY_SCANS_SIGNED_IN = int(_optional('DAILY_SCANS_SIGNED_IN', '100') or 100)
DAILY_SCANS_GUEST = int(_optional('DAILY_SCANS_GUEST', '50') or 50)
DAILY_GEMINI_SIGNED_IN = int(_optional('DAILY_GEMINI_SIGNED_IN', '10') or 10)
DAILY_GEMINI_GUEST = int(_optional('DAILY_GEMINI_GUEST', '10') or 10)
