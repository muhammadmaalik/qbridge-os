"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import MoleculeCloudPanel from "@/components/chemistry/MoleculeCloudPanel";
import VqeEnergyChart from "@/components/chemistry/VqeEnergyChart";
import {
  chemistryKvRows,
  isRealVqeBackend,
  MOLECULE_PRESETS,
  type MoleculePreset,
  type MoleculeSimResult,
  nucleiForMolecule,
  optimizerKvRows,
  runMoleculeSync,
  vqeHistoryPoints,
} from "@/lib/chemistryApi";
import { establishPqcSession } from "@/lib/pqcHandshake";
import AuthGuard from "@/components/AuthGuard";

function DataTable({
  title,
  rows,
  emptyMessage = "Run a simulation to populate this table.",
}: {
  title: string;
  rows: { label: string; value: string }[];
  emptyMessage?: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className="border-b border-gray-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
      </div>
      {rows.length === 0 ? (
        <p className="px-4 py-6 text-sm text-gray-500">{emptyMessage}</p>
      ) : (
        <table className="w-full text-left text-sm">
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-b border-gray-100 last:border-0">
                <th className="w-[42%] px-4 py-2.5 font-medium text-gray-600">
                  {row.label}
                </th>
                <td className="px-4 py-2.5 text-gray-900">{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function ChemistryPage() {
  const [selected, setSelected] = useState<MoleculePreset>(MOLECULE_PRESETS[0]);
  const [customMolecule, setCustomMolecule] = useState("");
  const [chemMode, setChemMode] = useState<"single" | "dimer">("single");
  const [smilesA, setSmilesA] = useState("C");
  const [smilesB, setSmilesB] = useState("O");
  const [distanceAngstrom, setDistanceAngstrom] = useState(2.0);
  const [totalCharge, setTotalCharge] = useState(0);
  const [maxQubits, setMaxQubits] = useState(12);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MoleculeSimResult | null>(null);
  const [fallbackMode, setFallbackMode] = useState(false);
  const [pqcReady, setPqcReady] = useState(false);

  useEffect(() => {
    let mounted = true;
    establishPqcSession()
      .then(() => {
        if (mounted) setPqcReady(true);
      })
      .catch(() => {
        if (mounted) setPqcReady(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const activeToken =
    chemMode === "dimer"
      ? `${smilesA.trim()} + ${smilesB.trim()}`
      : customMolecule.trim() || selected.value;
  const activeLabel =
    chemMode === "dimer"
      ? `Dimer (A+B)`
      : customMolecule.trim()
        ? customMolecule.trim()
        : selected.label;

  const chartData = useMemo(
    () => vqeHistoryPoints(result?.vqe),
    [result?.vqe]
  );

  const jwRows = useMemo(
    () => chemistryKvRows(result?.chemistry),
    [result?.chemistry]
  );

  const optRows = useMemo(() => optimizerKvRows(result), [result]);

  const nuclei = useMemo(
    () => nucleiForMolecule(activeToken, result, result?.cloud_data),
    [activeToken, result]
  );

  const realVqe = result ? isRealVqeBackend(result.backend) : null;

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setFallbackMode(false);

    try {
      const useCustom = customMolecule.trim().length > 0;
      const mode = useCustom ? ("smiles" as const) : selected.mode;
      const value = useCustom ? customMolecule.trim() : selected.value;

      if (chemMode === "dimer") {
        const body: Record<string, unknown> = {
          username: "testuser",
          max_qubits: maxQubits,
          hardware_provider: "local",
          noise: false,
          charge: totalCharge,
          smiles_a: smilesA.trim(),
          smiles_b: smilesB.trim(),
          distance_angstrom: distanceAngstrom,
        };
        const sync = await runMoleculeSync(body);
        setResult(sync.data);
        setFallbackMode(Boolean(sync.engaged_simulator_fallback));
        return;
      }

      const body: Record<string, unknown> = {
        username: "testuser",
        max_qubits: maxQubits,
        hardware_provider: "local",
        noise: false,
      };
      if (mode === "smiles") body.smiles = value;
      else body.structure = value;

      const sync = await runMoleculeSync(body);
      setResult(sync.data);
      setFallbackMode(Boolean(sync.engaged_simulator_fallback));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthGuard>
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-4">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              Quantum Chemistry
            </h1>
            <p className="mt-0.5 text-sm text-gray-600">
              Variational quantum eigensolver · ground-state energy analysis
            </p>
          </div>
          <nav className="flex gap-2 text-sm">
            <Link
              href="/"
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-gray-700 hover:bg-gray-50"
            >
              Dashboard
            </Link>
            <Link
              href="/finance"
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-gray-700 hover:bg-gray-50"
            >
              Finance
            </Link>
            <Link
              href="/security"
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-gray-700 hover:bg-gray-50"
            >
              Security
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="grid gap-6 lg:grid-cols-12">
          <aside className="lg:col-span-4">
            <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-semibold text-gray-900">
                Simulation controls
              </h2>

              <div className="mt-4 space-y-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Input mode
                  </label>
                  <select
                    value={chemMode}
                    onChange={(e) =>
                      setChemMode(e.target.value as "single" | "dimer")
                    }
                    className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="single">Single molecule</option>
                    <option value="dimer">Dimer (A + B)</option>
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Molecule preset
                  </label>
                  <select
                    value={`${selected.mode}:${selected.value}`}
                    onChange={(e) => {
                      const picked = MOLECULE_PRESETS.find(
                        (m) => `${m.mode}:${m.value}` === e.target.value
                      );
                      if (picked) setSelected(picked);
                    }}
                    disabled={chemMode === "dimer"}
                    className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    {MOLECULE_PRESETS.map((m) => (
                      <option
                        key={`${m.mode}:${m.value}`}
                        value={`${m.mode}:${m.value}`}
                      >
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Custom molecule
                  </label>
                  <input
                    value={customMolecule}
                    onChange={(e) => setCustomMolecule(e.target.value)}
                    placeholder="Formula, name, or SMILES"
                    disabled={chemMode === "dimer"}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Overrides the preset when filled in.
                  </p>
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Max qubits (statevector budget)
                  </label>
                  <input
                    type="number"
                    value={maxQubits}
                    step={1}
                    min={4}
                    max={28}
                    onChange={(e) =>
                      setMaxQubits(
                        Math.max(
                          4,
                          Math.min(28, Number(e.target.value) || 4)
                        )
                      )
                    }
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Higher means exponentially slower simulation.
                  </p>
                </div>

                {chemMode === "dimer" && (
                  <>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">
                        Dimer SMILES A
                      </label>
                      <input
                        value={smilesA}
                        onChange={(e) => setSmilesA(e.target.value)}
                        placeholder="e.g. CC, O, C1=CC=CC=C1 ..."
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    </div>

                    <div>
                      <label className="mb-1 block text-sm font-medium text-gray-700">
                        Dimer SMILES B
                      </label>
                      <input
                        value={smilesB}
                        onChange={(e) => setSmilesB(e.target.value)}
                        placeholder="e.g. O, NCC, C(=O)O ..."
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="mb-1 block text-sm font-medium text-gray-700">
                          Separation (Angstrom)
                        </label>
                        <input
                          type="number"
                          value={distanceAngstrom}
                          step={0.1}
                          onChange={(e) =>
                            setDistanceAngstrom(
                              Number(e.target.value) || 0
                            )
                          }
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        />
                      </div>

                      <div>
                        <label className="mb-1 block text-sm font-medium text-gray-700">
                          Total charge
                        </label>
                        <input
                          type="number"
                          value={totalCharge}
                          step={1}
                          onChange={(e) =>
                            setTotalCharge(
                              Number.parseInt(e.target.value || "0", 10)
                            )
                          }
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        />
                      </div>
                    </div>
                  </>
                )}

                <button
                  type="button"
                  onClick={runSimulation}
                  disabled={loading || !pqcReady}
                  className="w-full rounded-md bg-blue-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading
                    ? "Running simulation…"
                    : !pqcReady
                      ? "Connecting secure session…"
                      : "Run VQE simulation"}
                </button>

                {!pqcReady && !loading && (
                  <p className="text-xs text-amber-700">
                    Establishing PQC session with the API…
                  </p>
                )}

                {error && (
                  <div
                    role="alert"
                    className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
                  >
                    {error}
                  </div>
                )}
              </div>

              {result && (
                <dl className="mt-6 space-y-2 border-t border-gray-200 pt-4 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-gray-600">Ground state energy</dt>
                    <dd className="font-medium tabular-nums text-gray-900">
                      {typeof result.energy === "number"
                        ? `${result.energy.toFixed(6)} Ha`
                        : "—"}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-600">Molecule</dt>
                    <dd className="text-gray-900">{result.molecule ?? activeLabel}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-600">Backend</dt>
                    <dd className="text-gray-900">
                      {result.backend ?? "—"}
                      {realVqe === false && (
                        <span className="ml-1 text-xs text-amber-700">
                          (catalog fallback — install qiskit-nature)
                        </span>
                      )}
                      {realVqe === true && (
                        <span className="ml-1 text-xs text-emerald-700">
                          (live VQE)
                        </span>
                      )}
                    </dd>
                  </div>
                </dl>
              )}
            </div>
          </aside>

          <div className="space-y-6 lg:col-span-8">
            {result && realVqe === false && (
              <div
                role="status"
                className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
              >
                The full chemistry stack is unavailable on the server, so this run used
                a deterministic catalog fallback instead of Jordan–Wigner + SLSQP VQE.
                Install backend deps (<code className="text-xs">qiskit-nature</code>,{" "}
                <code className="text-xs">scipy</code>) and restart the API for real
                quantum simulation.
              </div>
            )}

            <div className="grid gap-6 md:grid-cols-2">
              <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                <h2 className="mb-3 text-sm font-semibold text-gray-900">
                  Electron density (3D)
                </h2>
                <MoleculeCloudPanel
                  cloudData={result?.cloud_data}
                  nuclei={nuclei}
                  moleculeLabel={result?.molecule ?? activeLabel}
                  loading={loading}
                />
                {result?.qubits != null && (
                  <p className="mt-2 text-xs text-gray-500">
                    Mapped qubits: {result.qubits}
                  </p>
                )}
              </section>

              <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                <h2 className="mb-3 text-sm font-semibold text-gray-900">
                  VQE energy convergence
                </h2>
                <VqeEnergyChart data={chartData} groundState={result?.energy} />
                {result?.energy != null && chartData.length > 0 && (
                  <p className="mt-2 text-center text-xs text-gray-500">
                    Converged to {result.energy.toFixed(6)} Ha over{" "}
                    {chartData.length} iterations
                  </p>
                )}
              </section>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <DataTable title="Jordan–Wigner mapping" rows={jwRows} />
              <DataTable title="Optimizer & qubit telemetry" rows={optRows} />
            </div>

            {result?.result && (
              <div className="rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-sm">
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                  Result summary
                </p>
                <p className="mt-1 text-sm text-gray-800">{result.result}</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
    </AuthGuard>
  );
}
