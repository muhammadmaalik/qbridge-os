"use client";

import dynamic from "next/dynamic";
import { memo, useEffect, useMemo, useRef, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import QuantumTerminal, { type QuantumTerminalHandle } from "./QuantumTerminal";
import { mockH2ElectronCloud, type CloudPoint } from "./ElectronCloudViewer";
import { webSocketUrlForApi } from "@/lib/pqcHandshake";

const ElectronCloudViewer = dynamic(
  () => import("./ElectronCloudViewer"),
  {
    ssr: false,
    loading: () => (
      <div className="w-full min-h-[192px] rounded-md border border-zinc-800/80 bg-zinc-950 flex items-center justify-center">
        <span className="text-[10px] text-zinc-600 tracking-wider uppercase">
          Loading ψ*ψ cloud…
        </span>
      </div>
    ),
  }
);

type LogEntry = {
  id: string;
  message: string;
  status: "info" | "success" | "error" | "running";
  timestamp: string;
  data?: any;
};

/** Tight Y-axis around scan energies so the PES minimum is visible. */
function scanEnergyYDomain(curve: { energy: number }[]): [number, number] {
  const vals = curve.map((p) => p.energy);
  const minE = Math.min(...vals);
  const maxE = Math.max(...vals);
  const span = maxE - minE;
  const pad =
    span > 1e-12
      ? span * 0.18
      : Math.max(Math.abs(minE) * 0.02, 0.04);
  return [minE - pad, maxE + pad];
}

function badgeClass(status: string) {
  switch (status) {
    case "success":
      return "bg-emerald-500/10 text-emerald-500 border-emerald-500/20";
    case "error":
      return "bg-red-500/10 text-red-500 border-red-500/20";
    case "running":
      return "bg-amber-500/10 text-amber-500 border-amber-500/20";
    default:
      return "bg-zinc-500/10 text-zinc-400 border-zinc-500/20";
  }
}

/** Isolated so Recharts / R3F resize cycles do not re-run the whole feed. */
const ActivityLogRow = memo(function ActivityLogRow({ log }: { log: LogEntry }) {
  const showViz = Boolean(log.data && (log.data.molecule || log.data.is_scan));
  const scanCurve =
    showViz &&
    log.data &&
    Array.isArray(log.data.scan_curve) &&
    log.data.scan_curve.length > 0
      ? log.data.scan_curve
      : null;

  const yDomain = useMemo(
    () => (scanCurve ? scanEnergyYDomain(scanCurve) : undefined),
    [scanCurve]
  );

  const cloudPoints = useMemo((): CloudPoint[] => {
    if (!showViz || !log.data) return mockH2ElectronCloud();
    const cd = log.data.cloud_data;
    if (Array.isArray(cd) && cd.length > 0) return cd as CloudPoint[];
    return mockH2ElectronCloud();
  }, [showViz, log.data]);

  return (
    <div className="flex gap-3 text-sm items-start">
      <div
        className={`mt-0.5 whitespace-nowrap px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${badgeClass(log.status)}`}
      >
        {log.status}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-zinc-300 leading-relaxed">{log.message}</p>

        {showViz && log.data && (
          <div className="mt-2 bg-zinc-950/50 border border-zinc-800 rounded-lg p-3 shadow-inner">
            <div className="flex justify-between items-center mb-2 pb-2 border-b border-zinc-800/50">
              <span className="text-xs font-semibold text-zinc-400">
                {log.data.is_scan ? "PES scan" : "VQE Results"} (
                {log.data.molecule || "Molecule"})
              </span>
              <span className="text-[10px] font-mono text-zinc-500">
                {log.data.backend || "Simulator"}
              </span>
            </div>

            {log.data.is_scan && scanCurve && yDomain && (
              <div className="mb-4 w-full min-w-0 font-sans">
                <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-2">
                  Potential energy surface (Å vs Hartree)
                </p>
                {/* Explicit box size so ResponsiveContainer never measures 0×0 (flex/scroll parents). */}
                <div
                  className="h-[240px] w-full min-h-[240px] min-w-0 overflow-hidden"
                  style={{ minHeight: 240, width: "100%" }}
                >
                  <ResponsiveContainer width="100%" height="100%" debounce={150}>
                    <LineChart
                      data={scanCurve}
                      margin={{ top: 4, right: 8, left: 0, bottom: 4 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                      <XAxis
                        dataKey="distance"
                        stroke="#71717a"
                        tick={{ fontSize: 10 }}
                        label={{
                          value: "r (Å)",
                          position: "insideBottom",
                          offset: -2,
                          fill: "#71717a",
                          fontSize: 10,
                        }}
                      />
                      <YAxis
                        dataKey="energy"
                        stroke="#71717a"
                        tick={{ fontSize: 10 }}
                        width={56}
                        domain={yDomain}
                        allowDataOverflow={false}
                        label={{
                          value: "E (Ha)",
                          angle: -90,
                          position: "insideLeft",
                          fill: "#71717a",
                          fontSize: 10,
                        }}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#18181b",
                          border: "1px solid #3f3f46",
                          borderRadius: 6,
                          fontSize: 12,
                        }}
                        labelFormatter={(v) => `r = ${v} Å`}
                      />
                      <Line
                        type="monotone"
                        dataKey="energy"
                        stroke="#34d399"
                        strokeWidth={2}
                        dot={{ r: 2, fill: "#6ee7b7" }}
                        activeDot={{ r: 4 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            <div className="flex min-w-0 flex-col gap-4 md:flex-row">
              <div className="flex w-full flex-col gap-1 md:w-1/2">
                <div className="flex justify-between text-xs">
                  <span className="text-zinc-500">
                    {log.data.is_scan ? "Best energy" : "Ground State Energy"}
                  </span>
                  <span className="font-mono font-bold text-emerald-400">
                    {log.data.energy !== undefined
                      ? log.data.energy.toFixed(6)
                      : "N/A"}{" "}
                    Ha
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-zinc-500">Circuit Depth</span>
                  <span className="font-mono text-zinc-300">{log.data.depth}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-zinc-500">Qubits Used</span>
                  <span className="font-mono text-zinc-300">{log.data.qubits}</span>
                </div>
              </div>

              <div className="min-h-[200px] w-full min-w-0 py-1 md:w-1/2">
                <ElectronCloudViewer cloudData={cloudPoints} />
              </div>
            </div>
          </div>
        )}

        <p className="mt-1 text-[10px] text-zinc-600">{log.timestamp}</p>
      </div>
    </div>
  );
});

export default function Console() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const activityScrollRef = useRef<HTMLDivElement>(null);
  const terminalRef = useRef<QuantumTerminalHandle>(null);

  useEffect(() => {
    // Set initial logs after mount to avoid hydration mismatch
    setLogs([
      { id: "1", message: "Boot sequence initiated...", status: "info", timestamp: new Date().toLocaleTimeString() },
      { id: "2", message: "Quantum Bridge OS v1.0.0 Online.", status: "success", timestamp: new Date().toLocaleTimeString() }
    ]);
    
    wsRef.current = new WebSocket(webSocketUrlForApi());

    wsRef.current.onopen = () => {
      addLog("Secure WebSocket channel established.", "success");
    };

    wsRef.current.onmessage = (event) => {
      const text = event.data as string;

      try {
        const parsed = JSON.parse(text) as {
          type?: string;
          reason?: string;
          job_id?: string;
          execution_time_ms?: number;
          data?: unknown;
          message?: string;
        };
        if (parsed.type === "heartbeat") {
          return;
        }
        if (parsed.type === "error") {
          const msg =
            parsed.message ||
            `Job ${parsed.job_id ?? "?"} failed (see activity for details).`;
          terminalRef.current?.appendLine(`[ws error] ${msg}`, "stderr");
          addLog(msg, "error");
          return;
        }
        if (parsed.type === "result" && parsed.data) {
          const payload = parsed.data as {
            warnings?: string[];
            is_scan?: boolean;
            scan_curve?: { distance: number; energy: number }[];
          };
          if (Array.isArray(payload.warnings)) {
            for (const w of payload.warnings) {
              terminalRef.current?.appendLine(w, "system");
            }
          }
          addLog(
            `Job ${parsed.job_id} Completed in ${parsed.execution_time_ms}ms`,
            "success",
            parsed.data
          );
          return;
        }
      } catch {
        // Not JSON, proceed with normal string parsing
      }

      let status: "info" | "success" | "error" | "running" = "info";

      const lower = text.toLowerCase();
      if (lower.includes("error") || lower.includes("fail")) {
        status = "error";
        terminalRef.current?.appendLine(`[ws] ${text}`, "stderr");
      } else if (
        lower.includes("success") ||
        lower.includes("completed") ||
        lower.includes("secured")
      )
        status = "success";
      else if (
        lower.includes("processing") ||
        lower.includes("routing") ||
        lower.includes("computing") ||
        lower.includes("starting")
      )
        status = "running";

      addLog(text, status);
    };

    wsRef.current.onclose = () => {
      addLog("Connection lost. Attempting reconnect...", "error");
    };

    return () => {
      wsRef.current?.close();
    };
  }, []);

  const addLog = (message: string, status: "info" | "success" | "error" | "running", data?: any) => {
    setLogs(prev => [...prev, {
      id: Math.random().toString(36).substring(7),
      message,
      status,
      timestamp: new Date().toLocaleTimeString(),
      data
    }]);
  };

  useEffect(() => {
    const id = requestAnimationFrame(() => {
      const el = activityScrollRef.current;
      if (el) el.scrollTop = el.scrollHeight;
    });
    return () => cancelAnimationFrame(id);
  }, [logs]);

  return (
    <div className="flex min-h-[560px] flex-col overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/40 p-0 shadow-sm">
      <div className="p-4 pb-2 border-b border-zinc-800/60 bg-zinc-950/30">
        <h2 className="text-zinc-100 font-semibold text-xs tracking-widest uppercase mb-3 flex items-center gap-2 text-zinc-400">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.4)]" />
          Main Control Unit
        </h2>
        <QuantumTerminal ref={terminalRef} />
      </div>
      <div className="flex justify-between items-center px-4 py-3 border-b border-zinc-800/80 bg-zinc-900/50">
        <h3 className="text-zinc-300 font-medium text-sm tracking-wide flex items-center gap-2">
          <svg className="w-4 h-4 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" /></svg>
          Recent Activity
        </h3>
        <span className="text-xs text-zinc-500 font-medium px-2 py-1 bg-zinc-800/50 rounded-md">Live Feed</span>
      </div>

      <div
        ref={activityScrollRef}
        className="custom-scrollbar flex max-h-[280px] min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4"
      >
        {logs.map((log) => (
          <ActivityLogRow key={log.id} log={log} />
        ))}
      </div>
    </div>
  );
}
