"""
SQLite State Manager
Saves drafts, party details, property info, and automation checkpoints
so the user can resume interrupted registries.
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from modules.config import DB_PATH, LOG_FORMAT, LOG_LEVEL

logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)
logger = logging.getLogger(__name__)


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def _transaction():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create all tables if they do not exist."""
    with _transaction() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS registries (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                title        TEXT NOT NULL DEFAULT 'New Registry',
                deed_category TEXT,
                instrument   TEXT,
                district     TEXT,
                tehsil       TEXT,
                patwari_halka TEXT,
                ward_colony  TEXT,
                area_type    TEXT,
                status       TEXT NOT NULL DEFAULT 'draft',
                current_step TEXT NOT NULL DEFAULT 'idle',
                created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                error_log    TEXT,
                extra_json   TEXT
            );

            CREATE TABLE IF NOT EXISTS parties (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                registry_id  INTEGER NOT NULL REFERENCES registries(id) ON DELETE CASCADE,
                role         TEXT NOT NULL,   -- Buyer 1, Seller 1, Witness 1 …
                name_english TEXT,
                name_hindi   TEXT,
                father_husband_name_english TEXT,
                father_husband_name_hindi   TEXT,
                dob          TEXT,
                gender       TEXT,
                category     TEXT,
                address_english TEXT,
                address_hindi   TEXT,
                id_type      TEXT,
                id_number    TEXT,
                pan_number   TEXT,
                mobile_number TEXT,
                email        TEXT,
                photo_path   TEXT,
                verified     INTEGER NOT NULL DEFAULT 0,
                created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS properties (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                registry_id  INTEGER NOT NULL UNIQUE REFERENCES registries(id) ON DELETE CASCADE,
                district     TEXT,
                tehsil       TEXT,
                area_type    TEXT,
                ward_colony_name TEXT,
                plot_number  TEXT,
                total_area_sqmt      REAL,
                constructed_area_sqmt REAL,
                road_width_mt        REAL,
                boundaries_json      TEXT,
                valuation_json       TEXT,
                extra_json           TEXT,
                created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS documents (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                registry_id  INTEGER NOT NULL REFERENCES registries(id) ON DELETE CASCADE,
                doc_type     TEXT,   -- id_scan, property_scan, draft_pdf, old_deed …
                role_hint    TEXT,   -- Buyer 1, Seller 1, etc.
                file_path    TEXT NOT NULL,
                file_name    TEXT,
                mime_type    TEXT,
                uploaded_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS automation_logs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                registry_id  INTEGER NOT NULL REFERENCES registries(id) ON DELETE CASCADE,
                step         TEXT NOT NULL,
                status       TEXT NOT NULL,   -- success, error, pause, resume
                message      TEXT,
                screenshot_path TEXT,
                created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    logger.info("Database initialised at %s", DB_PATH)


# ── Registry CRUD ────────────────────────────────────────────────────

def create_registry(title: str = "New Registry") -> int:
    with _transaction() as conn:
        cur = conn.execute(
            "INSERT INTO registries (title) VALUES (?)", (title,)
        )
        return cur.lastrowid


def get_registry(registry_id: int) -> Optional[Dict[str, Any]]:
    with _transaction() as conn:
        row = conn.execute(
            "SELECT * FROM registries WHERE id = ?", (registry_id,)
        ).fetchone()
        return dict(row) if row else None


def list_registries(status: Optional[str] = None) -> List[Dict[str, Any]]:
    with _transaction() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM registries WHERE status = ? ORDER BY updated_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM registries ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]


def update_registry(
    registry_id: int,
    fields: Dict[str, Any],
) -> None:
    """fields: any columns from registries table."""
    allowed = {
        "title", "deed_category", "instrument", "district", "tehsil",
        "patwari_halka", "ward_colony", "area_type", "status",
        "current_step", "error_log", "extra_json",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    updates["updated_at"] = datetime.now().isoformat()
    sets = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [registry_id]
    with _transaction() as conn:
        conn.execute(f"UPDATE registries SET {sets} WHERE id = ?", values)


# ── Party CRUD ───────────────────────────────────────────────────────

def add_party(registry_id: int, data: Dict[str, Any]) -> int:
    cols = [
        "registry_id", "role", "name_english", "name_hindi",
        "father_husband_name_english", "father_husband_name_hindi",
        "dob", "gender", "category", "address_english", "address_hindi",
        "id_type", "id_number", "pan_number", "mobile_number",
        "email", "photo_path", "verified",
    ]
    placeholders = ", ".join("?" for _ in cols)
    values = [registry_id] + [data.get(c) for c in cols[1:]]
    with _transaction() as conn:
        cur = conn.execute(
            f"INSERT INTO parties ({', '.join(cols)}) VALUES ({placeholders})",
            values,
        )
        return cur.lastrowid


def get_parties(registry_id: int) -> List[Dict[str, Any]]:
    with _transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM parties WHERE registry_id = ? ORDER BY role",
            (registry_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def update_party(party_id: int, data: Dict[str, Any]) -> None:
    allowed = {
        "role", "name_english", "name_hindi", "father_husband_name_english",
        "father_husband_name_hindi", "dob", "gender", "category",
        "address_english", "address_hindi", "id_type", "id_number",
        "pan_number", "mobile_number", "email", "photo_path", "verified",
    }
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return
    sets = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [party_id]
    with _transaction() as conn:
        conn.execute(f"UPDATE parties SET {sets} WHERE id = ?", values)


def delete_party(party_id: int) -> None:
    with _transaction() as conn:
        conn.execute("DELETE FROM parties WHERE id = ?", (party_id,))


# ── Property CRUD ────────────────────────────────────────────────────

def save_property(registry_id: int, data: Dict[str, Any]) -> int:
    boundaries = data.get("boundaries")
    valuation = data.get("valuation")
    extra = data.get("extra_json")
    with _transaction() as conn:
        conn.execute("DELETE FROM properties WHERE registry_id = ?", (registry_id,))
        cur = conn.execute(
            """
            INSERT INTO properties (
                registry_id, district, tehsil, area_type, ward_colony_name,
                plot_number, total_area_sqmt, constructed_area_sqmt,
                road_width_mt, boundaries_json, valuation_json, extra_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                registry_id,
                data.get("district"),
                data.get("tehsil"),
                data.get("area_type"),
                data.get("ward_colony_name"),
                data.get("plot_number"),
                data.get("total_area_sqmt"),
                data.get("constructed_area_sqmt"),
                data.get("road_width_mt"),
                json.dumps(boundaries) if boundaries else None,
                json.dumps(valuation) if valuation else None,
                json.dumps(extra) if extra else None,
            ),
        )
        return cur.lastrowid


def get_property(registry_id: int) -> Optional[Dict[str, Any]]:
    with _transaction() as conn:
        row = conn.execute(
            "SELECT * FROM properties WHERE registry_id = ?", (registry_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        if d.get("boundaries_json"):
            d["boundaries"] = json.loads(d["boundaries_json"])
        if d.get("valuation_json"):
            d["valuation"] = json.loads(d["valuation_json"])
        if d.get("extra_json"):
            d["extra"] = json.loads(d["extra_json"])
        return d


# ── Document CRUD ────────────────────────────────────────────────────

def add_document(
    registry_id: int,
    file_path: str,
    doc_type: str = "id_scan",
    role_hint: str = "",
    file_name: str = "",
    mime_type: str = "",
) -> int:
    with _transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO documents (registry_id, doc_type, role_hint, file_path, file_name, mime_type)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (registry_id, doc_type, role_hint, file_path, file_name, mime_type),
        )
        return cur.lastrowid


def get_documents(registry_id: int, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
    with _transaction() as conn:
        if doc_type:
            rows = conn.execute(
                "SELECT * FROM documents WHERE registry_id = ? AND doc_type = ?",
                (registry_id, doc_type),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM documents WHERE registry_id = ?",
                (registry_id,),
            ).fetchall()
        return [dict(r) for r in rows]


# ── Automation Log ───────────────────────────────────────────────────

def log_automation(
    registry_id: int,
    step: str,
    status: str,
    message: str = "",
    screenshot_path: str = "",
) -> None:
    with _transaction() as conn:
        conn.execute(
            """
            INSERT INTO automation_logs (registry_id, step, status, message, screenshot_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (registry_id, step, status, message, screenshot_path),
        )


def get_logs(registry_id: int) -> List[Dict[str, Any]]:
    with _transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM automation_logs WHERE registry_id = ? ORDER BY created_at",
            (registry_id,),
        ).fetchall()
        return [dict(r) for r in rows]
