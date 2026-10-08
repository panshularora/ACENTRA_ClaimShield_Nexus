import { Outlet, createRootRoute, createRoute, createRouter, useRouterState } from "@tanstack/react-router";
import { Shell } from "../components/Shell";
import { InvestigatorCasesPage } from "../features/cases/InvestigatorCasesPage";
import { LoginPage } from "../features/auth/LoginPage";
import { LandingPage } from "../features/landing/LandingPage";
import { ManagerQueuePage } from "../features/queue/ManagerQueuePage";
import { WorkspacePage } from "../features/workspace/WorkspacePage";
import { AuditPage } from "../features/audit/AuditPage";
import { WikiProposalDetailPage } from "../features/wiki/WikiProposalDetailPage";
import { WikiProposalsPage } from "../features/wiki/WikiProposalsPage";

function Root() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  if (pathname === "/" || pathname === "/login") {
    return <Outlet />;
  }
  return <Shell />;
}

const rootRoute = createRootRoute({
  component: Root,
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: LandingPage,
});

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: LoginPage,
});

const queueRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/manager/queue",
  component: ManagerQueuePage,
});

const casesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/investigator/cases",
  component: InvestigatorCasesPage,
});

const workspaceRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/investigator/workspace/$caseId",
  component: WorkspacePage,
});

const proposalsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/wiki/proposals",
  component: WikiProposalsPage,
});

const proposalDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/wiki/proposals/$proposalId",
  component: WikiProposalDetailPage,
});

const auditRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/audit",
  component: AuditPage,
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
