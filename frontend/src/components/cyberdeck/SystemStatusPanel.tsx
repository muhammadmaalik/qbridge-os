"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Activity,
  Cpu,
  Shield,
  Thermometer,
  Wifi,
} from "lucide-react";
import { API_BASE } from "@/lib/pqcHandshake";

type HealthPayload = {
  status?: string;
  pqc_auth_bypass_active?: boolean;
  pqc_auth_bypass_env_var?: string;
};

type SystemStatusPayload = {
  pqc?: {
    dev_bypass_active?: boolean;
    status?: string;
    algorithm?: string;
  };
  noise_model?: {
    t1_us?: number;
    t2_us?: number;
    readout_error_e3?: number;
    gate_error_e3?: number;
  };
  runtime?: { service?: string; version?: string };
};

function seededJitter(seed: number, amp: number): number {
  const x = Math.sin(seed * 12.9898) * 43758.5453;
  return (x - Math.floor(x)) * amp;
}

export default function SystemStatusPanel() {
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [system, setSystem] = useState<SystemStatusPayload | null>(null);
  const [apiOnline, setApiOnline] = useState(false);
  const [tick, setTick] = useState(0);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      const t0 = performance.now();
      try {
        const [hRes, sRes] = await Promise.all([
          fetch(`${API_BASE}/health`),
          fetch(`${API_BASE}/api/v1/system/status`),
        ]);
        const ms = Math.round(performance.now() - t0);
        if (cancelled) return;
        setLatencyMs(ms);
        setApiOnline(hRes.ok && sRes.ok);
        if (hRes.ok) setHealth((await hRes.json()) as HealthPayload);
        if (sRes.ok) setSystem((await sRes.json()) as SystemStatusPayload);
        setTick((t) => t + 1);
      } catch {
        if (!cancelled) {
          setApiOnline(false);
          setLatencyMs(null);
        }
      }
    };
    poll();
    const id = setInterval(poll, 3500);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const pqcBypass =
    health?.pqc_auth_bypass_active === true ||
    system?.pqc?.dev_bypass_active === true;

  const qubitTempMk = useMemo(() => {
    const t2 = system?.noise_model?.t2_us ?? 42;
    const base = 12 + 1000 / Math.max(t2, 1);
    return base + seededJitter(tick, 2.8);
  }, [system?.noise_model?.t2_us, tick]);

  const cpuLoad = useMemo(() => {
    const gate = system?.noise_model?.gate_error_e3 ?? 1.2;
    const base = 18 + gate * 4 + (apiOnline ? 12 : 0);
    return Math.min(99, base + seededJitter(tick + 1, 14));
  }, [system?.noise_model?.gate_error_e3, apiOnline, tick]);

  return (
    <aside className="cyber-panel sticky top-0 z-40 border-b border-cyan-500/20 bg-[#030508]/95 backdrop-blur-md">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-stretch gap-3 px-4 py-3 md:px-6">
        <div className="flex min-w-[200px] flex-col justify-center border-r border-cyan-500/15 pr-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-cyan-400/80">
            Quantum Bridge OS
          </p>
          <p className="font-mono text-xs text-emerald-400/90">
            KERNEL v{system?.runtime?.version ?? "1.0.0"} · CHEMISTRY_MODULE
          </p>
        </div>

        <Metric
          icon={<Thermometer className="h-3.5 w-3.5" />}
          label="Qubit temp"
          value={`${qubitTempMk.toFixed(1)} mK`}
          meter={Math.min(100, (qubitTempMk / 80) * 100)}
          tone="cyan"
        />
        <Metric
          icon={<Cpu className="h-3.5 w-3.5" />}
          label="CPU load"
          value={`${cpuLoad.toFixed(0)}%`}
          meter={cpuLoad}
          tone="green"
        />
        <Metric
          icon={<Wifi className="h-3.5 w-3.5" />}
          label="API ping"
          value={latencyMs != null ? `${latencyMs} ms` : "—"}
          meter={apiOnline ? Math.max(8, 100 - latencyMs! / 3) : 0}
          tone={apiOnline ? "green" : "red"}
        />
        <Metric
          icon={<Shield className="h-3.5 w-3.5" />}
          label="PQC bypass"
          value={pqcBypass ? "DEV_ACTIVE" : "ENFORCED"}
          meter={pqcBypass ? 72 : 100}
          tone={pqcBypass ? "amber" : "green"}
        />
        <div className="ml-auto flex items-center gap-2 self-center">
          <span
            className={`inline-flex items-center gap-1.5 rounded border px-2 py-1 font-mono text-[10px] uppercase tracking-wider ${
              apiOnline
                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                : "border-red-500/40 bg-red-500/10 text-red-300"
            }`}
          >
            <Activity className={`h-3 w-3 ${apiOnline ? "animate-pulse" : ""}`} />
            {apiOnline ? "API_ONLINE" : "API_OFFLINE"}
          </span>
        </div>
      </div>
    </aside>
  );
}

function Metric({
  icon,
  label,
  value,
  meter,
  tone,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  meter: number;
  tone: "cyan" | "green" | "amber" | "red";
}) {
  const bar =
    tone === "cyan"
      ? "bg-cyan-400"
      : tone === "green"
        ? "bg-emerald-400"
        : tone === "amber"
          ? "bg-amber-400"
          : "bg-red-400";
  const text =
    tone === "cyan"
      ? "text-cyan-300"
      : tone === "green"
        ? "text-emerald-300"
        : tone === "amber"
          ? "text-amber-300"
          : "text-red-300";

  return (
    <div className="flex min-w-[130px] flex-1 flex-col gap-1 rounded border border-white/5 bg-black/40 px-3 py-2">
      <div className={`flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-zinc-500`}>
        {icon}
        {label}
      </div>
      <p className={`font-mono text-sm font-semibold tabular-nums ${text}`}>{value}</p>
      <div className="h-1 overflow-hidden rounded-full bg-zinc-900">
        <div
          className={`h-full rounded-full transition-all duration-700 ${bar} shadow-[0_0_12px_currentColor]`}
          style={{ width: `${Math.min(100, Math.max(4, meter))}%` }}
        />
      </div>
    </div>
  );
}
