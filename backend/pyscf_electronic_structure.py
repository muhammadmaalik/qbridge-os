"""
Ab-initio electronic structure via PySCF (STO-3G RHF by default).

Runs on Intel/AMD x86_64 Windows when ``pyscf`` is installed. Integrals are
computed from the molecule geometry — not tabulated or hash-derived placeholders.
"""

from __future__ import annotations

from typing import Any

from qiskit_nature.second_q.formats.molecule_info import MoleculeInfo
from qiskit_nature.second_q.problems import ElectronicStructureProblem


def pyscf_available() -> bool:
    try:
        import pyscf  # noqa: F401

        return True
    except ImportError:
        return False


def molecule_info_to_atom_string(mi: MoleculeInfo) -> str:
    """PySCF atom spec: ``"H 0 0 0; O 0 0 1.2"`` (coordinates in Å)."""
    parts: list[str] = []
    for sym, coord in zip(mi.symbols, mi.coords):
        x, y, z = (float(coord[0]), float(coord[1]), float(coord[2]))
        parts.append(f"{sym} {x:.8f} {y:.8f} {z:.8f}")
    if not parts:
        raise ValueError("MoleculeInfo has no atoms")
    return "; ".join(parts)


def build_electronic_structure_problem(
    mi: MoleculeInfo,
    *,
    basis: str = "sto3g",
) -> tuple[ElectronicStructureProblem, dict[str, Any]]:
    """
    Hartree–Fock + integral extraction with :class:`PySCFDriver`.

    Returns the qiskit-nature problem and metadata marking this as ab-initio.
    """
    if not pyscf_available():
        raise ImportError(
            "pyscf is not installed. Install with: pip install pyscf"
        )

    from qiskit_nature.second_q.drivers import PySCFDriver

    atom = molecule_info_to_atom_string(mi)
    charge = int(getattr(mi, "charge", 0) or 0)
    multiplicity = max(1, int(getattr(mi, "multiplicity", 1) or 1))
    spin = multiplicity - 1  # PySCF: 2S (unpaired electrons)

    driver = PySCFDriver(
        atom=atom,
        basis=basis,
        charge=charge,
        spin=spin,
    )
    problem = driver.run()
    problem.molecule = mi

    meta: dict[str, Any] = {
        "electronic_structure_driver": "PySCFDriver",
        "basis": basis,
        "ab_initio": True,
        "simulation_mode": False,
        "windows_fallback": False,
        "windows_fallback_notes": "",
        "pyscf_atom": atom,
        "charge": charge,
        "multiplicity": multiplicity,
    }
    return problem, meta
