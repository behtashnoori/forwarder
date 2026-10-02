import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CustomerRequestLocationSelector, type CustomerRequestLocationSelection } from "@/components/CustomerRequestLocationSelector";
import * as api from "@/lib/api";

vi.mock("@/lib/api", async () => ({
  ...await vi.importActual<typeof import("@/lib/api")>("@/lib/api"),
  fetchPublicCanonicalCitiesByCountry: vi.fn(),
  fetchInternationalCityPage: vi.fn(),
}));

function Harness({ countryId = "1", countryCode = "IR" }: { countryId?: string; countryCode?: string }) {
  const [value, setValue] = useState<CustomerRequestLocationSelection | null>(null);
  return <><CustomerRequestLocationSelector countryId={countryId} countryCode={countryCode} locale="fa" side="destination" value={value} onChange={setValue}/><output>{value ? JSON.stringify(value.write) : "empty"}</output></>;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.fetchPublicCanonicalCitiesByCountry).mockResolvedValue({
    items: [{ source_id: 10, geoname_id: 418863, name_fa: "اصفهان", name_en: "Isfahan", latitude: "32", longitude: "51", province: { source_id: 2, geoname_id: 418862, name_fa: "اصفهان", name_en: "Isfahan" } }],
    offset: 0, limit: 50, has_more: true,
  });
  vi.mocked(api.fetchInternationalCityPage).mockImplementation(async (_country, _query, _offset, type) => ({
    items: type === "airport" ? [{ id: 20, name: "فرودگاه امام خمینی", name_en: "Imam Khomeini Airport", city_type: "airport", is_major_airport: true, is_major_port: false, un_locode: "IRIKA" }] : [],
    offset: 0, limit: 50, has_more: false,
  }));
});

describe("HW_GEO_009 customer request place selector", () => {
  it("selects a canonical city and pages the country-wide catalog", async () => {
    render(<Harness/>);
    const select = await screen.findByLabelText("انتخاب شهر مقصد");
    await waitFor(() => expect(select).not.toBeDisabled());
    await userEvent.selectOptions(select, "10");
    expect(screen.getByText(/canonical_city/)).toHaveTextContent('"source_id":10');
    await userEvent.click(screen.getByRole("button", { name: "نتایج بیشتر" }));
    await waitFor(() => expect(api.fetchPublicCanonicalCitiesByCountry).toHaveBeenLastCalledWith("IR", "", 50, 50));
  });

  it("keeps airports typed separately from cities", async () => {
    render(<Harness/>);
    await userEvent.click(screen.getByRole("button", { name: "فرودگاه یا بندر" }));
    const select = await screen.findByLabelText("انتخاب نقطه مرجع مقصد");
    await waitFor(() => expect(screen.getByRole("option", { name: /فرودگاه امام خمینی/ })).toBeInTheDocument());
    await userEvent.selectOptions(select, "20");
    expect(screen.getByText(/physical_reference/)).toHaveTextContent('"source_id":20');
  });

  it("requires explicit text for the declared fallback", async () => {
    render(<Harness countryId="3" countryCode="BR"/>);
    await userEvent.click(screen.getByRole("button", { name: "محل موردنظر در فهرست نیست" }));
    expect(screen.getByText("empty")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("نام شهر یا محل موردنظر مقصد"), "انبار سانتوس");
    expect(screen.getByText(/declared/)).toHaveTextContent("انبار سانتوس");
    expect(screen.getByText("محل اعلام‌شده مشتری؛ نیازمند بررسی کارشناس")).toBeInTheDocument();
  });

  it("distinguishes request failure from no matching city", async () => {
    vi.mocked(api.fetchPublicCanonicalCitiesByCountry).mockRejectedValueOnce(new Error("network"));
    render(<Harness/>);
    expect(await screen.findByRole("alert")).toHaveTextContent("دریافت فهرست ناموفق بود");
    expect(screen.queryByText("نتیجه‌ای برای این جست‌وجو یافت نشد.")).not.toBeInTheDocument();
  });
});
