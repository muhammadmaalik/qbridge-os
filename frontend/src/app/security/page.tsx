"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  API_BASE,
  establishPqcSession,
  encapsulateKyber512,
  pqcSignMessage,
} from "@/lib/pqcHandshake";

export default function SecurityPage() {
  const [publicKey, setPublicKey] = useState<string>("");
  const [sessionId, setSessionId] = useState<string>("");
  const [plaintext, setPlaintext] = useState("Trade order: BUY 100 AAPL @ market");
  const [macHex, setMacHex] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/security/pqc-public-key`)
      .then((r) => r.json())
      .then((j: { public_key?: string }) => {
        if (j.public_key) setPublicKey(j.public_key);
      })
      .catch(() => setStatus("Could not reach API — start backend on :8000"));
  }, []);

  const runHandshake = async () => {
    setLoading(true);
    setStatus("");
    try {
      const sess = await establishPqcSession({ force: true });
      setSessionId(sess.sessionId);
      const sig = await pqcSignMessage(sess.sharedSecretHex, plaintext);
      setMacHex(sig);
      setStatus("PQC session established. Request MAC computed with shared secret.");
    } catch (e) {
      setStatus(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const demoEncapsulation = async () => {
    if (!publicKey) return;
    setLoading(true);
    try {
      const { ciphertext, sharedSecretHex } = await encapsulateKyber512(publicKey);
      setStatus(
        `Client encapsulation OK. Ciphertext length: ${ciphertext.length} hex chars. ` +
          `Shared secret prefix: ${sharedSecretHex.slice(0, 16)}…`
      );
    } catch (e) {
      setStatus(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-zinc-950 px-4 py-8 text-zinc-100">
      <div className="mx-auto max-w-3xl">
        <header className="mb-8">
          <h1 className="text-2xl font-semibold">Post-quantum security demo</h1>
          <p className="mt-2 text-sm text-zinc-400">
            Kyber-inspired key exchange + HMAC request signing (dev mock aligned with NIST
            PQC workflows).
          </p>
          <nav className="mt-4 flex gap-2 text-sm">
            <Link href="/" className="text-cyan-400 hover:underline">
              Home
            </Link>
            <Link href="/chemistry" className="text-cyan-400 hover:underline">
              Chemistry
            </Link>
            <Link href="/finance" className="text-cyan-400 hover:underline">
              Finance
            </Link>
            <a
              href={`${API_BASE}/docs`}
              className="text-cyan-400 hover:underline"
              target="_blank"
              rel="noreferrer"
            >
              OpenAPI /docs
            </a>
          </nav>
        </header>

        <section className="space-y-6 rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
          <div>
            <h2 className="text-sm font-semibold text-cyan-300">Before (plaintext)</h2>
            <textarea
              value={plaintext}
              onChange={(e) => setPlaintext(e.target.value)}
              rows={3}
              className="mt-2 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm"
            />
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={demoEncapsulation}
              disabled={loading || !publicKey}
              className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium hover:bg-violet-500 disabled:opacity-50"
            >
              1. Encapsulate (client → server)
            </button>
            <button
              type="button"
              onClick={runHandshake}
              disabled={loading}
              className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium hover:bg-cyan-500 disabled:opacity-50"
            >
              2. Full handshake + sign message
            </button>
          </div>

          <div>
            <h2 className="text-sm font-semibold text-emerald-300">After (authenticated)</h2>
            <dl className="mt-2 space-y-2 text-sm">
              <div>
                <dt className="text-zinc-500">Session ID</dt>
                <dd className="break-all font-mono text-xs">{sessionId || "—"}</dd>
              </div>
              <div>
                <dt className="text-zinc-500">HMAC-SHA256 (hex)</dt>
                <dd className="break-all font-mono text-xs">{macHex || "—"}</dd>
              </div>
              <div>
                <dt className="text-zinc-500">Server public key (prefix)</dt>
                <dd className="break-all font-mono text-xs">
                  {publicKey ? `${publicKey.slice(0, 48)}…` : "—"}
                </dd>
              </div>
            </dl>
          </div>

          {status && (
            <p className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-300">
              {status}
            </p>
          )}

          <p className="text-xs text-zinc-500">
            Local dev: set <code className="text-zinc-300">QBRIDGE_SKIP_PQC_VERIFY=1</code> on
            the API to call compute routes without headers. Production must require{" "}
            <code className="text-zinc-300">X-QBridge-Session</code> and{" "}
            <code className="text-zinc-300">X-QBridge-Signature</code>.
          </p>
        </section>
      </div>
    </main>
  );
}
