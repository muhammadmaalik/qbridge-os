"""
Windows / no-PySCF fallback: build :class:`ElectronicStructureProblem` from tabulated or synthetic MO integrals.
"""

from __future__ import annotations

import hashlib
import numpy as np

from qiskit_nature.second_q.hamiltonians import ElectronicEnergy
from qiskit_nature.second_q.operators.tensor_ordering import IndexType, to_physicist_ordering
from qiskit_nature.second_q.problems import ElectronicBasis, ElectronicStructureProblem
from qiskit_nature.second_q.properties import ParticleNumber

# --- Exact H2 (STO-3G, R = 1.4 Bohr) -------------------------------------------------
_H2_H1 = np.array(
    [
        [-1.12041067, -0.95838123],
        [-0.95838123, -1.12041067],
    ],
    dtype=np.float64,
)

_H2_ERI = np.zeros((2, 2, 2, 2), dtype=np.float64)


def _fill_h2_eri() -> None:
    v = _H2_ERI
    v[0, 0, 0, 0] = v[1, 1, 1, 1] = 0.7746079055149173
    v[0, 0, 1, 1] = v[1, 1, 0, 0] = 0.5696774985883134
    v[0, 1, 0, 1] = v[1, 0, 1, 0] = 0.29702949599279366
    x = 0.44410895821293
    v[0, 0, 0, 1] = v[0, 0, 1, 0] = v[0, 1, 0, 0] = v[1, 0, 0, 0] = x
    v[1, 1, 0, 1] = v[1, 1, 1, 0] = v[1, 0, 1, 1] = v[0, 1, 1, 1] = x
    v[0, 1, 1, 0] = v[1, 0, 0, 1] = 0.29702949599279366


_fill_h2_eri()
_H2_ENUC = 1.0 / 1.4
_BOHR_PER_ANGSTROM = 1.0 / 0.529177249


def _pairwise_enuc(
    symbols: list[str], coords: list[tuple[float, float, float]], charges: list[float] | None = None
) -> float:
    zmap = {
        "H": 1.0,
        "LI": 3.0,
        "NA": 11.0,
        "BE": 4.0,
        "B": 5.0,
        "C": 6.0,
        "N": 7.0,
        "O": 8.0,
        "F": 9.0,
        "P": 15.0,
        "S": 16.0,
        "CL": 17.0,
    }
    if charges is None:
        charges = [zmap.get(s.upper(), 1.0) for s in symbols]
    en = 0.0
    n = len(symbols)
    for i in range(n):
        for j in range(i + 1, n):
            xi, yi, zi = coords[i]
            xj, yj, zj = coords[j]
            dx = (xi - xj) * _BOHR_PER_ANGSTROM
            dy = (yi - yj) * _BOHR_PER_ANGSTROM
            dz = (zi - zj) * _BOHR_PER_ANGSTROM
            r = max(np.sqrt(dx * dx + dy * dy + dz * dz), 1e-12)
            en += charges[i] * charges[j] / r
    return float(en)


def _synthetic_mo_integrals(
    n_so: int, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    """Deterministic MO-like one- and two-body tensors for Windows fallback (qualitative only)."""
    rng = np.random.default_rng(seed)
    h1 = np.diag(np.linspace(-2.1, -0.35, n_so, dtype=np.float64))
    h1 += 0.03 * (rng.standard_normal((n_so, n_so)) + rng.standard_normal((n_so, n_so)).T) / 2.0
    eri = np.zeros((n_so, n_so, n_so, n_so), dtype=np.float64)
    for i in range(n_so):
        eri[i, i, i, i] = 0.52 + 0.04 * i
    for _ in range(max(1, n_so * n_so // 2)):
        i, j, k, l = (
            int(rng.integers(0, n_so)),
            int(rng.integers(0, n_so)),
            int(rng.integers(0, n_so)),
            int(rng.integers(0, n_so)),
        )
        v = 0.02 * rng.standard_normal()
        eri[i, j, k, l] = eri[j, i, k, l] = eri[i, j, l, k] = eri[j, i, l, k] = v
    return h1, eri


class FallbackElectronicStructureDriver:
    """PySCF substitute: tabulated small molecules or synthetic MO tensors for arbitrary stoichiometry."""

    def __init__(
        self,
        formula_key: str,
        symbols: list[str],
        coords: list[tuple[float, float, float]],
        *,
        n_electrons: int | None = None,
        multiplicity: int = 1,
    ):
        self.formula_key = formula_key.strip().upper() or "GENERIC"
        self.symbols = symbols
        self.coords = coords
        self.n_electrons = n_electrons
        self.multiplicity = multiplicity

    def run(self) -> ElectronicStructureProblem:
        key = self.formula_key

        if key == "H2" and len(self.symbols) == 2:
            h1 = _H2_H1.copy()
            eri = _H2_ERI.copy()
            enuc = _H2_ENUC
            n_alpha, n_beta = 1, 1
            notes = "full_tabulated_sto3g_h2_r1.4bohr"
        elif key in ("LIH", "H2O") and len(self.symbols) <= 3:
            h1 = _H2_H1.copy()
            eri = _H2_ERI.copy()
            enuc = _pairwise_enuc(self.symbols, list(self.coords))
            n_alpha, n_beta = 2, 2
            notes = f"minimal_2orb_proxy_{key}_install_pyscf_for_real_integrals"
        else:
            ne = int(self.n_electrons or sum(_element_z(s) for s in self.symbols))
            mult = max(1, self.multiplicity)
            if mult == 1 and ne % 2 == 0:
                n_alpha = n_beta = ne // 2
            elif mult == 1:
                ne -= 1
                n_alpha = n_beta = max(1, ne // 2)
            else:
                n_beta = (ne - (mult - 1)) // 2
                n_alpha = ne - n_beta
            n_so = min(14, max(2, max(n_alpha, n_beta), (ne + 1) // 2))
            seed = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
            h1, eri = _synthetic_mo_integrals(n_so, seed)
            enuc = _pairwise_enuc(self.symbols, list(self.coords))
            notes = f"synthetic_mo_fallback_nso={n_so}_ne={ne}_install_pyscf_linux"

        # Tabulated / synthetic MO ERIs are in chemists' notation; auto-detection can return
        # IndexType.UNKNOWN. Fix convention explicitly, then skip re-validation in from_raw_integrals.
        eri_phys = to_physicist_ordering(eri, index_order=IndexType.CHEMIST)
        electronic_energy = ElectronicEnergy.from_raw_integrals(
            h1, eri_phys, validate=False, auto_index_order=False
        )
        electronic_energy.nuclear_repulsion_energy = enuc

        problem = ElectronicStructureProblem(electronic_energy)
        problem.basis = ElectronicBasis.MO
        if key == "H2" and len(self.symbols) == 2:
            problem.num_particles = (1, 1)
        elif key in ("LIH", "H2O") and len(self.symbols) <= 3:
            problem.num_particles = (2, 2)
        else:
            ne = int(self.n_electrons or sum(_element_z(s) for s in self.symbols))
            mult = max(1, self.multiplicity)
            if mult == 1 and ne % 2 == 0:
                n_alpha = n_beta = ne // 2
            elif mult == 1:
                ne2 = ne - 1
                n_alpha = n_beta = max(1, ne2 // 2)
            else:
                n_beta = (ne - (mult - 1)) // 2
                n_alpha = ne - n_beta
            problem.num_particles = (n_alpha, n_beta)

        problem.num_spatial_orbitals = h1.shape[0]
        problem.properties.particle_number = ParticleNumber(h1.shape[0])
        problem.reference_energy = None

        setattr(problem, "_windows_fallback_notes", notes)
        setattr(problem, "_windows_fallback_formula", key)

        return problem


def _element_z(sym: str) -> int:
    zmap = {
        "H": 1,
        "LI": 3,
        "NA": 11,
        "BE": 4,
        "B": 5,
        "C": 6,
        "N": 7,
        "O": 8,
        "F": 9,
        "P": 15,
        "S": 16,
        "CL": 17,
    }
    return int(zmap.get(sym.upper(), 1))
