import logging
import os

import asyncpg
from pydantic_settings import BaseSettings

from backend.memory_store import handle_execute, handle_fetchval, memory

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
        # Docker compose uses DB_* env vars
        self.db_user = os.environ.get("DB_USER", self.db_user)
        self.db_password = os.environ.get("DB_PASSWORD", self.db_password)
        self.db_name = os.environ.get("DB_NAME", self.db_name)
        self.db_host = os.environ.get("DB_HOST", self.db_host)
        self.db_port = os.environ.get("DB_PORT", self.db_port)

settings = Settings()

class Database:
    def __init__(self):
        self.pool = None
        self.use_memory = False

    async def connect(self):
        if os.environ.get("QBRIDGE_FORCE_MEMORY_DB", "").strip() in ("1", "true", "yes"):
            self.use_memory = True
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
                timeout=3.0,
            )
            self.use_memory = False
        except Exception as e:
            self.pool = None
            self.use_memory = True
            memory._ensure_demo_user()
            logger.warning(
                "PostgreSQL unavailable (%s); using in-memory job/user store.", e
            )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def execute(self, query: str, *args):
        if self.use_memory or self.pool is None:
            return handle_execute(query, *args)
        async with self.pool.acquire() as connection:
            return await connection.execute(query, *args)

    async def fetch(self, query: str, *args):
        if self.use_memory or self.pool is None:
            return []
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        if self.use_memory or self.pool is None:
            from backend.memory_store import handle_fetchrow

            return handle_fetchrow(query, *args)
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        if self.use_memory or self.pool is None:
            return handle_fetchval(query, *args)
        async with self.pool.acquire() as connection:
            return await connection.fetchval(query, *args)

    async def ensure_demo_user(self) -> None:
        if self.use_memory or self.pool is None:
            memory._ensure_demo_user()
            return
        try:
            await self.execute(
                "INSERT INTO users (username) VALUES ('testuser') ON CONFLICT (username) DO NOTHING"
            )
        except Exception:
            pass

db = Database()
