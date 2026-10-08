import { Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuth } from "../auth/AuthProvider";
import { AppLogo } from "./ui/AppLogo";

interface NavItem {
  to: "/manager/queue" | "/investigator/cases" | "/wiki/proposals" | "/audit";
  label: string;
  /** Path prefix that marks this item as the current section. */
  section: string;
  permission: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/manager/queue", label: "Queue", section: "/manager/queue", permission: "queue:read" },
  { to: "/investigator/cases", label: "Cases", section: "/investigator/", permission: "case:read" },
  { to: "/wiki/proposals", label: "Precedents", section: "/wiki/", permission: "wiki:read" },
  { to: "/audit", label: "Audit", section: "/audit", permission: "audit:read" },
];

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
      <div className="boot" role="status">
        <AppLogo />
        <p>ClaimShield Nexus</p>
        <p>Checking session…</p>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="app">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <header className="mast">
        <Link to="/" className="mast-brand">
          <AppLogo />
          <span>
            <strong>ClaimShield Nexus</strong>
            <small>SIU case prioritisation · prototype</small>
          </span>
        </Link>
        <nav className="mast-nav" aria-label="Primary">
          {NAV_ITEMS.filter((item) => allowed(item.permission)).map((item) => (
            <Link
              key={item.to}
              to={item.to}
              aria-current={pathname.startsWith(item.section) ? "page" : undefined}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="mast-user">
          <span className="mast-user-name">
            {user.display_name}
            <span>{user.role}</span>
          </span>
          <button
            type="button"
            className="btn small ghost"
            onClick={() => {
              void logout().then(() => navigate({ to: "/login" }));
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      <div className="app-main">
        <Outlet />
      </div>
    </div>
  );
}
