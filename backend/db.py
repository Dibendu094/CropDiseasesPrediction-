"""
AgriCare AI — Storage layer (Postgres with automatic SQLite fallback)
=====================================================================
Two interchangeable backends sit behind one API:

**Postgres / Supabase** — the original design. Supabase gives one database, so
each authenticated user gets their own **schema** inside it, i.e. a private
namespace no other user can see::

    agricare.users                 <- central registry of everyone who signed up
    user_<uid>.detections          <- one private schema per user, holds history

**SQLite** — a single local file (`agricare_local.db`). SQLite has no schemas,
so per-user isolation is a `user_id` foreign key on one `detections` table and
every query filters on it. Same guarantees for a local single-user install,
zero setup, no network.

Which backend is used is decided once, lazily, by `DB_BACKEND`:
`auto` (default) tries Postgres and falls back to SQLite if it is unreachable,
so the app keeps working when the cloud database is down or unconfigured.

The `users` table stores `password_hash` and optional `reset_token` /
`reset_expires` for the local email/password auth flow.
"""

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone

import config

try:
    import psycopg2
    from psycopg2 import sql
    _PSYCOPG2_AVAILABLE = True
except ImportError:                                   # pragma: no cover
    _PSYCOPG2_AVAILABLE = False


# ─── Backend selection ──────────────────────────────────────────────────

_BACKEND = None                  # 'postgres' | 'sqlite'
_BACKEND_ERROR = None            # why Postgres was rejected, for diagnostics
_LOCK = threading.Lock()


def backend():
    """Return the active backend name, choosing one on first use."""
    _ensure_backend()
    return _BACKEND


def backend_error():
    """Return the Postgres failure reason when we fell back to SQLite."""
    return _BACKEND_ERROR


def _ensure_backend():
    """Pick a backend once, then reuse it for the process lifetime."""
    global _BACKEND, _BACKEND_ERROR
    if _BACKEND is not None:
        return _BACKEND

    with _LOCK:
        if _BACKEND is not None:
            return _BACKEND

        want = config.DB_BACKEND
        if want == 'sqlite':
            _init_sqlite()
            _BACKEND = 'sqlite'
            return _BACKEND

        if want in ('auto', 'postgres'):
            if not _PSYCOPG2_AVAILABLE:
                _BACKEND_ERROR = "psycopg2 is not installed"
            elif not config.POSTGRES_CONFIGURED:
                _BACKEND_ERROR = "DB_HOST / DB_USER are not configured"
            else:
                try:
                    _init_postgres()
                    _BACKEND = 'postgres'
                    return _BACKEND
                except Exception as e:                # noqa: BLE001
                    _BACKEND_ERROR = f"{type(e).__name__}: {e}"

            if want == 'postgres':
                raise RuntimeError(
                    f"DB_BACKEND=postgres but the database is unreachable — {_BACKEND_ERROR}"
                )

        # auto → fall back to a local file so the app stays usable.
        _init_sqlite()
        _BACKEND = 'sqlite'
        return _BACKEND


def _is_postgres():
    return _ensure_backend() == 'postgres'


# ─── Connections ────────────────────────────────────────────────────────

def get_connection():
    """Open a fresh Postgres connection to the configured database."""
    return psycopg2.connect(connect_timeout=15, **config.DB_CONFIG)


def _sqlite_connection():
    """Open a SQLite connection with foreign keys and sane concurrency."""
    conn = sqlite3.connect(config.SQLITE_PATH, timeout=15)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def schema_name_for(user_id):
    """Turn a user id (UUID) into a safe schema identifier.

    UUID characters are hex + hyphens; hyphens aren't valid unquoted in an
    identifier, so we swap them for underscores and prefix with `user_`.
    Anything unexpected is stripped to keep the identifier injection-proof
    (we also quote it via psycopg2.sql, so this is belt-and-suspenders)."""
    safe = ''.join(c if (c.isalnum() or c == '_') else '_' for c in str(user_id))
    return f"user_{safe}"


# ─── Schema setup ───────────────────────────────────────────────────────

def _init_postgres():
    """Create the central `agricare.users` registry. Doubles as the
    reachability probe for backend selection."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS agricare;")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS agricare.users (
                    user_id        TEXT PRIMARY KEY,
                    email          TEXT UNIQUE,
                    full_name      TEXT,
                    schema_name    TEXT NOT NULL,
                    password_hash  TEXT,
                    reset_token    TEXT,
                    reset_expires  TIMESTAMPTZ,
                    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
                    last_login     TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """)
            # Add columns if they don't exist (for upgrades from older schemas)
            cur.execute("ALTER TABLE agricare.users ADD COLUMN IF NOT EXISTS password_hash TEXT;")
            cur.execute("ALTER TABLE agricare.users ADD COLUMN IF NOT EXISTS reset_token TEXT;")
            cur.execute("ALTER TABLE agricare.users ADD COLUMN IF NOT EXISTS reset_expires TIMESTAMPTZ;")
            # Google sign-in profile data, so the avatar and provider survive
            # a new session instead of living only in the cookie.
            cur.execute("ALTER TABLE agricare.users ADD COLUMN IF NOT EXISTS picture TEXT;")
            cur.execute("ALTER TABLE agricare.users ADD COLUMN IF NOT EXISTS auth_provider TEXT DEFAULT 'password';")
            cur.execute("CREATE INDEX IF NOT EXISTS users_email_idx ON agricare.users (email);")
        conn.commit()


def _init_sqlite():
    """Create the local users + detections tables."""
    directory = os.path.dirname(os.path.abspath(config.SQLITE_PATH))
    if directory:
        os.makedirs(directory, exist_ok=True)

    with _sqlite_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id        TEXT PRIMARY KEY,
                email          TEXT UNIQUE,
                full_name      TEXT,
                schema_name    TEXT NOT NULL,
                password_hash  TEXT,
                reset_token    TEXT,
                reset_expires  TEXT,
                created_at     TEXT NOT NULL DEFAULT (datetime('now')),
                last_login     TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                crop        TEXT,
                disease     TEXT,
                class_name  TEXT,
                confidence  REAL,
                is_healthy  INTEGER,
                image_url   TEXT,
                result      TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_detections_user "
            "ON detections(user_id, created_at DESC);"
        )
        conn.commit()


def init_registry():
    """Prepare storage at startup. Returns the chosen backend name."""
    return _ensure_backend()


# ─── User management (local auth) ───────────────────────────────────────

_USER_FIELDS = ('user_id', 'email', 'full_name', 'schema_name', 'password_hash',
                'reset_token', 'reset_expires', 'created_at', 'last_login')


def get_user_by_email(email):
    """Fetch a user row by email. Returns a dict or None."""
    if _is_postgres():
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id, email, full_name, schema_name, password_hash, "
                    "reset_token, reset_expires, created_at, last_login "
                    "FROM agricare.users WHERE email = %s;",
                    (email,)
                )
                row = cur.fetchone()
    else:
        with _sqlite_connection() as conn:
            row = conn.execute(
                "SELECT user_id, email, full_name, schema_name, password_hash, "
                "reset_token, reset_expires, created_at, last_login "
                "FROM users WHERE email = ?;",
                (email,)
            ).fetchone()

    return dict(zip(_USER_FIELDS, row)) if row else None


def save_google_profile(user_id, full_name, picture):
    """Persist the profile Google gave us, so the name and avatar survive a
    new session instead of living only in the cookie.

    Postgres only — the SQLite fallback has no such columns and the profile
    simply stays session-scoped there, which is fine for local use.
    """
    if not _is_postgres():
        return
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE agricare.users
                       SET full_name     = COALESCE(NULLIF(%s, ''), full_name),
                           picture       = COALESCE(NULLIF(%s, ''), picture),
                           auth_provider = 'google',
                           last_login    = now()
                     WHERE user_id = %s;
                """, (full_name, picture, user_id))
            conn.commit()
    except Exception as e:
        # Never block sign-in over a profile-cosmetics write.
        print(f"[AgriCare AI] WARNING: could not save Google profile: {e}")


def get_google_profile(user_id):
    """Return {'picture': ..., 'auth_provider': ...} for a user, or {}."""
    if not _is_postgres():
        return {}
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT picture, auth_provider FROM agricare.users "
                            "WHERE user_id = %s;", (user_id,))
                row = cur.fetchone()
        return {'picture': row[0] or '', 'auth_provider': row[1] or ''} if row else {}
    except Exception:
        return {}


def create_user(user_id, full_name, email, password_hash):
    """Insert a brand-new user and provision their private storage.

    `password_hash` is only ever written when it is non-empty — an empty value
    leaves any existing hash untouched rather than locking the user out.
    """
    schema = schema_name_for(user_id)

    if _is_postgres():
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 1. The user's private schema ("their own database").
                cur.execute(
                    sql.SQL("CREATE SCHEMA IF NOT EXISTS {};").format(sql.Identifier(schema))
                )

                # 2. Their private detections history table.
                cur.execute(
                    sql.SQL("""
                        CREATE TABLE IF NOT EXISTS {}.detections (
                            id            BIGSERIAL PRIMARY KEY,
                            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
                            crop          TEXT,
                            disease       TEXT,
                            class_name    TEXT,
                            confidence    NUMERIC,
                            is_healthy    BOOLEAN,
                            image_url     TEXT,
                            result        JSONB
                        );
                    """).format(sql.Identifier(schema))
                )

                # 3. Register the user in the central registry. NULLIF guards the
                #    password hash so a blank value never clobbers a real one.
                cur.execute("""
                    INSERT INTO agricare.users
                        (user_id, email, full_name, schema_name, password_hash)
                    VALUES (%s, %s, %s, %s, NULLIF(%s, ''))
                    ON CONFLICT (user_id) DO UPDATE
                        SET email          = COALESCE(EXCLUDED.email, agricare.users.email),
                            full_name      = COALESCE(EXCLUDED.full_name, agricare.users.full_name),
                            schema_name    = COALESCE(EXCLUDED.schema_name, agricare.users.schema_name),
                            password_hash  = COALESCE(EXCLUDED.password_hash, agricare.users.password_hash),
                            last_login     = now();
                """, (user_id, email, full_name, schema, password_hash))
            conn.commit()
        return schema

    with _sqlite_connection() as conn:
        existing = conn.execute(
            "SELECT password_hash FROM users WHERE user_id = ?;", (user_id,)
        ).fetchone()
        if existing:
            conn.execute("""
                UPDATE users
                SET email         = COALESCE(?, email),
                    full_name     = COALESCE(?, full_name),
                    schema_name   = ?,
                    password_hash = COALESCE(NULLIF(?, ''), password_hash),
                    last_login    = datetime('now')
                WHERE user_id = ?;
            """, (email, full_name, schema, password_hash or '', user_id))
        else:
            conn.execute("""
                INSERT INTO users (user_id, email, full_name, schema_name, password_hash)
                VALUES (?, ?, ?, ?, NULLIF(?, ''));
            """, (user_id, email, full_name, schema, password_hash or ''))
        conn.commit()
    return schema


def update_password(user_id, password_hash):
    """Update a user's password hash and clear any reset token."""
    if _is_postgres():
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE agricare.users
                    SET password_hash = %s,
                        reset_token   = NULL,
                        reset_expires = NULL
                    WHERE user_id = %s;
                """, (password_hash, user_id))
            conn.commit()
        return

    with _sqlite_connection() as conn:
        conn.execute("""
            UPDATE users
            SET password_hash = ?, reset_token = NULL, reset_expires = NULL
            WHERE user_id = ?;
        """, (password_hash, user_id))
        conn.commit()


def store_reset_token(user_id, token, expires):
    """Store a password-reset token with its expiry."""
    if _is_postgres():
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE agricare.users
                    SET reset_token   = %s,
                        reset_expires = %s
                    WHERE user_id = %s;
                """, (token, expires, user_id))
            conn.commit()
        return

    # SQLite has no timestamp type — store an ISO-8601 UTC string.
    if isinstance(expires, datetime):
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        expires = expires.astimezone(timezone.utc).isoformat()

    with _sqlite_connection() as conn:
        conn.execute(
            "UPDATE users SET reset_token = ?, reset_expires = ? WHERE user_id = ?;",
            (token, expires, user_id)
        )
        conn.commit()


def get_user_by_reset_token(token):
    """Look up a user by their password-reset token. Returns a dict or None."""
    fields = ('user_id', 'email', 'full_name', 'reset_token', 'reset_expires')

    if _is_postgres():
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id, email, full_name, reset_token, reset_expires "
                    "FROM agricare.users WHERE reset_token = %s;",
                    (token,)
                )
                row = cur.fetchone()
    else:
        with _sqlite_connection() as conn:
            row = conn.execute(
                "SELECT user_id, email, full_name, reset_token, reset_expires "
                "FROM users WHERE reset_token = ?;",
                (token,)
            ).fetchone()

    return dict(zip(fields, row)) if row else None


def update_last_login(user_id):
    """Refresh the last_login timestamp for a user."""
    if _is_postgres():
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE agricare.users SET last_login = now() WHERE user_id = %s;",
                    (user_id,)
                )
            conn.commit()
        return

    with _sqlite_connection() as conn:
        conn.execute(
            "UPDATE users SET last_login = datetime('now') WHERE user_id = ?;",
            (user_id,)
        )
        conn.commit()


# ─── Detection history ──────────────────────────────────────────────────

def save_detection(user_id, result):
    """Store one prediction result in the user's private history."""
    if _is_postgres():
        schema = schema_name_for(user_id)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("""
                        INSERT INTO {}.detections
                            (crop, disease, class_name, confidence, is_healthy, image_url, result)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id;
                    """).format(sql.Identifier(schema)),
                    (
                        result.get('crop'),
                        result.get('disease'),
                        result.get('class_name'),
                        result.get('confidence'),
                        result.get('is_healthy'),
                        result.get('image_url'),
                        json.dumps(result),
                    )
                )
                new_id = cur.fetchone()[0]
            conn.commit()
        return new_id

    with _sqlite_connection() as conn:
        cur = conn.execute("""
            INSERT INTO detections
                (user_id, crop, disease, class_name, confidence, is_healthy, image_url, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            user_id,
            result.get('crop'),
            result.get('disease'),
            result.get('class_name'),
            result.get('confidence'),
            1 if result.get('is_healthy') else 0,
            result.get('image_url'),
            json.dumps(result),
        ))
        conn.commit()
        return cur.lastrowid


def get_detections(user_id, limit=50):
    """Return the user's most recent detections."""
    if _is_postgres():
        schema = schema_name_for(user_id)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("""
                        SELECT id, created_at, crop, disease, confidence, is_healthy, image_url, result
                        FROM {}.detections
                        ORDER BY created_at DESC
                        LIMIT %s;
                    """).format(sql.Identifier(schema)),
                    (limit,)
                )
                rows = cur.fetchall()

        return [
            {
                'id': r[0],
                'created_at': r[1].isoformat() if r[1] else None,
                'crop': r[2],
                'disease': r[3],
                'confidence': float(r[4]) if r[4] is not None else None,
                'is_healthy': r[5],
                'image_url': r[6],
                'result': r[7] if r[7] is not None else {},
            }
            for r in rows
        ]

    with _sqlite_connection() as conn:
        rows = conn.execute("""
            SELECT id, created_at, crop, disease, confidence, is_healthy, image_url, result
            FROM detections
            WHERE user_id = ?
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT ?;
        """, (user_id, limit)).fetchall()

    out = []
    for r in rows:
        try:
            parsed = json.loads(r[7]) if r[7] else {}
        except (TypeError, ValueError):
            parsed = {}
        out.append({
            'id': r[0],
            'created_at': r[1],
            'crop': r[2],
            'disease': r[3],
            'confidence': float(r[4]) if r[4] is not None else None,
            'is_healthy': bool(r[5]),
            'image_url': r[6],
            'result': parsed,
        })
    return out


def delete_detection(user_id, detection_id):
    """Delete one detection by id from the user's private history."""
    if _is_postgres():
        schema = schema_name_for(user_id)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("""
                        DELETE FROM {}.detections
                        WHERE id = %s;
                    """).format(sql.Identifier(schema)),
                    (detection_id,)
                )
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    with _sqlite_connection() as conn:
        # The user_id filter is what keeps one user from deleting another's row.
        cur = conn.execute(
            "DELETE FROM detections WHERE id = ? AND user_id = ?;",
            (detection_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0
