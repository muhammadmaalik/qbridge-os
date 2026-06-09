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
import { API_BASE } from "@/lib/pqcHandshake";

type Step = "credentials" | "otp" | "register";

const IBM_QUANTUM_BG =
  "https://upload.wikimedia.org/wikipedia/commons/8/8e/IBM_Q_system.jpg";

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
      if (res.dev_otp) setOtp(res.dev_otp);
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
    <main
      className="min-h-screen bg-slate-900 bg-cover bg-center bg-no-repeat"
      style={{ backgroundImage: `url('${IBM_QUANTUM_BG}')` }}
    >
      <div className="min-h-screen bg-slate-900/70 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="mb-6 text-center text-white">
            <h1 className="text-2xl font-semibold tracking-tight">Quantum Bridge OS</h1>
            <p className="mt-1 text-sm text-slate-200">Sign in to access the quantum platform</p>
          </div>

          <div className="rounded border border-slate-200 bg-white p-6 shadow-lg">
            <div className="mb-5 flex border-b border-slate-200">
              <button
                type="button"
                onClick={() => {
                  setStep("credentials");
                  setError("");
                }}
                className={`flex-1 border-b-2 pb-2 text-sm font-medium ${
                  step !== "register"
                    ? "border-blue-600 text-blue-700"
                    : "border-transparent text-slate-500"
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
                className={`flex-1 border-b-2 pb-2 text-sm font-medium ${
                  step === "register"
                    ? "border-blue-600 text-blue-700"
                    : "border-transparent text-slate-500"
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
                  placeholder="Defaults to email prefix"
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
                <p className="text-center text-xs text-slate-500">
                  After password verification, enter the 6-digit security code.
                </p>
              </form>
            )}

            {step === "otp" && (
              <form onSubmit={onVerify} className="space-y-4">
                <p className="text-sm text-slate-600">{message}</p>
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
                <SubmitButton loading={loading}>Verify and sign in</SubmitButton>
                <button
                  type="button"
                  className="w-full text-sm text-slate-500 hover:text-slate-800"
                  onClick={() => {
                    setStep("credentials");
                    setOtp("");
                    setError("");
                  }}
                >
                  Back to email and password
                </button>
              </form>
            )}
          </div>

          <p className="mt-4 text-center text-xs text-slate-300">
            API: {API_BASE}
            {" · "}
            <Link href="/" className="underline hover:text-white">
              Dashboard
            </Link>
            {" · "}
            <button
              type="button"
              className="underline hover:text-white"
              onClick={() => {
                clearSession();
                router.push("/login");
              }}
            >
              Clear session
            </button>
          </p>
        </div>
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
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        maxLength={maxLength}
        inputMode={inputMode}
        className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
      />
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
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
      className="w-full rounded bg-blue-700 py-2.5 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50"
    >
      {loading ? "Please wait…" : children}
    </button>
  );
}

function Alert({ children, kind }: { children: React.ReactNode; kind: "error" | "info" }) {
  const cls =
    kind === "error"
      ? "border-red-200 bg-red-50 text-red-800"
      : "border-blue-200 bg-blue-50 text-blue-900";
  return (
    <div className={`rounded border px-3 py-2 text-sm ${cls}`}>{children}</div>
  );
}
