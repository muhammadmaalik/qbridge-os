"""SQLite persistence when PostgreSQL is unavailable."""

from __future__ import annotations

import os
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT,
    email_verified INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registration_ips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_registration_ips_ip ON registration_ips(ip_address);

CREATE TABLE IF NOT EXISTS api_credentials (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    service_provider TEXT NOT NULL,
    encrypted_api_key TEXT NOT NULL,
    UNIQUE(user_id, service_provider)
);

CREATE TABLE IF NOT EXISTS job_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    execution_time_ms INTEGER,
    hardware_backend_used TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


class SQLiteDatabase:
    def __init__(self) -> None:
        self._path: str | None = None
        self._conn: sqlite3.Connection | None = None

    @property
    def ready(self) -> bool:
        return self._conn is not None

    def connect(self) -> None:
        root = Path(__file__).resolve().parent.parent
        default_path = root / "data" / "qbridge.db"
        path = os.environ.get("QBRIDGE_SQLITE_PATH", str(default_path))
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        cur = self._conn.execute("SELECT id FROM users WHERE username = ?", ("testuser",))
        if cur.fetchone() is None:
            uid = str(uuid.uuid4())
            self._conn.execute(
                "INSERT INTO users (id, username) VALUES (?, ?)",
                (uid, "testuser"),
            )
            self._conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
        if self._conn is None:
            return None
        q = " ".join(query.split())
        if "INSERT INTO users" in q and "RETURNING" in q:
            user_id, username, email, password_hash = args[:4]
            self._conn.execute(
                "INSERT INTO users (id, username, email, password_hash, email_verified) VALUES (?, ?, ?, ?, 1)",
                (str(user_id), str(username), str(email), str(password_hash)),
            )
            self._conn.commit()
            return {
                "id": str(user_id),
                "username": str(username),
                "email": str(email),
                "password_hash": str(password_hash),
            }
        cur = self._conn.execute(_to_sqlite_query(query), args)
        row = cur.fetchone()
        return dict(row) if row else None

    def fetchval(self, query: str, *args: Any) -> Any:
        if self._conn is None:
            return None
        cur = self._conn.execute(_to_sqlite_query(query), args)
        row = cur.fetchone()
        return row[0] if row else None

    def execute(self, query: str, *args: Any) -> str | None:
        if self._conn is None:
            return None
        self._conn.execute(_to_sqlite_query(query), args)
        self._conn.commit()
        return "OK"


sqlite_db = SQLiteDatabase()


def _to_sqlite_query(query: str) -> str:
    q = query
    for i in range(len(query), 0, -1):
        q = q.replace(f"${i}", "?")
    q = re.sub(r"::\w+", "", q)
    q = q.replace("gen_random_uuid()", "lower(hex(randomblob(16)))")
    q = q.replace("NOW()", "CURRENT_TIMESTAMP")
    q = q.replace("now()", "CURRENT_TIMESTAMP")
    q = q.replace("RETURNING id", "")
    q = q.replace("ON CONFLICT (username) DO NOTHING", "OR IGNORE")
    q = q.replace("ON CONFLICT (id) DO UPDATE SET otp_hash = EXCLUDED.otp_hash, expires_at = EXCLUDED.expires_at, attempts = 0", "")
    q = q.replace("ON CONFLICT (user_id, service_provider) DO UPDATE SET encrypted_api_key = EXCLUDED.encrypted_api_key", "")
    return q
