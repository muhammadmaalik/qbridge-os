"use client";

import { useCallback, useEffect, useState } from "react";

const scrollOpts: ScrollIntoViewOptions = {
  behavior: "smooth",
  block: "start",
};

export default function HelpCenter() {
  const [open, setOpen] = useState(false);

  const scrollToId = useCallback((id: string) => {
    document.getElementById(id)?.scrollIntoView(scrollOpts);
    setOpen(false);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-5 left-5 z-40 flex h-14 w-14 items-center justify-center rounded-2xl border border-white/15 bg-zinc-900/35 text-zinc-100 shadow-[0_8px_32px_rgba(0,0,0,0.45)] backdrop-blur-xl transition hover:border-emerald-400/35 hover:bg-zinc-800/45 hover:text-emerald-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/60"
        aria-label="Open help and documentation"
      >
        <span className="text-2xl font-semibold leading-none">?</span>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center p-4 pb-8 sm:items-center sm:p-6"
          role="dialog"
          aria-modal="true"
          aria-labelledby="help-modal-title"
        >
          <button
            type="button"
            className="absolute inset-0 bg-zinc-950/55 backdrop-blur-md"
            aria-label="Close help"
            onClick={() => setOpen(false)}
          />
          <div
            className="relative max-h-[min(90vh,720px)] w-full max-w-2xl overflow-hidden rounded-2xl border border-white/12 bg-zinc-900/40 shadow-[0_24px_80px_rgba(0,0,0,0.55)] ring-1 ring-white/5 backdrop-blur-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="max-h-[min(90vh,720px)] overflow-y-auto custom-scrollbar">
              <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-white/10 bg-zinc-950/50 px-6 py-4 backdrop-blur-xl">
                <div>
                  <h2
                    id="help-modal-title"
                    className="text-lg font-semibold tracking-tight text-zinc-50"
                  >
                    Help &amp; Documentation
                  </h2>
                  <p className="mt-1 text-xs text-zinc-400">
                    Quantum Bridge OS — quick reference
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="shrink-0 rounded-lg p-2 text-zinc-400 transition hover:bg-white/5 hover:text-zinc-100"
                  aria-label="Close"
                >
                  <svg
                    className="h-5 w-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>

              <div className="space-y-6 px-6 py-5">
                <div>
                  <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                    Quick actions
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => scrollToId("section-terminal")}
                      className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium text-emerald-200/95 backdrop-blur-sm transition hover:border-emerald-400/30 hover:bg-emerald-500/10"
                    >
                      Finance — Terminal
                    </button>
                    <button
                      type="button"
                      onClick={() => scrollToId("section-activity")}
                      className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium text-cyan-200/95 backdrop-blur-sm transition hover:border-cyan-400/30 hover:bg-cyan-500/10"
                    >
                      Chemistry — Activity
                    </button>
                    <button
                      type="button"
                      onClick={() => scrollToId("section-security")}
                      className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium text-violet-200/95 backdrop-blur-sm transition hover:border-violet-400/30 hover:bg-violet-500/10"
                    >
                      Security — Keys
                    </button>
                  </div>
                </div>

                <section className="rounded-xl border border-white/8 bg-white/[0.03] p-4 backdrop-blur-sm">
                  <h3 className="text-sm font-semibold text-cyan-200/95">
                    Quantum chemistry
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-zinc-300/95">
                    We support realistic molecules—from simple diatomics like{" "}
                    <span className="font-mono text-zinc-200">H₂</span> and{" "}
                    <span className="font-mono text-zinc-200">ethane (CC)</span>{" "}
                    to complex organics such as{" "}
                    <span className="font-mono text-zinc-200">caffeine</span>.
                    Simulations use{" "}
                    <strong className="font-medium text-zinc-100">
                      VQE (Variational Quantum Eigensolver)
                    </strong>{" "}
                    on a qubit Hamiltonian to estimate{" "}
                    <strong className="font-medium text-zinc-100">
                      ground-state energies
                    </strong>
                    , optional PES scans along a bond, and Aer noise models that
                    mimic IBM hardware. Results stream into the activity feed
                    below the terminal.
                  </p>
                </section>

                <section className="rounded-xl border border-white/8 bg-white/[0.03] p-4 backdrop-blur-sm">
                  <h3 className="text-sm font-semibold text-emerald-200/95">
                    Quantum finance
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-zinc-300/95">
                    <strong className="font-medium text-zinc-100">
                      Portfolio optimization
                    </strong>{" "}
                    pulls live market data, blends in NLP news sentiment, and
                    encodes selection as a combinatorial problem solved with{" "}
                    <strong className="font-medium text-zinc-100">QAOA</strong>{" "}
                    on a local simulator—conceptually in the same family of
                    amplitude amplification and structured search ideas as{" "}
                    <strong className="font-medium text-zinc-100">Grover</strong>
                    -style heuristics, while discrete portfolio constraints echo
                    the period-finding structure behind{" "}
                    <strong className="font-medium text-zinc-100">Shor</strong>
                    -class algorithms (here used pedagogically, not for
                    factoring). Together this supports{" "}
                    <strong className="font-medium text-zinc-100">
                      risk-aware allocation
                    </strong>{" "}
                    narratives tied to covariance and sentiment-adjusted returns.
                    Use the terminal command{" "}
                    <code className="rounded bg-zinc-950/80 px-1.5 py-0.5 font-mono text-[11px] text-emerald-300/90">
                      optimize --tickers AAPL,MSFT,TSLA
                    </code>
                    .
                  </p>
                </section>

                <section className="rounded-xl border border-white/8 bg-white/[0.03] p-4 backdrop-blur-sm">
                  <h3 className="text-sm font-semibold text-violet-200/95">
                    PQC security
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-zinc-300/95">
                    The dashboard establishes a{" "}
                    <strong className="font-medium text-zinc-100">
                      post-quantum cryptographic (PQC) session
                    </strong>{" "}
                    before sensitive compute requests: a Kyber-style KEM
                    metaphor derives a shared secret, and requests are
                    authenticated with a quantum-safe MAC. That closes the gap
                    where attackers could{" "}
                    <strong className="font-medium text-zinc-100">
                      harvest ciphertexts today and decrypt later
                    </strong>{" "}
                    with a future quantum computer (&quot;harvest now, decrypt
                    later&quot;)—sessions and signatures are designed for a
                    PQC-aware threat model. Manage IBM credentials under{" "}
                    <strong className="font-medium text-zinc-100">
                      Security — Keys
                    </strong>
                    .
                  </p>
                </section>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
