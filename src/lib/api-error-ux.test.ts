import { describe, expect, it } from "vitest";
import { toUserFacingApiError } from "@/lib/api-error-ux";

describe("API error UX", () => {
  it.each([[403, "permission", false], [404, "not-found", false], [409, "conflict", true], [422, "validation", false], [500, "server", true]])("maps HTTP %s to a distinct user state", (status, state, retryable) => {
    expect(toUserFacingApiError({ status })).toMatchObject({ state, retryable });
  });
  it("maps transport failure to a retryable network state", () => expect(toUserFacingApiError(new TypeError("offline"))).toMatchObject({ state: "network", retryable: true }));
});
