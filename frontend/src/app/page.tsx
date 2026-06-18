"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import KeyManager from "@/components/KeyManager";
import Console from "@/components/Console";
import ActionPanel from "@/components/ActionPanel";
import HelpCenter from "@/components/HelpCenter";
import AuthGuard from "@/components/AuthGuard";
import AppShell from "@/components/AppShell";
import { API_BASE, establishPqcSession } from "@/lib/pqcHandshake";
import { getStoredUser } from "@/lib/authApi";

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

    const connectTunnel = async () => {
      for (let attempt = 0; attempt < 10 && !cancelled; attempt++) {
        try {
          await establishPqcSession(attempt > 2 ? { force: true } : undefined);
          if (!cancelled) setSecureTunnel(true);
          return;
        } catch {
          if (!cancelled) setSecureTunnel(false);
          await new Promise((resolve) => setTimeout(resolve, 1500));
        }
      }
    };

    void connectTunnel();
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

  const accountEmail = getStoredUser()?.email;

  return (
    <AuthGuard>
      <AppShell
        headerRight={
          <Link
            href="/login"
            className="border border-[#393939] px-3 py-1.5 font-medium text-[#e0e0e0] transition hover:border-[#0f62fe] hover:text-white"
          >
            {accountEmail ?? "Account"}
          </Link>
        }
      >
        <div className="mx-auto max-w-5xl">
          <header className="mb-6 border-b border-[#e0e0e0] pb-5">
            <h1 className="text-[1.75rem] font-semibold leading-tight text-[#161616]">
              Dashboard
            </h1>
            <p className="mt-2 text-sm text-[#525252]">
              QaaS API gateway — monitor jobs, manage credentials, and launch
              quantum workloads.
            </p>
            <div className="mt-4 flex flex-wrap gap-2 font-mono text-[11px] text-[#525252]">
              <StatusPill ok label="DB: ONLINE" />
              <StatusPill ok label="WS: CONNECTED" />
              <StatusPill ok={secureTunnel} label={`Secure tunnel: ${secureTunnel ? "ACTIVE" : "OFFLINE"}`} />
              <StatusPill ok={Boolean(noiseTelemetry?.active)} label={`Noise: ${noiseLabel}`} />
            </div>
          </header>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            <div className="lg:col-span-12">
              <Console />
            </div>

            <div
              id="section-security"
              className="scroll-mt-28 lg:col-span-4"
            >
              <KeyManager />
            </div>

            <div className="flex flex-col gap-6 lg:col-span-8">
              <ActionPanel />

              <div className="flex min-h-[260px] items-center justify-center border border-[#e0e0e0] bg-white p-6">
                <div className="text-center">
                  <div className="mb-4 text-[#525252]">
                    <svg
                      className="mx-auto h-10 w-10"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                      />
                    </svg>
                  </div>
                  <p className="mb-3 text-sm font-medium tracking-wide text-[#161616]">
                    Hardware abstraction layer
                  </p>
                  <div className="mt-4 flex flex-wrap justify-center gap-3 font-mono text-xs text-[#525252]">
                    <span className="border border-[#e0e0e0] bg-[#f4f4f4] px-4 py-2">
                      IBM Qiskit Runtime
                    </span>
                    <span className="border border-[#e0e0e0] bg-[#f4f4f4] px-4 py-2">
                      ANU Vacuum Entropy
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <HelpCenter />
      </AppShell>
    </AuthGuard>
  );
}

function StatusPill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className="inline-flex items-center gap-2 border border-[#e0e0e0] bg-white px-3 py-1.5">
      <span
        className={`h-2 w-2 rounded-full ${ok ? "bg-[#24a148]" : "bg-[#8d8d8d]"}`}
      />
      {label}
    </span>
  );
}
