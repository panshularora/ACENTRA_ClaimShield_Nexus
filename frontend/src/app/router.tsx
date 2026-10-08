import {
  Outlet,
  createRootRoute,
  createRoute,
  createRouter,
  lazyRouteComponent,
  useRouterState,
} from "@tanstack/react-router";
import { Shell } from "../components/Shell";

function Root() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  if (pathname === "/" || pathname === "/login") {
    return <Outlet />;
  }
  return <Shell />;
}

// Every page is its own chunk. three.js and React Three Fiber are only imported by the public
// landing and login pages, so they no longer ship in the main bundle.
const rootRoute = createRootRoute({
  component: Root,
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: lazyRouteComponent(() => import("../features/landing/LandingPage"), "LandingPage"),
});

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: lazyRouteComponent(() => import("../features/auth/LoginPage"), "LoginPage"),
});

const queueRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/manager/queue",
  component: lazyRouteComponent(() => import("../features/queue/ManagerQueuePage"), "ManagerQueuePage"),
});

const casesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/investigator/cases",
  component: lazyRouteComponent(() => import("../features/cases/InvestigatorCasesPage"), "InvestigatorCasesPage"),
});

const workspaceRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/investigator/workspace/$caseId",
  component: lazyRouteComponent(() => import("../features/workspace/WorkspacePage"), "WorkspacePage"),
});

const proposalsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/wiki/proposals",
  component: lazyRouteComponent(() => import("../features/wiki/WikiProposalsPage"), "WikiProposalsPage"),
});

const proposalDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/wiki/proposals/$proposalId",
  component: lazyRouteComponent(() => import("../features/wiki/WikiProposalDetailPage"), "WikiProposalDetailPage"),
});

const auditRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/audit",
  component: lazyRouteComponent(() => import("../features/audit/AuditPage"), "AuditPage"),
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  loginRoute,
  queueRoute,
  casesRoute,
  workspaceRoute,
  proposalsRoute,
  proposalDetailRoute,
  auditRoute,
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
