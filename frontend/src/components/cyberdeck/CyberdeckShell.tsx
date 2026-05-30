"use client";

import Link from "next/link";
import { Atom, Home, LineChart, Shield } from "lucide-react";
import SystemStatusPanel from "./SystemStatusPanel";

type CyberdeckShellProps = {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  activeModule?: "chemistry" | "finance" | "home";
};

export default function CyberdeckShell({
  title,
  subtitle,
  children,
  activeModule = "chemistry",
}: CyberdeckShellProps) {
  return (
    <div className="cyberdeck-root min-h-screen bg-[#020305] text-zinc-200">
      <div className="cyberdeck-grid pointer-events-none fixed inset-0 opacity-40" aria-hidden />
      <SystemStatusPanel />

      <div className="relative mx-auto max-w-[1600px] px-4 py-6 md:px-6">
        <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-mono text-2xl font-semibold tracking-tight text-cyan-100 md:text-3xl">
              {title}
            </h1>
            <p className="mt-1 max-w-2xl font-mono text-xs text-zinc-500">{subtitle}</p>
          </div>
          <nav className="flex flex-wrap gap-2 font-mono text-[11px] uppercase tracking-wider">
            <NavLink href="/" active={activeModule === "home"} icon={<Home className="h-3.5 w-3.5" />}>
              OS Root
            </NavLink>
            <NavLink
              href="/chemistry"
              active={activeModule === "chemistry"}
              icon={<Atom className="h-3.5 w-3.5" />}
            >
              Chemistry
            </NavLink>
            <NavLink
              href="/finance"
              active={activeModule === "finance"}
              icon={<LineChart className="h-3.5 w-3.5" />}
            >
              Finance
            </NavLink>
            <span className="inline-flex items-center gap-1.5 rounded border border-zinc-800 bg-zinc-950/80 px-3 py-2 text-zinc-600">
              <Shield className="h-3.5 w-3.5" />
              Entropy · PQC
            </span>
          </nav>
        </header>

        {children}
      </div>
    </div>
  );
}

function NavLink({
  href,
  active,
  icon,
  children,
}: {
  href: string;
  active: boolean;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center gap-1.5 rounded border px-3 py-2 transition ${
        active
          ? "border-cyan-400/50 bg-cyan-500/10 text-cyan-200 shadow-[0_0_20px_rgba(34,211,238,0.15)]"
          : "border-zinc-800 bg-zinc-950/60 text-zinc-400 hover:border-cyan-500/30 hover:text-cyan-200"
      }`}
    >
      {icon}
      {children}
    </Link>
  );
}
