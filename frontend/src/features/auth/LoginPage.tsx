import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";
import type { SessionUser } from "../../api/types";
import { StoryScene } from "../../three/StoryScene";
import { usePrefersReducedMotion } from "../../three/useScrollProgress";
import "./login.css";

function homeFor(user: SessionUser): string {
  if (user.role === "auditor") return "/audit";
  if (user.permissions.includes("queue:read") || user.permissions.includes("admin:*")) {
    if (user.role === "investigator") return "/investigator/cases";
    return "/manager/queue";
  }
  if (user.permissions.includes("case:read")) return "/investigator/cases";
  if (user.permissions.includes("wiki:read") || user.permissions.includes("wiki:approve")) {
    return "/wiki/proposals";
  }
  if (user.permissions.includes("audit:read")) return "/audit";
  return "/manager/queue";
}

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const reduced = usePrefersReducedMotion();
  const [email, setEmail] = useState("manager@demo.claimshield");
  const [password, setPassword] = useState("demo-manager");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const meta = useQuery({ queryKey: ["meta"], queryFn: api.meta });

  useEffect(() => {
    if (user) void navigate({ to: homeFor(user) });
  }, [user, navigate]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const session = await login(email, password);
      await navigate({ to: homeFor(session) });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-screen">
      <div className="login-stage" aria-hidden="true">
        <StoryScene progress={0.46} reduced={reduced} />
      </div>
      <header className="login-top">
        <Link to="/" className="brand-lockup">
          <span className="brand-mark" aria-hidden="true" />
          <div>
            <strong>ClaimShield Nexus</strong>
            <em>Acentra Health code-a-thon prototype</em>
          </div>
        </Link>
      </header>
      <main className="login-panel" id="main">
        <p className="kicker">Recommend only · humans decide</p>
        <h1>Enter the special investigations unit.</h1>
        <p className="lede">
          Live FastAPI session. Cookie JWT, role-based routes. The model does not print fraud on a
          provider.
        </p>
        <form onSubmit={(e) => void onSubmit(e)} className="login-form">
          <label>
            Email
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {error && (
            <p className="error-text" role="alert">
              {error}
            </p>
          )}
          <button type="submit" className="btn solid" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        {meta.data?.demo_mode && meta.data.demo_users && (
          <div className="demo-switch">
            <p className="kicker">Demo roles for the walkthrough</p>
            <div className="demo-grid">
              {meta.data.demo_users.map((demo) => (
                <button
                  key={demo.email}
                  type="button"
                  className={`demo-chip ${email === demo.email ? "is-on" : ""}`}
                  onClick={() => {
                    setEmail(demo.email);
                    setPassword(demo.password);
                  }}
                >
                  <strong>{demo.role}</strong>
                  <span>{demo.email}</span>
                </button>
              ))}
            </div>
          </div>
        )}
        {meta.isError && (
          <p className="error-text" role="status">
            API is not reachable. Start the backend on :8000, then sign in.
          </p>
        )}
      </main>
    </div>
  );
}
