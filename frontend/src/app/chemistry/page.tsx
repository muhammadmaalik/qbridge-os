"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  API_BASE,
  establishPqcSession,
  moleculeRequestCanonical,
  pqcSignMessage,
  webSocketUrlForApi,
} from "@/lib/pqcHandshake";

const FRIENDLY_CHEM_ERROR =
  "Simulation failed: Molecule too complex for current quantum quota or backend timeout.";

type MoleculeOption = {
  label: string;
  value: string;
  mode: "structure" | "smiles";
};

type MoleculeResult = {
  energy?: number;
  depth?: number;
  qubits?: number;
  backend?: string;
  molecule?: string;
  chemistry?: Record<string, unknown>;
  warnings?: string[];
};

function mapChemistryError(msg: string): string {
  const t = msg.toLowerCase();
  if (
    t.includes("could not resolve") ||
    t.includes("invalid smiles") ||
    t.includes("unsupported formula") ||
    t.includes("pubchem")
  ) {
    return "Simulation failed: Unknown or invalid molecule input. Try a valid formula, name, or SMILES.";
  }
  if (
    t.includes("max_qubits") ||
    t.includes("qubits") ||
    t.includes("active space") ||
    t.includes("too complex")
  ) {
    return "Simulation failed: Molecule exceeds current qubit quota. Try a smaller molecule or reduce complexity.";
  }
  return FRIENDLY_CHEM_ERROR;
}

const MOLECULES: MoleculeOption[] = [
  { label: "Hydrogen (H2)", value: "H2", mode: "structure" },
  { label: "Lithium Hydride (LiH)", value: "LiH", mode: "structure" },
  { label: "Water (H2O)", value: "H2O", mode: "structure" },
  { label: "Ethane (C2H6)", value: "CC", mode: "smiles" },
  { label: "Caffeine (C8H10N4O2)", value: "caffeine", mode: "structure" },
];

function extractDipoleMoment(result: MoleculeResult | null): string {
  if (!result?.chemistry || typeof result.chemistry !== "object") return "N/A";
  const c = result.chemistry as Record<string, unknown>;
  const fromFields = c.dipole_moment ?? c.dipole ?? c.dipole_au ?? c.dipole_debye;
  if (typeof fromFields === "number") return fromFields.toFixed(6);
  if (typeof fromFields === "string" && fromFields.trim()) return fromFields;
  return "N/A";
}

async function waitForChemistryResult(jobId: string, timeoutMs = 35000): Promise<MoleculeResult> {
  const wsUrl = webSocketUrlForApi();
  return await new Promise<MoleculeResult>((resolve, reject) => {
    let done = false;
    const ws = new WebSocket(wsUrl);

    const timer = window.setTimeout(() => {
      if (done) return;
      done = true;
      try {
        ws.close();
      } catch {
        /* ignore */
      }
      reject(new Error("timeout"));
    }, timeoutMs);

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(String(event.data)) as {
          type?: string;
          job_id?: string;
          message?: string;
          data?: unknown;
        };

        if (parsed.type === "result" && parsed.job_id === jobId && parsed.data) {
          if (done) return;
          done = true;
          window.clearTimeout(timer);
          ws.close();
          resolve(parsed.data as MoleculeResult);
          return;
        }
        if (parsed.type === "error" && parsed.job_id === jobId) {
          if (done) return;
          done = true;
          window.clearTimeout(timer);
          ws.close();
          reject(new Error(parsed.message || "simulation_failed"));
        }
      } catch {
        /* ignore non-json frames */
      }
    };

    ws.onerror = () => {
      if (done) return;
      done = true;
      window.clearTimeout(timer);
      reject(new Error("ws_error"));
    };
  });
}

export default function ChemistryPage() {
  const [selected, setSelected] = useState<MoleculeOption>(MOLECULES[0]);
  const [customMolecule, setCustomMolecule] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MoleculeResult | null>(null);
  const [engineLog, setEngineLog] = useState<Record<string, unknown> | null>(null);

  const dipoleText = useMemo(() => extractDipoleMoment(result), [result]);

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setEngineLog(null);

    try {
      const session = await establishPqcSession();
      const useCustom = customMolecule.trim().length > 0;
      const chosenMode = useCustom ? ("structure" as const) : selected.mode;
      const chosenValue = useCustom ? customMolecule.trim() : selected.value;

      const body: Record<string, unknown> = {
        username: "testuser",
        max_qubits: 28,
        hardware_provider: "ibm",
        noise: false,
      };
      if (chosenMode === "smiles") body.smiles = chosenValue;
      else body.structure = chosenValue;

      const canonical = moleculeRequestCanonical("testuser", {
        structure: chosenMode === "structure" ? chosenValue : "",
        smiles: chosenMode === "smiles" ? chosenValue : "",
        hardwareProvider: "ibm",
        maxQubits: 28,
        scan: "",
        noise: false,
      });
      const signature = await pqcSignMessage(session.sharedSecretHex, canonical);

      const queueRes = await fetch(`${API_BASE}/api/v1/compute/molecule`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-QBridge-Session": session.sessionId,
          "X-QBridge-Signature": signature,
        },
        body: JSON.stringify(body),
      });

      if (!queueRes.ok) {
        const detail = await queueRes.text();
        setError(mapChemistryError(detail));
        return;
      }
      const queueJson = (await queueRes.json()) as { job_id?: string };
      if (!queueJson.job_id) {
        setError(FRIENDLY_CHEM_ERROR);
        return;
      }

      const r = await waitForChemistryResult(queueJson.job_id, 35000);
      setResult(r);
      setEngineLog({
        hartree_fock_initial_state: "Reference determinant |1100...> (backend-internal HF seed)",
        jordan_wigner_mapping: r.chemistry ?? null,
        qubits_used: r.qubits ?? null,
        optimizer_logs: {
          backend: r.backend ?? null,
          circuit_depth: r.depth ?? null,
          warnings: r.warnings ?? [],
        },
      });
    } catch (e) {
      setError(mapChemistryError(String(e)));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-zinc-950 px-4 py-6 text-zinc-200 md:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-6 rounded-2xl border border-white/10 bg-zinc-900/40 p-5 shadow-[0_20px_60px_rgba(0,0,0,0.35)] backdrop-blur-xl">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">
                Quantum Chemistry Dashboard
              </h1>
              <p className="mt-1 text-sm text-zinc-400">
                Biotech-lab inspired VQE interface for molecular simulation.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Link
                href="/"
                className="rounded-xl border border-zinc-700 bg-zinc-900/60 px-4 py-2 text-sm text-zinc-300 transition hover:border-blue-400/40 hover:text-blue-200"
              >
                Main Dashboard
              </Link>
              <Link
                href="/finance"
                className="rounded-xl border border-zinc-700 bg-zinc-900/60 px-4 py-2 text-sm text-zinc-300 transition hover:border-emerald-400/40 hover:text-emerald-200"
              >
                Quantum Finance
              </Link>
            </div>
          </div>
        </header>

        <section className="mb-6 grid gap-6 lg:grid-cols-12">
          <div className="rounded-2xl border border-white/10 bg-zinc-900/40 p-5 backdrop-blur-xl lg:col-span-4">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-blue-300">
              Molecule Selection Panel
            </h2>
            <div className="space-y-4">
              <div>
                <label className="mb-2 block text-xs font-medium text-zinc-400">
                  Molecule Preset
                </label>
                <select
                  value={`${selected.mode}:${selected.value}`}
                  onChange={(e) => {
                    const picked = MOLECULES.find(
                      (m) => `${m.mode}:${m.value}` === e.target.value
                    );
                    if (picked) setSelected(picked);
                  }}
                  className="w-full rounded-xl border border-zinc-700 bg-zinc-950/80 px-3 py-2 text-sm text-zinc-100 outline-none transition focus:border-blue-400/50 focus:ring-2 focus:ring-blue-500/20"
                >
                  {MOLECULES.map((m) => (
                    <option key={`${m.mode}:${m.value}`} value={`${m.mode}:${m.value}`}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-2 block text-xs font-medium text-zinc-400">
                  Custom Molecule Input (formula/name/SMILES)
                </label>
                <input
                  value={customMolecule}
                  onChange={(e) => setCustomMolecule(e.target.value)}
                  placeholder="e.g., C6H12O6, Aspirin, C1=CC=CC=C1"
                  className="w-full rounded-xl border border-zinc-700 bg-zinc-950/80 px-3 py-2 text-sm text-zinc-100 outline-none transition focus:border-violet-400/50 focus:ring-2 focus:ring-violet-500/20"
                />
                <p className="mt-1 text-[11px] text-zinc-500">
                  If provided, custom input overrides the preset dropdown.
                </p>
              </div>

              <button
                onClick={runSimulation}
                disabled={loading}
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-violet-400/30 bg-violet-500/15 px-4 py-2.5 text-sm font-semibold text-violet-200 transition hover:bg-violet-500/25 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading && (
                  <svg
                    className="h-4 w-4 animate-spin text-violet-300"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      cx="12"
                      cy="12"
                      r="9"
                      className="opacity-25"
                      stroke="currentColor"
                      strokeWidth="3"
                    />
                    <path
                      d="M21 12a9 9 0 0 1-9 9"
                      stroke="currentColor"
                      strokeWidth="3"
                      strokeLinecap="round"
                    />
                  </svg>
                )}
                {loading
                  ? "Fetching 3D geometry & computing quantum state..."
                  : "Run VQE Chemistry Simulation"}
              </button>

              {error && (
                <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-300">
                  {error}
                </p>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-zinc-900/40 p-5 backdrop-blur-xl lg:col-span-8">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-violet-300">
              Visual Dashboard
            </h2>

            <div className="grid gap-5 md:grid-cols-2">
              <div className="rounded-xl border border-zinc-700/80 bg-zinc-950/50 p-5">
                <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Calculated Ground State Energy
                </p>
                <p className="mt-4 text-3xl font-semibold tracking-tight text-cyan-300">
                  {typeof result?.energy === "number" ? result.energy.toFixed(6) : "--"}
                </p>
                <p className="mt-1 text-xs text-zinc-500">Hartree</p>
              </div>

              <div className="rounded-xl border border-zinc-700/80 bg-zinc-950/50 p-5">
                <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
                  Dipole Moment
                </p>
                <p className="mt-4 text-3xl font-semibold tracking-tight text-violet-300">
                  {dipoleText}
                </p>
                <p className="mt-1 text-xs text-zinc-500">Debye / backend units</p>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-white/10 bg-zinc-900/40 p-5 backdrop-blur-xl">
          <details className="group" open>
            <summary className="cursor-pointer list-none text-sm font-semibold uppercase tracking-wider text-blue-300">
              VQE Quantum Engine Logs
              <span className="ml-2 text-zinc-500 group-open:hidden">(expand)</span>
            </summary>
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-zinc-700/80 bg-zinc-950/55 p-3">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  Hartree-Fock Initial State
                </h3>
                <pre className="custom-scrollbar max-h-[260px] overflow-auto rounded-lg bg-black/30 p-3 text-[11px] text-zinc-300">
{JSON.stringify(engineLog?.hartree_fock_initial_state ?? null, null, 2)}
                </pre>
              </div>

              <div className="rounded-xl border border-zinc-700/80 bg-zinc-950/55 p-3">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  Jordan-Wigner Mapping Data
                </h3>
                <pre className="custom-scrollbar max-h-[260px] overflow-auto rounded-lg bg-black/30 p-3 text-[11px] text-zinc-300">
{JSON.stringify(engineLog?.jordan_wigner_mapping ?? null, null, 2)}
                </pre>
              </div>

              <div className="rounded-xl border border-zinc-700/80 bg-zinc-950/55 p-3 lg:col-span-2">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  Qubits + Optimizer Logs
                </h3>
                <pre className="custom-scrollbar max-h-[320px] overflow-auto rounded-lg bg-black/30 p-3 text-[11px] text-zinc-300">
{JSON.stringify(
  {
    qubits_used: engineLog?.qubits_used ?? null,
    optimizer_logs: engineLog?.optimizer_logs ?? null,
    molecule: result?.molecule ?? selected.label,
  },
  null,
  2
)}
                </pre>
              </div>
            </div>
          </details>
        </section>
      </div>
    </main>
  );
}

