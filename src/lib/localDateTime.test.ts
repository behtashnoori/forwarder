import { afterEach, describe, expect, it } from "vitest";
import { localDateTimeInputToUtc, toLocalDateTimeInputValue } from "./localDateTime";

const originalTimezone = process.env.TZ;
afterEach(() => { process.env.TZ = originalTimezone; });

describe("datetime-local conversion", () => {
  it("shows Tehran wall-clock time", () => {
    process.env.TZ = "Asia/Tehran";
    expect(toLocalDateTimeInputValue(new Date("2026-07-29T09:25:00.000Z"))).toBe("2026-07-29T12:55");
  });
  it("round-trips Tehran time once", () => {
    process.env.TZ = "Asia/Tehran";
    expect(localDateTimeInputToUtc("2026-07-29T12:55")).toBe("2026-07-29T09:25:00.000Z");
  });
  it("round-trips UTC", () => {
    process.env.TZ = "UTC";
    expect(localDateTimeInputToUtc("2026-07-29T09:25")).toBe("2026-07-29T09:25:00.000Z");
  });
  it("crosses the local day boundary", () => {
    process.env.TZ = "Asia/Tehran";
    expect(toLocalDateTimeInputValue(new Date("2026-07-29T22:30:00.000Z"))).toBe("2026-07-30T02:00");
  });
  it.each(["", "not-a-date", "2026-02-30T12:00"])("rejects invalid input %j", (value) => {
    expect(localDateTimeInputToUtc(value)).toBeNull();
  });
});
