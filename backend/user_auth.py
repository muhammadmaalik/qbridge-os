"""Password hashing, JWT sessions, and email OTP two-factor authentication."""

from __future__ import annotations

import hashlib
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from backend.database import db
from backend.email_service import send_otp_email

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.environ.get("QBRIDGE_JWT_EXPIRE_HOURS", "24"))
OTP_EXPIRE_MINUTES = int(os.environ.get("QBRIDGE_OTP_EXPIRE_MINUTES", "10"))
OTP_MAX_ATTEMPTS = int(os.environ.get("QBRIDGE_OTP_MAX_ATTEMPTS", "5"))


def jwt_secret() -> str:
    secret = os.environ.get("QBRIDGE_JWT_SECRET", "").strip()
    if not secret:
        secret = "qbridge-dev-insecure-jwt-secret-change-in-production"
    return secret


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def _generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


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


@dataclass
class OtpChallenge:
    id: str
    user_id: str
    email: str
    username: str
    otp_hash: str
    expires_at: datetime
    attempts: int = 0


# In-memory OTP challenges (also used when Postgres is offline)
_otp_challenges: dict[str, OtpChallenge] = {}


async def register_user(*, email: str, password: str, username: str | None = None) -> UserRecord:
    email_norm = email.strip().lower()
    if not email_norm or "@" not in email_norm:
        raise ValueError("A valid email address is required")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    uname = (username or email_norm.split("@")[0]).strip().lower()
    if not uname:
        raise ValueError("Username is required")

    pw_hash = hash_password(password)

    if db.use_memory or db.pool is None:
        from backend.memory_store import memory

        if email_norm in memory.users_by_email:
            raise ValueError("An account with this email already exists")
        if uname in memory.users_by_name:
            raise ValueError("Username already taken")
        uid = str(uuid.uuid4())
        memory.create_auth_user(uid=uid, username=uname, email=email_norm, password_hash=pw_hash)
        return UserRecord(id=uid, username=uname, email=email_norm, password_hash=pw_hash)

    existing = await db.fetchrow("SELECT id FROM users WHERE email = $1", email_norm)
    if existing:
        raise ValueError("An account with this email already exists")
    existing_u = await db.fetchrow("SELECT id FROM users WHERE username = $1", uname)
    if existing_u:
        raise ValueError("Username already taken")

    row = await db.fetchrow(
        """
        INSERT INTO users (username, email, password_hash, email_verified)
        VALUES ($1, $2, $3, FALSE)
        RETURNING id, username, email, password_hash
        """,
        uname,
        email_norm,
        pw_hash,
    )
    if not row:
        raise ValueError("Could not create account")
    return UserRecord(
        id=str(row["id"]),
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


async def start_login_otp(user: UserRecord) -> str:
    """Create OTP challenge, email the code, return challenge_id."""
    otp = _generate_otp()
    challenge_id = secrets.token_urlsafe(24)
    expires = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
    challenge = OtpChallenge(
        id=challenge_id,
        user_id=user.id,
        email=user.email,
        username=user.username,
        otp_hash=_hash_otp(otp),
        expires_at=expires,
    )
    _otp_challenges[challenge_id] = challenge

    if not db.use_memory and db.pool is not None:
        await db.execute(
            """
            INSERT INTO login_otp_challenges (id, user_id, otp_hash, expires_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (id) DO UPDATE SET otp_hash = EXCLUDED.otp_hash, expires_at = EXCLUDED.expires_at, attempts = 0
            """,
            challenge_id,
            user.id,
            challenge.otp_hash,
            expires,
        )

    send_otp_email(to_email=user.email, otp_code=otp, username=user.username)
    return challenge_id


async def verify_login_otp(*, challenge_id: str, otp: str) -> UserRecord:
    otp_clean = otp.strip()
    if len(otp_clean) != 6 or not otp_clean.isdigit():
        raise ValueError("Enter the 6-digit code from your email")

    challenge = _otp_challenges.get(challenge_id)
    if challenge is None and not db.use_memory and db.pool is not None:
        row = await db.fetchrow(
            "SELECT id, user_id, otp_hash, expires_at, attempts FROM login_otp_challenges WHERE id = $1",
            challenge_id,
        )
        if row:
            challenge = OtpChallenge(
                id=challenge_id,
                user_id=str(row["user_id"]),
                email="",
                username="",
                otp_hash=row["otp_hash"],
                expires_at=row["expires_at"],
                attempts=int(row["attempts"]),
            )

    if challenge is None:
        raise ValueError("Login session expired — sign in again")

    now = datetime.now(timezone.utc)
    exp = challenge.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if now > exp:
        _otp_challenges.pop(challenge_id, None)
        raise ValueError("Verification code expired — sign in again")

    challenge.attempts += 1
    if challenge.attempts > OTP_MAX_ATTEMPTS:
        _otp_challenges.pop(challenge_id, None)
        raise ValueError("Too many attempts — sign in again")

    if _hash_otp(otp_clean) != challenge.otp_hash:
        if not db.use_memory and db.pool is not None:
            await db.execute(
                "UPDATE login_otp_challenges SET attempts = attempts + 1 WHERE id = $1",
                challenge_id,
            )
        raise ValueError("Incorrect verification code")

    _otp_challenges.pop(challenge_id, None)
    if not db.use_memory and db.pool is not None:
        await db.execute("DELETE FROM login_otp_challenges WHERE id = $1", challenge_id)

    user = await _get_user_by_id(challenge.user_id)
    if not user:
        raise ValueError("User account not found")
    return user


async def _get_user_by_email(email: str) -> UserRecord | None:
    if db.use_memory or db.pool is None:
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


async def _get_user_by_id(user_id: str) -> UserRecord | None:
    if db.use_memory or db.pool is None:
        from backend.memory_store import memory

        u = memory.users_by_id.get(user_id)
        if not u or not u.email or not u.password_hash:
            return None
        return UserRecord(id=u.id, username=u.username, email=u.email, password_hash=u.password_hash)

    row = await db.fetchrow(
        "SELECT id, username, email, password_hash FROM users WHERE id = $1",
        user_id,
    )
    if not row or not row["password_hash"]:
        return None
    return UserRecord(
        id=str(row["id"]),
        username=row["username"],
        email=row["email"],
        password_hash=row["password_hash"],
    )
