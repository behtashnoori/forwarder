import { describe, expect, it } from "vitest";
import locationFormSource from "@/components/LocationForm.tsx?raw";

/**
 * RG-08: the public destination selector must treat Iran as a normal
 * canonical City country. This guard prevents restoration of the legacy-only
 * InternationalCity dependency.
 */
describe("RG-08 public Iran destination wiring", () => {
  it("does not short-circuit Iran before fetching its governed city options", () => {
    expect(locationFormSource).not.toMatch(/destCountry\s*\|\|\s*selectedCountry\?\.code\s*===\s*["']IR["']/);
    expect(locationFormSource).toContain("CustomerRequestLocationSelector");
    expect(locationFormSource).not.toContain("fetchInternationalCities(");
    expect(locationFormSource).toContain("payload.destination_location = destinationRequestLocation!.write");
    expect(locationFormSource).not.toContain("payload.dest_international_city_id = Number(formData.destCityInternational)");
  });
});
