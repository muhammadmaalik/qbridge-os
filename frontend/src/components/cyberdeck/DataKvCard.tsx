"use client";

import type { LucideIcon } from "lucide-react";

type Row = { label: string; value: string };

export default function DataKvCard({
  title,
  icon: Icon,
  rows,
  accent = "cyan",
  emptyMessage = "Awaiting simulation…",
}: {
  title: string;
  icon?: LucideIcon;
  rows: Row[];
  accent?: "cyan" | "green" | "violet";
  emptyMessage?: string;
}) {
  const border =
    accent === "green"
      ? "border-emerald-500/25"
      : accent === "violet"
        ? "border-violet-500/25"
        : "border-cyan-500/25";
  const titleColor =
    accent === "green"
      ? "text-emerald-400"
      : accent === "violet"
        ? "text-violet-400"
        : "text-cyan-400";

  return (
    <div className={`cyber-panel h-full rounded-lg border ${border} bg-black/50 p-4`}>
      <div className="mb-3 flex items-center gap-2">
        {Icon && <Icon className={`h-4 w-4 ${titleColor}`} />}
        <h3 className={`font-mono text-[11px] font-semibold uppercase tracking-[0.2em] ${titleColor}`}>
          {title}
        </h3>
      </div>
      {rows.length === 0 ? (
        <p className="font-mono text-xs text-zinc-600">{emptyMessage}</p>
      ) : (
        <dl className="space-y-2">
          {rows.map((row) => (
            <div
              key={row.label}
              className="grid grid-cols-[minmax(0,42%)_1fr] gap-2 border-b border-white/5 pb-2 last:border-0"
            >
              <dt className="font-mono text-[10px] uppercase tracking-wide text-zinc-500">
                {row.label}
              </dt>
              <dd className="break-words font-mono text-xs text-zinc-200">{row.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}
