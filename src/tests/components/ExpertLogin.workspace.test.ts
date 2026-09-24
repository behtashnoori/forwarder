import { describe, expect, it } from "vitest";
import { getExpertLoginFallback } from "@/lib/authContinuity";

describe("ExpertLogin workspace routing", () => {
  it("routes an ordinary expert to the operational workspace", () => {
    expect(getExpertLoginFallback({ authority: "EXPERT", role: "expert" })).toBe("/operations");
  });

  it.each([
    [{ authority: "PLATFORM_ADMIN", role: "expert" }, "/admin"],
    [{ authority: "ORGANIZATION_ADMIN", role: "expert" }, "/admin"],
    [{ authority: "EXPERT", role: "admin" }, "/admin"],
    [{ authority: "EXPERT", role: "crm_manager" }, "/crm"],
    [{ authority: "EXPERT", role: "business_expert" }, "/crm"],
    [{ authority: "EXPERT", role: "supervisor" }, "/expert"],
  ])("preserves the existing destination for %o", (expert, expected) => {
    expect(getExpertLoginFallback(expert)).toBe(expected);
  });
});
