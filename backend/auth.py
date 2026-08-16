"""
AgriCare AI — Authentication helpers
=====================================
Local email/password authentication backed by the Supabase Postgres database.

Users are stored in the central `agricare.users` table alongside their
password hash and optional password-reset token. Each user still gets their
own private schema (`user_<uid>`) for detection history — that provisioning
is handled in `db.py`.

Password policy: at least 6 characters, must contain at least one digit.
"""

import re
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import session, redirect, url_for, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

import config
import db


# ─── Password validation ────────────────────────────────────────────────

def validate_password(password):
    """Return (is_valid, error_message) for a candidate password.

    Policy:
      • At least PASSWORD_MIN_LENGTH characters
      • Must contain at least one digit
    """
    if not password or len(password) < config.PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {config.PASSWORD_MIN_LENGTH} characters long."
    if config.PASSWORD_REQUIRES_DIGIT and not re.search(r'\d', password):
        return False, "Password must contain at least one number."
    return True, None


# ─── User registration ──────────────────────────────────────────────────

def register_user(full_name, email, password):
    """Create a new user.

    Returns (success: bool, message: str, user: dict|None).
    """
    # Basic field validation
    if not full_name or not full_name.strip():
        return False, "Name is required.", None
    if not email or not email.strip():
        return False, "Email is required.", None
    email = email.strip().lower()

    is_valid, msg = validate_password(password)
    if not is_valid:
        return False, msg, None

    # Check for existing email
    existing = db.get_user_by_email(email)
    if existing:
        return False, "An account with this email already exists.", None

    # Create the user
    user_id = str(uuid.uuid4())
    password_hash = generate_password_hash(password)

    try:
        db.create_user(user_id, full_name.strip(), email, password_hash)
    except Exception as e:
        return False, f"Could not create account: {e}", None

    user = {
        'id': user_id,
        'email': email,
        'full_name': full_name.strip(),
    }
    return True, "Account created successfully.", user


# ─── User login ─────────────────────────────────────────────────────────

def authenticate_user(email, password):
    """Verify credentials and return a user dict, or None."""
    if not email or not password:
        return None

    email = email.strip().lower()
    user = db.get_user_by_email(email)
    if not user:
        return None

    stored_hash = user.get('password_hash')
    if not stored_hash:
        return None

    if not check_password_hash(stored_hash, password):
        return None

    return {
        'id': user['user_id'],
        'email': user['email'],
        'full_name': user.get('full_name') or user['email'].split('@')[0],
    }


# ─── Password reset ─────────────────────────────────────────────────────

def generate_reset_token(email):
    """Generate a password-reset token for the given email.

    Returns (success: bool, message: str, token: str|None).
    The token is stored in the database with a 1-hour expiry.
    """
    email = email.strip().lower()
    user = db.get_user_by_email(email)
    if not user:
        # Don't reveal whether the email exists
        return True, "If an account with that email exists, a reset link has been sent.", None

    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc) + timedelta(hours=1)

    try:
        db.store_reset_token(user['user_id'], token, expires)
    except Exception as e:
        return False, f"Could not generate reset token: {e}", None

    return True, "If an account with that email exists, a reset link has been sent.", token


def reset_password(token, new_password):
    """Reset a user's password using a valid reset token.

    Returns (success: bool, message: str).
    """
    is_valid, msg = validate_password(new_password)
    if not is_valid:
        return False, msg

    user = db.get_user_by_reset_token(token)
    if not user:
        return False, "Invalid or expired reset link."

    # Check expiry. Postgres hands back a timezone-aware datetime while SQLite
    # returns an ISO string, and comparing an aware value to a naive utcnow()
    # raises TypeError — which used to be swallowed here, silently letting
    # expired links through. Normalise both sides to aware UTC instead.
    expires_raw = user.get('reset_expires')
    if expires_raw:
        expires = expires_raw if isinstance(expires_raw, datetime) else None
        if expires is None:
            try:
                expires = datetime.fromisoformat(str(expires_raw))
            except (ValueError, TypeError):
                expires = None
        if expires is not None:
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < datetime.now(timezone.utc):
                return False, "Reset link has expired. Please request a new one."

    password_hash = generate_password_hash(new_password)
    try:
        db.update_password(user['user_id'], password_hash)
    except Exception as e:
        return False, f"Could not reset password: {e}"

    return True, "Password has been reset. You can now sign in."


# ─── Session helpers ────────────────────────────────────────────────────

def current_user():
    """Return the logged-in user dict stored in the session, or None."""
    return session.get('user')


def login_required(view):
    """Protect a route: browsers get redirected to /auth, APIs get 401 JSON."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('user'):
            # Anything under /api/ is fetched by JavaScript, which calls
            # response.json() on the reply — redirecting it to the HTML sign-in
            # page makes the frontend throw a parse error instead of prompting
            # the user to log in.
            wants_json = (
                request.path.startswith('/api/')
                or request.path.startswith('/predict')
                or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                or 'application/json' in (request.headers.get('Accept') or '')
            )
            if wants_json:
                return jsonify({
                    'success': False,
                    'error': 'Authentication required. Please sign in to detect diseases.',
                    'auth_required': True,
                }), 401
            return redirect(url_for('auth_page', next=request.path))
        return view(*args, **kwargs)
    return wrapped
