import { describe, expect, it } from "vitest";
import locationFormSource from "@/components/LocationForm.tsx?raw";

/**
 * RG-08: the public destination selector must treat Iran as a normal
 * governed InternationalCity country. The API-level contract is covered by
 * test_governed_international_geography; this guard prevents restoration of
 * the former client-side IR short-circuit.
 */
describe("RG-08 public Iran destination wiring", () => {
  it("does not short-circuit Iran before fetching its governed city options", () => {
    expect(locationFormSource).not.toMatch(/destCountry\s*\|\|\s*selectedCountry\?\.code\s*===\s*["']IR["']/);
    expect(locationFormSource).toContain("fetchInternationalCities(countryId)");
    expect(locationFormSource).toContain("payload.dest_international_city_id = Number(formData.destCityInternational)");
  });
});
