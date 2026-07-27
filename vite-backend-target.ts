import fs from "fs";
import path from "path";

const LEGACY_BACKEND_TARGET = "http://localhost:5001";

function validateExplicitBackendTarget(value: string): string {
  let target: URL;
  try {
    target = new URL(value);
  } catch {
    throw new Error("VITE_BACKEND_URL must be a valid absolute HTTP(S) URL");
  }

  if (
    !["http:", "https:"].includes(target.protocol) ||
    target.username ||
    target.password ||
    target.pathname !== "/" ||
    target.search ||
    target.hash
  ) {
    throw new Error(
      "VITE_BACKEND_URL must be an HTTP(S) origin without credentials, a path, query, or fragment",
    );
  }

  return target.origin;
}

export function getBackendTarget(): string {
  if (Object.prototype.hasOwnProperty.call(process.env, "VITE_BACKEND_URL")) {
    return validateExplicitBackendTarget(process.env.VITE_BACKEND_URL ?? "");
  }

  const portFile = path.resolve(process.cwd(), ".backend-port");
  try {
    if (fs.existsSync(portFile)) {
      const port = fs.readFileSync(portFile, "utf-8").trim();
      if (/^\d+$/.test(port)) {
        const parsedPort = Number(port);
        if (parsedPort >= 1 && parsedPort <= 65535) {
          return `http://localhost:${parsedPort}`;
        }
      }
    }
  } catch {
    // A missing or unreadable local convenience file falls through.
  }
  return LEGACY_BACKEND_TARGET;
}
