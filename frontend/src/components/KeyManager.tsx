"use client";

import { useState, useEffect } from "react";
import { API_BASE } from "@/lib/pqcHandshake";

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
      const res = await fetch(`${API_BASE}/api/v1/auth/keys`, {
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
    <div className="relative border border-[#e0e0e0] bg-white p-6">
      {toast && (
        <div
          className={`absolute -top-12 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 border px-4 py-2 text-sm font-medium ${
            toast.type === "success"
              ? "border-[#a7f0ba] bg-[#defbe6] text-[#198038]"
              : "border-[#ffb3b8] bg-[#fff1f1] text-[#da1e28]"
          }`}
        >
          {toast.type === "success" ? (
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
          ) : (
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          )}
          {toast.message}
        </div>
      )}

      <h2 className="mb-5 flex items-center gap-2 text-sm font-semibold tracking-wide text-[#161616]">
        <svg className="h-4 w-4 text-[#6f6f6f]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" /></svg>
        Identity &amp; security
      </h2>
      <form onSubmit={handleSave} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium uppercase tracking-wide text-[#525252]">Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="border-0 border-b border-[#8d8d8d] bg-[#f4f4f4] px-3 py-3 text-sm text-[#161616] focus:border-[#0f62fe] focus:bg-white focus:outline-none"
            placeholder="System user"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium uppercase tracking-wide text-[#525252]">IBM Quantum key</label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="border-0 border-b border-[#8d8d8d] bg-[#f4f4f4] px-3 py-3 text-sm text-[#161616] focus:border-[#0f62fe] focus:bg-white focus:outline-none"
            placeholder="Enter quantum token..."
            required
          />
        </div>
        <button
          type="submit"
          className="mt-2 flex items-center justify-center gap-2 bg-[#0f62fe] px-4 py-3 text-sm font-medium text-white transition hover:bg-[#0353e9]"
        >
          Save credentials
        </button>
      </form>
    </div>
  );
}
