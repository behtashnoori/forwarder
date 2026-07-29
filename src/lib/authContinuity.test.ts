import { beforeEach, describe, expect, it } from "vitest";
import {
  consumeReturnTo,
  isSafeInternalReturnTo,
  rememberCurrentRouteForLogin,
} from "./authContinuity";

describe("authentication route continuity", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    window.history.replaceState({}, "", "/expert/requests/42?tab=timeline#latest");
  });

  it("restores the shipment path including query and hash", () => {
    rememberCurrentRouteForLogin();
    expect(consumeReturnTo("/expert")).toBe("/expert/requests/42?tab=timeline#latest");
    expect(consumeReturnTo("/expert")).toBe("/expert");
  });

  it("rejects external and protocol-relative return URLs", () => {
    expect(isSafeInternalReturnTo("https://evil.example/path")).toBe(false);
    expect(isSafeInternalReturnTo("//evil.example/path")).toBe(false);
    expect(isSafeInternalReturnTo("/operations/shipments/7")).toBe(true);
  });
});
