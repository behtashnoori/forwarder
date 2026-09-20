import { describe, expect, it } from "vitest";
import {
  formatRouteTransportModes,
  getOrderedRouteTransportModes,
  getRequestTransportMethod,
} from "./transportPresentation";

describe("existing transport presentation", () => {
  it("selects the stored request mode for its request scope without mutation", () => {
    const request = Object.freeze({
      shipping_type: "domestic",
      transport_method: "road",
      domestic_transport_method: "Rail Transport",
      international_transport_method: "Sea Freight",
    });

    expect(getRequestTransportMethod(request)).toBe("Rail Transport");
    expect(request).toEqual({
      shipping_type: "domestic",
      transport_method: "road",
      domestic_transport_method: "Rail Transport",
      international_transport_method: "Sea Freight",
    });
  });

  it("keeps missing request transport missing instead of assuming road", () => {
    expect(getRequestTransportMethod({ shipping_type: "domestic" })).toBeNull();
    expect(getRequestTransportMethod({
      shipping_type: "domestic",
      international_transport_method: "Air Freight",
    })).toBeNull();
  });

  it("does not choose between conflicting scoped modes when shipping type is absent", () => {
    expect(getRequestTransportMethod({
      domestic_transport_method: "Rail Transport",
      international_transport_method: "Sea Freight",
    })).toBeNull();
  });

  it("preserves actual leg order and repeated modes without creating a combined state", () => {
    const legs = Object.freeze([
      Object.freeze({ sequence_number: 3, transport_mode: "road" }),
      Object.freeze({ sequence_number: 1, transport_mode: "road" }),
      Object.freeze({ sequence_number: 2, transport_mode: "rail" }),
    ]);

    expect(getOrderedRouteTransportModes(legs)).toEqual(["road", "rail", "road"]);
    expect(formatRouteTransportModes(legs, (mode) => ({ road: "جاده‌ای", rail: "ریلی" })[mode] ?? mode))
      .toBe("جاده‌ای ← ریلی ← جاده‌ای");
    expect(legs.map((leg) => leg.sequence_number)).toEqual([3, 1, 2]);
    expect(formatRouteTransportModes([], (mode) => mode)).toBeNull();
  });
});
