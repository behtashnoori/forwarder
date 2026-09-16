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
  fetchTransportMethodOptions: vi.fn(), submitShipmentRequest: vi.fn(),
}));
const countries = [
  { id: 1, name: "ITALY", name_en: "ITALY", code: "IT" },
  { id: 2, name: "ایران", name_en: "Iran", code: "IR" },
  { id: 3, name: "NORWAY", name_en: "NORWAY", code: "NO" },
];
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.fetchCountries).mockResolvedValue(countries);
  vi.mocked(api.fetchInternationalCityPage).mockImplementation(async id => ({ items: [{ id: id * 10, name: id === 2 ? "Sahand" : "Fertilia", name_en: id === 2 ? "Sahand" : "Fertilia", city_type: "airport", is_major_airport: false, is_major_port: false }], offset: 0, limit: 50, has_more: false }));
  vi.mocked(api.fetchProvinces).mockResolvedValue([]);
  vi.mocked(api.fetchIranPorts).mockResolvedValue([]);
  vi.mocked(api.fetchBorderCustoms).mockResolvedValue([]);
  vi.mocked(api.fetchTransportMethodOptions).mockResolvedValue({ international_methods: [], domestic_methods: [], preference_options: [] });
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
  const selects = screen.getAllByRole("combobox");
  fireEvent.change(selects[selects.length - 2], { target: { value: "forwarder_choice" } });
  fireEvent.click(screen.getByRole("button", { name: "shipping.submit" }));
  await screen.findByRole("button", { name: "requestFlow.confirmAndSend" });
  fireEvent.click(screen.getByRole("button", { name: "requestFlow.confirmAndSend" }));
  await waitFor(() => expect(api.submitShipmentRequest).toHaveBeenCalledWith(expect.objectContaining({
    origin_country_id: 1, origin_international_city_id: 10, dest_country_id: 2, dest_international_city_id: 20,
  })));
});
