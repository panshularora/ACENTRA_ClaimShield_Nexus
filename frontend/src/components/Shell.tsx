import { Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuth } from "../auth/AuthProvider";

export function Shell() {
  const { user, loading, logout, allowed } = useAuth();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  useEffect(() => {
    if (!loading && !user) {
      void navigate({ to: "/login" });
    }
  }, [loading, user, pathname, navigate]);

  if (loading) {
    return (
      <div className="boot">
        <span className="brand-mark" aria-hidden="true" />
        <p>ClaimShield Nexus</p>
        <p className="muted">Checking session…</p>
      </div>
    );
  }

  if (!user) return null;

  const showQueue = allowed("queue:read");
  const showCases = allowed("case:read");
  const showWiki = allowed("wiki:read");
  const showAudit = allowed("audit:read");

  return (
    <div className="app">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <header className="mast">
        <Link to="/" className="mast-brand">
          <span className="brand-mark" aria-hidden="true" />
          <div>
            <strong>ClaimShield Nexus</strong>
            <p>SIU · post-adjudication · Acentra Health</p>
          </div>
        </Link>
        <nav className="mast-nav" aria-label="Primary">
          {showQueue && (
            <Link to="/manager/queue" className={pathname.startsWith("/manager/queue") ? "active" : ""}>
              Queue
            </Link>
          )}
          {showCases && (
            <Link
              to="/investigator/cases"
              className={pathname.startsWith("/investigator/") ? "active" : ""}
            >
              Cases
            </Link>
          )}
          {showWiki && (
            <Link to="/wiki/proposals" className={pathname.startsWith("/wiki/") ? "active" : ""}>
              Precedents
            </Link>
          )}
          {showAudit && (
            <Link to="/audit" className={pathname.startsWith("/audit") ? "active" : ""}>
              Audit
            </Link>
          )}
        </nav>
        <div className="mast-user">
          <span>
            {user.display_name}
            <em>{user.role}</em>
          </span>
          <button
            type="button"
            className="btn ghost"
            onClick={() => {
              void logout().then(() => navigate({ to: "/login" }));
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      <Outlet />
    </div>
  );
}
