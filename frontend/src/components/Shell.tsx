import { Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuth } from "../auth/AuthProvider";

export function Shell() {
  const { user, loading, logout, allowed } = useAuth();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  if (loading) {
    return (
      <div className="boot">
        <p>ClaimShield Nexus</p>
        <p className="muted">Checking session…</p>
      </div>
    );
  }

  useEffect(() => {
    if (!loading && !user && pathname !== "/login") {
      void navigate({ to: "/login" });
    }
  }, [loading, user, pathname, navigate]);

  if (!user) {
    if (pathname !== "/login") return null;
    return <Outlet />;
  }

  const showQueue = allowed("queue:read");
  const showCases = allowed("case:read");

  return (
    <div className="app">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <header className="mast">
        <div className="mast-brand">
          <span className="mark">CS</span>
          <div>
            <strong>ClaimShield Nexus</strong>
            <p>SIU case ranking · post-adjudication</p>
          </div>
        </div>
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
              My cases
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
