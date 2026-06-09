"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import MoleculeCloudPanel from "@/components/chemistry/MoleculeCloudPanel";
import VqeEnergyChart from "@/components/chemistry/VqeEnergyChart";
import {
  chemistryKvRows,
  MOLECULE_PRESETS,
  type MoleculePreset,
  type MoleculeSimResult,
  nucleiForMolecule,
  optimizerKvRows,
  runMoleculeSync,
  vqeHistoryPoints,
} from "@/lib/chemistryApi";

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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MoleculeSimResult | null>(null);
  const [fallbackMode, setFallbackMode] = useState(false);

  const activeToken = customMolecule.trim() || selected.value;
  const activeLabel = customMolecule.trim()
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
    () => nucleiForMolecule(activeToken, result?.cloud_data),
    [activeToken, result?.cloud_data]
  );

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setFallbackMode(false);

    try {
      const useCustom = customMolecule.trim().length > 0;
      const mode = useCustom ? ("structure" as const) : selected.mode;
      const value = useCustom ? customMolecule.trim() : selected.value;

      const body: Record<string, unknown> = {
        username: "testuser",
        max_qubits: 28,
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
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Overrides the preset when filled in.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={runSimulation}
                  disabled={loading}
                  className="w-full rounded-md bg-blue-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? "Running simulation…" : "Run VQE simulation"}
                </button>

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
                      {fallbackMode && (
                        <span className="ml-1 text-xs text-amber-700">
                          (demo fallback)
                        </span>
                      )}
                      {!fallbackMode && result.chemistry?.ab_initio && (
                        <span className="ml-1 text-xs text-emerald-700">
                          (ab initio)
                        </span>
                      )}
                    </dd>
                  </div>
                </dl>
              )}
            </div>
          </aside>

          <div className="space-y-6 lg:col-span-8">
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
  );
}
