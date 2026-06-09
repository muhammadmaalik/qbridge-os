"""Step-by-step H2 VQE pipeline tracer (run from qbridge-os root)."""
from __future__ import annotations

import asyncio
import sys
import traceback

ROOT = __file__
for _ in range(3):
    ROOT = __import__("os").path.dirname(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def step(name: str) -> None:
    print(f"\n=== {name} ===", flush=True)


async def main() -> None:
    payload = {"structure": "H2", "max_qubits": 12, "hardware_provider": "local"}

    step("0. import pyscf")
    try:
        import pyscf  # noqa: F401

        print("pyscf OK", pyscf.__version__)
    except ImportError as e:
        print("FAIL:", e)
        traceback.print_exc()
        return

    step("0b. import rdkit")
    try:
        import rdkit  # noqa: F401

        print("rdkit OK")
    except ImportError as e:
        print("FAIL:", e)
        traceback.print_exc()
        return

    step("1. resolve geometry")
    try:
        from backend.chemistry_mapper import resolve_molecule_geometry

        mi, meta = resolve_molecule_geometry(structure="H2", charge=0)
        print("symbols:", mi.symbols, "coords:", len(mi.coords), meta.get("resolution_path"))
    except Exception:
        traceback.print_exc()
        return

    step("2. build qubit operator (PySCF + JW)")
    try:
        from backend.chemistry_mapper import build_qubit_operator_from_chemical_input

        obs, mi2, chem = build_qubit_operator_from_chemical_input(
            structure="H2", max_qubits=12, mapper_kind="jordan_wigner"
        )
        print("qubits:", obs.num_qubits, "driver:", chem.get("electronic_structure_driver"))
    except Exception:
        traceback.print_exc()
        return

    step("3. VQE SLSQP")
    try:
        from backend.quantum_router import run_local_vqe_slsqp

        vqe = run_local_vqe_slsqp(obs, maxiter=50)
        print("energy:", vqe["energy"], "converged:", vqe["converged"])
    except Exception:
        traceback.print_exc()
        return

    step("4. full simulate_molecule")
    try:
        from backend.quantum_router import QuantumRouter

        result = await QuantumRouter().simulate_molecule("trace", payload)
        print("energy:", result.get("energy"), "backend:", result.get("backend"))
    except Exception:
        traceback.print_exc()
        return

    print("\nALL STEPS OK")


if __name__ == "__main__":
    asyncio.run(main())
