import fs from "fs";
import { afterEach, describe, expect, it, vi } from "vitest";

import { getBackendTarget } from "../../vite-backend-target";

const originalBackendUrl = process.env.VITE_BACKEND_URL;

afterEach(() => {
  vi.restoreAllMocks();
  if (originalBackendUrl === undefined) {
    delete process.env.VITE_BACKEND_URL;
  } else {
    process.env.VITE_BACKEND_URL = originalBackendUrl;
  }
});

describe("Vite backend target precedence", () => {
  it("prefers an explicit VITE_BACKEND_URL over .backend-port", () => {
    process.env.VITE_BACKEND_URL = "http://127.0.0.1:49123";
    vi.spyOn(fs, "existsSync").mockReturnValue(true);
    vi.spyOn(fs, "readFileSync").mockReturnValue("57065");

    expect(getBackendTarget()).toBe("http://127.0.0.1:49123");
    expect(fs.readFileSync).not.toHaveBeenCalled();
  });

  it("uses .backend-port when the explicit variable is absent", () => {
    delete process.env.VITE_BACKEND_URL;
    vi.spyOn(fs, "existsSync").mockReturnValue(true);
    vi.spyOn(fs, "readFileSync").mockReturnValue("57065\n");

    expect(getBackendTarget()).toBe("http://localhost:57065");
  });

  it("uses the legacy default when neither prior source is usable", () => {
    delete process.env.VITE_BACKEND_URL;
    vi.spyOn(fs, "existsSync").mockReturnValue(false);

    expect(getBackendTarget()).toBe("http://localhost:5001");
  });

  it.each([
    "",
    "not-a-url",
    "ftp://127.0.0.1:49123",
    "http://user:secret@127.0.0.1:49123",
    "http://127.0.0.1:49123/api",
  ])("fails closed for invalid explicit target %j", (value) => {
    process.env.VITE_BACKEND_URL = value;
    vi.spyOn(fs, "existsSync").mockReturnValue(true);
    vi.spyOn(fs, "readFileSync").mockReturnValue("57065");

    expect(() => getBackendTarget()).toThrow(/VITE_BACKEND_URL/);
    expect(fs.readFileSync).not.toHaveBeenCalled();
  });
});
