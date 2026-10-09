import { can } from "../api/client";
import type { SessionUser } from "../api/types";

export type AppHome = "/manager/queue" | "/investigator/cases" | "/wiki/proposals" | "/audit";

/** Where a signed-in user lands after login, or when they hit a page their role cannot use. */
export function homeFor(user: SessionUser): AppHome {
  switch (user.role) {
    case "investigator":
      return "/investigator/cases";
    case "manager":
    case "admin":
      return "/manager/queue";
    case "analyst":
      return "/wiki/proposals";
    case "auditor":
      return "/audit";
    default:
      if (can(user, "queue:configure")) return "/manager/queue";
      if (can(user, "case:read")) return "/investigator/cases";
      if (can(user, "wiki:read")) return "/wiki/proposals";
      if (can(user, "audit:read")) return "/audit";
      return "/investigator/cases";
  }
}

/** Manager desk is capacity, ingest and recompute — not the investigator worklist. */
export function canOpenManagerDesk(user: SessionUser | null): boolean {
  return can(user, "queue:configure");
}

export function canVisit(user: SessionUser | null, pathname: string): boolean {
  if (!user) return false;
  if (pathname === "/" || pathname === "/login") return true;
  if (pathname.startsWith("/manager/queue")) return canOpenManagerDesk(user);
  if (pathname.startsWith("/investigator")) return can(user, "case:read");
  if (pathname.startsWith("/wiki")) return can(user, "wiki:read");
  if (pathname.startsWith("/audit")) return can(user, "audit:read");
  return false;
}
