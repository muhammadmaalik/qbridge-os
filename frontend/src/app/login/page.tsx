"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import {
  clearSession,
  loginStep1,
  registerAccount,
  verifyOtp,
} from "@/lib/authApi";

type Step = "credentials" | "otp" | "register";

export default function LoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("credentials");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [otp, setOtp] = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onLogin = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await loginStep1(email, password);
      setChallengeId(res.challenge_id);
      setMessage(res.message);
      setStep("otp");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const onVerify = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await verifyOtp(challengeId, otp);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const onRegister = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await registerAccount(email, password, username || undefined);
      setMessage("Account created. Sign in with your email and password.");
      setStep("credentials");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-200 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-500" />
            <span className="text-xl font-semibold text-zinc-100">Quantum Bridge OS</span>
          </div>
          <p className="text-sm text-zinc-500">Secure access for students and operators</p>
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 shadow-xl">
          <div className="flex gap-2 mb-6">
            <button
              type="button"
              onClick={() => {
                setStep("credentials");
                setError("");
              }}
              className={`flex-1 py-2 text-sm rounded-lg border ${
                step !== "register"
                  ? "border-indigo-500/50 bg-indigo-500/10 text-indigo-300"
                  : "border-zinc-800 text-zinc-500"
              }`}
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => {
                setStep("register");
                setError("");
              }}
              className={`flex-1 py-2 text-sm rounded-lg border ${
                step === "register"
                  ? "border-indigo-500/50 bg-indigo-500/10 text-indigo-300"
                  : "border-zinc-800 text-zinc-500"
              }`}
            >
              Register
            </button>
          </div>

          {step === "register" && (
            <form onSubmit={onRegister} className="space-y-4">
              <Field label="Email" type="email" value={email} onChange={setEmail} required />
              <Field
                label="Username (optional)"
                value={username}
                onChange={setUsername}
                placeholder="defaults to email prefix"
              />
              <Field
                label="Password"
                type="password"
                value={password}
                onChange={setPassword}
                required
                hint="Minimum 8 characters"
              />
              {error && <Alert kind="error">{error}</Alert>}
              <SubmitButton loading={loading}>Create account</SubmitButton>
            </form>
          )}

          {step === "credentials" && (
            <form onSubmit={onLogin} className="space-y-4">
              <Field label="Email" type="email" value={email} onChange={setEmail} required />
              <Field
                label="Password"
                type="password"
                value={password}
                onChange={setPassword}
                required
              />
              {message && <Alert kind="info">{message}</Alert>}
              {error && <Alert kind="error">{error}</Alert>}
              <SubmitButton loading={loading}>Continue</SubmitButton>
              <p className="text-xs text-zinc-500 text-center">
                After password verification, a 6-digit code is sent to your email.
              </p>
            </form>
          )}

          {step === "otp" && (
            <form onSubmit={onVerify} className="space-y-4">
              <p className="text-sm text-zinc-400">{message}</p>
              <Field
                label="Security code"
                value={otp}
                onChange={setOtp}
                placeholder="000000"
                maxLength={6}
                inputMode="numeric"
                required
              />
              {error && <Alert kind="error">{error}</Alert>}
              <SubmitButton loading={loading}>Verify &amp; sign in</SubmitButton>
              <button
                type="button"
                className="w-full text-sm text-zinc-500 hover:text-zinc-300"
                onClick={() => {
                  setStep("credentials");
                  setOtp("");
                  setError("");
                }}
              >
                ← Back to email &amp; password
              </button>
            </form>
          )}
        </div>

        <p className="mt-6 text-center text-xs text-zinc-600">
          <Link href="/" className="hover:text-zinc-400">
            Skip to dashboard
          </Link>
          {" · "}
          <button
            type="button"
            className="hover:text-zinc-400"
            onClick={() => {
              clearSession();
              router.push("/login");
            }}
          >
            Clear session
          </button>
        </p>
      </div>
    </main>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  required,
  placeholder,
  hint,
  maxLength,
  inputMode,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
  placeholder?: string;
  hint?: string;
  maxLength?: number;
  inputMode?: React.HTMLAttributes<HTMLInputElement>["inputMode"];
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        maxLength={maxLength}
        inputMode={inputMode}
        className="mt-1.5 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
      />
      {hint && <span className="mt-1 block text-xs text-zinc-600">{hint}</span>}
    </label>
  );
}

function SubmitButton({
  children,
  loading,
}: {
  children: React.ReactNode;
  loading: boolean;
}) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors"
    >
      {loading ? "Please wait…" : children}
    </button>
  );
}

function Alert({ children, kind }: { children: React.ReactNode; kind: "error" | "info" }) {
  const cls =
    kind === "error"
      ? "border-red-900/50 bg-red-950/30 text-red-300"
      : "border-indigo-900/50 bg-indigo-950/30 text-indigo-300";
  return (
    <div className={`rounded-lg border px-3 py-2 text-sm ${cls}`}>{children}</div>
  );
}
