import "@fontsource-variable/inter";
import "@fontsource/roboto/700.css";
import "@fontsource/roboto-mono/400.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { router } from "./app/router";
import { AuthProvider } from "./auth/AuthProvider";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/public.css";
import "./styles/components.css";
import "./styles/shell.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false, retry: 1 },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);
