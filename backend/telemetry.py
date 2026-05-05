"""Last-run telemetry for dashboard (noise injection, etc.)."""

from __future__ import annotations

from threading import Lock

_lock = Lock()
_noise: dict = {
    "active": False,
    "level": "off",
    "profile": None,
    "readout_error_e3": None,
    "gate_error_e3": None,
}


def set_noise_telemetry(
    *,
    active: bool,
    profile: str | None = None,
    level: str | None = None,
    readout_error_e3: float | None = None,
    gate_error_e3: float | None = None,
) -> None:
    with _lock:
        _noise["active"] = active
        _noise["profile"] = profile
        _noise["level"] = level or ("simulated-device" if active else "off")
        _noise["readout_error_e3"] = readout_error_e3
        _noise["gate_error_e3"] = gate_error_e3


def get_noise_telemetry() -> dict:
    with _lock:
        return dict(_noise)
