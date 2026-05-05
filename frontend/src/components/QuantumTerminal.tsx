"use client";

import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import {
  API_BASE,
  establishPqcSession,
  moleculeRequestCanonical,
  pqcSignMessage,
  type PqcSession,
} from "@/lib/pqcHandshake";

export type QuantumTerminalHandle = {
  appendLine: (
    text: string,
    kind?: "stdout" | "stderr" | "system" | "success"
  ) => void;
};

type Line = {
  id: string;
  text: string;
  kind: "stdout" | "stderr" | "system" | "success";
};

const PROMPT = "qbridge@os:~$ ";

/** Parse `command --flag1 v1 --flag2 v2` (values run until the next ` --` or end of line). */
export function parseFlagCommand(input: string, command: string): Map<string, string> | null {
  const trimmed = input.trim();
  if (!new RegExp(`^${command}\\b`, "i").test(trimmed)) return null;
  let rest = trimmed.replace(new RegExp(`^${command}\\s*`, "i"), "");
  const out = new Map<string, string>();

  while (rest.length > 0) {
    rest = rest.replace(/^\s+/, "");
    if (!rest) break;
    const m = rest.match(/^--([a-z0-9-]+)(\s+|$)/i);
    if (!m) break;
    const flag = m[1].toLowerCase();
    rest = rest.slice(m[0].length);
    if (!rest || rest.startsWith("--")) {
      out.set(flag, "");
      continue;
    }
    let value = "";
    if (rest[0] === '"' || rest[0] === "'") {
      const q = rest[0];
      let i = 1;
      while (i < rest.length) {
        if (rest[i] === "\\" && i + 1 < rest.length) {
          i += 2;
          continue;
        }
        if (rest[i] === q) break;
        i++;
      }
      value = rest.slice(1, i);
      rest = rest.slice(i + 1);
    } else {
      const next = rest.search(/\s+--/);
      if (next === -1) {
        value = rest.trim();
        rest = "";
      } else {
        value = rest.slice(0, next).trim();
        rest = rest.slice(next);
      }
    }
    out.set(flag, value);
  }
  return out;
}

function isPqcAuthFailure(status: number, message: string): boolean {
  if (status === 401) return true;
  const t = message.toLowerCase();
  return (
    t.includes("pqc") ||
    t.includes("verification failed") ||
    t.includes("invalid or missing session") ||
    t.includes("quantum-safe signature")
  );
}

async function formatHttpError(res: Response): Promise<string> {
  const t = await res.text();
  try {
    const j = JSON.parse(t) as { detail?: unknown };
    const d = j.detail;
    if (Array.isArray(d)) {
      return d
        .map((x: unknown) =>
          typeof x === "object" && x !== null && "msg" in x
            ? String((x as { msg: string }).msg)
            : JSON.stringify(x)
        )
        .join("; ");
    }
    if (typeof d === "string") return d;
    return t.slice(0, 1200);
  } catch {
    return t.slice(0, 1200) || `HTTP ${res.status}`;
  }
}

const QuantumTerminal = forwardRef<QuantumTerminalHandle>(function QuantumTerminal(
  _props,
  ref
) {
  const [lines, setLines] = useState<Line[]>([
    {
      id: "boot",
      text: "Quantum Bridge OS — main control unit. Type `help`.",
      kind: "system",
    },
  ]);
  const [input, setInput] = useState("");
  const [hw, setHw] = useState<"ibm" | "local" | "anu">("ibm");
  const pqcRef = useRef<PqcSession | null>(null);
  const terminalScrollRef = useRef<HTMLDivElement>(null);

  useImperativeHandle(
    ref,
    () => ({
      appendLine: (text, kind: Line["kind"] = "stdout") => {
        setLines((prev) => [
          ...prev,
          { id: `${Date.now()}-${Math.random()}`, text, kind },
        ]);
      },
    }),
    []
  );

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const s = await establishPqcSession();
        if (mounted) pqcRef.current = s;
      } catch {
        if (mounted) pqcRef.current = null;
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const el = terminalScrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines]);

  const runCommand = async (raw: string) => {
    const cmd = raw.trim();
    if (!cmd) return;

    setLines((p) => [
      ...p,
      { id: `${Date.now()}-in`, text: `${PROMPT}${cmd}`, kind: "stdout" },
    ]);

    const lower = cmd.toLowerCase();
    if (lower === "help" || lower === "?") {
      setLines((p) => [
        ...p,
        {
          id: `${Date.now()}-h`,
          kind: "stdout",
          text: [
            "Commands:",
            "  simulate --smiles <STRING> [--scan start:end:step] [--noise]",
            "    Queue VQE; optional PES scan; --noise = Aer noise from fake IBM device",
            "  optimize --tickers AAPL,MSFT,TSLA [--period 1mo] [--risk 0.5]",
            "    Quantum portfolio selection (QAOA); period defaults to 1mo, risk to 0.5",
            "  connect --hw <ibm|local|anu>  Execution target",
            "  status --system              GET /api/v1/system/status",
            "  help                         This list",
            "",
            "Quantum operations: VQE (molecule job), Entropy (/api/v1/entropy), PQC-Handshake (/api/v1/security/handshake)",
          ].join("\n"),
        },
      ]);
      return;
    }

    const optFlags = parseFlagCommand(cmd, "optimize");
    if (optFlags) {
      const tickersRaw = optFlags.get("tickers")?.trim();
      if (!tickersRaw) {
        setLines((p) => [
          ...p,
          {
            id: `${Date.now()}-e`,
            text: "[error] optimize requires --tickers SYMBOL[,SYMBOL,...]",
            kind: "stderr",
          },
        ]);
        return;
      }
      const tickerList = tickersRaw
        .split(",")
        .map((t) => t.trim().toUpperCase())
        .filter(Boolean);
      if (tickerList.length < 2) {
        setLines((p) => [
          ...p,
          {
            id: `${Date.now()}-e`,
            text: "[error] optimize needs at least two tickers (comma-separated).",
            kind: "stderr",
          },
        ]);
        return;
      }

      const period = optFlags.get("period")?.trim() || "1mo";
      const riskRaw = optFlags.get("risk")?.trim();
      let riskFactor = 0.5;
      if (riskRaw !== undefined && riskRaw !== "") {
        const r = Number.parseFloat(riskRaw);
        if (!Number.isFinite(r)) {
          setLines((p) => [
            ...p,
            {
              id: `${Date.now()}-e`,
              text: "[error] --risk must be a number (e.g. 0.5).",
              kind: "stderr",
            },
          ]);
          return;
        }
        riskFactor = r;
      }

      try {
        const res = await fetch(`${API_BASE}/api/v1/finance/optimize`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tickers: tickerList,
            period,
            risk_factor: riskFactor,
          }),
        });

        if (!res.ok) {
          const errMsg = await formatHttpError(res);
          setLines((p) => [
            ...p,
            {
              id: `${Date.now()}-e`,
              text: `[error] HTTP ${res.status}: ${errMsg}`,
              kind: "stderr",
            },
          ]);
          return;
        }

        const data = (await res.json()) as {
          allocation?: Record<string, number>;
          budget?: number;
          selected_tickers?: string[];
        };

        const allocation = data.allocation ?? {};
        const budget = data.budget ?? 0;
        const buy = Object.entries(allocation)
          .filter(([, v]) => Number(v) >= 1)
          .map(([k]) => k);
        const reject = Object.entries(allocation)
          .filter(([, v]) => Number(v) < 1)
          .map(([k]) => k);

        const buyLabel =
          buy.length > 0 ? buy.sort().join(", ") : "(none)";
        const rejectLabel =
          reject.length > 0 ? reject.sort().join(", ") : "(none)";

        setLines((p) => [
          ...p,
          {
            id: `${Date.now()}-fo1`,
            kind: "success",
            text: `[finance] QAOA Optimization Complete (Budget: ${budget})`,
          },
          {
            id: `${Date.now()}-fo2`,
            kind: "success",
            text: `[finance] BUY / HOLD: ${buyLabel}`,
          },
          {
            id: `${Date.now()}-fo3`,
            kind: "success",
            text: `[finance] REJECT: ${rejectLabel}`,
          },
        ]);
      } catch (e) {
        setLines((p) => [
          ...p,
          {
            id: `${Date.now()}-ex`,
            text: `[error] ${String(e)}`,
            kind: "stderr",
          },
        ]);
      }
      return;
    }

    const flags = parseFlagCommand(cmd, "simulate");
    if (flags) {
      const smiles = flags.get("smiles")?.trim();
      if (!smiles) {
        setLines((p) => [
          ...p,
          {
            id: `${Date.now()}-e`,
            text: "[error] simulate requires --smiles <string>",
            kind: "stderr",
          },
        ]);
        return;
      }
      const scan = flags.get("scan")?.trim() || undefined;
      const hasNoise = flags.has("noise");
      let sess = pqcRef.current;
      if (!sess) {
        setLines((p) => [
          ...p,
          {
            id: `${Date.now()}-e`,
            text: "[error] PQC session not ready — wait a moment or reload the page.",
            kind: "stderr",
          },
        ]);
        return;
      }
      const username = "testuser";
      if (hasNoise) {
        setLines((p) => [
          ...p,
          {
            id: `${Date.now()}-nm`,
            text: "[noise mode active] Using qiskit-aer NoiseModel from a fake IBM backend (local / fallback paths).",
            kind: "system",
          },
        ]);
      }
      try {
        const runSignedPost = async (session: PqcSession) => {
          const canonical = moleculeRequestCanonical(username, {
            smiles,
            hardwareProvider: hw,
            maxQubits: 28,
            scan: scan ?? "",
            noise: hasNoise,
          });
          const sig = await pqcSignMessage(session.sharedSecretHex, canonical);
          return fetch(`${API_BASE}/api/v1/compute/molecule`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-QBridge-Session": session.sessionId,
              "X-QBridge-Signature": sig,
            },
            body: JSON.stringify({
              username,
              smiles,
              max_qubits: 28,
              hardware_provider: hw,
              scan: scan ?? null,
              noise: hasNoise,
            }),
          });
        };

        let res = await runSignedPost(sess);

        if (!res.ok) {
          const errMsg = await formatHttpError(res);
          if (isPqcAuthFailure(res.status, errMsg)) {
            setLines((p) => [
              ...p,
              {
                id: `${Date.now()}-rh`,
                text: "[system] PQC verification failed — performing one automatic re-handshake…",
                kind: "system",
              },
            ]);
            const fresh = await establishPqcSession({ force: true });
            pqcRef.current = fresh;
            sess = fresh;
            res = await runSignedPost(sess);
          } else {
            setLines((p) => [
              ...p,
              {
                id: `${Date.now()}-e`,
                text: `[error] HTTP ${res.status}: ${errMsg}`,
                kind: "stderr",
              },
            ]);
            return;
          }
        }

        if (!res.ok) {
          const errRetry = await formatHttpError(res);
          setLines((p) => [
            ...p,
            {
              id: `${Date.now()}-e`,
              text: `[error] HTTP ${res.status}: ${errRetry}`,
              kind: "stderr",
            },
          ]);
          return;
        }

        const j = (await res.json()) as {
          job_id?: string;
          warnings?: string[];
          engaged_local_fallback?: boolean;
        };
        if (j.engaged_local_fallback) {
          setLines((p) => [
            ...p,
            {
              id: `${Date.now()}-hwfb`,
              text: "[hardware] IBM Key missing. Engaging Local Qiskit Aer Simulator (Reference: FakeOsaka)...",
              kind: "system",
            },
          ]);
        }
        if (j.warnings?.length) {
          setLines((p) => [
            ...p,
            ...j.warnings!.map((w, i) => ({
              id: `${Date.now()}-w-${i}`,
              text: w,
              kind: "system" as const,
            })),
          ]);
        }
        setLines((p) => [
          ...p,
          {
            id: `${Date.now()}-ok`,
            kind: "stdout",
            text: `Queued job ${j.job_id ?? "?"}. Awaiting WebSocket feed…`,
          },
        ]);
      } catch (e) {
        setLines((p) => [
          ...p,
          {
            id: `${Date.now()}-ex`,
            text: `[error] ${String(e)}`,
            kind: "stderr",
          },
        ]);
      }
      return;
    }

    const conn = cmd.match(/^connect\s+--hw\s+(\w+)$/i);
    if (conn) {
      const w = conn[1].toLowerCase();
      if (w === "ibm" || w === "local" || w === "anu") {
        setHw(w);
        setLines((p) => [
          ...p,
          {
            id: `${Date.now()}-hw`,
            text: `Hardware target → ${w}`,
            kind: "system",
          },
        ]);
      } else {
        setLines((p) => [
          ...p,
          {
            id: `${Date.now()}-badhw`,
            text: "[error] Use: ibm | local | anu",
            kind: "stderr",
          },
        ]);
      }
      return;
    }

    if (/^status\s+--system$/i.test(cmd)) {
      try {
        const res = await fetch(`${API_BASE}/api/v1/system/status`);
        if (!res.ok) {
          const err = await formatHttpError(res);
          setLines((p) => [
            ...p,
            { id: `${Date.now()}-e`, text: `[error] ${err}`, kind: "stderr" },
          ]);
          return;
        }
        const data = await res.json();
        setLines((p) => [
          ...p,
          {
            id: `${Date.now()}-st`,
            kind: "stdout",
            text: JSON.stringify(data, null, 2),
          },
        ]);
      } catch (e) {
        setLines((p) => [
          ...p,
          {
            id: `${Date.now()}-ex`,
            text: `[error] ${String(e)}`,
            kind: "stderr",
          },
        ]);
      }
      return;
    }

    setLines((p) => [
      ...p,
      {
        id: `${Date.now()}-uk`,
        text: "[error] Unknown command. Try `help`.",
        kind: "stderr",
      },
    ]);
  };

  return (
    <div className="font-mono text-sm rounded-xl border border-zinc-700/80 bg-zinc-900 text-zinc-200 shadow-lg overflow-hidden flex flex-col min-h-[300px] ring-1 ring-zinc-800/50">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-zinc-800 bg-zinc-950">
        <div className="flex gap-1.5">
          <span className="w-3 h-3 rounded-full bg-red-500/85" />
          <span className="w-3 h-3 rounded-full bg-amber-500/85" />
          <span className="w-3 h-3 rounded-full bg-emerald-500/85" />
        </div>
        <span className="text-[10px] uppercase tracking-[0.2em] text-zinc-500">
          main-control · hw:{hw}
        </span>
      </div>
      <div
        ref={terminalScrollRef}
        className="flex-1 overflow-y-auto p-3 space-y-1 max-h-[340px] custom-scrollbar bg-zinc-900"
      >
        {lines.map((ln) => (
          <pre
            key={ln.id}
            className={`whitespace-pre-wrap break-words text-[13px] leading-relaxed ${
              ln.kind === "stderr"
                ? "text-red-400"
                : ln.kind === "system"
                  ? "text-cyan-400/95"
                  : ln.kind === "success"
                    ? "text-emerald-400"
                    : "text-zinc-300"
            }`}
          >
            {ln.text}
          </pre>
        ))}
      </div>
      <form
        className="flex items-center gap-2 border-t border-zinc-800 bg-black/40 px-3 py-2.5"
        onSubmit={(e) => {
          e.preventDefault();
          const v = input;
          setInput("");
          void runCommand(v);
        }}
      >
        <span className="text-emerald-500/90 shrink-0 select-none">{PROMPT}</span>
        <input
          className="flex-1 min-w-0 bg-transparent outline-none text-zinc-100 placeholder:text-zinc-600"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="optimize --tickers AAPL,MSFT,TSLA --period 3mo --risk 0.5"
          spellCheck={false}
          autoCapitalize="off"
          autoCorrect="off"
        />
      </form>
    </div>
  );
});

export default QuantumTerminal;
