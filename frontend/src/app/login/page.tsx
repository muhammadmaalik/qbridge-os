"use client";

import Image from "next/image";
import Link from "next/link";
import { Inter } from "next/font/google";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import {
  checkApiHealth,
  clearSession,
  login,
  registerAccount,
} from "@/lib/authApi";
import { API_BASE } from "@/lib/pqcHandshake";

const sans = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

type Step = "credentials" | "register";

export default function LoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("credentials");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [apiOk, setApiOk] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    checkApiHealth()
      .then((h) => {
        if (cancelled) return;
        setApiOk(h.status === "ok");
      })
      .catch(() => {
        if (!cancelled) setApiOk(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const onLogin = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
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
    <div className={`${sans.className} min-h-screen flex flex-col bg-[#f4f4f4] text-[#161616]`}>
      <header className="flex h-12 items-center border-b border-[#e0e0e0] bg-[#161616] px-6">
        <span className="text-sm font-semibold tracking-wide text-white">
          Quantum Bridge OS
        </span>
        <span className="ml-3 text-xs text-[#c6c6c6]">Quantum computing platform</span>
      </header>

      <div className="flex flex-1 min-h-0">
        <aside className="relative hidden w-[52%] lg:block">
          <Image
            src="/login-hero.jpg"
            alt="Abstract science and technology background"
            fill
            priority
            className="object-cover"
            sizes="52vw"
          />
          <div className="absolute inset-0 bg-slate-900/50" />
          <div className="absolute bottom-0 left-0 right-0 p-10 text-white">
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-sky-300">
              Quantum Bridge OS
            </p>
            <h2 className="mt-2 max-w-md text-2xl font-semibold leading-snug">
              Secure access to quantum simulation tools
            </h2>
            <p className="mt-3 max-w-lg text-sm leading-relaxed text-[#e8e8e8]">
              Sign in to run chemistry VQE workloads, portfolio optimization, and
              post-quantum secured API sessions.
            </p>
          </div>
        </aside>

        <main className="flex flex-1 items-center justify-center px-6 py-10">
          <div className="w-full max-w-[400px]">
            <div className="mb-8">
              <h1 className="text-[1.75rem] font-semibold leading-tight text-[#161616]">
                {step === "register" ? "Create account" : "Log in"}
              </h1>
              <p className="mt-2 text-sm text-[#525252]">
                Use your email and password to continue.
              </p>
            </div>

            <div className="border border-[#e0e0e0] bg-white p-6">
              {apiOk === false && (
                <div className="mb-4">
                  <Alert kind="error">
                  Cannot reach the API at {API_BASE}. If you are on the live site, redeploy
                  the Render backend. Locally, run <code className="text-xs">.\start-local.ps1</code>.
                  </Alert>
                </div>
              )}

              <div className="mb-6 flex border-b border-[#e0e0e0]">
                <TabButton
                  active={step !== "register"}
                  onClick={() => {
                    setStep("credentials");
                    setError("");
                  }}
                >
                  Log in
                </TabButton>
                <TabButton
                  active={step === "register"}
                  onClick={() => {
                    setStep("register");
                    setError("");
                  }}
                >
                  Register
                </TabButton>
              </div>

              {step === "register" && (
                <form onSubmit={onRegister} className="space-y-5">
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
                <form onSubmit={onLogin} className="space-y-5">
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
                  <SubmitButton loading={loading}>Sign in</SubmitButton>
                </form>
              )}
            </div>

            <p className="mt-6 text-center text-xs text-[#6f6f6f]">
              <Link href="/" className="text-[#0f62fe] hover:underline">
                Continue without signing in
              </Link>
              {" · "}
              <button
                type="button"
                className="text-[#0f62fe] hover:underline"
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
      </div>
    </div>
  );
}

function TabButton({
  children,
  active,
  onClick,
}: {
  children: React.ReactNode;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex-1 border-b-2 pb-3 text-sm font-medium ${
        active
          ? "border-[#0f62fe] text-[#161616]"
          : "border-transparent text-[#6f6f6f] hover:text-[#161616]"
      }`}
    >
      {children}
    </button>
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
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
  placeholder?: string;
  hint?: string;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium uppercase tracking-wide text-[#525252]">
        {label}
      </span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        className="mt-2 w-full border-0 border-b border-[#8d8d8d] bg-[#f4f4f4] px-3 py-3 text-sm text-[#161616] placeholder:text-[#a8a8a8] focus:border-[#0f62fe] focus:bg-white focus:outline-none"
      />
      {hint && <span className="mt-2 block text-xs text-[#6f6f6f]">{hint}</span>}
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
      className="w-full bg-[#0f62fe] px-4 py-3 text-sm font-medium text-white hover:bg-[#0353e9] disabled:opacity-50"
    >
      {loading ? "Please wait..." : children}
    </button>
  );
}

function Alert({ children, kind }: { children: React.ReactNode; kind: "error" | "info" }) {
  const cls =
    kind === "error"
      ? "border-l-4 border-[#da1e28] bg-[#fff1f1] text-[#161616]"
      : "border-l-4 border-[#0f62fe] bg-[#edf5ff] text-[#161616]";
  return <div className={`px-4 py-3 text-sm ${cls}`}>{children}</div>;
}
