import { createRootRoute, createRoute, createRouter, redirect } from "@tanstack/react-router";
import { Shell } from "../components/Shell";
import { InvestigatorCasesPage } from "../features/cases/InvestigatorCasesPage";
import { LoginPage } from "../features/auth/LoginPage";
import { ManagerQueuePage } from "../features/queue/ManagerQueuePage";
import { WorkspacePage } from "../features/workspace/WorkspacePage";

const rootRoute = createRootRoute({
  component: Shell,
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({ to: "/login" });
  },
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

const routeTree = rootRoute.addChildren([
  indexRoute,
  loginRoute,
  queueRoute,
  casesRoute,
  workspaceRoute,
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
