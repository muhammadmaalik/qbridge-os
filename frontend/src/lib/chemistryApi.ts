import {
  API_BASE,
  establishPqcSession,
  moleculeRequestCanonical,
  pqcSignMessage,
} from "@/lib/pqcHandshake";
import type { CloudPoint } from "@/components/ElectronCloudViewer";

export type MoleculePreset = {
  label: string;
  value: string;
  mode: "structure" | "smiles";
};

export const MOLECULE_PRESETS: MoleculePreset[] = [
  { label: "Hydrogen (H₂)", value: "H2", mode: "structure" },
  { label: "Lithium Hydride (LiH)", value: "LiH", mode: "structure" },
  { label: "Water (H₂O)", value: "H2O", mode: "structure" },
  { label: "Ethane (C₂H₆)", value: "CC", mode: "smiles" },
  {
    label: "Caffeine",
    value: "Cn1cnc2n(C)c(=O)n(C)c(=O)c12",
    mode: "smiles",
  },
];

export type VqeMeta = {
  energy?: number;
  energy_history?: number[];
  history_tail?: number[];
  n_iterations?: number;
  n_function_evals?: number;
  converged?: boolean;
  convergence_message?: string;
  optimizer?: string;
  ansatz?: string;
  backend?: string;
  num_qubits?: number;
  num_parameters?: number;
  simulation_mode?: boolean;
};

export type MoleculeSimResult = {
  result?: string;
  energy?: number;
  molecule?: string;
  smiles?: string | null;
  structure?: string | null;
  backend?: string;
  depth?: number;
  qubits?: number;
  chemistry?: Record<string, unknown>;
  vqe?: VqeMeta;
  cloud_data?: CloudPoint[];
  warnings?: string[];
  is_scan?: boolean;
  scan_curve?: { distance: number; energy: number }[];
  noise_active?: boolean;
};

export type SyncMoleculeResponse = {
  status: string;
  data: MoleculeSimResult;
  engaged_simulator_fallback?: boolean;
  ab_initio?: boolean;
};

export function normalizeFormulaKey(raw: string): string {
  const s = raw.trim().toUpperCase().replace(/\s+/g, "");
  if (s === "CAFFEINE" || s === "C8H10N4O2") return "CAFFEINE";
  return s;
}

function parseNucleiCoords(raw: unknown): [number, number, number][] | null {
  if (!Array.isArray(raw) || raw.length === 0) return null;
  const out: [number, number, number][] = [];
  for (const row of raw) {
    if (!Array.isArray(row) || row.length < 3) continue;
    const x = Number(row[0]);
    const y = Number(row[1]);
    const z = Number(row[2]);
    if (Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z)) {
      out.push([x, y, z]);
    }
  }
  return out.length > 0 ? out : null;
}

export function nucleiForMolecule(
  _structureOrSmiles: string,
  result?: MoleculeSimResult | null,
  cloud?: CloudPoint[]
): [number, number, number][] {
  const fromApi = parseNucleiCoords(result?.chemistry?.nuclei_coords);
  if (fromApi) return fromApi;

  if (cloud && cloud.length > 0) {
    const hi = cloud.reduce((best, p) =>
      p.probability > best.probability ? p : best
    );
    return [[hi.x * 0.3, hi.y * 0.3, hi.z * 0.3]];
  }
  return [[0, 0, 0], [0, 0, 0.74]];
}

/** Only plot energy values returned by the backend VQE loop (no synthetic padding). */
export function vqeHistoryPoints(vqe?: VqeMeta): { step: number; energy: number }[] {
  const hist = vqe?.energy_history;
  if (!hist?.length) return [];
  return hist.map((energy, i) => ({ step: i + 1, energy }));
}

export function isRealVqeBackend(backend?: string): boolean {
  if (!backend) return false;
  return backend !== "simulated_vqe_fallback";
}

export function mapChemistryError(msg: string): string {
  const t = msg.toLowerCase();
  if (t.includes("pqc verification")) {
    return "Secure session not ready. Reload the page or set QBRIDGE_SKIP_PQC_VERIFY=1 on the API for local dev.";
  }
  if (
    t.includes("could not resolve") ||
    t.includes("invalid smiles") ||
    t.includes("unsupported formula") ||
    t.includes("pubchem")
  ) {
    return "Could not resolve molecule input. Try a valid formula, name, or SMILES.";
  }
  if (t.includes("max_qubits") || t.includes("active space") || t.includes("too complex")) {
    return "Molecule exceeds the configured qubit limit.";
  }
  if (t.includes("timeout") || t.includes("failed to fetch")) {
    return "Could not reach the API. Ensure the backend is running on port 8000.";
  }
  return "Simulation failed. Check backend logs for details.";
}

export async function runMoleculeSync(body: Record<string, unknown>): Promise<SyncMoleculeResponse> {
  const username = String(body.username ?? "testuser");
  const structure = body.structure as string | undefined;
  const smiles = body.smiles as string | undefined;
  const smilesA = body.smiles_a as string | undefined;
  const smilesB = body.smiles_b as string | undefined;
  const distanceAngstrom = body.distance_angstrom as number | undefined;
  const charge = body.charge as number | undefined;
  const hardwareProvider = String(body.hardware_provider ?? "local");
  const maxQubits = Number(body.max_qubits ?? 12);
  const scan = body.scan as string | undefined;
  const noise = Boolean(body.noise);

  const sess = await establishPqcSession();
  const canonical = moleculeRequestCanonical(username, {
    structure,
    smiles,
    smilesA,
    smilesB,
    distanceAngstrom,
    charge,
    hardwareProvider,
    maxQubits,
    scan,
    noise,
  });
  const sig = await pqcSignMessage(sess.sharedSecretHex, canonical);

  const res = await fetch(`${API_BASE}/api/v1/compute/molecule/sync`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-QBridge-Session": sess.sessionId,
      "X-QBridge-Signature": sig,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(mapChemistryError(detail));
  }
  return (await res.json()) as SyncMoleculeResponse;
}

export function chemistryKvRows(
  chemistry?: Record<string, unknown>
): { label: string; value: string }[] {
  if (!chemistry) return [];
  const keys = [
    ["Driver", chemistry.electronic_structure_driver],
    [
      "Ab initio",
      chemistry.ab_initio === true
        ? "yes (HF + VQE)"
        : chemistry.ab_initio === false
          ? "no"
          : undefined,
    ],
    [
      "HF reference (Ha)",
      chemistry.hf_reference_energy_ha != null
        ? String(chemistry.hf_reference_energy_ha)
        : undefined,
    ],
    ["Mapper", chemistry.mapper],
    ["JW / mapped qubits", chemistry.jw_qubits ?? chemistry.qubit_op_qubits],
    ["Spatial orbitals", chemistry.num_spatial_orbitals],
    ["Basis", chemistry.basis],
    ["Particles (α, β)", chemistry.num_particles],
    ["Nuclear repulsion", chemistry.nuclear_repulsion_energy],
    ["Resolution", chemistry.resolution_path],
    ["Active space", chemistry.active_space_adjusted],
    ["Fallback notes", chemistry.windows_fallback_notes],
    ["Simulation mode", chemistry.simulation_mode],
  ] as const;
  return keys
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([label, value]) => ({
      label,
      value: Array.isArray(value) ? JSON.stringify(value) : String(value),
    }));
}

export function optimizerKvRows(
  result: MoleculeSimResult | null
): { label: string; value: string }[] {
  if (!result) return [];
  const v = result.vqe;
  const rows: { label: string; value: string }[] = [
    { label: "Ground state (Ha)", value: result.energy?.toFixed(6) ?? "—" },
    { label: "Backend", value: result.backend ?? "—" },
    { label: "Circuit depth", value: result.depth != null ? String(result.depth) : "—" },
    { label: "Qubits", value: result.qubits != null ? String(result.qubits) : "—" },
    { label: "Optimizer", value: v?.optimizer ?? "—" },
    { label: "Ansatz", value: v?.ansatz ?? "—" },
    { label: "Iterations", value: v?.n_iterations != null ? String(v.n_iterations) : "—" },
    { label: "Function evals", value: v?.n_function_evals != null ? String(v.n_function_evals) : "—" },
    { label: "Converged", value: v?.converged != null ? (v.converged ? "YES" : "NO") : "—" },
    { label: "Parameters", value: v?.num_parameters != null ? String(v.num_parameters) : "—" },
  ];
  if (v?.convergence_message) {
    rows.push({ label: "Message", value: v.convergence_message });
  }
  if (result.warnings?.length) {
    rows.push({ label: "Warnings", value: result.warnings.join(" · ") });
  }
  return rows;
}
