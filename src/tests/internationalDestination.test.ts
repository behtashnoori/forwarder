import { describe, expect, it } from "vitest";

import {
  buildIranDestinationPayload,
  isInternationalRouteComplete,
} from "@/lib/api";

const route = (overrides: Partial<Parameters<typeof isInternationalRouteComplete>[0]> = {}) => ({
  originCountry: "1",
  originCity: "10",
  destinationCountry: "2",
  destinationCity: "20",
  isIranDestination: false,
  ...overrides,
});

describe("international destination rules", () => {
  it("requires a generic destination city for non-Iran countries", () => {
    expect(isInternationalRouteComplete(route({ destinationCity: "" }))).toBe(false);
    expect(isInternationalRouteComplete(route())).toBe(true);
  });

  it("requires a governed international location for Iran too", () => {
    expect(isInternationalRouteComplete(route({
      destinationCity: "",
      isIranDestination: true,
    }))).toBe(false);
    expect(buildIranDestinationPayload({ type: "city" })).toEqual({});
  });

  it.each([
    ["city", { cityId: "31" }, "iran_dest_city_id"],
    ["port", { portId: "41" }, "iran_entry_port_id"],
    ["customs", { customsOfficeId: "51" }, "iran_dest_customs_office_id"],
  ] as const)("builds a complete %s destination only", (type, selected, expectedKey) => {
    const payload = buildIranDestinationPayload({
      type,
      provinceId: "7",
      ...selected,
    });

    expect(payload).toMatchObject({
      iran_dest_type: type,
      iran_entry_province_id: 7,
      [expectedKey]: Number(Object.values(selected)[0]),
    });
  });

  it("omits an incomplete precise destination fragment", () => {
    expect(buildIranDestinationPayload({ type: "port", portId: "41" })).toEqual({});
    expect(buildIranDestinationPayload({ type: "customs", provinceId: "7" })).toEqual({});
  });
});
