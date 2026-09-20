import { describe, expect, it } from "vitest";
import { formatDualCalendarDate, formatDualCalendarInstant } from "./dualCalendar";

describe("dual-calendar presentation", () => {
  it.each([
    ["2026-03-20", "Mar 20, 2026 (Esfand 29, 1404 AP)"],
    ["2026-03-21", "Mar 21, 2026 (Farvardin 1, 1405 AP)"],
    ["2024-02-29", "Feb 29, 2024 (Esfand 10, 1402 AP)"],
    ["2026-12-31", "Dec 31, 2026 (Dey 10, 1405 AP)"],
  ])("converts known Local Date boundary %s", (value, expected) => {
    expect(formatDualCalendarDate(value, "en-US")).toBe(expected);
  });

  it.each(["UTC", "Asia/Tehran", "America/New_York", "Pacific/Honolulu"])(
    "does not shift a Local Date in process zone %s",
    (timezone) => {
      const previous = process.env.TZ;
      process.env.TZ = timezone;
      try {
        expect(formatDualCalendarDate("2026-09-20", "en-US"))
          .toBe("Sep 20, 2026 (Shahrivar 29, 1405 AP)");
      } finally {
        process.env.TZ = previous;
      }
    },
  );

  it("resolves both calendars from the same Instant near local midnight", () => {
    const instant = "2026-03-20T21:00:00Z";
    expect(formatDualCalendarInstant(instant, "en-US", {
      includeTime: false,
      timeZone: "UTC",
    })).toBe("Mar 20, 2026 (Esfand 29, 1404 AP)");
    expect(formatDualCalendarInstant(instant, "en-US", {
      includeTime: false,
      timeZone: "Asia/Tehran",
    })).toBe("Mar 21, 2026 (Farvardin 1, 1405 AP)");
  });

  it("renders the clock once while preserving the selected Instant zone", () => {
    const rendered = formatDualCalendarInstant("2026-01-01T00:15:00Z", "en-US", {
      timeZone: "UTC",
      timeZoneName: "short",
    });
    expect(rendered).toBe("Jan 1, 2026 (Dey 11, 1404 AP) · 12:15 AM UTC");
    expect(rendered.match(/12:15/g)).toHaveLength(1);
  });

  it("localizes the Gregorian-first structure for Persian RTL", () => {
    expect(formatDualCalendarDate("2026-03-21", "fa-IR"))
      .toBe("۲۱ مارس ۲۰۲۶ (۱ فروردین ۱۴۰۵)");
  });

  it.each([null, undefined, "", "invalid", "2026-02-30"])(
    "returns the existing empty-state value for invalid Local Date %j",
    (value) => expect(formatDualCalendarDate(value, "en-US", "pending")).toBe("pending"),
  );

  it.each([null, undefined, "", "invalid"])(
    "returns the existing empty-state value for invalid Instant %j",
    (value) => expect(formatDualCalendarInstant(value, "en-US", { fallback: "pending" })).toBe("pending"),
  );
});
