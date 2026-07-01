import { API_BASE } from "./pqcHandshake";

const TOKEN_KEY = "qbridge_auth_token_v1";
const USER_KEY = "qbridge_auth_user_v1";
const IS_RENDER = API_BASE.includes("onrender.com");
const DEFAULT_TIMEOUT_MS = IS_RENDER ? 90_000 : 30_000;
const WAKE_MAX_MS = IS_RENDER ? 90_000 : 20_000;

export type AuthUser = {
  id: string;
  email: string;
  username: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

export type ApiHealth = {
  status?: string;
  auth_enabled?: boolean;
  user_store?: string;
};

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

export function saveSession(token: string, user: AuthUser): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function authHeaders(): Record<string, string> {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Wait for Render cold start — retries /health until the API responds or time runs out. */
export async function wakeApi(maxWaitMs = WAKE_MAX_MS): Promise<boolean> {
  const deadline = Date.now() + maxWaitMs;
  let attempt = 0;
  while (Date.now() < deadline) {
    attempt += 1;
    try {
      const res = await apiFetch("/health", { method: "GET" }, 18_000);
      if (res.ok) return true;
    } catch {
      /* server still waking */
    }
    if (Date.now() >= deadline) break;
    await sleep(Math.min(2000 + attempt * 1500, 8000));
  }
  return false;
}

async function apiFetch(
  path: string,
  init?: RequestInit,
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error(
        IS_RENDER
          ? "The server is still waking up (Render free tier). Wait a moment and try again."
          : `Request timed out after ${Math.round(timeoutMs / 1000)}s.`
      );
    }
    throw new Error(
      IS_RENDER
        ? "Cannot reach the API yet. The server may be starting — try again in 30 seconds."
        : `Cannot reach the API at ${API_BASE}. Start the backend locally or check your deployment.`
    );
  } finally {
    clearTimeout(timer);
  }
}

async function parseError(res: Response, path: string): Promise<string> {
  if (res.status === 404) {
    return (
      `Auth API not found (${path}). Redeploy the API on Render, then try again.`
    );
  }
  if (res.status === 429) {
    return "Too many attempts. Wait one minute and try again.";
  }
  try {
    const j = (await res.json()) as { detail?: string | { msg?: string }[] };
    if (typeof j.detail === "string") return j.detail;
    if (Array.isArray(j.detail) && j.detail[0]?.msg) return j.detail[0].msg;
  } catch {
    /* ignore */
  }
  return res.statusText || "Request failed";
}

export async function checkApiHealth(): Promise<ApiHealth> {
  const ok = await wakeApi();
  if (!ok) throw new Error("API unavailable");
  const res = await apiFetch("/health", { method: "GET" }, 18_000);
  if (!res.ok) throw new Error(`API health check failed (${res.status})`);
  return (await res.json()) as ApiHealth;
}

export async function registerAccount(
  email: string,
  password: string
): Promise<AuthUser> {
  await wakeApi();
  const res = await apiFetch("/api/v1/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await parseError(res, "/api/v1/auth/register"));
  return (await res.json()) as AuthUser;
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  await wakeApi();
  const res = await apiFetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await parseError(res, "/api/v1/auth/login"));
  const data = (await res.json()) as TokenResponse;
  saveSession(data.access_token, data.user);
  return data;
}

/** Create account and sign in immediately (email + password only). */
export async function registerAndLogin(
  email: string,
  password: string
): Promise<TokenResponse> {
  await registerAccount(email, password);
  return login(email, password);
}

export async function fetchMe(): Promise<AuthUser | null> {
  const token = getStoredToken();
  if (!token) return null;
  const res = await apiFetch("/api/v1/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    clearSession();
    return null;
  }
  const user = (await res.json()) as AuthUser;
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  return user;
}
