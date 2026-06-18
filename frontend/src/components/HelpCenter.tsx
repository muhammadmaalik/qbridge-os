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
        className="fixed bottom-5 left-5 z-40 flex h-14 w-14 items-center justify-center border border-[#e0e0e0] bg-white text-[#0f62fe] shadow-lg transition hover:border-[#0f62fe] hover:bg-[#edf5ff] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0f62fe]/40"
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
            className="absolute inset-0 bg-[#161616]/40 backdrop-blur-sm"
            aria-label="Close help"
            onClick={() => setOpen(false)}
          />
          <div
            className="relative max-h-[min(90vh,720px)] w-full max-w-2xl overflow-hidden border border-[#e0e0e0] bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="max-h-[min(90vh,720px)] overflow-y-auto dashboard-scrollbar">
              <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-[#e0e0e0] bg-[#f4f4f4] px-6 py-4">
                <div>
                  <h2
                    id="help-modal-title"
                    className="text-lg font-semibold tracking-tight text-[#161616]"
                  >
                    Help &amp; Documentation
                  </h2>
                  <p className="mt-1 text-xs text-[#525252]">
                    Quantum Bridge OS — quick reference
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="shrink-0 p-2 text-[#6f6f6f] transition hover:bg-[#e0e0e0] hover:text-[#161616]"
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
                  <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#525252]">
                    Quick actions
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => scrollToId("section-terminal")}
                      className="border border-[#e0e0e0] bg-[#f4f4f4] px-4 py-2 text-xs font-medium text-[#161616] transition hover:border-[#0f62fe] hover:bg-[#edf5ff]"
                    >
                      Finance — Terminal
                    </button>
                    <button
                      type="button"
                      onClick={() => scrollToId("section-activity")}
                      className="border border-[#e0e0e0] bg-[#f4f4f4] px-4 py-2 text-xs font-medium text-[#161616] transition hover:border-[#0f62fe] hover:bg-[#edf5ff]"
                    >
                      Chemistry — Activity
                    </button>
                    <button
                      type="button"
                      onClick={() => scrollToId("section-security")}
                      className="border border-[#e0e0e0] bg-[#f4f4f4] px-4 py-2 text-xs font-medium text-[#161616] transition hover:border-[#0f62fe] hover:bg-[#edf5ff]"
                    >
                      Security — Keys
                    </button>
                  </div>
                </div>

                <section className="border border-[#e0e0e0] bg-[#f4f4f4] p-4">
                  <h3 className="text-sm font-semibold text-[#0f62fe]">
                    Quantum chemistry
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-[#525252]">
                    We support realistic molecules—from simple diatomics like{" "}
                    <span className="font-mono text-[#161616]">H₂</span> and{" "}
                    <span className="font-mono text-[#161616]">ethane (CC)</span>{" "}
                    to complex organics such as{" "}
                    <span className="font-mono text-[#161616]">caffeine</span>.
                    Simulations use{" "}
                    <strong className="font-medium text-[#161616]">
                      VQE (Variational Quantum Eigensolver)
                    </strong>{" "}
                    on a qubit Hamiltonian to estimate{" "}
                    <strong className="font-medium text-[#161616]">
                      ground-state energies
                    </strong>
                    , optional PES scans along a bond, and Aer noise models that
                    mimic IBM hardware. Results stream into the activity feed
                    below the terminal.
                  </p>
                </section>

                <section className="border border-[#e0e0e0] bg-[#f4f4f4] p-4">
                  <h3 className="text-sm font-semibold text-[#198038]">
                    Quantum finance
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-[#525252]">
                    <strong className="font-medium text-[#161616]">
                      Portfolio optimization
                    </strong>{" "}
                    pulls live market data, blends in NLP news sentiment, and
                    encodes selection as a combinatorial problem solved with{" "}
                    <strong className="font-medium text-[#161616]">QAOA</strong>{" "}
                    on a local simulator—conceptually in the same family of
                    amplitude amplification and structured search ideas as{" "}
                    <strong className="font-medium text-[#161616]">Grover</strong>
                    -style heuristics, while discrete portfolio constraints echo
                    the period-finding structure behind{" "}
                    <strong className="font-medium text-[#161616]">Shor</strong>
                    -class algorithms (here used pedagogically, not for
                    factoring). Together this supports{" "}
                    <strong className="font-medium text-[#161616]">
                      risk-aware allocation
                    </strong>{" "}
                    narratives tied to covariance and sentiment-adjusted returns.
                    Use the terminal command{" "}
                    <code className="bg-white px-1.5 py-0.5 font-mono text-[11px] text-[#0f62fe] border border-[#e0e0e0]">
                      optimize --tickers AAPL,MSFT,TSLA
                    </code>
                    .
                  </p>
                </section>

                <section className="border border-[#e0e0e0] bg-[#f4f4f4] p-4">
                  <h3 className="text-sm font-semibold text-[#8a3ffc]">
                    PQC security
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-[#525252]">
                    The dashboard establishes a{" "}
                    <strong className="font-medium text-[#161616]">
                      post-quantum cryptographic (PQC) session
                    </strong>{" "}
                    before sensitive compute requests: a Kyber-style KEM
                    metaphor derives a shared secret, and requests are
                    authenticated with a quantum-safe MAC. That closes the gap
                    where attackers could{" "}
                    <strong className="font-medium text-[#161616]">
                      harvest ciphertexts today and decrypt later
                    </strong>{" "}
                    with a future quantum computer (&quot;harvest now, decrypt
                    later&quot;)—sessions and signatures are designed for a
                    PQC-aware threat model. Manage IBM credentials under{" "}
                    <strong className="font-medium text-[#161616]">
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
