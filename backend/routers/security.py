"""PQC handshake endpoints and persistent session registry (file-backed)."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from threading import Lock

from fastapi import APIRouter
from pydantic import BaseModel

from backend.security_utils import kyber512_generate_keypair, kyber512_decapsulate

router = APIRouter()

# Module-scope Kyber-like keypair (simulates hardware-backed PQC root of trust)
_PQC_PUBLIC_KEY, _PQC_SECRET_KEY = kyber512_generate_keypair()

# session_id -> shared_secret_hex (matches client encapsulation output)
_sessions: dict[str, str] = {}
_sessions_lock = Lock()

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SESSIONS_FILE = _PROJECT_ROOT / ".qbridge_pqc_sessions.json"
SESSIONS_FILE = Path(
    os.environ.get("QBRIDGE_PQC_SESSIONS_PATH", str(_DEFAULT_SESSIONS_FILE))
)


def _load_sessions_from_disk() -> None:
    global _sessions
    if not SESSIONS_FILE.is_file():
        return
    try:
        raw = SESSIONS_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            with _sessions_lock:
                for k, v in data.items():
                    if isinstance(k, str) and isinstance(v, str) and len(k) > 8:
                        _sessions[k] = v
    except (OSError, json.JSONDecodeError):
        pass


def _persist_sessions_unlocked() -> None:
    try:
        SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSIONS_FILE.write_text(json.dumps(_sessions, indent=0), encoding="utf-8")
    except OSError:
        pass


_load_sessions_from_disk()


class HandshakeRequest(BaseModel):
    ciphertext: str


class HandshakeResponse(BaseModel):
    session_id: str
    algorithm: str


@router.get("/pqc-public-key")
async def get_pqc_public_key():
    return {
        "algorithm": "CRYSTALS-Kyber-512-mock",
        "public_key": _PQC_PUBLIC_KEY,
    }


@router.post("/handshake", response_model=HandshakeResponse)
async def pqc_handshake(body: HandshakeRequest):
    """Client encapsulates against our public key; we decapsulate and open a session."""
    shared_secret_hex = kyber512_decapsulate(_PQC_SECRET_KEY, body.ciphertext)
    session_id = secrets.token_urlsafe(24)
    with _sessions_lock:
        _sessions[session_id] = shared_secret_hex
        _persist_sessions_unlocked()
    return HandshakeResponse(session_id=session_id, algorithm="CRYSTALS-Kyber-512-mock")


@router.get("/session/{session_id}/valid")
async def session_valid(session_id: str):
    """Return whether a persisted session id is still known to the gateway."""
    with _sessions_lock:
        ok = session_id in _sessions
    return {"valid": ok, "session_id": session_id}


def _skip_pqc_verify_enabled() -> bool:
    return os.environ.get("QBRIDGE_SKIP_PQC_VERIFY", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def verify_simulation_request(session_id: str | None, mac_hex: str | None, canonical_message: str) -> bool:
    """Returns True only if the session exists and the MAC matches.

    For local testing without PQC handshake headers, set ``QBRIDGE_SKIP_PQC_VERIFY=1``
    in the environment (never enable in production-facing deployments).
    """
    if _skip_pqc_verify_enabled():
        return True
    if not session_id or not mac_hex:
        return False
    with _sessions_lock:
        secret = _sessions.get(session_id)
    if not secret:
        return False
    from backend.security_utils import verify_mac

    return verify_mac(secret, canonical_message, mac_hex)


def consume_session(session_id: str) -> None:
    """Optional: invalidate after use. Currently sessions persist for demo UX."""
    with _sessions_lock:
        _sessions.pop(session_id, None)
        _persist_sessions_unlocked()
