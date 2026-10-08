import {
  createRootRoute,
  createRoute,
  createRouter,
  lazyRouteComponent,
} from "@tanstack/react-router";
import { Root, RouteError, RoutePending } from "./RouteShells";

const rootRoute = createRootRoute({ component: Root });

// Every page is code-split so the three.js landing scene, the chart library and
// the network graph only download on the routes that use them.
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
  component: lazyRouteComponent(
    () => import("../features/cases/InvestigatorCasesPage"),
    "InvestigatorCasesPage",
  ),
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
  component: lazyRouteComponent(
    () => import("../features/wiki/WikiProposalDetailPage"),
    "WikiProposalDetailPage",
  ),
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

export const router = createRouter({
  routeTree,
  defaultPendingComponent: RoutePending,
  defaultErrorComponent: RouteError,
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
