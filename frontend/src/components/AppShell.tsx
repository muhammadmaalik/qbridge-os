"use client";

import Image from "next/image";
import Link from "next/link";
import { Inter } from "next/font/google";

const sans = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

type AppShellProps = {
  children: React.ReactNode;
  /** Right side of the dark header (status pills, account, etc.) */
  headerRight?: React.ReactNode;
};

export default function AppShell({ children, headerRight }: AppShellProps) {
  return (
    <div className={`${sans.className} min-h-screen flex flex-col bg-[#f4f4f4] text-[#161616]`}>
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-[#e0e0e0] bg-[#161616] px-4 md:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <Link href="/" className="text-sm font-semibold tracking-wide text-white hover:text-white">
            Quantum Bridge OS
          </Link>
          <span className="hidden text-xs text-[#c6c6c6] sm:inline">
            Quantum computing platform
          </span>
        </div>
        <nav className="flex items-center gap-2 text-xs">
          <Link
            href="/chemistry"
            className="hidden border border-[#393939] px-3 py-1.5 font-medium text-[#e0e0e0] transition hover:border-[#0f62fe] hover:text-white sm:inline-block"
          >
            Chemistry
          </Link>
          <Link
            href="/finance"
            className="hidden border border-[#393939] px-3 py-1.5 font-medium text-[#e0e0e0] transition hover:border-[#0f62fe] hover:text-white sm:inline-block"
          >
            Finance
          </Link>
          {headerRight}
        </nav>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="relative hidden w-[38%] max-w-xl lg:block">
          <Image
            src="/home-hero.jpg"
            alt="Quantum computing visualization"
            fill
            priority
            className="object-cover"
            sizes="38vw"
          />
          <div className="absolute inset-0 bg-slate-900/55" />
          <div className="absolute bottom-0 left-0 right-0 p-10 text-white">
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-sky-300">
              Operations console
            </p>
            <h2 className="mt-2 max-w-md text-2xl font-semibold leading-snug">
              Run quantum workloads from one control surface
            </h2>
            <p className="mt-3 max-w-lg text-sm leading-relaxed text-[#e8e8e8]">
              Chemistry VQE, portfolio optimization, secure API sessions, and live
              hardware telemetry — unified in Quantum Bridge OS.
            </p>
          </div>
        </aside>

        <main className="dashboard-carbon min-h-0 flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
