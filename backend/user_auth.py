"""Password hashing, JWT sessions, and user registration."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from backend.database import db

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.environ.get("QBRIDGE_JWT_EXPIRE_HOURS", "24"))
MAX_REGISTRATIONS_PER_IP = int(os.environ.get("QBRIDGE_MAX_REGS_PER_IP", "3"))


def jwt_secret() -> str:
    secret = os.environ.get("QBRIDGE_JWT_SECRET", "").strip()
    if not secret:
        secret = "qbridge-dev-insecure-jwt-secret-change-in-production"
    return secret


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(*, user_id: str, email: str, username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "username": username,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=JWT_EXPIRE_HOURS)).timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, jwt_secret(), algorithms=[JWT_ALGORITHM])
    except JWTError as e:
        raise ValueError("Invalid or expired session token") from e
    if payload.get("type") != "access" or not payload.get("sub"):
        raise ValueError("Invalid session token")
    return payload


@dataclass
class UserRecord:
    id: str
    username: str
    email: str
    password_hash: str


async def register_user(
    *,
    email: str,
    password: str,
    username: str | None = None,
    client_ip: str,
) -> UserRecord:
    email_norm = email.strip().lower()
    if not email_norm or "@" not in email_norm:
        raise ValueError("A valid email address is required")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    uname = (username or email_norm.split("@")[0]).strip().lower()
    if not uname:
        raise ValueError("Username is required")

    ip = (client_ip or "unknown").strip()
    reg_count = await _count_registrations_by_ip(ip)
    if reg_count >= MAX_REGISTRATIONS_PER_IP:
        raise ValueError(
            f"Too many accounts registered from this network (limit {MAX_REGISTRATIONS_PER_IP})"
        )

    pw_hash = hash_password(password)
    user_id = str(uuid.uuid4())

    if db.use_memory:
        from backend.memory_store import memory

        if email_norm in memory.users_by_email:
            raise ValueError("An account with this email already exists")
        if uname in memory.users_by_name:
            raise ValueError("Username already taken")
        uid = str(uuid.uuid4())
        memory.create_auth_user(uid=uid, username=uname, email=email_norm, password_hash=pw_hash)
        memory.record_registration_ip(ip, uid)
        return UserRecord(id=uid, username=uname, email=email_norm, password_hash=pw_hash)

    existing = await db.fetchrow("SELECT id FROM users WHERE email = $1", email_norm)
    if existing:
        raise ValueError("An account with this email already exists")
    existing_u = await db.fetchrow("SELECT id FROM users WHERE username = $1", uname)
    if existing_u:
        raise ValueError("Username already taken")

    row = await db.fetchrow(
        """
        INSERT INTO users (id, username, email, password_hash, email_verified)
        VALUES ($1, $2, $3, $4, TRUE)
        RETURNING id, username, email, password_hash
        """,
        user_id,
        uname,
        email_norm,
        pw_hash,
    )
    if not row:
        raise ValueError("Could not create account")

    await db.execute(
        "INSERT INTO registration_ips (ip_address, user_id) VALUES ($1, $2)",
        ip,
        user_id,
    )
    return UserRecord(
        id=user_id,
        username=row["username"],
        email=row["email"],
        password_hash=row["password_hash"],
    )


async def authenticate_password(*, email: str, password: str) -> UserRecord:
    email_norm = email.strip().lower()
    user = await _get_user_by_email(email_norm)
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password")
    return user


async def _count_registrations_by_ip(ip: str) -> int:
    if db.use_memory:
        from backend.memory_store import memory

        return memory.count_registrations_by_ip(ip)

    val = await db.fetchval(
        "SELECT COUNT(*) FROM registration_ips WHERE ip_address = $1",
        ip,
    )
    return int(val or 0)


async def _get_user_by_email(email: str) -> UserRecord | None:
    if db.use_memory:
        from backend.memory_store import memory

        u = memory.users_by_email.get(email)
        if not u or not u.password_hash:
            return None
        return UserRecord(id=u.id, username=u.username, email=u.email, password_hash=u.password_hash)

    row = await db.fetchrow(
        "SELECT id, username, email, password_hash FROM users WHERE email = $1",
        email,
    )
    if not row or not row["password_hash"]:
        return None
    return UserRecord(
        id=str(row["id"]),
        username=row["username"],
        email=row["email"],
        password_hash=row["password_hash"],
    )
