"use client";

import { useEffect, useRef, useState } from "react";
import {
  API_BASE,
  establishPqcSession,
  moleculeRequestCanonical,
  pqcSignMessage,
  type PqcSession,
} from "@/lib/pqcHandshake";

const cmdBtn =
  "group relative flex flex-col gap-3 border border-[#e0e0e0] bg-[#f4f4f4] p-5 text-left transition hover:border-[#0f62fe] hover:bg-white disabled:opacity-50";

export default function ActionPanel() {
  const [loading, setLoading] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formula, setFormula] = useState("CN1C=NC2=C1C(=O)N(C(=O)N2C)C");
  const pqcRef = useRef<PqcSession | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const sess = await establishPqcSession();
        if (!mounted) return;
        pqcRef.current = sess;
      } catch {
        if (!mounted) return;
        pqcRef.current = null;
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const requestEntropy = async () => {
    setLoading("entropy");
    try {
      await fetch(`${API_BASE}/api/v1/entropy?username=testuser`, { method: "GET" });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(null);
    }
  };

  const submitMolecule = async () => {
    const sess = pqcRef.current;
    if (!sess) {
      alert("Secure tunnel not ready — PQC handshake incomplete.");
      return;
    }
    setLoading("molecule");
    try {
      const canonical = moleculeRequestCanonical("testuser", {
        structure: formula,
        hardwareProvider: "ibm",
        maxQubits: 28,
        scan: "",
        noise: false,
      });
      const sig = await pqcSignMessage(sess.sharedSecretHex, canonical);
      await fetch(`${API_BASE}/api/v1/compute/molecule`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-QBridge-Session": sess.sessionId,
          "X-QBridge-Signature": sig,
        },
        body: JSON.stringify({
          username: "testuser",
          structure: formula,
          max_qubits: 28,
          hardware_provider: "ibm",
          noise: false,
        }),
      });
      setTimeout(() => {
        setIsModalOpen(false);
        setLoading(null);
      }, 500);
    } catch (e) {
      console.error(e);
      setIsModalOpen(false);
      setLoading(null);
    }
  };

  const computeOracle = async () => {
    const sess = pqcRef.current;
    if (!sess) {
      alert("Secure tunnel not ready — PQC handshake incomplete.");
      return;
    }
    setLoading("oracle");
    try {
      const ds = "massive_data_01";
      const canonical = `testuser|ORACLE|${ds}`;
      const sig = await pqcSignMessage(sess.sharedSecretHex, canonical);
      await fetch(`${API_BASE}/api/v1/compute/oracle-sketch`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-QBridge-Session": sess.sessionId,
          "X-QBridge-Signature": sig,
        },
        body: JSON.stringify({ username: "testuser", payload: { dataset: ds } }),
      });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="relative border border-[#e0e0e0] bg-white p-6">
      <h2 className="mb-5 flex items-center gap-2 text-sm font-semibold tracking-wide text-[#161616]">
        <svg className="h-4 w-4 text-[#6f6f6f]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
        Operational commands
      </h2>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <button onClick={requestEntropy} disabled={loading !== null} className={cmdBtn}>
          <div className="flex h-10 w-10 items-center justify-center border border-[#e0e0e0] bg-white">
            <svg className="h-5 w-5 text-[#0f62fe]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>
          </div>
          <div>
            <span className="mb-1 block text-sm font-semibold text-[#161616]">Entropy generation</span>
            <span className="text-xs text-[#525252]">Fetch ANU vacuum data</span>
          </div>
        </button>

        <button onClick={() => setIsModalOpen(true)} disabled={loading !== null} className={cmdBtn}>
          <div className="flex h-10 w-10 items-center justify-center border border-[#e0e0e0] bg-white">
            <svg className="h-5 w-5 text-[#198038]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5" /></svg>
          </div>
          <div>
            <span className="mb-1 block text-sm font-semibold text-[#161616]">VQE simulation</span>
            <span className="text-xs text-[#525252]">Molecular binding energy</span>
          </div>
        </button>

        <button onClick={computeOracle} disabled={loading !== null} className={cmdBtn}>
          <div className="flex h-10 w-10 items-center justify-center border border-[#e0e0e0] bg-white">
            <svg className="h-5 w-5 text-[#8a3ffc]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" /></svg>
          </div>
          <div>
            <span className="mb-1 block text-sm font-semibold text-[#161616]">Quantum oracle</span>
            <span className="text-xs text-[#525252]">Interferometric shadows</span>
          </div>
        </button>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#161616]/40 p-4 backdrop-blur-sm">
          <div className="w-full max-w-sm border border-[#e0e0e0] bg-white p-6 shadow-lg">
            <div className="mb-5 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-[#161616]">Configure simulation</h3>
              <button onClick={() => setIsModalOpen(false)} className="text-[#6f6f6f] hover:text-[#161616]">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>

            <div className="mb-6">
              <label className="mb-2 block text-xs font-medium uppercase tracking-wide text-[#525252]">
                Molecule (formula, name, or SMILES)
              </label>
              <input
                type="text"
                value={formula}
                onChange={(e) => setFormula(e.target.value)}
                className="w-full border-0 border-b border-[#8d8d8d] bg-[#f4f4f4] px-3 py-3 font-mono text-sm text-[#161616] focus:border-[#0f62fe] focus:bg-white focus:outline-none"
                placeholder="Caffeine SMILES — or H2, CC, caffeine"
                list="molecule-examples"
                autoFocus
              />
              <datalist id="molecule-examples">
                <option value="CN1C=NC2=C1C(=O)N(C(=O)N2C)C">Caffeine (SMILES)</option>
                <option value="CC">Ethane</option>
                <option value="H2">Hydrogen</option>
                <option value="caffeine">Caffeine (name)</option>
              </datalist>
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 text-sm font-medium text-[#525252] hover:text-[#161616]"
              >
                Cancel
              </button>
              <button
                onClick={submitMolecule}
                className="flex items-center gap-2 bg-[#0f62fe] px-4 py-2 text-sm font-medium text-white hover:bg-[#0353e9]"
              >
                Run simulation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
