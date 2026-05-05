"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { API_BASE } from "@/lib/pqcHandshake";

type OptimizeResponse = {
  allocation: Record<string, number>;
  selected_tickers: string[];
  budget: number;
  risk_factor: number;
  objective_value: number;
  market?: {
    period?: string;
    start_date?: string;
    end_date?: string;
    n_observations?: number;
  };
  solver?: Record<string, unknown>;
  quantum_details?: Record<string, unknown>;
};

type MarketDataResponse = {
  tickers: string[];
  expected_returns: Record<string, number>;
  covariance_matrix: number[][];
  correlation_matrix?: number[][];
  sentiment_scores?: Record<string, number>;
};

function parseTickers(input: string): string[] {
  return Array.from(
    new Set(
      input
        .split(",")
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean)
    )
  );
}

function portfolioMetrics(
  allocation: Record<string, number>,
  expectedReturns: Record<string, number>,
  covariance: number[][]
): { expectedReturn: number; risk: number } {
  const chosen = Object.entries(allocation)
    .filter(([, v]) => v >= 1)
    .map(([k]) => k);
  if (chosen.length === 0) return { expectedReturn: 0, risk: 0 };

  const w = chosen.map(() => 1 / chosen.length);
  let mu = 0;
  for (let i = 0; i < chosen.length; i++) {
    mu += w[i] * (expectedReturns[chosen[i]] ?? 0);
  }

  const idx: number[] = [];
  const keys = Object.keys(allocation);
  for (const c of chosen) idx.push(Math.max(0, keys.indexOf(c)));

  let variance = 0;
  for (let i = 0; i < idx.length; i++) {
    for (let j = 0; j < idx.length; j++) {
      const cov = covariance[idx[i]]?.[idx[j]] ?? 0;
      variance += w[i] * cov * w[j];
    }
  }
  return { expectedReturn: mu, risk: Math.sqrt(Math.max(variance, 0)) };
}

export default function FinancePage() {
  const [tickersInput, setTickersInput] = useState("AAPL,MSFT,TSLA");
  const [period, setPeriod] = useState("1mo");
  const [risk, setRisk] = useState(0.5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [opt, setOpt] = useState<OptimizeResponse | null>(null);
  const [marketData, setMarketData] = useState<MarketDataResponse | null>(null);

  const allocationChart = useMemo(() => {
    if (!opt?.allocation) return [];
    return Object.entries(opt.allocation).map(([ticker, v]) => ({
      ticker,
      weight: Number(v) >= 1 ? 100 : 0,
      selected: Number(v) >= 1 ? "BUY/HOLD" : "REJECT",
    }));
  }, [opt]);

  const metrics = useMemo(() => {
    if (!opt?.allocation || !marketData?.expected_returns || !marketData?.covariance_matrix) {
      return { expectedReturn: 0, risk: 0 };
    }
    return portfolioMetrics(opt.allocation, marketData.expected_returns, marketData.covariance_matrix);
  }, [opt, marketData]);

  const metricChart = useMemo(
    () => [
      { metric: "Predicted Return", value: metrics.expectedReturn * 100 },
      { metric: "Predicted Risk", value: metrics.risk * 100 },
    ],
    [metrics]
  );

  const onOptimize = async () => {
    setLoading(true);
    setError(null);
    try {
      const tickers = parseTickers(tickersInput);
      if (tickers.length < 2) {
        setError("Use at least 2 tickers (comma-separated).");
        return;
      }

      const optimizeRes = await fetch(`${API_BASE}/api/v1/finance/optimize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tickers,
          period,
          risk_factor: risk,
        }),
      });

      if (!optimizeRes.ok) {
        const txt = await optimizeRes.text();
        setError(`Optimize failed (${optimizeRes.status}): ${txt}`);
        return;
      }
      const optimizeData = (await optimizeRes.json()) as OptimizeResponse;
      setOpt(optimizeData);

      const query = encodeURIComponent(tickers.join(","));
      const dataRes = await fetch(`${API_BASE}/api/v1/finance/data?tickers=${query}&period=${encodeURIComponent(period)}`);
      if (!dataRes.ok) {
        const txt = await dataRes.text();
        setError(`Data fetch failed (${dataRes.status}): ${txt}`);
        setMarketData(null);
        return;
      }
      const md = (await dataRes.json()) as MarketDataResponse;
      setMarketData(md);
    } catch (e) {
      setError(String(e));
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
              <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">Quantum Finance Dashboard</h1>
              <p className="mt-1 text-sm text-zinc-400">
                Bloomberg-inspired portfolio desk powered by QAOA optimization.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Link
                href="/"
                className="rounded-xl border border-zinc-700 bg-zinc-900/60 px-4 py-2 text-sm text-zinc-300 transition hover:border-cyan-400/40 hover:text-cyan-200"
              >
                Main Dashboard
              </Link>
            </div>
          </div>
        </header>

        <section className="mb-6 grid gap-6 lg:grid-cols-12">
          <div className="rounded-2xl border border-white/10 bg-zinc-900/40 p-5 backdrop-blur-xl lg:col-span-4">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-cyan-300">Stock Selection Panel</h2>
            <div className="space-y-4">
              <div>
                <label className="mb-2 block text-xs font-medium text-zinc-400">Tickers</label>
                <input
                  value={tickersInput}
                  onChange={(e) => setTickersInput(e.target.value)}
                  className="w-full rounded-xl border border-zinc-700 bg-zinc-950/80 px-3 py-2 text-sm text-zinc-100 outline-none transition focus:border-cyan-400/50 focus:ring-2 focus:ring-cyan-500/20"
                  placeholder="AAPL,MSFT,TSLA"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-2 block text-xs font-medium text-zinc-400">Period</label>
                  <select
                    value={period}
                    onChange={(e) => setPeriod(e.target.value)}
                    className="w-full rounded-xl border border-zinc-700 bg-zinc-950/80 px-3 py-2 text-sm text-zinc-100 outline-none transition focus:border-cyan-400/50"
                  >
                    <option value="1mo">1mo</option>
                    <option value="3mo">3mo</option>
                    <option value="6mo">6mo</option>
                    <option value="1y">1y</option>
                  </select>
                </div>
                <div>
                  <label className="mb-2 block text-xs font-medium text-zinc-400">Risk Factor</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={risk}
                    onChange={(e) => setRisk(Number(e.target.value))}
                    className="w-full rounded-xl border border-zinc-700 bg-zinc-950/80 px-3 py-2 text-sm text-zinc-100 outline-none transition focus:border-emerald-400/50"
                  />
                </div>
              </div>
              <button
                onClick={onOptimize}
                disabled={loading}
                className="w-full rounded-xl border border-emerald-400/30 bg-emerald-500/15 px-4 py-2.5 text-sm font-semibold text-emerald-200 transition hover:bg-emerald-500/25 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Optimizing..." : "Run Quantum Finance Optimize"}
              </button>
              {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-300">{error}</p>}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-zinc-900/40 p-5 backdrop-blur-xl lg:col-span-8">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-emerald-300">Results Dashboard</h2>
            {!opt ? (
              <div className="flex min-h-[260px] items-center justify-center rounded-xl border border-dashed border-zinc-700 bg-zinc-950/35">
                <p className="text-sm text-zinc-500">Run optimization to view portfolio predictions.</p>
              </div>
            ) : (
              <div className="grid gap-5 md:grid-cols-2">
                <div className="rounded-xl border border-zinc-700/80 bg-zinc-950/50 p-3">
                  <p className="mb-2 text-xs font-medium text-zinc-400">Portfolio Weights</p>
                  <div className="h-[220px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={allocationChart}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                        <XAxis dataKey="ticker" stroke="#a1a1aa" />
                        <YAxis stroke="#a1a1aa" />
                        <Tooltip
                          contentStyle={{
                            background: "#18181b",
                            border: "1px solid #3f3f46",
                            borderRadius: 8,
                          }}
                        />
                        <Bar dataKey="weight" fill="#22d3ee" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className="rounded-xl border border-zinc-700/80 bg-zinc-950/50 p-3">
                  <p className="mb-2 text-xs font-medium text-zinc-400">Predicted Return vs Risk</p>
                  <div className="h-[220px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={metricChart}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                        <XAxis dataKey="metric" stroke="#a1a1aa" />
                        <YAxis stroke="#a1a1aa" />
                        <Tooltip
                          contentStyle={{
                            background: "#18181b",
                            border: "1px solid #3f3f46",
                            borderRadius: 8,
                          }}
                        />
                        <Bar dataKey="value" fill="#34d399" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className="rounded-xl border border-zinc-700/80 bg-zinc-950/50 p-3 md:col-span-2">
                  <div className="flex flex-wrap items-center gap-3 text-sm">
                    <span className="rounded-lg bg-zinc-900 px-2 py-1 text-zinc-300">
                      Budget: <strong className="text-zinc-100">{opt.budget}</strong>
                    </span>
                    <span className="rounded-lg bg-zinc-900 px-2 py-1 text-zinc-300">
                      Objective: <strong className="text-zinc-100">{opt.objective_value.toFixed(5)}</strong>
                    </span>
                    <span className="rounded-lg bg-zinc-900 px-2 py-1 text-zinc-300">
                      Selected: <strong className="text-emerald-300">{opt.selected_tickers.join(", ") || "(none)"}</strong>
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-white/10 bg-zinc-900/40 p-5 backdrop-blur-xl">
          <details className="group" open>
            <summary className="cursor-pointer list-none text-sm font-semibold uppercase tracking-wider text-cyan-300">
              Classical vs. Quantum Engine
              <span className="ml-2 text-zinc-500 group-open:hidden">(expand)</span>
            </summary>
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-zinc-700/80 bg-zinc-950/55 p-3">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">Covariance Matrix</h3>
                <pre className="custom-scrollbar max-h-[280px] overflow-auto rounded-lg bg-black/30 p-3 text-[11px] text-zinc-300">
{JSON.stringify(marketData?.covariance_matrix ?? null, null, 2)}
                </pre>
              </div>
              <div className="rounded-xl border border-zinc-700/80 bg-zinc-950/55 p-3">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">Expected Returns + Sentiment</h3>
                <pre className="custom-scrollbar max-h-[280px] overflow-auto rounded-lg bg-black/30 p-3 text-[11px] text-zinc-300">
{JSON.stringify(
  {
    expected_returns: marketData?.expected_returns ?? null,
    sentiment_scores: marketData?.sentiment_scores ?? null,
  },
  null,
  2
)}
                </pre>
              </div>
              <div className="rounded-xl border border-zinc-700/80 bg-zinc-950/55 p-3 lg:col-span-2">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">Qiskit QAOA Simulation Logs</h3>
                <pre className="custom-scrollbar max-h-[320px] overflow-auto rounded-lg bg-black/30 p-3 text-[11px] text-zinc-300">
{JSON.stringify(
  {
    solver: opt?.solver ?? null,
    quantum_details: opt?.quantum_details ?? null,
    market_window: opt?.market ?? null,
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

