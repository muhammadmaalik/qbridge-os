"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import KeyManager from "@/components/KeyManager";
import Console from "@/components/Console";
import ActionPanel from "@/components/ActionPanel";
import HelpCenter from "@/components/HelpCenter";
import { API_BASE, establishPqcSession } from "@/lib/pqcHandshake";

type NoiseInjection = {
  active?: boolean;
  level?: string;
  profile?: string | null;
  readout_error_e3?: number | null;
  gate_error_e3?: number | null;
};

export default function Home() {
  const [secureTunnel, setSecureTunnel] = useState(false);
  const [noiseTelemetry, setNoiseTelemetry] = useState<NoiseInjection | null>(
    null
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await establishPqcSession();
        if (!cancelled) setSecureTunnel(true);
      } catch {
        if (!cancelled) setSecureTunnel(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/system/status`);
        if (!res.ok || cancelled) return;
        const data = (await res.json()) as { noise_injection?: NoiseInjection };
        if (!cancelled && data.noise_injection) {
          setNoiseTelemetry(data.noise_injection);
        }
      } catch {
        /* ignore */
      }
    };
    poll();
    const id = setInterval(poll, 4000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const noiseLabel =
    noiseTelemetry?.active === true
      ? noiseTelemetry.readout_error_e3 != null
        ? `${noiseTelemetry.profile ?? "aer"} · readout×10³≈${noiseTelemetry.readout_error_e3}`
        : `${noiseTelemetry.profile ?? "aer"} · ${noiseTelemetry.level ?? "simulated"}`
      : "off";

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-200 font-sans p-4 md:p-8 relative">
      <div className="max-w-6xl mx-auto relative z-10">
        <header className="mb-8 border-b border-zinc-800 pb-5 flex justify-between items-end">
          <div>
            <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight flex items-center gap-2">
              <div className="w-5 h-5 rounded-md bg-gradient-to-tr from-indigo-500 to-purple-500 shadow-sm"></div>
              Quantum Bridge <span className="font-normal text-zinc-500">OS</span>
            </h1>
            <p className="text-sm text-zinc-500 mt-2 font-medium">QaaS API Gateway Middleware</p>
            <div className="mt-3 flex items-center gap-2">
              <Link
                href="/finance"
                className="rounded-xl border border-cyan-400/35 bg-cyan-500/10 px-3 py-1.5 text-xs font-semibold tracking-wide text-cyan-200 transition hover:border-cyan-300/60 hover:bg-cyan-500/20"
              >
                Quantum Finance
              </Link>
            </div>
          </div>
          <div className="hidden md:flex flex-wrap gap-x-5 gap-y-2 font-mono text-xs text-zinc-500 bg-zinc-900/50 px-4 py-2 rounded-full border border-zinc-800/80 shadow-sm">
            <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div> DB: ONLINE</span>
            <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div> WS: CONNECTED</span>
            <span className={`flex items-center gap-2 ${secureTunnel ? "text-emerald-400" : "text-zinc-500"}`}>
              <div className={`w-2 h-2 rounded-full shadow-[0_0_8px_rgba(16,185,129,0.45)] ${secureTunnel ? "bg-emerald-500" : "bg-zinc-600"}`}></div>
              Secure Tunnel: {secureTunnel ? "ACTIVE" : "OFFLINE"}
            </span>
            <span
              className={`flex items-center gap-2 ${noiseTelemetry?.active ? "text-amber-400/95" : "text-zinc-500"}`}
              title="Noise injection telemetry (last Aer fake-backend VQE)"
            >
              <div
                className={`w-2 h-2 rounded-full ${noiseTelemetry?.active ? "bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.45)]" : "bg-zinc-600"}`}
              />
              Noise Level: {noiseLabel}
            </span>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div className="lg:col-span-12">
            <Console />
          </div>

          <div
            id="section-security"
            className="scroll-mt-28 lg:col-span-4 flex flex-col gap-8"
          >
            <KeyManager />
          </div>

          <div className="lg:col-span-8 flex flex-col gap-8">
            <ActionPanel />
            
            {/* Diagram / Architecture Vis (Clean Version) */}
            <div className="flex-1 border border-zinc-800 bg-zinc-900/40 p-6 rounded-xl shadow-sm relative overflow-hidden min-h-[300px] flex items-center justify-center">
              
              <div className="relative text-center opacity-80">
                <div className="text-zinc-400 mb-5">
                  <svg className="w-10 h-10 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </div>
                <p className="text-sm font-medium tracking-wide mb-3 text-zinc-300">Hardware Abstraction Layer</p>
                <div className="flex gap-4 text-xs text-zinc-500 font-mono justify-center mt-4">
                  <div className="border border-zinc-800 bg-zinc-900/80 px-4 py-2 rounded-lg shadow-sm">IBM Qiskit Runtime</div>
                  <div className="border border-zinc-800 bg-zinc-900/80 px-4 py-2 rounded-lg shadow-sm">ANU Vacuum Entropy</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <HelpCenter />
    </main>
  );
}
