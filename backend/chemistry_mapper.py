"""
Universal chemical input → :class:`MoleculeInfo` + Jordan–Wigner qubit operator.

- SMILES: RDKit 3D conformer (ETKDG + MMFF/UFF), electron count, formula metadata.
- Plain text: try RDKit SMILES, then PubChemPy (formula / name), then legacy hardcoded formulas.
- PySCF when available; otherwise :class:`FallbackElectronicStructureDriver` (Windows-safe).
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

import numpy as np
from qiskit.quantum_info import SparsePauliOp

from qiskit_nature.second_q.formats.molecule_info import MoleculeInfo
from qiskit_nature.second_q.mappers import JordanWignerMapper
from qiskit_nature.second_q.problems import ElectronicStructureProblem
from qiskit_nature.second_q.problems.properties_container import PropertiesContainer
from qiskit_nature.second_q.transformers import ActiveSpaceTransformer
from qiskit_nature.units import DistanceUnit

from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit.Chem import rdMolDescriptors

_GEOMETRIES: dict[str, tuple[list[str], list[tuple[float, float, float]], int]] = {
    "H2": (["H", "H"], [(0.0, 0.0, 0.0), (0.0, 0.0, 0.74)], 1),
    "LIH": (["Li", "H"], [(0.0, 0.0, 0.0), (0.0, 0.0, 1.595)], 1),
    "H2O": (
        ["O", "H", "H"],
        [
            (0.0, 0.0, 0.11917),
            (0.0, 0.76344, -0.47656),
            (0.0, -0.76344, -0.47656),
        ],
        1,
    ),
    "N2": (["N", "N"], [(0.0, 0.0, 0.0), (0.0, 0.0, 1.098)], 1),
    "CO": (["C", "O"], [(0.0, 0.0, 0.0), (0.0, 0.0, 1.128)], 1),
    "CO2": (["C", "O", "O"], [(0.0, 0.0, 0.0), (0.0, 0.0, 1.16), (0.0, 0.0, -1.16)], 1),
    "CH4": (
        ["C", "H", "H", "H", "H"],
        [
            (0.0, 0.0, 0.0),
            (0.629, 0.629, 0.629),
            (-0.629, -0.629, 0.629),
            (-0.629, 0.629, -0.629),
            (0.629, -0.629, -0.629),
        ],
        1,
    ),
}


def normalize_formula(raw: str) -> str:
    s = raw.strip().upper()
    s = re.sub(r"\s+", "", s)
    return s


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
        "BR": 35,
        "I": 53,
    }
    return int(zmap.get(sym.upper(), 1))


def _electron_count_molecule_info(mi: MoleculeInfo) -> int:
    return sum(_element_z(s) for s in mi.symbols) - int(mi.charge)


def _geometry_fallback_from_token(token: str, charge: int = 0) -> tuple[MoleculeInfo, dict[str, Any]] | None:
    """If ``token`` normalizes to a key in ``_GEOMETRIES``, return table geometry + meta."""
    fk = normalize_formula(token)
    if fk not in _GEOMETRIES:
        return None
    mi = parse_formula_to_molecule_info(token.strip(), charge=charge)
    ne = _electron_count_molecule_info(mi)
    meta: dict[str, Any] = {
        "resolution_path": "legacy_geometry_table_fallback",
        "electron_count": ne,
        "molecular_formula": fk,
        "display_label": token.strip(),
    }
    return mi, meta


def parse_formula_to_molecule_info(formula: str, charge: int = 0) -> MoleculeInfo:
    key = normalize_formula(formula)
    if key not in _GEOMETRIES:
        supported = ", ".join(sorted(_GEOMETRIES.keys()))
        raise ValueError(f"Unsupported formula '{formula}'. Try SMILES, PubChem name, or: {supported}")

    symbols, coords, multiplicity = _GEOMETRIES[key]
    return MoleculeInfo(
        symbols=list(symbols),
        coords=list(coords),
        multiplicity=multiplicity,
        charge=charge,
        units=DistanceUnit.ANGSTROM,
    )


def smiles_to_molecule_info(smiles: str, charge: int = 0) -> tuple[MoleculeInfo, dict[str, Any]]:
    """RDKit: SMILES → 3D :class:`MoleculeInfo` + metadata (electrons, InChI key prefix, formula)."""
    s = smiles.strip()
    mol = Chem.MolFromSmiles(s)
    if mol is None:
        fb = _geometry_fallback_from_token(s, charge=charge)
        if fb:
            mi, meta = fb
            meta = {
                **meta,
                "resolution_path": "formula_fallback_after_smiles_parse",
                "display_stub": s,
                "input_smiles": s,
            }
            return mi, meta
        raise ValueError(f"Invalid SMILES string: {smiles!r}")

    try:
        mol = Chem.AddHs(mol)
        Chem.SanitizeMol(mol)

        params = AllChem.ETKDGv3()
        params.randomSeed = 0xC0DE
        ret = AllChem.EmbedMolecule(mol, params)
        if ret != 0:
            AllChem.EmbedMolecule(mol, randomSeed=0xBEEF)

        try:
            AllChem.MMFFOptimizeMolecule(mol)
        except Exception:
            try:
                AllChem.UFFOptimizeMolecule(mol)
            except Exception:
                pass

        conf = mol.GetConformer()
        symbols: list[str] = []
        coords: list[tuple[float, float, float]] = []
        for i in range(mol.GetNumAtoms()):
            a = mol.GetAtomWithIdx(i)
            symbols.append(a.GetSymbol())
            p = conf.GetAtomPosition(i)
            coords.append((float(p.x), float(p.y), float(p.z)))

        zsum = sum(mol.GetAtomWithIdx(i).GetAtomicNum() for i in range(mol.GetNumAtoms()))
        ne = int(zsum - charge)
        mult = 1 if ne % 2 == 0 else 2

        inchi_key = Chem.MolToInchiKey(mol)
        prefix = inchi_key.split("-")[0] if inchi_key else hashlib.sha256(s.encode()).hexdigest()[:14]

        try:
            formula = rdMolDescriptors.CalcMolFormula(mol)
        except Exception:
            fb = _geometry_fallback_from_token(s, charge=charge)
            if fb:
                mi, meta = fb
                meta = {
                    **meta,
                    "resolution_path": "legacy_geometry_table_rdkit_formula_fallback",
                    "input_smiles": s,
                }
                return mi, meta
            raise

        mi = MoleculeInfo(
            symbols=symbols,
            coords=coords,
            multiplicity=mult,
            charge=charge,
            units=DistanceUnit.ANGSTROM,
        )
        meta = {
            "smiles": Chem.MolToSmiles(mol),
            "electron_count": ne,
            "inchi_key_prefix": prefix,
            "molecular_formula": formula,
            "input_smiles": s,
        }
        return mi, meta
    except Exception:
        fb = _geometry_fallback_from_token(s, charge=charge)
        if fb:
            mi, meta = fb
            meta = {
                **meta,
                "resolution_path": "legacy_geometry_table_rdkit_error_fallback",
                "input_smiles": s,
            }
            return mi, meta
        raise


def resolve_text_to_smiles(text: str) -> str | None:
    """PubChemPy: formula / name / inchikey-style lookup → isomeric SMILES."""
    import pubchempy as pcp

    t = text.strip()
    if not t:
        return None
    for namespace in ("formula", "name", "smiles"):
        try:
            comps = pcp.get_compounds(t, namespace)
            if comps:
                smi = comps[0].isomeric_smiles
                if smi:
                    return str(smi)
        except Exception:
            continue
    return None


def _try_parse_as_smiles(text: str) -> str | None:
    m = Chem.MolFromSmiles(text.strip())
    if m is not None:
        return text.strip()
    return None


def _molecule_info_to_pyscf_atom(mi: MoleculeInfo) -> str:
    parts = []
    for sym, xyz in zip(mi.symbols, mi.coords):
        parts.append(f"{sym} {xyz[0]} {xyz[1]} {xyz[2]}")
    return "; ".join(parts)


def _pyscf_available() -> bool:
    try:
        import pyscf  # noqa: F401

        return True
    except ImportError:
        return False


def _run_pyscf_driver(mi: MoleculeInfo) -> ElectronicStructureProblem:
    from qiskit_nature.second_q.drivers import PySCFDriver

    spin = max(0, mi.multiplicity - 1)
    driver = PySCFDriver(
        atom=_molecule_info_to_pyscf_atom(mi),
        basis="sto3g",
        charge=mi.charge,
        spin=spin,
    )
    problem = driver.run()
    problem.molecule = mi
    return problem


def _trim_active_space(
    problem: ElectronicStructureProblem, max_qubits: int
) -> tuple[ElectronicStructureProblem, dict[str, Any]]:
    meta: dict[str, Any] = {"active_space_adjusted": False}

    def estimated_jw_qubits(prob: ElectronicStructureProblem) -> int:
        nso = prob.num_spatial_orbitals
        if nso is None:
            return prob.hamiltonian.register_length
        return int(2 * nso)

    n_so = int(problem.num_spatial_orbitals or 0)

    if estimated_jw_qubits(problem) <= max_qubits:
        meta["jw_qubits"] = estimated_jw_qubits(problem)
        return problem, meta

    particles = problem.num_particles
    if particles is None:
        raise ValueError("Electronic structure problem missing particle numbers")
    n_alpha, n_beta = particles
    total_e = int(n_alpha + n_beta)

    max_so = max(1, max_qubits // 2)

    for n_act_so in range(min(n_so, max_so), 0, -1):
        if 2 * n_act_so > max_qubits:
            continue
        n_act_e = min(total_e, 2 * n_act_so)
        if n_act_e % 2 != 0:
            n_act_e -= 1
        try:
            tr = ActiveSpaceTransformer(n_act_e, n_act_so)
            reduced = tr.transform(problem)
            meta["active_space_adjusted"] = True
            meta["active_electrons"] = n_act_e
            meta["active_spatial_orbitals"] = n_act_so
            meta["jw_qubits"] = estimated_jw_qubits(reduced)
            return reduced, meta
        except Exception:
            continue

    raise ValueError(
        f"Could not fit active space within max_qubits={max_qubits}. "
        "Try raising max_qubits or using a smaller basis/different molecule."
    )


def molecule_with_first_bond_length(mi: MoleculeInfo, distance_angstrom: float) -> MoleculeInfo:
    """
    Stretch or shrink the first internuclear vector (atoms 0–1) to ``distance_angstrom`` (Å).
    Remaining atoms are translated rigidly with atom 1 so relative positions stay fixed.
    """
    if len(mi.symbols) < 2:
        raise ValueError("Bond-length scan requires at least two atoms")
    coords = [np.array(c, dtype=np.float64) for c in mi.coords]
    v = coords[1] - coords[0]
    n = float(np.linalg.norm(v))
    if n < 1e-9:
        direction = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    else:
        direction = v / n
    new_1 = coords[0] + direction * float(distance_angstrom)
    delta = new_1 - coords[1]
    new_coords: list[tuple[float, float, float]] = [
        tuple(float(x) for x in coords[0]),
        tuple(float(x) for x in new_1),
    ]
    for i in range(2, len(coords)):
        c = coords[i] + delta
        new_coords.append((float(c[0]), float(c[1]), float(c[2])))
    return MoleculeInfo(
        symbols=list(mi.symbols),
        coords=new_coords,
        multiplicity=mi.multiplicity,
        charge=mi.charge,
        units=mi.units,
    )


def hamiltonian_to_sparse_pauli(problem: ElectronicStructureProblem) -> SparsePauliOp:
    fermionic_op = problem.hamiltonian.second_q_op()
    mapper = JordanWignerMapper()
    qubit_op = mapper.map(fermionic_op)
    if not isinstance(qubit_op, SparsePauliOp):
        qubit_op = SparsePauliOp(qubit_op)
    qubit_op = qubit_op.simplify()
    # Drop numerical imaginary parts from JW mapping (Hermitian H must stay Hermitian as Pauli sum).
    qubit_op = SparsePauliOp(
        qubit_op.paulis,
        coeffs=np.asarray(np.real(qubit_op.coeffs), dtype=float),
    )
    return qubit_op.chop(1e-8)


def resolve_molecule_geometry(
    *,
    structure: str | None = None,
    smiles: str | None = None,
    charge: int = 0,
) -> tuple[MoleculeInfo, dict[str, Any]]:
    """
    Resolve user input to 3D :class:`MoleculeInfo` + metadata, without building the electronic problem.
    """
    meta: dict[str, Any] = {}
    resolved_smiles: str | None = None

    if smiles and smiles.strip():
        resolved_smiles = smiles.strip()
        meta["resolution_path"] = "explicit_smiles"
    elif structure and structure.strip():
        st = structure.strip()
        trial = _try_parse_as_smiles(st)
        if trial:
            resolved_smiles = trial
            meta["resolution_path"] = "rdkit_smiles_literal"
        else:
            pc = resolve_text_to_smiles(st)
            if pc:
                resolved_smiles = pc
                meta["resolution_path"] = "pubchempy"
            elif normalize_formula(st) in _GEOMETRIES:
                mi = parse_formula_to_molecule_info(st, charge=charge)
                ne = _electron_count_molecule_info(mi)
                fk = normalize_formula(st)
                meta["resolution_path"] = "legacy_geometry_table"
                meta["electron_count"] = ne
                meta["display_label"] = st.strip()
                meta["molecular_formula"] = fk
                return mi, meta
            else:
                raise ValueError(
                    f"Could not resolve {st!r} as SMILES or PubChem identifier. "
                    "Try an isomeric SMILES (e.g. CCO for ethanol) or a known formula (H2, CO2)."
                )
    else:
        raise ValueError("Either ``smiles`` or ``structure`` must be provided.")

    try:
        mi, smeta = smiles_to_molecule_info(resolved_smiles, charge=charge)
    except Exception:
        fb = _geometry_fallback_from_token(resolved_smiles, charge=charge)
        if fb:
            mi, smeta = fb
        else:
            raise
    meta.update(smeta)
    meta["display_label"] = meta.get("molecular_formula") or resolved_smiles
    return mi, meta


def build_qubit_operator_from_molecule_info(
    mi: MoleculeInfo,
    *,
    max_qubits: int = 28,
    meta_extra: dict[str, Any] | None = None,
) -> tuple[SparsePauliOp, MoleculeInfo, dict[str, Any]]:
    """Build JW qubit operator from explicit geometry (e.g. PES scan points)."""
    meta: dict[str, Any] = {"basis": "sto3g", "max_qubits_budget": max_qubits}
    if meta_extra:
        meta.update(meta_extra)
    ne = _electron_count_molecule_info(mi)
    fk = hashlib.sha256(("".join(mi.symbols) + repr(mi.coords)).encode()).hexdigest()[
        :14
    ]
    meta.setdefault("electron_count", ne)
    meta.setdefault("display_label", "".join(mi.symbols))
    return _finalize_problem(mi, fk, ne, meta, max_qubits)


def build_qubit_operator_from_chemical_input(
    *,
    structure: str | None = None,
    smiles: str | None = None,
    max_qubits: int = 28,
    charge: int = 0,
) -> tuple[SparsePauliOp, MoleculeInfo, dict[str, Any]]:
    """
    Resolve SMILES, PubChem text, or legacy formula → JW :class:`SparsePauliOp`.
    Active space is trimmed so ``2 × n_spatial_active ≤ max_qubits`` (default 28).
    """
    meta: dict[str, Any] = {"basis": "sto3g", "max_qubits_budget": max_qubits}
    mi, gmeta = resolve_molecule_geometry(
        structure=structure, smiles=smiles, charge=charge
    )
    meta.update(gmeta)
    if meta.get("resolution_path") == "legacy_geometry_table":
        ne = int(meta["electron_count"])
        fk = normalize_formula(
            str(meta.get("molecular_formula") or meta.get("display_label") or "")
        )
        return _finalize_problem(mi, fk, ne, meta, max_qubits)

    ne = int(meta["electron_count"])
    fk = str(meta.get("inchi_key_prefix") or "GENERIC")
    meta["display_label"] = meta.get("molecular_formula") or meta.get(
        "display_label", "molecule"
    )
    return _finalize_problem(mi, fk, ne, meta, max_qubits)


def _finalize_problem(
    mi: MoleculeInfo,
    formula_key: str,
    ne: int,
    meta: dict[str, Any],
    max_qubits: int,
) -> tuple[SparsePauliOp, MoleculeInfo, dict[str, Any]]:
    if _pyscf_available():
        problem = _run_pyscf_driver(mi)
        meta["electronic_structure_driver"] = "PySCFDriver"
    else:
        from .fallback_electronic_structure import FallbackElectronicStructureDriver

        problem = FallbackElectronicStructureDriver(
            formula_key,
            mi.symbols,
            list(mi.coords),
            n_electrons=ne,
            multiplicity=mi.multiplicity,
        ).run()
        problem.molecule = mi
        meta["electronic_structure_driver"] = "FallbackElectronicStructureDriver"
        meta["windows_fallback"] = True
        meta["windows_fallback_notes"] = getattr(problem, "_windows_fallback_notes", "")

    problem, trim_meta = _trim_active_space(problem, max_qubits=max_qubits)
    meta.update(trim_meta)

    # Do not carry dipole / particle-number / etc. property operators into any second_q_ops bundle;
    # we only JW-map the electronic Hamiltonian for Estimator energy.
    problem.properties = PropertiesContainer()

    qop = hamiltonian_to_sparse_pauli(problem)
    meta["jw_qubits"] = int(qop.num_qubits)
    meta["num_spatial_orbitals"] = problem.num_spatial_orbitals

    return qop, mi, meta


def build_qubit_operator_from_formula(
    formula: str,
    *,
    max_qubits: int = 28,
    charge: int = 0,
) -> tuple[SparsePauliOp, MoleculeInfo, dict[str, Any]]:
    """Backward-compatible wrapper."""
    return build_qubit_operator_from_chemical_input(
        structure=formula, smiles=None, max_qubits=max_qubits, charge=charge
    )
