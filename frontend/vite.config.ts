import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

const SPA_SHELL_ROUTES = [
  "login",
  "manager/queue",
  "investigator/cases",
  "investigator/workspace",
  "wiki/proposals",
  "audit",
];

function spaFallbackPages(): Plugin {
  return {
    name: "spa-fallback-pages",
    closeBundle() {
      const dist = resolve(fileURLToPath(new URL(".", import.meta.url)), "dist");
      const index = resolve(dist, "index.html");
      const html = readFileSync(index, "utf8");
      for (const route of SPA_SHELL_ROUTES) {
        const dest = resolve(dist, route, "index.html");
        mkdirSync(dirname(dest), { recursive: true });
        writeFileSync(dest, html);
      }
      copyFileSync(index, resolve(dist, "404.html"));
    },
  };
}

export default defineConfig({
  plugins: [react(), spaFallbackPages()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/healthz": { target: "http://127.0.0.1:8000" },
      "/readyz": { target: "http://127.0.0.1:8000" },
    },
  },
});
