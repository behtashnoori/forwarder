import { describe, expect, it } from "vitest";
import form from "@/components/LocationForm.tsx?raw";
import selector from "@/components/CustomerRequestLocationSelector.tsx?raw";
import newOperation from "@/pages/NewOperation.tsx?raw";

describe("HW_GEO_009 consumer coverage guard", () => {
  it("keeps Customer Request on the canonical city plus typed fallback contract", () => {
    expect(form).toContain("CustomerRequestLocationSelector");
    expect(form).toContain("payload.origin_location");
    expect(form).toContain("payload.destination_location");
    expect(form).not.toContain("payload.origin_international_city_id = Number");
    expect(selector).toContain("fetchPublicCanonicalCitiesByCountry");
    expect(selector).toContain('"canonical_city"');
    expect(selector).toContain('"physical_reference"');
    expect(selector).toContain('"declared"');
  });

  it("keeps unresolved demand visible at the explicit operations handoff", () => {
    expect(newOperation).toContain("requires_location_resolution");
    expect(newOperation).toContain("پیش از برنامه‌ریزی به نقاط عملیاتی دقیق متصل شود");
  });
});
