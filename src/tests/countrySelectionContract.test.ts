import { describe, expect, it } from "vitest";

import { countryMatchesSearch } from "@/lib/api";
import locationForm from "@/components/LocationForm.tsx?raw";
import routeAuthoring from "@/components/RouteAuthoringSection.tsx?raw";
import routeActual from "@/components/RouteActualSection.tsx?raw";
import canonicalPicker from "@/components/CanonicalLocationPicker.tsx?raw";
import newOperation from "@/pages/NewOperation.tsx?raw";
import delivery from "@/components/DeliverySection.tsx?raw";
import routeReference from "@/components/RouteReferenceLocationPicker.tsx?raw";
import locationsAdmin from "@/components/LocationsAdminTab.tsx?raw";

describe("HW_GEO_008 country consumer contract", () => {
  it("keeps every discovered general-purpose selector on an approved shared source", () => {
    for (const source of [locationForm, routeAuthoring, routeActual]) {
      expect(source).toContain("fetchCountries");
      expect(source).not.toMatch(/const\s+(countries|countryOptions)\s*=\s*\[/);
    }
    expect(canonicalPicker).toContain("fetchCanonicalCountries");
    expect(newOperation).toContain("CanonicalLocationPicker");
    expect(delivery).toContain("CanonicalLocationPicker");
    expect(routeReference).toContain("CanonicalLocationPicker");
    expect(locationsAdmin).toContain("fetchAdminCountries");
  });

  it("normalizes Persian/Arabic variants and searches names and ISO code", () => {
    const iran = { id: 1, code: "IR", name: "ایران", name_en: "Iran" };
    expect(countryMatchesSearch(iran, "iran")).toBe(true);
    expect(countryMatchesSearch(iran, "IR")).toBe(true);
    expect(countryMatchesSearch({ ...iran, name: "ايران" }, "ایران")).toBe(true);
    expect(countryMatchesSearch(iran, "Brazil")).toBe(false);
  });
});
