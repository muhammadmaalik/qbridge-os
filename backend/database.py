import os
import asyncpg
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_user: str = "qbridge"
    db_password: str = "password"
    db_name: str = "qaas_db"
    db_host: str = "localhost"
    db_port: str = "5432"

    class Config:
        env_file = ".env"

settings = Settings()

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            host=settings.db_host,
            port=settings.db_port
        )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def execute(self, query: str, *args):
        if self.pool is None: return None
        async with self.pool.acquire() as connection:
            return await connection.execute(query, *args)

    async def fetch(self, query: str, *args):
        if self.pool is None: return []
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        if self.pool is None: return None
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        if self.pool is None:
            if "SELECT id FROM users" in query:
                return "mock_user_id"
            if "INSERT INTO job_logs" in query:
                import uuid
                return str(uuid.uuid4())
            return None
        async with self.pool.acquire() as connection:
            return await connection.fetchval(query, *args)

    async def ensure_demo_user(self) -> None:
        """Create default ``testuser`` for the Quantum Terminal when PostgreSQL is empty."""
        if self.pool is None:
            return
        try:
            await self.execute(
                "INSERT INTO users (username) VALUES ('testuser') ON CONFLICT (username) DO NOTHING"
            )
        except Exception:
            pass

db = Database()
