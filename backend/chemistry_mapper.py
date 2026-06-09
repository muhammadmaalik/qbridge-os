"""
Universal chemical input → :class:`MoleculeInfo` + Jordan–Wigner qubit operator.

- SMILES: RDKit 3D conformer (ETKDG + MMFF/UFF), electron count, formula metadata.
- Plain text: try RDKit SMILES, then PubChemPy (formula / name), then legacy hardcoded formulas.
- Electronic structure: PySCF (ab initio) when available; H₂ tabulated STO-3G only if PySCF is missing.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

import numpy as np
from qiskit.quantum_info import SparsePauliOp

from qiskit_nature.second_q.formats.molecule_info import MoleculeInfo
from qiskit_nature.second_q.mappers import JordanWignerMapper, ParityMapper
from qiskit_nature.second_q.problems import ElectronicStructureProblem
from qiskit_nature.second_q.problems.properties_container import PropertiesContainer
from qiskit_nature.second_q.transformers import ActiveSpaceTransformer
from qiskit_nature.units import DistanceUnit

# Public mapper identifiers accepted by the ``mapper_kind`` kwargs below.
_MAPPER_JW = "jordan_wigner"
_MAPPER_PARITY = "parity"
_MAPPER_ALIASES: dict[str, str] = {
    "jw": _MAPPER_JW,
    "jordanwigner": _MAPPER_JW,
    "jordan_wigner": _MAPPER_JW,
    "jordan-wigner": _MAPPER_JW,
    "p": _MAPPER_PARITY,
    "parity": _MAPPER_PARITY,
    "parity_mapper": _MAPPER_PARITY,
}


def _normalize_mapper_kind(mapper_kind: str | None) -> str:
    if mapper_kind is None:
        return _MAPPER_JW
    key = str(mapper_kind).strip().lower().replace(" ", "_")
    if key not in _MAPPER_ALIASES:
        raise ValueError(
            f"Unknown mapper_kind={mapper_kind!r}. "
            f"Supported: 'jordan_wigner' or 'parity'."
        )
    return _MAPPER_ALIASES[key]


def _formula_key_from_symbols(symbols: list[str]) -> str:
    """
    Build a canonical uppercase formula key from a symbol list.

    Returns keys compatible with :class:`FallbackElectronicStructureDriver`'s
    tabulated branches (``"H2"``, ``"LIH"``, ``"H2O"``) so callers that build
    a problem from explicit geometry (PES scans, SDK bond-distance stretching)
    still hit the hand-coded integrals instead of falling through to the
    synthetic-MO fallback. For other molecules a Hill-system formula is
    returned for diagnostic clarity (the driver still treats them as synthetic).
    """
    counts: dict[str, int] = {}
    for s in symbols:
        u = str(s).upper()
        counts[u] = counts.get(u, 0) + 1

    if counts == {"H": 2}:
        return "H2"
    if counts == {"LI": 1, "H": 1}:
        return "LIH"
    if counts == {"O": 1, "H": 2}:
        return "H2O"

    parts: list[str] = []
    rem = dict(counts)
    for elem in ("C", "H"):
        if elem in rem:
            n = rem.pop(elem)
            parts.append(elem if n == 1 else f"{elem}{n}")
    for elem in sorted(rem.keys()):
        n = rem[elem]
        parts.append(elem if n == 1 else f"{elem}{n}")
    return "".join(parts) or "GENERIC"

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from rdkit.Chem import rdMolDescriptors

    _RDKIT_AVAILABLE = True
except ImportError:
    Chem = None  # type: ignore[misc, assignment]
    AllChem = None  # type: ignore[misc, assignment]
    rdMolDescriptors = None  # type: ignore[misc, assignment]
    _RDKIT_AVAILABLE = False

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
    if not _RDKIT_AVAILABLE:
        fb = _geometry_fallback_from_token(s, charge=charge)
        if fb:
            mi, meta = fb
            meta["resolution_path"] = "legacy_geometry_table_no_rdkit"
            return mi, meta
        raise ValueError(
            f"RDKit unavailable; could not resolve {s!r}. "
            "Use a built-in formula (H2, LiH, H2O) or install rdkit."
        )
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
    try:
        import pubchempy as pcp
    except ImportError:
        return None

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
    if not _RDKIT_AVAILABLE:
        return None
    m = Chem.MolFromSmiles(text.strip())
    if m is not None:
        return text.strip()
    return None


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


def hamiltonian_to_sparse_pauli(
    problem: ElectronicStructureProblem,
    *,
    mapper_kind: str = _MAPPER_JW,
) -> SparsePauliOp:
    """
    Map the electronic Hamiltonian of ``problem`` to a real, Hermitian :class:`SparsePauliOp`.

    ``mapper_kind="jordan_wigner"`` (default) preserves prior behavior.
    ``mapper_kind="parity"`` uses :class:`ParityMapper` with ``num_particles`` taken
    from the (already active-space-trimmed) ``problem``; supplying ``num_particles``
    enables the modern symmetry-based two-qubit reduction inside ``ParityMapper``.
    """
    kind = _normalize_mapper_kind(mapper_kind)
    fermionic_op = problem.hamiltonian.second_q_op()

    if kind == _MAPPER_PARITY:
        particles = problem.num_particles
        if particles is None:
            mapper = ParityMapper()
        else:
            n_alpha, n_beta = particles
            mapper = ParityMapper(num_particles=(int(n_alpha), int(n_beta)))
    else:
        mapper = JordanWignerMapper()

    qubit_op = mapper.map(fermionic_op)
    if not isinstance(qubit_op, SparsePauliOp):
        qubit_op = SparsePauliOp(qubit_op)
    qubit_op = qubit_op.simplify()
    # Hermitian H must stay Hermitian; drop numerical imaginary noise from the mapping.
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
            nf = normalize_formula(st)
            if nf in _GEOMETRIES:
                mi = parse_formula_to_molecule_info(st, charge=charge)
                ne = _electron_count_molecule_info(mi)
                fk = nf
                meta["resolution_path"] = "legacy_geometry_table"
                meta["electron_count"] = ne
                meta["display_label"] = st.strip()
                meta["molecular_formula"] = fk
                return mi, meta
            pc = resolve_text_to_smiles(st)
            if pc:
                resolved_smiles = pc
                meta["resolution_path"] = "pubchempy"
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
    mapper_kind: str = _MAPPER_JW,
) -> tuple[SparsePauliOp, MoleculeInfo, dict[str, Any]]:
    """Build qubit operator from explicit geometry (e.g. PES scan points).

    ``mapper_kind`` selects the fermion-to-qubit mapping; defaults to Jordan–Wigner.
    """
    meta: dict[str, Any] = {"basis": "sto3g", "max_qubits_budget": max_qubits}
    if meta_extra:
        meta.update(meta_extra)
    ne = _electron_count_molecule_info(mi)
    # Prefer caller-supplied formula, then symbol-derived formula, then geometry hash.
    # The driver dispatches its tabulated H2/LIH/H2O integrals on this key, so a hash
    # would silently force PES-scan / SDK bond-stretch callers into the synthetic
    # fallback even for molecules we have hand-coded integrals for.
    fk_meta = str(meta.get("molecular_formula") or "").strip().upper()
    fk_sym = _formula_key_from_symbols(list(mi.symbols))
    if fk_meta:
        fk = fk_meta
    elif fk_sym and fk_sym != "GENERIC":
        fk = fk_sym
    else:
        fk = hashlib.sha256(
            ("".join(mi.symbols) + repr(mi.coords)).encode()
        ).hexdigest()[:14]
    meta.setdefault("electron_count", ne)
    meta.setdefault("display_label", "".join(mi.symbols))
    return _finalize_problem(mi, fk, ne, meta, max_qubits, mapper_kind=mapper_kind)


def build_qubit_operator_from_chemical_input(
    *,
    structure: str | None = None,
    smiles: str | None = None,
    max_qubits: int = 28,
    charge: int = 0,
    mapper_kind: str = _MAPPER_JW,
) -> tuple[SparsePauliOp, MoleculeInfo, dict[str, Any]]:
    """
    Resolve SMILES, PubChem text, or legacy formula → :class:`SparsePauliOp`.
    Active space is trimmed so ``2 × n_spatial_active ≤ max_qubits`` (default 28).

    ``mapper_kind`` selects the fermion-to-qubit mapping. ``"parity"`` engages
    :class:`ParityMapper` with ``num_particles`` taken from the trimmed problem,
    which performs the modern symmetry-based two-qubit reduction.
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
        return _finalize_problem(mi, fk, ne, meta, max_qubits, mapper_kind=mapper_kind)

    ne = int(meta["electron_count"])
    # Same dispatch as ``build_qubit_operator_from_molecule_info``: prefer a
    # symbol-derived formula key (so RDKit/PubChem-resolved H2/LiH/H2O still
    # hit the driver's tabulated integrals), then the molecular formula from
    # metadata, then the InChI hash, then "GENERIC".
    fk_sym = _formula_key_from_symbols(list(mi.symbols))
    fk_meta = str(meta.get("molecular_formula") or "").strip().upper()
    if fk_sym and fk_sym != "GENERIC":
        fk = fk_sym
    elif fk_meta:
        fk = fk_meta
    else:
        fk = str(meta.get("inchi_key_prefix") or "GENERIC")
    meta["display_label"] = meta.get("molecular_formula") or meta.get(
        "display_label", "molecule"
    )
    return _finalize_problem(mi, fk, ne, meta, max_qubits, mapper_kind=mapper_kind)


def _run_electronic_structure(
    mi: MoleculeInfo,
    formula_key: str,
    ne: int,
) -> tuple[ElectronicStructureProblem, dict[str, Any]]:
    """Build an :class:`ElectronicStructureProblem` from real integrals when possible."""
    driver_meta: dict[str, Any] = {}

    try:
        from .ab_initio_electronic_structure import build_electronic_structure_problem

        problem, driver_meta = build_electronic_structure_problem(mi)
        return problem, driver_meta
    except ImportError:
        driver_meta = {"ab_initio_backend_missing": True}
    except Exception as exc:
        raise RuntimeError(
            f"Ab-initio electronic structure failed for {formula_key}: {exc}"
        ) from exc

    from .fallback_electronic_structure import FallbackElectronicStructureDriver

    if formula_key != "H2" or len(mi.symbols) != 2:
        raise RuntimeError(
            "Ab-initio backend (pyqint) is required for this molecule. "
            "Install with: pip install pyqint"
        )

    problem = FallbackElectronicStructureDriver(
        formula_key,
        mi.symbols,
        list(mi.coords),
        n_electrons=ne,
        multiplicity=mi.multiplicity,
    ).run()
    driver_meta = {
        "electronic_structure_driver": "FallbackElectronicStructureDriver",
        "ab_initio": False,
        "simulation_mode": False,
        "windows_fallback": True,
        "windows_fallback_notes": getattr(problem, "_windows_fallback_notes", ""),
        "pyscf_unavailable": True,
    }
    return problem, driver_meta


def _finalize_problem(
    mi: MoleculeInfo,
    formula_key: str,
    ne: int,
    meta: dict[str, Any],
    max_qubits: int,
    *,
    mapper_kind: str = _MAPPER_JW,
) -> tuple[SparsePauliOp, MoleculeInfo, dict[str, Any]]:
    try:
        problem, driver_meta = _run_electronic_structure(mi, formula_key, ne)
    except Exception as drv_err:
        raise RuntimeError(f"electronic structure driver failed: {drv_err}") from drv_err

    problem.molecule = mi
    meta.update(driver_meta)

    problem, trim_meta = _trim_active_space(problem, max_qubits=max_qubits)
    meta.update(trim_meta)

    # Property operators (dipole, particle number, etc.) are not energy observables;
    # strip them before mapping so we only emit the electronic Hamiltonian for VQE.
    problem.properties = PropertiesContainer()

    kind = _normalize_mapper_kind(mapper_kind)
    qop = hamiltonian_to_sparse_pauli(problem, mapper_kind=kind)

    # qiskit-nature returns the *electronic* second-quantized operator only;
    # the nuclear repulsion is tracked separately on ``ElectronicEnergy``. Fold
    # it into the qubit operator as an identity offset so the lowest eigenvalue
    # of ``qop`` is the total Born–Oppenheimer ground-state energy directly,
    # not the electronic part minus E_NN. Downstream VQE / noisy-pass code
    # then doesn't have to remember to add it.
    enuc = float(getattr(problem.hamiltonian, "nuclear_repulsion_energy", 0.0) or 0.0)
    if enuc != 0.0:
        identity = SparsePauliOp.from_list([("I" * qop.num_qubits, enuc)])
        qop = (qop + identity).simplify()
        qop = SparsePauliOp(
            qop.paulis,
            coeffs=np.asarray(np.real(qop.coeffs), dtype=float),
        ).chop(1e-8)

    particles = problem.num_particles
    meta["mapper"] = kind
    meta["num_particles"] = (
        [int(particles[0]), int(particles[1])] if particles is not None else None
    )
    meta["nuclear_repulsion_energy"] = enuc
    meta["energy_includes_nuclear_repulsion"] = True
    meta["qubit_op_qubits"] = int(qop.num_qubits)
    # Backward-compat: legacy callers (and the frontend) read ``jw_qubits`` as
    # "the qubit width of the mapped operator", regardless of which mapper produced it.
    meta["jw_qubits"] = int(qop.num_qubits)
    meta["num_spatial_orbitals"] = problem.num_spatial_orbitals

    return qop, mi, meta


def build_qubit_operator_from_formula(
    formula: str,
    *,
    max_qubits: int = 28,
    charge: int = 0,
    mapper_kind: str = _MAPPER_JW,
) -> tuple[SparsePauliOp, MoleculeInfo, dict[str, Any]]:
    """Backward-compatible wrapper."""
    return build_qubit_operator_from_chemical_input(
        structure=formula,
        smiles=None,
        max_qubits=max_qubits,
        charge=charge,
        mapper_kind=mapper_kind,
    )
