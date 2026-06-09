"""
Public SDK surface for qbridge-os.

    from qbridge import run_vqe, optimize_portfolio
"""

from __future__ import annotations

import asyncio
from typing import Any

from backend.quantum_finance import optimize_portfolio


async def run_vqe_async(
    *,
    structure: str | None = None,
    smiles: str | None = None,
    smiles_a: str | None = None,
    smiles_b: str | None = None,
    distance_angstrom: float = 2.0,
    charge: int = 0,
    max_qubits: int = 12,
    vqe_maxiter: int = 50,
    noise: bool = False,
) -> dict[str, Any]:
    """Run the full chemistry → VQE pipeline (same as POST /compute/molecule/sync)."""
    from backend.quantum_router import QuantumRouter

    payload: dict[str, Any] = {
        "structure": structure,
        "smiles": smiles,
        "smiles_a": smiles_a,
        "smiles_b": smiles_b,
        "distance_angstrom": distance_angstrom,
        "charge": charge,
        "max_qubits": max_qubits,
        "vqe_maxiter": vqe_maxiter,
        "hardware_provider": "local",
        "noise": noise,
    }
    return await QuantumRouter().simulate_molecule("sdk", payload)


def run_vqe(
    *,
    structure: str | None = None,
    smiles: str | None = None,
    smiles_a: str | None = None,
    smiles_b: str | None = None,
    distance_angstrom: float = 2.0,
    charge: int = 0,
    max_qubits: int = 12,
    vqe_maxiter: int = 50,
    noise: bool = False,
) -> dict[str, Any]:
    """Synchronous wrapper around :func:`run_vqe_async`."""
    return asyncio.run(
        run_vqe_async(
            structure=structure,
            smiles=smiles,
            smiles_a=smiles_a,
            smiles_b=smiles_b,
            distance_angstrom=distance_angstrom,
            charge=charge,
            max_qubits=max_qubits,
            vqe_maxiter=vqe_maxiter,
            noise=noise,
        )
    )


__all__ = ["run_vqe", "run_vqe_async", "optimize_portfolio"]
