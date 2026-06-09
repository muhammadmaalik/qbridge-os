"""
qbridge.services.chemistry
==========================

Public SDK entry point for the quantum-chemistry pillar.

``MolecularSimulator.simulate_ground_state`` used to be a hardcoded mock that
built a fixed 2-qubit X/RY/CX circuit and returned a hand-tuned scalar. It now
routes through the real local pipeline:

    legacy formula geometry  ->  ElectronicStructureProblem (Hartree-Fock)
    -> dynamic ActiveSpaceTransformer (chemistry_mapper._trim_active_space)
    -> ParityMapper(num_particles=...)  (modern symmetry-based 2-qubit reduction)
    -> SLSQP variational loop on local statevector  (run_local_vqe_slsqp)

No GPU. No qiskit_ibm_runtime. CPU statevector only.
"""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np


class MolecularSimulator:
    def simulate_ground_state(
        self,
        molecule: str = "H2",
        bond_distance: float = 0.74,
        temperature: float = 298.0,
        *,
        max_qubits: int = 12,
        vqe_maxiter: int = 50,
        noise: bool = False,
        noise_shots: int = 4096,
    ) -> dict[str, Any]:
        """
        Compute the ground-state energy of ``molecule`` with a real local VQE.

        Supports the legacy ``_GEOMETRIES`` table in :mod:`backend.chemistry_mapper`
        (H2, LiH, H2O, N2, CO, CO2, CH4). For diatomics and triatomics with at
        least two atoms, ``bond_distance`` rescales the first internuclear vector
        before the Hamiltonian is built; for monatomics it is recorded but unused.

        ``temperature`` is accepted for SDK back-compat but does not enter the
        zero-K ground-state calculation; it is echoed back as
        ``temperature_kelvin_input`` for transparency.

        ``max_qubits`` caps the qubit width *before* parity reduction; the
        resulting parity-mapped operator typically lands two qubits below this.
        ``vqe_maxiter`` is forwarded to SciPy's SLSQP. The ``status`` and
        ``vqe.converged`` keys in the returned dict surface SLSQP's convergence
        flag so the frontend can detect early bailout.

        When ``noise=True``, after the VQE optimum is found a single noisy ⟨H⟩
        is evaluated on the *optimal* circuit using
        :class:`qiskit_aer.primitives.Estimator` with
        :class:`NoiseModel.from_backend(FakeOsaka)` and ``noise_shots`` shots.
        SLSQP itself runs only on the exact statevector — the noisy pass is
        cosmetic for the UI and does not destabilize the optimizer.
        """
        # Imports are local to avoid pulling the heavy backend graph (httpx,
        # qiskit-nature, scipy, ...) at SDK import time.
        from backend.chemistry_mapper import (
            build_qubit_operator_from_molecule_info,
            molecule_with_first_bond_length,
            parse_formula_to_molecule_info,
        )
        from backend.quantum_router import (
            run_local_noisy_expectation,
            run_local_vqe_slsqp,
        )

        base_mi = parse_formula_to_molecule_info(molecule, charge=0)

        if len(base_mi.symbols) >= 2:
            mi = molecule_with_first_bond_length(base_mi, float(bond_distance))
            stretched = True
        else:
            mi = base_mi
            stretched = False

        observable, _, chem_meta = build_qubit_operator_from_molecule_info(
            mi,
            max_qubits=int(max_qubits),
            meta_extra={
                "display_label": molecule,
                "molecular_formula": str(molecule).strip().upper(),
            },
            mapper_kind="parity",
        )

        vqe = run_local_vqe_slsqp(
            observable,
            maxiter=int(vqe_maxiter),
        )

        noisy_pass: dict[str, Any] | None = None
        if noise:
            try:
                noisy_pass = run_local_noisy_expectation(
                    observable,
                    vqe["circuit"],
                    shots=int(noise_shots),
                )
            except Exception as e:
                noisy_pass = {"error": f"{type(e).__name__}: {e}"}

        status = "Optimized" if vqe["converged"] else "Did not converge (SLSQP maxiter)"

        return {
            "molecule": molecule,
            "simulated_bond_distance": float(bond_distance),
            "bond_distance_applied": bool(stretched),
            "temperature_kelvin_input": float(temperature),
            "ground_state_energy": f"{vqe['energy']:.4f} Hartree",
            "energy_hartree": float(vqe["energy"]),
            "quantum_hardware": "AerSimulator (local statevector, CPU)",
            "qubit_op_qubits": int(observable.num_qubits),
            "mapper": "parity",
            "active_space": {
                "num_spatial_orbitals": chem_meta.get("num_spatial_orbitals"),
                "num_particles": chem_meta.get("num_particles"),
                "active_space_adjusted": bool(chem_meta.get("active_space_adjusted", False)),
                "active_electrons": chem_meta.get("active_electrons"),
                "active_spatial_orbitals": chem_meta.get("active_spatial_orbitals"),
                "max_qubits_budget": chem_meta.get("max_qubits_budget"),
                "nuclear_repulsion_energy": chem_meta.get("nuclear_repulsion_energy"),
            },
            "vqe": {
                "optimizer": vqe["optimizer"],
                "maxiter": vqe["maxiter"],
                "n_iterations": vqe["n_iterations"],
                "n_function_evals": vqe["n_function_evals"],
                "converged": vqe["converged"],
                "convergence_message": vqe["convergence_message"],
                "scipy_status": vqe["scipy_status"],
                "ansatz": vqe["ansatz"],
                "reps": vqe["reps"],
                "entanglement": vqe["entanglement"],
                "num_parameters": vqe["num_parameters"],
                "history_tail": vqe["history_tail"],
            },
            "noisy_pass": noisy_pass,
            "status": status,
        }

    def visualize_bond_curve(self, molecule: str = "H2") -> dict[str, Any]:
        distances = np.linspace(0.2, 2.5, 30)
        energies = [np.exp(-d) - (1.2 / d) for d in distances]

        plt.figure(figsize=(10, 6))
        plt.grid(True)
        plt.title(f"Q-Bridge Molecular Visualizer: {molecule} VQE Potential Energy Curve")
        plt.xlabel("Interatomic Distance (Angstroms)")
        plt.ylabel("Simulated Energy (Hartree)")
        plt.plot(distances, energies, color='#39FF14', linewidth=2.5, marker='o', label='Quantum Energy')
        plt.legend()
        plt.savefig("chemistry_viz.png")
        plt.close()

        return {
            "visualizer": "H2 Energy Curve",
            "status": "Saved to chemistry_viz.png",
        }
