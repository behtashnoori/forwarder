import { describe, expect, it } from "vitest";
import { formatDualCalendarInstant, formatInstant, formatQuantity, parseQuantityInput } from "./presentation";

describe("shared presentation", () => {
  it("normalizes Persian and Arabic quantity input without accepting ambiguous grouping", () => {
    expect(parseQuantityInput("۱٬۲۳۴٫۵۰")).toEqual({ canonical: "1234.50" });
    expect(parseQuantityInput("١,٢٣٤.٥٠")).toEqual({ canonical: "1234.50" });
    expect(parseQuantityInput("1,23")).toBeNull();
  });

  it("distinguishes zero, missing, and invalid quantities", () => {
    expect(formatQuantity(0, "en-US")).toBe("0");
    expect(formatQuantity(null, "en-US")).toBe("—");
    expect(formatQuantity("bad", "en-US")).toBe("—");
  });

  it("formats explicit instants in the product timezone, not the host timezone", () => {
    expect(formatInstant("2026-03-20T20:45:00Z", "en-GB")).toContain("00:15");
    expect(formatInstant("2026-03-20T20:45:00", "en-GB")).toBe("—");
    expect(formatInstant("2026-03-20T20:45:00Z", "en-GB", { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })).toContain("21 Mar");
  });

  it("renders two calendars from the same instant", () => {
    const calendars = formatDualCalendarInstant("2026-03-20T20:45:00Z");
    expect(calendars.primary).not.toBe("—");
    expect(calendars.secondary).toContain("2026");
  });
});
