"""
In-memory persistence when PostgreSQL is unavailable (local dev / hackathon).
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryUser:
    id: str
    username: str


@dataclass
class MemoryJob:
    id: str
    user_id: str
    job_type: str
    status: str
    execution_time_ms: int | None = None
    hardware_backend_used: str | None = None


class InMemoryStore:
    def __init__(self) -> None:
        self.users_by_name: dict[str, MemoryUser] = {}
        self.users_by_id: dict[str, MemoryUser] = {}
        self.jobs: dict[str, MemoryJob] = {}
        self.api_keys: dict[tuple[str, str], str] = {}  # (user_id, provider) -> key
        self._ensure_demo_user()

    def _ensure_demo_user(self) -> None:
        if "testuser" not in self.users_by_name:
            uid = str(uuid.uuid4())
            u = MemoryUser(id=uid, username="testuser")
            self.users_by_name["testuser"] = u
            self.users_by_id[uid] = u

    def get_user_id(self, username: str) -> str | None:
        u = self.users_by_name.get(username)
        return u.id if u else None

    def create_user(self, username: str) -> str:
        if username in self.users_by_name:
            return self.users_by_name[username].id
        uid = str(uuid.uuid4())
        u = MemoryUser(id=uid, username=username)
        self.users_by_name[username] = u
        self.users_by_id[uid] = u
        return uid

    def create_job(self, user_id: str, job_type: str, status: str = "PENDING") -> str:
        jid = str(uuid.uuid4())
        self.jobs[jid] = MemoryJob(
            id=jid, user_id=user_id, job_type=job_type, status=status
        )
        return jid

    def update_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        execution_time_ms: int | None = None,
        hardware_backend_used: str | None = None,
    ) -> None:
        j = self.jobs.get(job_id)
        if not j:
            return
        if status is not None:
            j.status = status
        if execution_time_ms is not None:
            j.execution_time_ms = execution_time_ms
        if hardware_backend_used is not None:
            j.hardware_backend_used = hardware_backend_used

    def get_api_key(self, user_id: str, provider: str) -> str | None:
        return self.api_keys.get((user_id, provider.upper()))

    def upsert_api_key(self, user_id: str, provider: str, key: str) -> str:
        self.api_keys[(user_id, provider.upper())] = key
        return str(uuid.uuid4())


memory = InMemoryStore()


def _parse_username(query: str, args: tuple) -> str | None:
    m = re.search(r"username\s*=\s*\$\d+", query, re.I)
    if m and args:
        return str(args[0])
    return None


def handle_fetchval(query: str, *args: Any) -> Any:
    q = " ".join(query.split())
    if "SELECT id FROM users" in q and "username" in q:
        uname = _parse_username(q, args) or (str(args[0]) if args else None)
        if not uname:
            return None
        uid = memory.get_user_id(uname)
        if uid:
            return uid
        return memory.create_user(uname)

    if "INSERT INTO users" in q and "RETURNING id" in q:
        uname = str(args[0]) if args else "user"
        return memory.create_user(uname)

    if "INSERT INTO job_logs" in q and "RETURNING id" in q:
        user_id = str(args[0]) if args else memory.users_by_name["testuser"].id
        job_type = str(args[1]) if len(args) > 1 else "SIMULATION"
        return memory.create_job(user_id, job_type)

    if "SELECT encrypted_api_key FROM api_credentials" in q:
        user_id = str(args[0]) if args else ""
        provider = str(args[1]) if len(args) > 1 else "IBM"
        return memory.get_api_key(user_id, provider)

    if "INSERT INTO api_credentials" in q and "RETURNING id" in q:
        user_id = str(args[0]) if args else ""
        provider = str(args[1]) if len(args) > 1 else "IBM"
        key = str(args[2]) if len(args) > 2 else ""
        return memory.upsert_api_key(user_id, provider, key)

    return None


def handle_execute(query: str, *args: Any) -> str | None:
    q = " ".join(query.split())
    if "UPDATE job_logs SET status" in q:
        if "FAILED" in q:
            job_id = str(args[-1]) if args else ""
            memory.update_job(job_id, status="FAILED")
        elif "COMPLETED" in q or "RUNNING" in q:
            if "RUNNING" in q:
                job_id = str(args[-1]) if args else ""
                memory.update_job(job_id, status="RUNNING")
            else:
                # COMPLETED with execution_time_ms
                if len(args) >= 2:
                    et = int(args[0]) if args[0] is not None else None
                    job_id = str(args[-1])
                    memory.update_job(
                        job_id,
                        status="COMPLETED",
                        execution_time_ms=et,
                        hardware_backend_used="ibm_brisbane_sim",
                    )
        return "OK"
    if "INSERT INTO users" in q:
        uname = str(args[0]) if args else "testuser"
        memory.create_user(uname)
        return "OK"
    return None
