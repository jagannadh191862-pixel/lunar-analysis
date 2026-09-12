"""
Database Access Layer for Lunar Correspondence AI
Vercel-compatible SQLite implementation for prototype/demo deployment.
"""

import os
import sqlite3
import hashlib
import secrets
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from threading import Lock

# ---------------------------------------------------------
# PATH CONFIGURATION
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
LOCAL_SCHEMA = BASE_DIR / "schema.sql"

IS_VERCEL = bool(
    os.environ.get("VERCEL") or
    os.environ.get("VERCEL_ENV")
)

if IS_VERCEL:
    # Vercel allows temporary writes only inside /tmp
    DB_PATH = Path("/tmp/lunar_ai.db")
    SCHEMA_PATH = Path("/tmp/schema.sql")
else:
    DB_PATH = BASE_DIR / "lunar_ai.db"
    SCHEMA_PATH = LOCAL_SCHEMA

DB_LOCK = Lock()


# ---------------------------------------------------------
# PREPARE SCHEMA
# ---------------------------------------------------------

def prepare_schema():
    """
    Makes sure schema.sql exists at the location used by the
    current runtime.
    """

    if IS_VERCEL:

        if not SCHEMA_PATH.exists():

            if not LOCAL_SCHEMA.exists():
                raise FileNotFoundError(
                    f"schema.sql not found at {LOCAL_SCHEMA}"
                )

            shutil.copyfile(
                str(LOCAL_SCHEMA),
                str(SCHEMA_PATH)
            )

    else:

        if not SCHEMA_PATH.exists():
            raise FileNotFoundError(
                f"schema.sql not found at {SCHEMA_PATH}"
            )


# ---------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------

def get_connection() -> sqlite3.Connection:

    # Make sure schema file exists
    prepare_schema()

    # Make sure parent directory exists
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    conn = sqlite3.connect(
        str(DB_PATH),
        timeout=30.0,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON;"
    )

    conn.execute(
        "PRAGMA journal_mode = WAL;"
    )

    return conn


# ---------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------

def init_db():

    prepare_schema()

    with DB_LOCK:

        conn = get_connection()

        try:

            with open(
                SCHEMA_PATH,
                "r",
                encoding="utf-8"
            ) as f:

                schema_script = f.read()

            conn.executescript(schema_script)
            conn.commit()

        finally:

            conn.close()


# ---------------------------------------------------------
# ENSURE DATABASE IS READY
# ---------------------------------------------------------

_db_initialized = False


def ensure_db():

    global _db_initialized

    if _db_initialized:
        return

    with DB_LOCK:

        if _db_initialized:
            return

        init_db()

        _db_initialized = True


# ---------------------------------------------------------
# PASSWORD HASHING
# ---------------------------------------------------------

def hash_password(
    password: str,
    salt: Optional[str] = None
) -> Tuple[str, str]:

    if salt is None:
        salt = secrets.token_hex(16)

    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000
    )

    return key.hex(), salt


def verify_password(
    stored_hash: str,
    salt: str,
    provided_password: str
) -> bool:

    test_hash, _ = hash_password(
        provided_password,
        salt
    )

    return secrets.compare_digest(
        stored_hash,
        test_hash
    )


# ---------------------------------------------------------
# USER MANAGEMENT
# ---------------------------------------------------------

def create_user(
    username: str,
    email: str,
    password: str,
    role: str = "researcher",
    institution: str =
        "Planetary Remote Sensing Laboratory"
) -> Optional[int]:

    ensure_db()

    pwd_hash, salt = hash_password(password)

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO users
            (
                username,
                email,
                password_hash,
                salt,
                role,
                institution
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                username.strip(),
                email.strip().lower(),
                pwd_hash,
                salt,
                role,
                institution
            )
        )

        conn.commit()

        return cursor.lastrowid

    except sqlite3.IntegrityError:

        return None

    finally:

        conn.close()


def get_user_by_username(
    username: str
) -> Optional[Dict[str, Any]]:

    ensure_db()

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
               OR email = ?
            """,
            (
                username.strip(),
                username.strip().lower()
            )
        )

        row = cursor.fetchone()

        return dict(row) if row else None

    finally:

        conn.close()


def get_user_by_id(
    user_id: int
) -> Optional[Dict[str, Any]]:

    ensure_db()

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                username,
                email,
                role,
                institution,
                created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        )

        row = cursor.fetchone()

        return dict(row) if row else None

    finally:

        conn.close()


# ---------------------------------------------------------
# ANALYSIS HISTORY
# ---------------------------------------------------------

def get_user_history(
    user_id: Optional[int] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:

    ensure_db()

    # Prevent invalid values
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 20

    # Keep limit safe
    limit = max(1, min(limit, 100))

    conn = get_connection()

    try:

        cursor = conn.cursor()

        query = """
            SELECT
                a.id,
                a.created_at,
                a.detector_type,
                a.model_type,
                a.status,
                a.total_time_ms,

                p.pair_name,
                p.ref_sensor,
                p.tgt_sensor,
                p.target_region,

                m.verified_inliers_count,
                m.inlier_ratio_percent,
                m.rmse_residual_px

            FROM analyses a

            INNER JOIN image_pairs p
                ON a.pair_id = p.id

            LEFT JOIN metrics m
                ON a.id = m.analysis_id
        """

        if user_id is not None:

            query += """
                WHERE a.user_id = ?
                ORDER BY a.id DESC
                LIMIT ?
            """

            cursor.execute(
                query,
                (
                    user_id,
                    limit
                )
            )

        else:

            query += """
                ORDER BY a.id DESC
                LIMIT ?
            """

            cursor.execute(
                query,
                (limit,)
            )

        rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()
