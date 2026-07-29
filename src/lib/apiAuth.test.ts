import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchUsers, refreshExpertSession } from "./api";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("controlled access-token refresh", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("expert_token", "expired-access");
    localStorage.setItem("expert_refresh_token", "refresh-1");
    vi.restoreAllMocks();
  });

  it("uses one refresh for concurrent callers", async () => {
    let refreshCalls = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/auth/refresh")) {
        refreshCalls += 1;
        await Promise.resolve();
        return jsonResponse(200, {
          access_token: "access-2",
          refresh_token: "refresh-2",
        });
      }
      return jsonResponse(200, {});
    }));

    const results = await Promise.all([
      refreshExpertSession(),
      refreshExpertSession(),
      refreshExpertSession(),
    ]);

    expect(results).toEqual([true, true, true]);
    expect(refreshCalls).toBe(1);
    expect(localStorage.getItem("expert_token")).toBe("access-2");
  });

  it("retries each failed API request only once after the shared refresh", async () => {
    let resourceCalls = 0;
    let refreshCalls = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/auth/refresh")) {
        refreshCalls += 1;
        return jsonResponse(200, {
          access_token: "access-2",
          refresh_token: "refresh-2",
        });
      }
      resourceCalls += 1;
      return resourceCalls <= 2
        ? jsonResponse(401, { error: "expired" })
        : jsonResponse(200, { users: [] });
    }));

    await Promise.all([fetchUsers(), fetchUsers()]);
    expect(refreshCalls).toBe(1);
    expect(resourceCalls).toBe(4);
  });
});
