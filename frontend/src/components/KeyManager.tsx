"use client";

import { useState, useEffect } from "react";

export default function KeyManager() {
  const [apiKey, setApiKey] = useState("");
  const [username, setUsername] = useState("testuser");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch("http://localhost:8000/api/v1/auth/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username,
          service_provider: "IBM",
          api_key: apiKey,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setToast({ message: "IBM key secured successfully.", type: "success" });
        setApiKey("");
      } else {
        setToast({ message: data.detail || "Invalid key or authentication failed.", type: "error" });
      }
    } catch (err) {
      setToast({ message: "Network failure. Could not connect to API.", type: "error" });
    }
  };

  return (
    <div className="border border-zinc-800 bg-zinc-900/40 p-6 rounded-xl shadow-sm relative">
      {/* Toast Notification */}
      {toast && (
        <div className={`absolute -top-12 left-1/2 -translate-x-1/2 px-4 py-2 rounded-lg shadow-lg border text-sm font-medium z-50 flex items-center gap-2 transition-all animate-in fade-in slide-in-from-top-2 ${toast.type === "success" ? "bg-emerald-950/80 border-emerald-800 text-emerald-400" : "bg-red-950/80 border-red-800 text-red-400"}`}>
          {toast.type === "success" ? (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          )}
          {toast.message}
        </div>
      )}

      <h2 className="text-zinc-100 mb-5 font-semibold text-sm tracking-wide flex items-center gap-2">
        <svg className="w-4 h-4 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" /></svg>
        Identity & Security
      </h2>
      <form onSubmit={handleSave} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs text-zinc-400 font-medium">Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="bg-zinc-950/50 border border-zinc-800 text-zinc-200 px-3 py-2 text-sm rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
            placeholder="System User"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-xs text-zinc-400 font-medium">IBM Quantum Key</label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="bg-zinc-950/50 border border-zinc-800 text-zinc-200 px-3 py-2 text-sm rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
            placeholder="Enter quantum token..."
            required
          />
        </div>
        <button
          type="submit"
          className="bg-zinc-100 hover:bg-white text-zinc-900 font-medium py-2 px-4 rounded-lg text-sm transition-all duration-200 mt-2 flex items-center justify-center gap-2 shadow-sm"
        >
          Save Credentials
        </button>
      </form>
    </div>
  );
}
