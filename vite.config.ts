import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";
import { getBackendTarget } from "./vite-backend-target";
import packageMetadata from "./package.json";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  define: {
    "import.meta.env.VITE_APP_VERSION": JSON.stringify(packageMetadata.version),
  },
  test: { environment: "jsdom", setupFiles: ["./src/tests/setup.ts"], include: ["src/**/*.test.{ts,tsx}"] },
  server: {
    host: "0.0.0.0",
    port: 8080,
    allowedHosts: ["server.logisticmarket.ir"],
    watch: {
      // A Windows directory rename is denied while Vite watches a release staging tree.
      // Release staging is immutable build output and must never trigger HMR.
      ignored: ["**/.release-v*-staging-*"],
    },
    proxy: {
      "/api": {
        target: getBackendTarget(),
        changeOrigin: true,
      },
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
