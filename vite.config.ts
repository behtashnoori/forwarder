import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import os from "os";
import { componentTagger } from "lovable-tagger";

function getNetworkUrl(port: number): string {
  const envUrl = process.env.VITE_PUBLIC_APP_URL || process.env.PUBLIC_APP_URL;
  if (envUrl) return envUrl.replace(/\/$/, "");
  const nets = os.networkInterfaces();
  for (const name of Object.keys(nets)) {
    const iface = nets[name];
    if (!iface) continue;
    for (const a of iface) {
      if (a.family === "IPv4" && !a.internal) return `http://${a.address}:${port}`;
    }
  }
  return "";
}

// https://vitejs.dev/config/
export default defineConfig((env) => {
  const mode = env?.mode ?? "development";
  return {
    server: {
      host: "0.0.0.0", // listen on all interfaces so http://130.185.77.25:8080 works
      port: 8080,
    },
    plugins: [
    react(),
    mode === "development" &&
      (() => {
        return {
          name: "log-urls",
          configureServer(server) {
            return () => {
              const port = server?.config?.server?.port ?? 8080;
              const local = `http://localhost:${port}/`;
              const network = getNetworkUrl(port);
              console.log("\n  Local:   " + local);
              console.log("  Network: " + (network ? network + "/" : "—"));
              console.log("  ➜  press h + enter to show help\n");
            };
          },
        };
      })(),
    mode === "development" && componentTagger(),
    ].filter(Boolean),
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});
