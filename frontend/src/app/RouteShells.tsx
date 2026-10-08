import { Outlet, useRouterState, type ErrorComponentProps } from "@tanstack/react-router";
import { Shell } from "../components/Shell";
import { ErrorState, LoadingState } from "../components/ui/States";

/** Public pages (landing, login) render bare; every other route gets the app shell. */
export function Root() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  if (pathname === "/" || pathname === "/login") {
    return <Outlet />;
  }
  return <Shell />;
}

export function RoutePending() {
  return (
    <main id="main" className="page">
      <LoadingState label="Loading page…" />
    </main>
  );
}

export function RouteError({ error }: ErrorComponentProps) {
  return (
    <main id="main" className="page">
      <ErrorState title="This page failed to load" error={error} />
    </main>
  );
}

