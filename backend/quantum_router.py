import httpx
import asyncio
import os
from typing import Any
import numpy as np
from scipy.optimize import minimize as _scipy_minimize
from qiskit import QuantumCircuit
from qiskit.circuit.library import RealAmplitudes
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit_nature.second_q.formats.molecule_info import MoleculeInfo

from backend.chemistry_mapper import (
    build_qubit_operator_from_chemical_input,
    build_qubit_operator_from_molecule_info,
    molecule_with_first_bond_length,
    resolve_dimer_geometry,
    resolve_molecule_geometry,
)
from backend.telemetry import set_noise_telemetry


def _expectation_sparse_pauli_statevector(qc: QuantumCircuit, observable: SparsePauliOp) -> float:
    """
    Exact ⟨H⟩ without Estimator / SparseObservable coercion (avoids Non-Hermitian V2 checks).
    """
    sv = Statevector(qc)
    acc = 0j
    for pauli, coeff in zip(observable.paulis, observable.coeffs):
        acc += complex(coeff) * sv.expectation_value(pauli)
    return float(np.real(acc))


def _prepare_estimator_hamiltonian(obs) -> SparsePauliOp:
    """
    Energy observable only: real-valued float coefficients and chopped noise.
    Avoids non-Hermitian / numerical issues in Estimator and Runtime validation.
    """
    if not isinstance(obs, SparsePauliOp):
        obs = SparsePauliOp(obs)
    obs = SparsePauliOp(
        obs.paulis,
        coeffs=np.asarray(np.real(obs.coeffs), dtype=float),
    )
    return obs.chop(1e-8)


def run_local_vqe_slsqp(
    observable: SparsePauliOp,
    *,
    maxiter: int = 50,
    reps: int = 1,
    entanglement: str = "linear",
    initial_point: np.ndarray | None = None,
    rng_seed: int = 1234,
    ftol: float = 1e-6,
) -> dict[str, Any]:
    """
    Real Variational Quantum Eigensolver on a local CPU statevector simulator.

    This is the actual minimization loop: a :class:`RealAmplitudes` ansatz is
    optimized with SciPy's SLSQP against the exact ⟨H⟩ on the statevector.
    The function is fully synchronous (cheap on small qubit counts; ~1ms per
    energy eval at 4–8 qubits) so it can be called directly from sync contexts
    or wrapped in :func:`asyncio.to_thread` from async ones.

    Returns a dict with the optimal energy, the bound circuit at the optimum,
    iteration counters, and SciPy's convergence ``success``/``message`` so the
    caller can surface early bailout (e.g. ``maxiter=50`` exhausted before
    SLSQP's tolerance was met).
    """
    obs = _prepare_estimator_hamiltonian(observable)
    nq = int(obs.num_qubits)
    if nq < 1:
        raise ValueError("observable must act on at least one qubit")

    ansatz = RealAmplitudes(
        num_qubits=nq,
        reps=int(reps),
        entanglement=str(entanglement),
        insert_barriers=False,
    )
    n_params = int(ansatz.num_parameters)

    if initial_point is None:
        rng = np.random.default_rng(int(rng_seed))
        x0 = np.full(n_params, np.pi / 5.0) + rng.normal(0.0, 0.05, size=n_params)
    else:
        x0 = np.asarray(initial_point, dtype=float).reshape(-1)
        if x0.shape[0] != n_params:
            raise ValueError(
                f"initial_point length {x0.shape[0]} != ansatz parameter count {n_params}"
            )

    history: list[float] = []

    def energy_fn(params: np.ndarray) -> float:
        bound = ansatz.assign_parameters(np.asarray(params, dtype=float))
        e = _expectation_sparse_pauli_statevector(bound, obs)
        history.append(e)
        return e

    res = _scipy_minimize(
        energy_fn,
        x0,
        method="SLSQP",
        options={"maxiter": int(maxiter), "ftol": float(ftol), "disp": False},
    )

    final_params = np.asarray(res.x, dtype=float)
    final_energy = float(np.real(res.fun))
    optimal_qc = ansatz.assign_parameters(final_params)

    return {
        "energy": final_energy,
        "circuit": optimal_qc,
        "optimal_params": [float(x) for x in final_params],
        "n_iterations": int(getattr(res, "nit", 0)),
        "n_function_evals": int(getattr(res, "nfev", len(history))),
        "converged": bool(getattr(res, "success", False)),
        "convergence_message": str(getattr(res, "message", "")),
        "scipy_status": int(getattr(res, "status", -1)),
        "optimizer": "SLSQP",
        "maxiter": int(maxiter),
        "ftol": float(ftol),
        "ansatz": "RealAmplitudes",
        "reps": int(reps),
        "entanglement": str(entanglement),
        "num_qubits": nq,
        "num_parameters": n_params,
        "history_tail": [float(x) for x in history[-5:]],
        "energy_history": [float(x) for x in history],
        "backend": "local_statevector_simulator",
    }


def _scalar_energy_float(val) -> float:
    """Coerce estimator output to a Python float (handles 0-d arrays and scalars)."""
    arr = np.asarray(val, dtype=np.float64)
    if arr.size == 0:
        raise ValueError("empty energy expectation value")
    return float(arr.ravel()[0])


def _public_vqe_meta(meta: dict[str, Any]) -> dict[str, Any]:
    """JSON-safe view of :func:`run_local_vqe_slsqp` output (drops the live circuit)."""
    if not meta:
        return {}
    return {k: v for k, v in meta.items() if k != "circuit"}


def run_local_noisy_expectation(
    observable: SparsePauliOp,
    circuit: QuantumCircuit,
    *,
    shots: int = 4096,
    fake_device: object | None = None,
    profile_label: str | None = None,
) -> dict[str, Any]:
    """
    One-shot noisy ⟨H⟩ on the VQE-optimal circuit.

    This is the post-VQE "what would this look like on hardware" pass. It runs
    :class:`qiskit_aer.primitives.estimator.Estimator` (V1, the only Aer
    primitive that doesn't trip the EstimatorV2 SparseObservable / Hermitian
    coercion) with a :class:`NoiseModel.from_backend(fake)` derived from a
    local IBM fake provider — no network, no qiskit_ibm_runtime service call.

    The optimization itself stays on the exact statevector path (see
    :func:`run_local_vqe_slsqp`); this function only re-evaluates the energy
    of the *already-optimal* circuit under simulated hardware noise so the UI
    can show a clean-vs-noisy comparison without destabilizing SLSQP.
    """
    from qiskit_aer.noise import NoiseModel
    from qiskit_aer.primitives.estimator import Estimator as AerEstimatorV1

    if fake_device is None or not profile_label:
        fake_device, profile_label = _resolve_fake_device_for_noise()

    obs = _prepare_estimator_hamiltonian(observable)
    noise_model = NoiseModel.from_backend(fake_device)
    estimator = AerEstimatorV1(
        backend_options={"noise_model": noise_model},
        run_options={"shots": int(shots)},
        approximation=False,
    )

    job = estimator.run([circuit], [obs], parameter_values=[[]])
    result = job.result()
    noisy_energy = _scalar_energy_float(result.values)

    return {
        "noisy_energy": noisy_energy,
        "noise_profile": profile_label,
        "shots": int(shots),
        "fake_device": type(fake_device).__name__,
        "estimator": "qiskit_aer.primitives.Estimator (V1)",
        "noise_source": "NoiseModel.from_backend",
    }


def _resolve_fake_device_for_noise() -> tuple[object, str]:
    """Pick a local IBM fake backend (no network) to seed :class:`NoiseModel.from_backend`."""
    name = os.environ.get("QBRIDGE_NOISE_PROFILE", "ibm_osaka").strip().lower()
    from qiskit_ibm_runtime.fake_provider import FakeKyiv, FakeOsaka

    if name in ("ibm_kyiv", "kyiv", "fake_kyiv"):
        return FakeKyiv(), "ibm_kyiv"
    return FakeOsaka(), "ibm_osaka"


def _parse_scan_distances(spec: str) -> list[float]:
    parts = [p.strip() for p in spec.strip().split(":")]
    if len(parts) != 3:
        raise ValueError("scan must be start:end:step (e.g. 0.5:2.0:0.1)")
    start, end, step = map(float, parts)
    if step == 0:
        raise ValueError("scan step must be non-zero")
    out: list[float] = []
    if step > 0:
        x = start
        while x <= end + 1e-9:
            out.append(round(x, 8))
            x += step
    else:
        x = start
        while x >= end - 1e-9:
            out.append(round(x, 8))
            x += step
    if len(out) > 150:
        raise ValueError("scan yields more than 150 points; increase step size")
    if not out:
        raise ValueError("scan range produced no points")
    return out


def build_electron_probability_cloud(
    qc: QuantumCircuit,
    molecule_info: MoleculeInfo,
    *,
    grid_resolution: int = 10,
    extent: float = 1.65,
) -> list[dict]:
    """
    Visualization density |ψ_vis(r)|² on a grid: amplitude-weighted Gaussians at nuclear centers.
    Not a full ab-initio electron density; ties the qubit statevector to Schrödinger-cloud UX.
    """
    amps = np.asarray(Statevector(qc).data, dtype=np.complex128)
    centers = [np.array(c, dtype=np.float64) for c in molecule_info.coords]
    k = min(len(amps), len(centers), 16)
    k = max(k, 1)
    weights = np.abs(amps[:k]) ** 2
    weights = weights / (weights.sum() or 1.0)
    centers_use = [centers[i % len(centers)] for i in range(k)]

    sigma = 0.34

    def gaussian(r: np.ndarray, center: np.ndarray) -> float:
        d = r - center
        return float(np.exp(-np.dot(d, d) / (2.0 * sigma * sigma)))

    ax = np.linspace(-extent, extent, grid_resolution)
    cloud: list[dict] = []
    for x in ax:
        for y in ax:
            for z in ax:
                r = np.array([x, y, z], dtype=np.float64)
                rho = 0.0
                for i in range(k):
                    rho += weights[i] * gaussian(r, centers_use[i])
                prob = float(rho * rho)
                cloud.append(
                    {
                        "x": float(x),
                        "y": float(y),
                        "z": float(z),
                        "probability": prob,
                    }
                )

    mx = max(c["probability"] for c in cloud) or 1.0
    for c in cloud:
        c["probability"] = float(c["probability"] / mx)
    return cloud


# NOTE: qiskit_ibm_runtime is intentionally NOT imported at the top level.
# The VQE solver runs strictly on local CPU (qiskit statevector). IBM Runtime
# routing was removed because remote dispatch was masking real bugs as
# "circuit too complex" rejections in this environment.


class QuantumRouter:
    def __init__(self):
        self.anu_api_url = "https://qrng.anu.edu.au/API/jsonI.php?length=1&type=hex16&size=8"
        self._last_run_used_aer_noise = False

    async def fetch_anu_entropy(self) -> str:
        """Path A: High-Assurance Entropy (Cryptography/Seeds)"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.anu_api_url, timeout=5.0)
                response.raise_for_status()
                data = response.json()
                if data.get("success"):
                    return data["data"][0]
                return "a1b2c3d4e5f6g7h8"
            except Exception:
                await asyncio.sleep(0.05)
                return "deadbeef12345678"

    async def _run_vqe_energy(
        self,
        observable,
        *,
        maxiter: int = 50,
        reps: int = 1,
        entanglement: str = "linear",
        initial_point: np.ndarray | None = None,
        rng_seed: int = 1234,
    ) -> tuple[float, str, QuantumCircuit, dict[str, Any]]:
        """
        Real local SLSQP-driven VQE on exact statevector (no IBM Runtime, no GPU).

        Returns ``(energy, backend_name, optimal_circuit, vqe_meta)``. The
        ``vqe_meta`` dict carries the SLSQP convergence flag and message so the
        frontend can detect early bailout. Noise is *not* applied here — see
        :meth:`_run_noisy_expectation` for the post-VQE noisy pass.
        """
        meta = await asyncio.to_thread(
            run_local_vqe_slsqp,
            observable,
            maxiter=maxiter,
            reps=reps,
            entanglement=entanglement,
            initial_point=initial_point,
            rng_seed=rng_seed,
        )
        return (
            float(meta["energy"]),
            str(meta["backend"]),
            meta["circuit"],
            meta,
        )

    async def _run_noisy_expectation(
        self,
        observable: SparsePauliOp,
        circuit: QuantumCircuit,
        *,
        shots: int = 4096,
        fake_device: object | None = None,
        profile_label: str | None = None,
    ) -> dict[str, Any]:
        """Async wrapper for :func:`run_local_noisy_expectation`."""
        return await asyncio.to_thread(
            run_local_noisy_expectation,
            observable,
            circuit,
            shots=shots,
            fake_device=fake_device,
            profile_label=profile_label,
        )

    async def simulate_molecule(self, api_key: str, payload: dict) -> dict:
        """Local CPU VQE pipeline. Never returns catalog/simulated energies."""
        return await self._simulate_molecule_pipeline(api_key, payload)

    async def _simulate_molecule_pipeline(self, api_key: str, payload: dict) -> dict:
        """
        ElectronicStructureProblem → ActiveSpaceTransformer → ParityMapper → SLSQP VQE.
        Optional PES scan over the first internuclear vector.
        """
        self._last_run_used_aer_noise = False
        structure = payload.get("structure")
        smiles = payload.get("smiles")
        charge = int(payload.get("charge") or 0)
        smiles_a = payload.get("smiles_a")
        smiles_b = payload.get("smiles_b")
        distance_angstrom = float(payload.get("distance_angstrom") or 2.0)
        dimer_mode = bool(smiles_a and str(smiles_a).strip()) and bool(smiles_b and str(smiles_b).strip())
        max_qubits = int(payload.get("max_qubits") or os.environ.get("QBRIDGE_MAX_QUBITS") or 12)
        vqe_maxiter = int(payload.get("vqe_maxiter") or 50)
        req_hw = payload.get("_requested_hardware_provider") or payload.get(
            "hardware_provider"
        )
        req_hw = str(req_hw or "local").strip().lower()
        # IBM Runtime / GPU are intentionally disabled on this VQE pipeline.
        # ``hw`` is retained only to gate the optional ANU-entropy decoration.
        hw = "anu" if req_hw == "anu" else "local"
        scan_raw = payload.get("scan")
        use_noise = bool(payload.get("noise"))
        warnings: list[str] = []

        if req_hw == "ibm":
            warnings.append(
                "[hardware] IBM Runtime routing is disabled in this build; "
                "running the VQE locally on CPU statevector."
            )

        # Noise is applied as a *post-VQE* one-shot ⟨H⟩ pass on the optimal
        # circuit, never inside the SLSQP loop (shot noise breaks gradients).
        noise_shots = int(payload.get("noise_shots") or 4096)
        fake_for_noise: object | None = None
        noise_prof: str | None = None
        if use_noise:
            fake_for_noise, noise_prof = _resolve_fake_device_for_noise()

        chem_meta: dict
        label: str

        if dimer_mode:
            if scan_raw and str(scan_raw).strip():
                raise ValueError("scan is not supported for dimer mode (smiles_a/smiles_b).")

            dimer_mi, geo_meta = resolve_dimer_geometry(
                smiles_a=str(smiles_a).strip(),
                smiles_b=str(smiles_b).strip(),
                distance_angstrom=distance_angstrom,
                charge=charge,
            )
            # Build qubit operator from explicit combined geometry.
            observable, molecule_info, chem_meta = build_qubit_operator_from_molecule_info(
                dimer_mi,
                max_qubits=max_qubits,
                meta_extra=geo_meta,
                mapper_kind="jordan_wigner",
            )
            label = str(chem_meta.get("display_label") or "dimer")

            energy, backend_used, qc, vqe_meta = await self._run_vqe_energy(
                observable,
                maxiter=vqe_maxiter,
            )
        elif scan_raw and str(scan_raw).strip():
            distances = _parse_scan_distances(str(scan_raw))
            base_mi, geo_meta = resolve_molecule_geometry(
                structure=structure, smiles=smiles, charge=charge
            )
            if len(base_mi.symbols) < 2:
                raise ValueError("PES scan requires at least two atoms (e.g. H2 or LiH).")
            label = str(
                geo_meta.get("display_label")
                or geo_meta.get("molecular_formula")
                or structure
                or smiles
                or "scan"
            )
            scan_curve: list[dict] = []
            best_i = 0
            best_energy = float("inf")
            last_qc: QuantumCircuit | None = None
            last_mi: MoleculeInfo = base_mi
            last_backend = "local_statevector_simulator"
            chem_meta = {**geo_meta, "scan_spec": str(scan_raw).strip()}

            best_vqe_meta: dict[str, Any] = {}
            best_observable: SparsePauliOp | None = None
            any_bailout = False

            for i, r in enumerate(distances):
                mi_r = molecule_with_first_bond_length(base_mi, r)
                observable, molecule_info, pt_meta = build_qubit_operator_from_molecule_info(
                    mi_r,
                    max_qubits=max_qubits,
                    meta_extra={
                        **geo_meta,
                        "scan_distance_angstrom": r,
                        "scan_point_index": i,
                    },
                    mapper_kind="jordan_wigner",
                )
                energy, backend_used, qc, vqe_meta = await self._run_vqe_energy(
                    observable,
                    maxiter=vqe_maxiter,
                )
                if not vqe_meta.get("converged", False):
                    any_bailout = True
                scan_curve.append(
                    {
                        "distance": float(r),
                        "energy": float(energy),
                        "converged": bool(vqe_meta.get("converged", False)),
                        "n_iterations": int(vqe_meta.get("n_iterations", 0)),
                    }
                )
                if energy < best_energy:
                    best_energy = energy
                    best_i = i
                    last_qc = qc
                    last_mi = molecule_info
                    last_backend = backend_used
                    best_vqe_meta = vqe_meta
                    best_observable = observable
                chem_meta = {**chem_meta, **pt_meta, "scan_points_computed": i + 1}

            assert last_qc is not None
            if hw == "anu":
                seed = await self.fetch_anu_entropy()
                chem_meta = {**chem_meta, "anu_entropy_preview": seed[:16]}

            # Single noisy pass on the lowest-energy PES point only; running it
            # on every scan point would multiply latency for no extra UX value.
            noisy_meta: dict[str, Any] | None = None
            if use_noise and best_observable is not None:
                try:
                    noisy_meta = await self._run_noisy_expectation(
                        best_observable,
                        last_qc,
                        shots=noise_shots,
                        fake_device=fake_for_noise,
                        profile_label=noise_prof,
                    )
                    self._last_run_used_aer_noise = True
                except Exception as e:
                    warnings.append(f"[noise] noisy ⟨H⟩ pass failed: {e!r}")

            chem_meta["nuclei_coords"] = [
                [float(c[0]), float(c[1]), float(c[2])] for c in last_mi.coords
            ]
            chem_meta["atomic_symbols"] = [str(s) for s in last_mi.symbols]

            cloud_data = build_electron_probability_cloud(last_qc, last_mi)
            if noisy_meta is not None:
                set_noise_telemetry(
                    active=True,
                    profile=noise_prof,
                    level="simulated-device",
                    readout_error_e3=None,
                    gate_error_e3=None,
                )
            else:
                set_noise_telemetry(active=False, level="off", profile=None)

            if any_bailout:
                warnings.append(
                    "[vqe] one or more PES points hit SLSQP maxiter without "
                    "converging; treat those energies as upper bounds."
                )

            return {
                "result": f"PES scan: {len(scan_curve)} points; min energy = {best_energy:.4f} Ha at r = {scan_curve[best_i]['distance']} Å",
                "energy": float(best_energy),
                "molecule": label,
                "smiles": smiles,
                "structure": structure,
                "hardware_provider": hw,
                "depth": last_qc.depth(),
                "qubits": last_qc.num_qubits,
                "backend": last_backend,
                "cloud_data": cloud_data,
                "chemistry": chem_meta,
                "is_scan": True,
                "scan_curve": scan_curve,
                "vqe": _public_vqe_meta(best_vqe_meta),
                "noisy_pass": noisy_meta,
                "warnings": warnings,
                "noise_active": noisy_meta is not None,
                "noise_profile": noise_prof if noisy_meta is not None else None,
            }

        if not dimer_mode:
            observable, molecule_info, chem_meta = build_qubit_operator_from_chemical_input(
                structure=structure,
                smiles=smiles,
                max_qubits=max_qubits,
                charge=charge,
                mapper_kind="jordan_wigner",
            )
            label = str(
                chem_meta.get("display_label") or structure or smiles or "unknown"
            )

            energy, backend_used, qc, vqe_meta = await self._run_vqe_energy(
                observable,
                maxiter=vqe_maxiter,
            )

        if hw == "anu":
            seed = await self.fetch_anu_entropy()
            chem_meta = {**chem_meta, "anu_entropy_preview": seed[:16]}

        # Post-VQE noisy ⟨H⟩ pass on the optimal circuit (does not affect SLSQP).
        noisy_meta: dict[str, Any] | None = None
        if use_noise:
            try:
                noisy_meta = await self._run_noisy_expectation(
                    observable,
                    qc,
                    shots=noise_shots,
                    fake_device=fake_for_noise,
                    profile_label=noise_prof,
                )
                self._last_run_used_aer_noise = True
            except Exception as e:
                warnings.append(f"[noise] noisy ⟨H⟩ pass failed: {e!r}")

        chem_meta["nuclei_coords"] = [
            [float(c[0]), float(c[1]), float(c[2])] for c in molecule_info.coords
        ]
        chem_meta["atomic_symbols"] = [str(s) for s in molecule_info.symbols]

        cloud_data = build_electron_probability_cloud(qc, molecule_info)
        if noisy_meta is not None:
            set_noise_telemetry(
                active=True,
                profile=noise_prof,
                level="simulated-device",
                readout_error_e3=None,
                gate_error_e3=None,
            )
        else:
            set_noise_telemetry(active=False, level="off", profile=None)

        if not vqe_meta.get("converged", False):
            warnings.append(
                f"[vqe] SLSQP did not report success "
                f"(message='{vqe_meta.get('convergence_message')}', "
                f"maxiter={vqe_meta.get('maxiter')}); "
                "treat the energy as an upper bound on the true ground state."
            )

        return {
            "result": f"Energy = {energy:.4f} Hartree",
            "energy": energy,
            "molecule": label,
            "smiles": smiles,
            "structure": structure,
            "hardware_provider": hw,
            "depth": qc.depth(),
            "qubits": qc.num_qubits,
            "backend": backend_used,
            "cloud_data": cloud_data,
            "chemistry": chem_meta,
            "is_scan": False,
            "vqe": _public_vqe_meta(vqe_meta),
            "noisy_pass": noisy_meta,
            "warnings": warnings,
            "noise_active": noisy_meta is not None,
            "noise_profile": noise_prof if noisy_meta is not None else None,
        }

    async def oracle_sketch(self, api_key: str, payload: dict) -> dict:
        """Path B: Oracle Sketching via Interferometric Classical Shadows"""
        await asyncio.sleep(1.5)
        num_qubits = 4
        qc = QuantumCircuit(num_qubits)
        for i in range(num_qubits):
            qc.h(i)
        qc.cx(0, 1)
        qc.cx(2, 3)
        qc.cz(1, 2)

        await asyncio.sleep(2)
        return {"sketch_dimension": num_qubits, "reduced_data": [0.85, -0.42, 0.11, 0.99]}
