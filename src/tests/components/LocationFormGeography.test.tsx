import type { ReactNode } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, expect, it, vi } from "vitest";
import LocationForm from "@/components/LocationForm";
import * as api from "@/lib/api";

const helpers = vi.hoisted(() => ({ t: (key: string) => key, tf: (key: string) => key, toast: vi.fn() }));
vi.mock("@/i18n", () => ({ useI18n: () => ({ language: "fa", shippingTypeLabel: helpers.t, ...helpers }) }));
vi.mock("@/hooks/use-toast", () => ({ useToast: () => ({ toast: helpers.toast }) }));
vi.mock("@/components/ui/select", () => ({
  Select: ({ value, onValueChange, children, disabled }: { value: string; onValueChange: (v: string) => void; children: ReactNode; disabled?: boolean }) =>
    <select value={value} disabled={disabled} onChange={e => onValueChange(e.target.value)}><option value="" />{children}</select>,
  SelectTrigger: () => null, SelectValue: () => null,
  SelectContent: ({ children }: { children: ReactNode }) => <>{children}</>,
  SelectItem: ({ value, children, disabled }: { value: string; children: ReactNode; disabled?: boolean }) => <option value={value} disabled={disabled}>{children}</option>,
}));
vi.mock("@/lib/api", async () => ({
  ...await vi.importActual("@/lib/api"), fetchCountries: vi.fn(), fetchInternationalCityPage: vi.fn(),
  fetchProvinces: vi.fn(), fetchIranPorts: vi.fn(), fetchBorderCustoms: vi.fn(),
  fetchTransportMethodOptions: vi.fn(), fetchTransportIntentOptions: vi.fn(), prepareShipmentRequest: vi.fn(), submitShipmentRequest: vi.fn(),
}));
const countries = [
  { id: 1, name: "ITALY", name_en: "ITALY", code: "IT" },
  { id: 2, name: "ایران", name_en: "Iran", code: "IR" },
  { id: 3, name: "NORWAY", name_en: "NORWAY", code: "NO" },
];
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.fetchTransportIntentOptions).mockResolvedValue({items: []});
  vi.mocked(api.prepareShipmentRequest).mockResolvedValue({transport_summary: {display: "پیشنهاد فورواردر", classification: null, legacy_display_limited: false, steps: []}});
  vi.mocked(api.fetchCountries).mockResolvedValue(countries);
  vi.mocked(api.fetchInternationalCityPage).mockImplementation(async id => ({ items: [{ id: id * 10, name: id === 2 ? "Sahand" : "Fertilia", name_en: id === 2 ? "Sahand" : "Fertilia", city_type: "airport", is_major_airport: false, is_major_port: false }], offset: 0, limit: 50, has_more: false }));
  vi.mocked(api.fetchProvinces).mockResolvedValue([]);
  vi.mocked(api.fetchIranPorts).mockResolvedValue([]);
  vi.mocked(api.fetchBorderCustoms).mockResolvedValue([]);
  vi.mocked(api.fetchTransportMethodOptions).mockResolvedValue({ international_methods: [], domestic_methods: [], preference_options: [{value: "forwarder_suggestion", label: "پیشنهاد فورواردر", description: ""}] });
  vi.mocked(api.submitShipmentRequest).mockResolvedValue({ id: 100, tracking_code: "TEST-GEO" } as Awaited<ReturnType<typeof api.submitShipmentRequest>>);
});

it("loads Iran destination and submits stable country/location IDs through confirmation", async () => {
  render(<MemoryRouter><LocationForm shippingType="international" onBack={vi.fn()} /></MemoryRouter>);
  await screen.findAllByRole("option", { name: "ITALY" });
  fireEvent.change(screen.getAllByRole("combobox")[0], { target: { value: "1" } });
  await screen.findByRole("option", { name: /Fertilia/ });
  fireEvent.change(screen.getAllByRole("combobox")[1], { target: { value: "10" } });
  fireEvent.change(screen.getAllByRole("combobox")[2], { target: { value: "2" } });
  await screen.findByRole("option", { name: /Sahand/ });
  expect(api.fetchInternationalCityPage).toHaveBeenCalledWith(2, "", 0);
  fireEvent.change(screen.getAllByRole("combobox")[3], { target: { value: "20" } });
  // Country search must not change the selected identity or summary.
  fireEvent.change(screen.getByLabelText("جست‌وجوی کشور مبدأ"), { target: { value: "Norway" } });
  expect(screen.getAllByRole("combobox")[0]).toHaveValue("1");
  fireEvent.change(screen.getByPlaceholderText("09123456789"), { target: { value: "09123456789" } });
  fireEvent.change(screen.getByRole("option", {name: "پیشنهاد فورواردر"}).closest("select")!, { target: {value: "forwarder_suggestion"} });
  fireEvent.change(screen.getByLabelText(/requestForm.cargoDescription/), {target: {value: "Synthetic cargo"}});
  fireEvent.click(screen.getByRole("button", { name: "shipping.submit" }));
  await screen.findByRole("button", { name: "requestFlow.confirmAndSend" });
  fireEvent.click(screen.getByRole("button", { name: "requestFlow.confirmAndSend" }));
  await waitFor(() => expect(api.submitShipmentRequest).toHaveBeenCalledWith(expect.objectContaining({
    origin_country_id: 1, origin_international_city_id: 10, dest_country_id: 2, dest_international_city_id: 20,
  })));
});

it("keeps ordered repeated intent and input values through owner field errors and final submission", async () => {
  vi.mocked(api.fetchProvinces).mockResolvedValue([{id: 1, name: "Tehran"}, {id: 2, name: "Esfahan"}]);
  vi.mocked(api.fetchTransportIntentOptions).mockResolvedValue({items: [
    {mode: "road", label: "جاده‌ای", catalog_ids: [1]},
    {mode: "sea", label: "دریایی", catalog_ids: [2]},
    {mode: "rail", label: "ریلی", catalog_ids: [3, 4]},
  ]});
  render(<MemoryRouter><LocationForm shippingType="domestic" onBack={vi.fn()} /></MemoryRouter>);
  await screen.findAllByRole("option", {name: "Tehran"});
  fireEvent.change(screen.getAllByRole("combobox")[0], {target: {value: "1"}});
  fireEvent.change(screen.getAllByRole("combobox")[1], {target: {value: "2"}});
  fireEvent.change(screen.getByPlaceholderText("09123456789"), {target: {value: "09000000000"}});
  fireEvent.change(screen.getByLabelText("نوع حمل"), {target: {value: "combined"}});
  for (let i = 0; i < 4; i++) fireEvent.click(screen.getByRole("button", {name: "افزودن مرحله حمل"}));
  fireEvent.change(screen.getByLabelText("روش مرحله 3"), {target: {value: "sea"}});
  expect(screen.getAllByRole("option", {name: "ریلی"})).toHaveLength(4); // one per step; no duplicated catalog choice
  vi.mocked(api.prepareShipmentRequest).mockRejectedValueOnce(new api.ApiError(400, "CARGO_DESCRIPTION_REQUIRED", "شرح کالا را وارد کنید.", ["cargo_description"]));
  fireEvent.click(screen.getByRole("button", {name: "shipping.submit"}));
  await screen.findByRole("alert");
  expect(screen.getByPlaceholderText("09123456789")).toHaveValue("09000000000");
  expect(screen.getByLabelText("روش مرحله 3")).toHaveValue("sea");
  expect(api.submitShipmentRequest).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText(/requestForm.cargoDescription/), {target: {value: "Synthetic cargo"}});
  vi.mocked(api.prepareShipmentRequest).mockResolvedValue({transport_summary: {display: "جاده‌ای ← جاده‌ای ← دریایی ← جاده‌ای", classification: "combined", legacy_display_limited: true, steps: []}});
  fireEvent.click(screen.getByRole("button", {name: "shipping.submit"}));
  await screen.findByText("جاده‌ای ← جاده‌ای ← دریایی ← جاده‌ای");
  fireEvent.click(screen.getByRole("button", {name: "requestFlow.confirmAndSend"}));
  await waitFor(() => expect(api.submitShipmentRequest).toHaveBeenCalledWith(expect.objectContaining({
    transport_intent: {version: 1, steps: [{mode: "road"}, {mode: "road"}, {mode: "sea"}, {mode: "road"}]},
    transport_classification: "combined", cargo_description: "Synthetic cargo",
  })));
});
