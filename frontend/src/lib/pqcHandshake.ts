/**
 * Mock CRYSTALS-Kyber encapsulation + HMAC signatures aligned with backend/security_utils.py
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "https://qbridge-os.onrender.com";

/** WebSocket URL for /ws on the same origin as API_BASE (ws or wss). */
export function webSocketUrlForApi(): string {
  const u = new URL(API_BASE.replace(/\/$/, ""));
  u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
  u.pathname = "";
  u.search = "";
  u.hash = "";
  return `${u.origin}/ws`;
}

const STORAGE_KEY = "qbridge_pqc_session_v1";

export type StoredPqcSession = {
  sessionId: string;
  sharedSecretHex: string;
  savedAt: number;
};

function loadStoredSession(): StoredPqcSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const o = JSON.parse(raw) as StoredPqcSession;
    if (
      o &&
      typeof o.sessionId === "string" &&
      typeof o.sharedSecretHex === "string" &&
      o.sessionId.length > 0
    ) {
      return o;
    }
  } catch {
    /* ignore */
  }
  return null;
}

function saveSession(sess: PqcSession): void {
  if (typeof window === "undefined") return;
  const payload: StoredPqcSession = {
    sessionId: sess.sessionId,
    sharedSecretHex: sess.sharedSecretHex,
    savedAt: Date.now(),
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

export function clearStoredPqcSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}

async function validateSessionOnServer(sessionId: string): Promise<boolean> {
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/security/session/${encodeURIComponent(sessionId)}/valid`
    );
    if (!res.ok) return false;
    const j = (await res.json()) as { valid?: boolean };
    return j.valid === true;
  } catch {
    return false;
  }
}

/** Canonical string for PQC MAC on /compute/molecule (must match backend). */
export function moleculeRequestCanonical(
  username: string,
  opts: {
    structure?: string | null;
    smiles?: string | null;
    hardwareProvider?: string;
    maxQubits?: number;
    scan?: string | null;
    noise?: boolean;
  }
): string {
  const hw = (opts.hardwareProvider ?? "ibm").trim().toLowerCase();
  const q = opts.maxQubits ?? 28;
  const scanPart = `|scan:${(opts.scan ?? "").trim()}`;
  const noisePart = opts.noise ? "|noise:1" : "|noise:0";
  const sm = (opts.smiles ?? "").trim();
  if (sm)
    return `${username}|smiles:${sm}|hw:${hw}|q:${q}${scanPart}${noisePart}`;
  const st = (opts.structure ?? "").trim();
  return `${username}|structure:${st}|hw:${hw}|q:${q}${scanPart}${noisePart}`;
}

function hexToBytes(hex: string): Uint8Array {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

function bytesToHex(b: Uint8Array): string {
  return Array.from(b)
    .map((x) => x.toString(16).padStart(2, "0"))
    .join("");
}

function concat(a: Uint8Array, b: Uint8Array): Uint8Array {
  const o = new Uint8Array(a.length + b.length);
  o.set(a, 0);
  o.set(b, a.length);
  return o;
}

async function sha256(data: Uint8Array): Promise<Uint8Array> {
  const buf = await crypto.subtle.digest("SHA-256", data as BufferSource);
  return new Uint8Array(buf);
}

function xor(a: Uint8Array, b: Uint8Array): Uint8Array {
  const o = new Uint8Array(32);
  for (let i = 0; i < 32; i++) o[i] = a[i] ^ b[i];
  return o;
}

const te = new TextEncoder();

export async function encapsulateKyber512(
  publicKeyHex: string
): Promise<{ ciphertext: string; sharedSecretHex: string }> {
  const pk = hexToBytes(publicKeyHex);
  const shared = new Uint8Array(32);
  crypto.getRandomValues(shared);
  const padIn = concat(pk, te.encode("KYBER_PAD"));
  const pad = await sha256(padIn);
  const ct = xor(shared, pad);
  return { ciphertext: bytesToHex(ct), sharedSecretHex: bytesToHex(shared) };
}

export async function pqcSignMessage(
  sharedSecretHex: string,
  message: string
): Promise<string> {
  const key = hexToBytes(sharedSecretHex);
  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    key as BufferSource,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", cryptoKey, te.encode(message));
  return bytesToHex(new Uint8Array(sig));
}

export type PqcSession = {
  sessionId: string;
  sharedSecretHex: string;
};

async function performHandshake(): Promise<PqcSession> {
  const pkRes = await fetch(`${API_BASE}/api/v1/security/pqc-public-key`);
  if (!pkRes.ok) throw new Error("PQC public key fetch failed");
  const { public_key: publicKey } = (await pkRes.json()) as { public_key: string };
  const { ciphertext, sharedSecretHex } = await encapsulateKyber512(publicKey);
  const hs = await fetch(`${API_BASE}/api/v1/security/handshake`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ciphertext }),
  });
  if (!hs.ok) throw new Error("PQC handshake failed");
  const { session_id: sessionId } = (await hs.json()) as { session_id: string };
  return { sessionId, sharedSecretHex };
}

export type EstablishPqcOptions = {
  /** Ignore localStorage and server validation; always perform a new handshake. */
  force?: boolean;
};

/** Serialize all PQC work so ActionPanel, QuantumTerminal, and page never race handshakes. */
let establishChain: Promise<unknown> = Promise.resolve();

async function establishPqcSessionImpl(
  opts?: EstablishPqcOptions
): Promise<PqcSession> {
  if (opts?.force) {
    clearStoredPqcSession();
  } else {
    const cached = loadStoredSession();
    if (cached) {
      const ok = await validateSessionOnServer(cached.sessionId);
      if (ok) {
        return {
          sessionId: cached.sessionId,
          sharedSecretHex: cached.sharedSecretHex,
        };
      }
      clearStoredPqcSession();
    }
  }

  const sess = await performHandshake();
  saveSession(sess);
  return sess;
}

/**
 * Return a PQC session, persisting (sessionId, sharedSecret) in localStorage.
 * After a server restart, a stored session is re-validated against the file-backed registry.
 *
 * Calls are queued: parallel invocations from the terminal, action panel, and page share one
 * logical flow so we never overwrite sessions mid-flight or flash the UI from competing handshakes.
 */
export function establishPqcSession(
  opts?: EstablishPqcOptions
): Promise<PqcSession> {
  const next = establishChain.then(() => establishPqcSessionImpl(opts));
  establishChain = next.then(
    () => undefined,
    () => undefined
  );
  return next;
}
