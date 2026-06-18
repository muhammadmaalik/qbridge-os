import logging
import os
from urllib.parse import urlparse

import asyncpg
from pydantic_settings import BaseSettings

from backend.memory_store import handle_execute, handle_fetchrow, handle_fetchval, memory
from backend.sqlite_db import sqlite_db

logger = logging.getLogger("qbridge.db")


class Settings(BaseSettings):
    db_user: str = "qbridge"
    db_password: str = "password"
    db_name: str = "qaas_db"
    db_host: str = "localhost"
    db_port: str = "5432"

    model_config = {"env_file": ".env", "extra": "ignore"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db_user = os.environ.get("DB_USER", self.db_user)
        self.db_password = os.environ.get("DB_PASSWORD", self.db_password)
        self.db_name = os.environ.get("DB_NAME", self.db_name)
        self.db_host = os.environ.get("DB_HOST", self.db_host)
        self.db_port = os.environ.get("DB_PORT", self.db_port)

        database_url = os.environ.get("DATABASE_URL", "").strip()
        if database_url:
            parsed = urlparse(database_url)
            if parsed.hostname:
                self.db_host = parsed.hostname
            if parsed.port:
                self.db_port = str(parsed.port)
            if parsed.username:
                self.db_user = parsed.username
            if parsed.password:
                self.db_password = parsed.password
            if parsed.path and len(parsed.path) > 1:
                self.db_name = parsed.path.lstrip("/")


settings = Settings()

_POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS registration_ips (
    id SERIAL PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_registration_ips_ip ON registration_ips(ip_address);
"""


class Database:
    def __init__(self):
        self.pool = None
        self.use_memory = False
        self.use_sqlite = False

    async def connect(self):
        if os.environ.get("QBRIDGE_FORCE_MEMORY_DB", "").strip() in ("1", "true", "yes"):
            self.use_memory = True
            self.use_sqlite = False
            self.pool = None
            memory._ensure_demo_user()
            logger.info("Using in-memory store (QBRIDGE_FORCE_MEMORY_DB).")
            return

        try:
            self.pool = await asyncpg.create_pool(
                user=settings.db_user,
                password=settings.db_password,
                database=settings.db_name,
                host=settings.db_host,
                port=settings.db_port,
                timeout=5.0,
            )
            self.use_memory = False
            self.use_sqlite = False
            await self._ensure_postgres_schema()
            logger.info("Connected to PostgreSQL at %s:%s", settings.db_host, settings.db_port)
            return
        except Exception as e:
            logger.warning("PostgreSQL unavailable (%s); falling back to SQLite.", e)

        try:
            sqlite_db.connect()
            self.pool = None
            self.use_memory = False
            self.use_sqlite = True
            logger.info("Using SQLite store at %s", sqlite_db._path)
        except Exception as e:
            self.pool = None
            self.use_memory = True
            self.use_sqlite = False
            memory._ensure_demo_user()
            logger.warning("SQLite unavailable (%s); using in-memory store.", e)

    async def _ensure_postgres_schema(self) -> None:
        if self.pool is None:
            return
        async with self.pool.acquire() as connection:
            await connection.execute(_POSTGRES_SCHEMA)

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None
        if self.use_sqlite:
            sqlite_db.close()
            self.use_sqlite = False

    async def execute(self, query: str, *args):
        if self.use_memory or (self.pool is None and not self.use_sqlite):
            return handle_execute(query, *args)
        if self.use_sqlite:
            return sqlite_db.execute(query, *args)
        async with self.pool.acquire() as connection:
            return await connection.execute(query, *args)

    async def fetch(self, query: str, *args):
        if self.use_memory or (self.pool is None and not self.use_sqlite):
            return []
        if self.use_sqlite:
            row = sqlite_db.fetchrow(query, *args)
            return [row] if row else []
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        if self.use_memory or (self.pool is None and not self.use_sqlite):
            return handle_fetchrow(query, *args)
        if self.use_sqlite:
            return sqlite_db.fetchrow(query, *args)
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        if self.use_memory or (self.pool is None and not self.use_sqlite):
            return handle_fetchval(query, *args)
        if self.use_sqlite:
            return sqlite_db.fetchval(query, *args)
        async with self.pool.acquire() as connection:
            return await connection.fetchval(query, *args)

    async def ensure_demo_user(self) -> None:
        if self.use_memory or (self.pool is None and not self.use_sqlite):
            memory._ensure_demo_user()
            return
        if self.use_sqlite:
            sqlite_db.fetchrow("SELECT id FROM users WHERE username = $1", "testuser")
            return
        try:
            await self.execute(
                "INSERT INTO users (username) VALUES ('testuser') ON CONFLICT (username) DO NOTHING"
            )
        except Exception:
            pass


db = Database()
