import { afterEach, describe, expect, it } from "vitest";
import { formatLocalDate, parseLocalDate } from "./localDate";

const originalTimezone = process.env.TZ;
afterEach(() => { process.env.TZ = originalTimezone; });

describe("date-only contract", () => {
  it.each(["UTC", "Asia/Tehran", "America/New_York", "Pacific/Honolulu"])(
    "preserves the calendar day in %s",
    (timezone) => {
      process.env.TZ = timezone;
      expect(formatLocalDate("2026-07-29", "en-US")).toBe("Jul 29, 2026");
      expect(parseLocalDate("2026-07-29")).toEqual({ year: 2026, month: 7, day: 29 });
    },
  );
  it.each([null, "", "invalid", "2026-13-01", "2026-02-30", "29/07/2026"])(
    "rejects invalid input %j",
    (value) => {
      expect(parseLocalDate(value)).toBeNull();
      expect(formatLocalDate(value, "en-US", "missing")).toBe("missing");
    },
  );
  it("validates leap years without normalization", () => {
    expect(parseLocalDate("2024-02-29")).toEqual({ year: 2024, month: 2, day: 29 });
    expect(parseLocalDate("2026-02-29")).toBeNull();
  });
  it("returns calendar parts rather than an instant", () => {
    const parsed = parseLocalDate("2026-07-29");
    expect(parsed).toEqual({ year: 2026, month: 7, day: 29 });
    expect(parsed).not.toHaveProperty("toISOString");
  });
  it.each(["pickup_date", "delivery_date", "valid_until", "expected_close_date", "actual_close_date"])(
    "uses the date-only contract for %s",
    () => expect(formatLocalDate("2026-07-29", "en-US")).toBe("Jul 29, 2026"),
  );
});
