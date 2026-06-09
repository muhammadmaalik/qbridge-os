from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from backend.user_auth import (
    OTP_EXPIRE_MINUTES,
    authenticate_password,
    create_access_token,
    decode_access_token,
    register_user,
    start_login_otp,
    verify_login_otp,
)

router = APIRouter(tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


class RegisterPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    username: str | None = Field(default=None, min_length=2, max_length=64)


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class VerifyOtpPayload(BaseModel):
    challenge_id: str
    otp: str = Field(min_length=6, max_length=6)


class AuthUserResponse(BaseModel):
    id: str
    email: str
    username: str


class LoginStepResponse(BaseModel):
    status: str = "otp_required"
    challenge_id: str
    message: str
    expires_in_seconds: int
    dev_otp: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthUserResponse:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Sign in required")
    try:
        payload = decode_access_token(creds.credentials)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    return AuthUserResponse(
        id=str(payload["sub"]),
        email=str(payload["email"]),
        username=str(payload["username"]),
    )


@router.post("/register", response_model=AuthUserResponse)
async def register(payload: RegisterPayload):
    try:
        user = await register_user(
            email=payload.email,
            password=payload.password,
            username=payload.username,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return AuthUserResponse(id=user.id, email=user.email, username=user.username)


@router.post("/login", response_model=LoginStepResponse)
async def login(payload: LoginPayload):
    try:
        user = await authenticate_password(email=payload.email, password=payload.password)
        challenge_id, dev_otp = await start_login_otp(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    dev_mode = os.environ.get("QBRIDGE_AUTH_DEV_LOG_OTP", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    message = f"A 6-digit security code was sent to {user.email}."
    if dev_mode and dev_otp:
        message = (
            f"Development mode: your verification code is {dev_otp}. "
            "Configure SMTP on the server to send codes by email."
        )

    return LoginStepResponse(
        challenge_id=challenge_id,
        message=message,
        expires_in_seconds=OTP_EXPIRE_MINUTES * 60,
        dev_otp=dev_otp if dev_mode else None,
    )


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(payload: VerifyOtpPayload):
    try:
        user = await verify_login_otp(challenge_id=payload.challenge_id, otp=payload.otp)
        token = create_access_token(
            user_id=user.id, email=user.email, username=user.username
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    return TokenResponse(
        access_token=token,
        user=AuthUserResponse(id=user.id, email=user.email, username=user.username),
    )


@router.get("/me", response_model=AuthUserResponse)
async def me(user: AuthUserResponse = Depends(get_current_user)):
    return user


class APIKeyPayload(BaseModel):
    username: str
    service_provider: str = "IBM"
    api_key: str


@router.post("/keys")
async def save_api_key(payload: APIKeyPayload):
    from backend.database import db

    user_id = await db.fetchval("SELECT id FROM users WHERE username = $1", payload.username)
    if not user_id:
        user_id = await db.fetchval(
            "INSERT INTO users (username) VALUES ($1) RETURNING id",
            payload.username,
        )

    encrypted_key = payload.api_key

    query = """
        INSERT INTO api_credentials (user_id, service_provider, encrypted_api_key)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id, service_provider)
        DO UPDATE SET encrypted_api_key = EXCLUDED.encrypted_api_key
        RETURNING id
    """
    try:
        cred_id = await db.fetchval(query, user_id, payload.service_provider, encrypted_key)
        return {"status": "success", "message": "API Key saved securely.", "credential_id": cred_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
