"""Lightweight system / telemetry for the Quantum OS dashboard."""

from __future__ import annotations

import random
from fastapi import APIRouter

from backend.telemetry import get_noise_telemetry

router = APIRouter()


@router.get("/status")
async def system_status():
    """Mock hardware noise + PQC surface (extend with real telemetry as needed)."""
    return {
        "pqc": {
            "algorithm": "CRYSTALS-Kyber-512-mock",
            "handshake_path": "/api/v1/security/handshake",
            "status": "ready",
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
