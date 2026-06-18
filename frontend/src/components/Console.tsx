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
      return "bg-[#defbe6] text-[#198038] border-[#a7f0ba]";
    case "error":
      return "bg-[#fff1f1] text-[#da1e28] border-[#ffb3b8]";
    case "running":
      return "bg-[#fff8e1] text-[#b28600] border-[#fddc69]";
    default:
      return "bg-[#f4f4f4] text-[#525252] border-[#e0e0e0]";
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
        <p className="text-[#161616] leading-relaxed">{log.message}</p>

        {showViz && log.data && (
          <div className="mt-2 border border-[#e0e0e0] bg-[#f4f4f4] p-3">
            <div className="mb-2 flex items-center justify-between border-b border-[#e0e0e0] pb-2">
              <span className="text-xs font-semibold text-[#525252]">
                {log.data.is_scan ? "PES scan" : "VQE Results"} (
                {log.data.molecule || "Molecule"})
              </span>
              <span className="text-[10px] font-mono text-[#6f6f6f]">
                {log.data.backend || "Simulator"}
              </span>
            </div>

            {log.data.is_scan && scanCurve && yDomain && (
              <div className="mb-4 w-full min-w-0 font-sans">
                <p className="mb-2 text-[10px] uppercase tracking-wider text-[#6f6f6f]">
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
                      <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                      <XAxis
                        dataKey="distance"
                        stroke="#6f6f6f"
                        tick={{ fontSize: 10 }}
                        label={{
                          value: "r (Å)",
                          position: "insideBottom",
                          offset: -2,
                          fill: "#6f6f6f",
                          fontSize: 10,
                        }}
                      />
                      <YAxis
                        dataKey="energy"
                        stroke="#6f6f6f"
                        tick={{ fontSize: 10 }}
                        width={56}
                        domain={yDomain}
                        allowDataOverflow={false}
                        label={{
                          value: "E (Ha)",
                          angle: -90,
                          position: "insideLeft",
                          fill: "#6f6f6f",
                          fontSize: 10,
                        }}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#ffffff",
                          border: "1px solid #e0e0e0",
                          borderRadius: 0,
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
                  <span className="text-[#6f6f6f]">
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
                  <span className="text-[#6f6f6f]">Circuit Depth</span>
                  <span className="font-mono text-[#161616]">{log.data.depth}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-[#6f6f6f]">Qubits Used</span>
                  <span className="font-mono text-[#161616]">{log.data.qubits}</span>
                </div>
              </div>

              <div className="min-h-[200px] w-full min-w-0 py-1 md:w-1/2">
                <ElectronCloudViewer cloudData={cloudPoints} />
              </div>
            </div>
          </div>
        )}

        <p className="mt-1 text-[10px] text-[#6f6f6f]">{log.timestamp}</p>
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
    <div
      id="section-console"
      className="flex min-h-[560px] flex-col overflow-hidden border border-[#e0e0e0] bg-white p-0"
    >
      <div
        id="section-terminal"
        className="scroll-mt-28 border-b border-[#e0e0e0] bg-[#161616] p-4 pb-2"
      >
        <h2 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-[#c6c6c6]">
          <span className="h-1.5 w-1.5 rounded-full bg-[#24a148]" />
          Main control unit
        </h2>
        <QuantumTerminal ref={terminalRef} />
      </div>
      <div
        id="section-activity"
        className="scroll-mt-28 flex min-h-0 flex-1 flex-col border-t border-[#e0e0e0]"
      >
        <div className="flex items-center justify-between border-b border-[#e0e0e0] bg-[#f4f4f4] px-4 py-3">
          <h3 className="flex items-center gap-2 text-sm font-medium tracking-wide text-[#161616]">
            <svg className="h-4 w-4 text-[#6f6f6f]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" /></svg>
            Recent activity
          </h3>
          <span className="bg-white px-2 py-1 text-xs font-medium text-[#525252] border border-[#e0e0e0]">Live feed</span>
        </div>

        <div
          ref={activityScrollRef}
          className="dashboard-scrollbar flex max-h-[280px] min-h-0 flex-1 flex-col gap-4 overflow-y-auto bg-white p-4"
        >
          {logs.map((log) => (
            <ActivityLogRow key={log.id} log={log} />
          ))}
        </div>
      </div>
    </div>
  );
}
