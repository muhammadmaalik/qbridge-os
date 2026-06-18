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
    email: str | None = None
    password_hash: str | None = None


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
        self.users_by_email: dict[str, MemoryUser] = {}
        self.jobs: dict[str, MemoryJob] = {}
        self.api_keys: dict[tuple[str, str], str] = {}  # (user_id, provider) -> key
        self.registration_ips: list[tuple[str, str]] = []
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

    def create_auth_user(
        self, *, uid: str, username: str, email: str, password_hash: str
    ) -> str:
        u = MemoryUser(
            id=uid, username=username, email=email, password_hash=password_hash
        )
        self.users_by_name[username] = u
        self.users_by_id[uid] = u
        self.users_by_email[email] = u
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

    def count_registrations_by_ip(self, ip: str) -> int:
        return sum(1 for registered_ip, _ in self.registration_ips if registered_ip == ip)

    def record_registration_ip(self, ip: str, user_id: str) -> None:
        self.registration_ips.append((ip, user_id))


memory = InMemoryStore()


def _parse_username(query: str, args: tuple) -> str | None:
    m = re.search(r"username\s*=\s*\$\d+", query, re.I)
    if m and args:
        return str(args[0])
    return None


def handle_fetchrow(query: str, *args: Any) -> dict[str, Any] | None:
    q = " ".join(query.split())
    if "SELECT id FROM users" in q and "email" in q:
        email = str(args[0]).lower() if args else ""
        u = memory.users_by_email.get(email)
        return {"id": u.id} if u else None
    if "SELECT id FROM users" in q and "username" in q:
        uname = str(args[0]) if args else ""
        u = memory.users_by_name.get(uname)
        return {"id": u.id} if u else None
    if "FROM users WHERE email" in q and "password_hash" in q:
        email = str(args[0]).lower() if args else ""
        u = memory.users_by_email.get(email)
        if not u:
            return None
        return {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "password_hash": u.password_hash,
        }
    if "FROM users WHERE id" in q and "password_hash" in q:
        uid = str(args[0]) if args else ""
        u = memory.users_by_id.get(uid)
        if not u or not u.email:
            return None
        return {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "password_hash": u.password_hash,
        }
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

    if "FROM registration_ips" in q and "COUNT" in q.upper():
        ip = str(args[0]) if args else ""
        return memory.count_registrations_by_ip(ip)

    if "INSERT INTO registration_ips" in q:
        ip = str(args[0]) if args else ""
        user_id = str(args[1]) if len(args) > 1 else ""
        memory.record_registration_ip(ip, user_id)
        return "OK"

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
