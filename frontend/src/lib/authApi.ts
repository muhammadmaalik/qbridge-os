import { API_BASE } from "./pqcHandshake";

const TOKEN_KEY = "qbridge_auth_token_v1";
const USER_KEY = "qbridge_auth_user_v1";
const DEFAULT_TIMEOUT_MS = 30_000;

export type AuthUser = {
  id: string;
  email: string;
  username: string;
};

export type LoginStep = {
  status: string;
  challenge_id: string;
  message: string;
  expires_in_seconds: number;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

export type ApiHealth = {
  status?: string;
  auth_enabled?: boolean;
  smtp_configured?: boolean;
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
        `Request timed out after ${Math.round(timeoutMs / 1000)}s. ` +
          `The API at ${API_BASE} may be waking up (free tier) or unreachable.`
      );
    }
    throw new Error(
      `Cannot reach the API at ${API_BASE}. ` +
        `Start the backend locally or check your deployment.`
    );
  } finally {
    clearTimeout(timer);
  }
}

async function parseError(res: Response, path: string): Promise<string> {
  if (res.status === 404) {
    return (
      `Auth API not found (${path}). The backend at ${API_BASE} is running an old build ` +
      `without login routes. Redeploy the API on Render, then try again.`
    );
  }
  if (res.status === 429) {
    return "Too many login attempts. Wait one minute and try again.";
  }
  try {
    const j = (await res.json()) as { detail?: string | { msg?: string }[] };
    if (typeof j.detail === "string") {
      if (res.status === 503 && j.detail.includes("QBRIDGE_SMTP")) {
        return (
          "Email is not configured on the server. Add SMTP settings to the API .env " +
          "(see .env.example), then restart the backend."
        );
      }
      return j.detail;
    }
    if (Array.isArray(j.detail) && j.detail[0]?.msg) return j.detail[0].msg;
  } catch {
    /* ignore */
  }
  return res.statusText || "Request failed";
}

export async function checkApiHealth(): Promise<ApiHealth> {
  const res = await apiFetch("/health", { method: "GET" }, 12_000);
  if (!res.ok) throw new Error(`API health check failed (${res.status})`);
  return (await res.json()) as ApiHealth;
}

export async function registerAccount(
  email: string,
  password: string,
  username?: string
): Promise<AuthUser> {
  const res = await apiFetch("/api/v1/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, username: username || undefined }),
  });
  if (!res.ok) throw new Error(await parseError(res, "/api/v1/auth/register"));
  return (await res.json()) as AuthUser;
}

export async function loginStep1(email: string, password: string): Promise<LoginStep> {
  const res = await apiFetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await parseError(res, "/api/v1/auth/login"));
  return (await res.json()) as LoginStep;
}

export async function verifyOtp(challengeId: string, otp: string): Promise<TokenResponse> {
  const res = await apiFetch("/api/v1/auth/verify-otp", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ challenge_id: challengeId, otp }),
  });
  if (!res.ok) throw new Error(await parseError(res, "/api/v1/auth/verify-otp"));
  const data = (await res.json()) as TokenResponse;
  saveSession(data.access_token, data.user);
  return data;
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
