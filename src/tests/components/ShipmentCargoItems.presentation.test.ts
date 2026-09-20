import { describe, expect, it } from "vitest";
import { formatBusinessNumber, formatMoney, formatQuantity } from "../../lib/formatQuantity";

describe("shipment cargo display quantities", () => {
  it("removes stored decimal scale noise and adds integer grouping", () => {
    expect(formatQuantity("1000.000000")).toBe("1,000");
  });

  it("retains significant fractional precision", () => {
    expect(formatQuantity("12.500000")).toBe("12.5");
    expect(formatQuantity("12.500001")).toBe("12.500001");
  });

  it("groups large integers and exact API decimal strings without Number coercion", () => {
    expect(formatBusinessNumber("1234567", { locale: "en-US" })).toBe("1,234,567");
    expect(formatBusinessNumber("900719925474099312345.1200", { locale: "en-US" })).toBe("900,719,925,474,099,312,345.1200");
    expect(formatQuantity("900719925474099312345.1200")).toBe("900,719,925,474,099,312,345.12");
    expect(formatBusinessNumber(1e21, { locale: "en-US" })).toBe("1,000,000,000,000,000,000,000");
  });

  it("uses the requested application locale without changing numeric meaning", () => {
    expect(formatQuantity("1234.5000", "fa-IR")).toBe("۱٬۲۳۴٫۵");
  });

  it("keeps zero distinct from missing and fails safely for invalid values", () => {
    expect(formatBusinessNumber(0)).toBe("0");
    expect(formatBusinessNumber(null)).toBe("—");
    expect(formatBusinessNumber(undefined, { missing: "Unknown" })).toBe("Unknown");
    expect(formatBusinessNumber("not-a-number")).toBe("—");
    expect(formatQuantity(null)).toBe("0");
    expect(formatQuantity("not-a-number")).toBe("—");
  });

  it("groups money without changing currency or recorded fractional digits", () => {
    expect(formatMoney("1234567.500000", "USD", "en-US")).toBe("1,234,567.500000 USD");
    expect(formatMoney("0", "IRR", "en-US")).toBe("0 IRR");
    expect(formatMoney(null, "USD", "en-US", "Unknown")).toBe("Unknown");
  });

  it("is display-only and does not mutate the source API payload", () => {
    const payload = { quantity: "1234567.500000", public_id: "12345678-1234-4234-8234-123456789012" };
    expect(formatQuantity(payload.quantity)).toBe("1,234,567.5");
    expect(payload).toEqual({ quantity: "1234567.500000", public_id: "12345678-1234-4234-8234-123456789012" });
  });
});
