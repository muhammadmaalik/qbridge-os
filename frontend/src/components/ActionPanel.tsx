"use client";

import { useEffect, useRef, useState } from "react";
import {
  API_BASE,
  establishPqcSession,
  moleculeRequestCanonical,
  pqcSignMessage,
  type PqcSession,
} from "@/lib/pqcHandshake";

export default function ActionPanel() {
  const [loading, setLoading] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  /** Default: caffeine (complex organic); backend accepts SMILES via structure resolution. */
  const [formula, setFormula] = useState(
    "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"
  );
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

  const handleSimClick = () => {
    setIsModalOpen(true);
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
    <div className="border border-zinc-800 bg-zinc-900/40 p-6 rounded-xl shadow-sm relative">
      <h2 className="text-zinc-100 mb-5 font-semibold text-sm tracking-wide flex items-center gap-2">
        <svg className="w-4 h-4 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
        Operational Commands
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        <button
          onClick={requestEntropy}
          disabled={loading !== null}
          className="relative group border border-zinc-800 bg-zinc-950/50 p-6 rounded-xl overflow-hidden transition-all hover:border-indigo-500/50 hover:bg-zinc-900/80 disabled:opacity-50 text-left flex flex-col gap-3 shadow-sm"
        >
          <div className="bg-zinc-900 p-2 rounded-lg w-10 h-10 flex items-center justify-center border border-zinc-800 shadow-inner">
            <svg className="w-5 h-5 text-indigo-400 group-hover:text-indigo-300 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>
          </div>
          <div>
            <span className="text-zinc-200 font-semibold text-sm block mb-1">Entropy Generation</span>
            <span className="text-zinc-500 text-xs">Fetch ANU Vacuum Data</span>
          </div>
        </button>

        <button
          onClick={handleSimClick}
          disabled={loading !== null}
          className="relative group border border-zinc-800 bg-zinc-950/50 p-6 rounded-xl overflow-hidden transition-all hover:border-emerald-500/50 hover:bg-zinc-900/80 disabled:opacity-50 text-left flex flex-col gap-3 shadow-sm"
        >
          <div className="bg-zinc-900 p-2 rounded-lg w-10 h-10 flex items-center justify-center border border-zinc-800 shadow-inner">
            <svg className="w-5 h-5 text-emerald-400 group-hover:text-emerald-300 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5" /></svg>
          </div>
          <div>
            <span className="text-zinc-200 font-semibold text-sm block mb-1">VQE Simulation</span>
            <span className="text-zinc-500 text-xs">Molecular Binding Energy</span>
          </div>
        </button>

        <button
          onClick={computeOracle}
          disabled={loading !== null}
          className="relative group border border-zinc-800 bg-zinc-950/50 p-6 rounded-xl overflow-hidden transition-all hover:border-purple-500/50 hover:bg-zinc-900/80 disabled:opacity-50 text-left flex flex-col gap-3 shadow-sm"
        >
          <div className="bg-zinc-900 p-2 rounded-lg w-10 h-10 flex items-center justify-center border border-zinc-800 shadow-inner">
            <svg className="w-5 h-5 text-purple-400 group-hover:text-purple-300 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" /></svg>
          </div>
          <div>
            <span className="text-zinc-200 font-semibold text-sm block mb-1">Quantum Oracle</span>
            <span className="text-zinc-500 text-xs">Interferometric Shadows</span>
          </div>
        </button>
      </div>

      {/* Modal Overlay */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-zinc-950 border border-zinc-800 p-6 rounded-2xl shadow-2xl max-w-sm w-full animate-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center mb-5">
              <h3 className="text-lg font-semibold text-zinc-100">Configure Simulation</h3>
              <button onClick={() => setIsModalOpen(false)} className="text-zinc-500 hover:text-zinc-300">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            
            <div className="mb-6">
              <label className="block text-sm font-medium text-zinc-400 mb-2">
                Molecule (formula, name, or SMILES)
              </label>
              <input
                type="text"
                value={formula}
                onChange={(e) => setFormula(e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-700 text-zinc-100 px-4 py-2.5 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all font-mono text-sm"
                placeholder="Caffeine SMILES — or H2, CC (ethane), caffeine"
                list="molecule-examples"
                autoFocus
              />
              <datalist id="molecule-examples">
                <option value="CN1C=NC2=C1C(=O)N(C(=O)N2C)C">Caffeine (SMILES)</option>
                <option value="CC">Ethane</option>
                <option value="H2">Hydrogen</option>
                <option value="caffeine">Caffeine (name)</option>
              </datalist>
              <p className="text-xs text-zinc-500 mt-2">
                Default is a full <span className="text-zinc-400">caffeine</span> SMILES for
                a complex organic demo; simpler species like{" "}
                <span className="font-mono text-zinc-400">H2</span> or{" "}
                <span className="font-mono text-zinc-400">CC</span> (ethane) work too.
              </p>
            </div>
            
            <div className="flex gap-3 justify-end">
              <button 
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 text-sm font-medium text-zinc-300 hover:text-white bg-transparent hover:bg-zinc-800 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button 
                onClick={submitMolecule}
                className="px-4 py-2 text-sm font-medium text-zinc-950 bg-emerald-500 hover:bg-emerald-400 rounded-lg shadow-[0_0_15px_rgba(16,185,129,0.3)] transition-all flex items-center gap-2"
              >
                Run Simulation
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
