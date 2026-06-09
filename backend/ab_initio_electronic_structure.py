"""
Ab-initio electronic structure for Intel/AMD Windows and Linux.

Primary engine: **PyQInt** (prebuilt win_amd64 wheels) — runs restricted Hartree–Fock
in STO-3G, transforms AO integrals to the MO basis, and feeds qiskit-nature.

Optional upgrade: **PySCF** via WSL/Linux when installed.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from qiskit_nature.second_q.formats.molecule_info import MoleculeInfo
from qiskit_nature.second_q.hamiltonians import ElectronicEnergy
from qiskit_nature.second_q.operators.tensor_ordering import IndexType, to_physicist_ordering
from qiskit_nature.second_q.problems import ElectronicBasis, ElectronicStructureProblem
from qiskit_nature.second_q.properties import ParticleNumber


def pyqint_available() -> bool:
    try:
        import pyqint  # noqa: F401

        return True
    except ImportError:
        return False


def pyscf_available() -> bool:
    try:
        import pyscf  # noqa: F401

        return True
    except ImportError:
        return False


def ab_initio_available() -> bool:
    return pyqint_available() or pyscf_available()


def _molecule_info_to_pyqint(mi: MoleculeInfo):
    from pyqint import Molecule

    mol = Molecule(getattr(mi, "name", None) or "qbridge")
    charge = int(getattr(mi, "charge", 0) or 0)
    if charge:
        mol.set_charge(charge)
    for sym, coord in zip(mi.symbols, mi.coords):
        mol.add_atom(str(sym), float(coord[0]), float(coord[1]), float(coord[2]), unit="angstrom")
    return mol


def _ao_to_mo_integrals(
    hcore: np.ndarray,
    eri_ao: np.ndarray,
    mo_coeff: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Transform AO integrals to the MO basis (chemist ERIs)."""
    h1 = mo_coeff.T @ hcore @ mo_coeff
    eri_mo = np.einsum(
        "ip,jq,ijkl,kr,ls->pqrs",
        mo_coeff,
        mo_coeff,
        eri_ao,
        mo_coeff,
        mo_coeff,
        optimize=True,
    )
    return h1, eri_mo


def _problem_from_mo_integrals(
    h1: np.ndarray,
    eri_mo: np.ndarray,
    *,
    enuc: float,
    n_alpha: int,
    n_beta: int,
    mi: MoleculeInfo,
) -> ElectronicStructureProblem:
    eri_phys = to_physicist_ordering(eri_mo, index_order=IndexType.CHEMIST)
    electronic_energy = ElectronicEnergy.from_raw_integrals(
        h1, eri_phys, validate=False, auto_index_order=False
    )
    electronic_energy.nuclear_repulsion_energy = float(enuc)

    problem = ElectronicStructureProblem(electronic_energy)
    problem.basis = ElectronicBasis.MO
    problem.molecule = mi
    problem.num_particles = (int(n_alpha), int(n_beta))
    problem.num_spatial_orbitals = int(h1.shape[0])
    problem.properties.particle_number = ParticleNumber(int(h1.shape[0]))
    problem.reference_energy = None
    return problem


def _build_with_pyqint(
    mi: MoleculeInfo,
    *,
    basis: str = "sto3g",
) -> tuple[ElectronicStructureProblem, dict[str, Any]]:
    from pyqint import HF

    mol = _molecule_info_to_pyqint(mi)
    multiplicity = max(1, int(getattr(mi, "multiplicity", 1) or 1))

    hf = HF(mol, basis)
    if multiplicity == 1:
        res = hf.rhf(verbose=False, tolerance=1e-9)
        n_alpha = n_beta = int(res["nelec"]) // 2
    else:
        res = hf.uhf(multiplicity=multiplicity, verbose=False, tolerance=1e-9)
        ne = int(res["nelec"])
        n_unpaired = multiplicity - 1
        n_beta = (ne - n_unpaired) // 2
        n_alpha = n_beta + n_unpaired

    h1, eri_mo = _ao_to_mo_integrals(res["hcore"], res["tetensor"], res["orbc"])
    enuc = float(res["enucrep"])
    hf_energy = float(res["energy"])

    problem = _problem_from_mo_integrals(
        h1,
        eri_mo,
        enuc=enuc,
        n_alpha=n_alpha,
        n_beta=n_beta,
        mi=mi,
    )

    meta: dict[str, Any] = {
        "electronic_structure_driver": "PyQInt_HF",
        "basis": basis,
        "ab_initio": True,
        "simulation_mode": False,
        "windows_fallback": False,
        "windows_fallback_notes": "",
        "hf_reference_energy_ha": hf_energy,
        "nuclear_repulsion_energy": enuc,
        "charge": int(getattr(mi, "charge", 0) or 0),
        "multiplicity": multiplicity,
        "platform_note": "native_x86_pyqint",
    }
    return problem, meta


def _build_with_pyscf(
    mi: MoleculeInfo,
    *,
    basis: str = "sto3g",
) -> tuple[ElectronicStructureProblem, dict[str, Any]]:
    from qiskit_nature.second_q.drivers import PySCFDriver

    from .pyscf_electronic_structure import molecule_info_to_atom_string

    atom = molecule_info_to_atom_string(mi)
    charge = int(getattr(mi, "charge", 0) or 0)
    multiplicity = max(1, int(getattr(mi, "multiplicity", 1) or 1))
    spin = multiplicity - 1

    driver = PySCFDriver(atom=atom, basis=basis, charge=charge, spin=spin)
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
        "platform_note": "pyscf",
    }
    return problem, meta


def build_electronic_structure_problem(
    mi: MoleculeInfo,
    *,
    basis: str = "sto3g",
) -> tuple[ElectronicStructureProblem, dict[str, Any]]:
    """
    Build a qiskit-nature problem from **computed** Hartree–Fock integrals.

    Prefers PyQInt on native Windows x86; uses PySCF when available on Linux/WSL.
    """
    basis_key = basis.lower().replace("-", "")

    if pyqint_available():
        return _build_with_pyqint(mi, basis=basis_key)

    if pyscf_available():
        return _build_with_pyscf(mi, basis=basis)

    raise ImportError(
        "No ab-initio backend available. Install pyqint (Windows/Linux): pip install pyqint"
    )
