from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from backend.user_auth import (
    authenticate_password,
    create_access_token,
    decode_access_token,
    register_user,
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


class AuthUserResponse(BaseModel):
    id: str
    email: str
    username: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "unknown"


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
async def register(payload: RegisterPayload, request: Request):
    try:
        user = await register_user(
            email=payload.email,
            password=payload.password,
            username=payload.username,
            client_ip=client_ip(request),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return AuthUserResponse(id=user.id, email=user.email, username=user.username)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginPayload):
    try:
        user = await authenticate_password(email=payload.email, password=payload.password)
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
