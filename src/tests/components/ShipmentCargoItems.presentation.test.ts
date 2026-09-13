import { describe, expect, it } from "vitest";
import { formatQuantity } from "../../lib/formatQuantity";

describe("shipment cargo display quantities", () => {
  it("removes stored decimal scale noise and adds integer grouping", () => {
    expect(formatQuantity("1000.000000")).toBe("1,000");
  });

  it("retains significant fractional precision", () => {
    expect(formatQuantity("12.500000")).toBe("12.5");
    expect(formatQuantity("12.500001")).toBe("12.500001");
  });
});
