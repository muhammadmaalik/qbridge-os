"""Lightweight system / telemetry for the Quantum OS dashboard."""

from __future__ import annotations

import os
import random
from fastapi import APIRouter

from backend.database import db
from backend.routers.security import _skip_pqc_verify_enabled
from backend.telemetry import get_noise_telemetry

router = APIRouter()

BUILD_ID = os.environ.get("RENDER_GIT_COMMIT", "local-dev")[:12]


@router.get("/version")
async def system_version():
    """Deployment fingerprint — use after Render redeploy to confirm the live API is current."""
    return {
        "service": "Quantum Bridge OS API",
        "build_id": BUILD_ID,
        "auth_routes": True,
        "features": [
            "auth_register_login",
            "chemistry_vqe_pyqint",
            "finance_qaoa",
            "pqc_handshake",
            "rate_limiting",
            "ip_registration_limit",
        ],
        "user_store": "memory" if db.use_memory else "postgres" if db.pool else "sqlite",
        "max_registrations_per_ip": int(os.environ.get("QBRIDGE_MAX_REGS_PER_IP", "3")),
    }


@router.get("/status")
async def system_status():
    """Mock hardware noise + PQC surface (extend with real telemetry as needed)."""
    return {
        "pqc": {
            "algorithm": "CRYSTALS-Kyber-512-mock",
            "handshake_path": "/api/v1/security/handshake",
            "status": "ready",
            # Dev-only bypass: True if QBRIDGE_SKIP_PQC_VERIFY is set. Lets the
            # frontend / Swagger user see whether the /compute/* routes are
            # currently accepting unsigned requests.
            "dev_bypass_active": _skip_pqc_verify_enabled(),
            "dev_bypass_env_var": "QBRIDGE_SKIP_PQC_VERIFY",
        },
        "noise_model": {
            "t1_us": round(80 + random.uniform(-15, 25), 1),
            "t2_us": round(45 + random.uniform(-10, 15), 1),
            "readout_error_e3": round(random.uniform(1.2, 4.5), 2),
            "gate_error_e3": round(random.uniform(0.8, 2.8), 2),
        },
        "noise_injection": get_noise_telemetry(),
        "runtime": {"service": "Quantum Bridge OS", "version": "1.0.0"},
    }
