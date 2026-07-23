import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import fs from "fs";
import { componentTagger } from "lovable-tagger";

function getBackendTarget(): string {
  const portFile = path.resolve(process.cwd(), ".backend-port");
  try {
    if (fs.existsSync(portFile)) {
      const port = fs.readFileSync(portFile, "utf-8").trim();
      if (port) return `http://localhost:${port}`;
    }
  } catch {
    // ignore
  }
  return process.env.VITE_BACKEND_URL || process.env.VITE_API_URL || "http://localhost:5001";
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  test: { environment: "jsdom", setupFiles: ["./src/tests/setup.ts"], include: ["src/**/*.test.{ts,tsx}"] },
  server: {
    host: "0.0.0.0",
    port: 8080,
    allowedHosts: ["server.logisticmarket.ir"],
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
