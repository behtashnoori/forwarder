import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import LocationForm from "@/components/LocationForm";
import * as api from "@/lib/api";

const toast = vi.hoisted(() => vi.fn());
vi.mock("@/hooks/use-toast", () => ({ useToast: () => ({ toast }) }));
vi.mock("@/i18n", () => {
  const t = (key: string) => key === "requestForm.iranDestStepTitle" ? "مرحله ۳: تعیین مقصد در ایران" : key;
  return { useI18n: () => ({ language: "en", t, tf: t }) };
});
vi.mock("@/components/RequestConfirmation", () => ({
  default: ({ onSubmit, locationDisplay }: { onSubmit: () => void; locationDisplay: { destination: string } }) =>
    <div><p>{locationDisplay.destination}</p><button onClick={onSubmit}>Confirm request</button></div>,
}));
vi.mock("@/lib/api", async () => ({
  ...await vi.importActual<typeof import("@/lib/api")>("@/lib/api"),
  fetchCountries: vi.fn(), fetchInternationalCities: vi.fn(), fetchTransportMethodOptions: vi.fn(),
  fetchProvinces: vi.fn(), fetchIranPorts: vi.fn(), fetchBorderCustoms: vi.fn(),
  submitShipmentRequest: vi.fn(),
}));

beforeAll(() => {
  HTMLElement.prototype.scrollIntoView = vi.fn();
  HTMLElement.prototype.hasPointerCapture = () => false;
  HTMLElement.prototype.setPointerCapture = vi.fn();
  HTMLElement.prototype.releasePointerCapture = vi.fn();
});
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.fetchCountries).mockResolvedValue([
    { id: 1, name: "Iran", name_en: "Iran", code: "IR" },
    { id: 2, name: "Turkey", name_en: "Turkey", code: "TR" },
  ]);
  vi.mocked(api.fetchInternationalCities).mockImplementation(async (id) => [
    { id: id === 1 ? 11 : 22, name: id === 1 ? "Tehran" : "Istanbul", name_en: id === 1 ? "Tehran" : "Istanbul", city_type: "city", is_major_port: false, is_major_airport: false },
  ]);
  vi.mocked(api.fetchTransportMethodOptions).mockResolvedValue({
    international_methods: [], domestic_methods: [],
    preference_options: [{ value: "forwarder_suggestion", label: "Forwarder chooses", description: "" }],
  });
  vi.mocked(api.submitShipmentRequest).mockResolvedValue({ id: 1, tracking_code: "SR-TEST", message: "Created" });
});

async function choose(index: number, option: string) {
  const user = userEvent.setup();
  await user.click(screen.getAllByRole("combobox")[index]);
  await user.click(await screen.findByRole("option", { name: option }));
}
async function start() {
  render(<MemoryRouter><LocationForm shippingType="international" onBack={vi.fn()} /></MemoryRouter>);
  // The real Radix controls are ordered: origin country/city, destination country/city, preference.
  await choose(0, "Turkey");
  await waitFor(() => expect(screen.getAllByRole("combobox")[1]).not.toBeDisabled());
  await choose(1, "Istanbul");
  fireEvent.change(screen.getByLabelText(/common.phone/), { target: { value: "09123456789" } });
  await choose(4, "Forwarder chooses");
}
async function destination(country: string, city: string) {
  await choose(2, country);
  await waitFor(() => expect(screen.getAllByRole("combobox")[3]).not.toBeDisabled());
  expect(screen.queryByText("مرحله ۳: تعیین مقصد در ایران")).not.toBeInTheDocument();
  await choose(3, city);
}
async function submit(countryId: number, cityId: number) {
  await userEvent.click(screen.getByRole("button", { name: "shipping.submit" }));
  await userEvent.click(await screen.findByRole("button", { name: "Confirm request" }));
  await waitFor(() => expect(api.submitShipmentRequest).toHaveBeenCalledTimes(1));
  const payload = vi.mocked(api.submitShipmentRequest).mock.calls[0][0];
  expect(payload).toMatchObject({ origin_country_id: 2, origin_international_city_id: 22,
    dest_country_id: countryId, dest_international_city_id: cityId });
  expect(Object.keys(payload).filter(key => key.startsWith("iran_"))).toEqual([]);
  expect(api.fetchIranPorts).not.toHaveBeenCalled();
  expect(api.fetchBorderCustoms).not.toHaveBeenCalled();
  expect(api.fetchProvinces).not.toHaveBeenCalled();
  await screen.findByText("SR-TEST");
}

describe("public destination business flow", () => {
  it.each([["Iran", "Tehran", 1, 11], ["Turkey", "Istanbul", 2, 22]] as const)(
    "%s uses country and InternationalCity without the obsolete step", async (country, city, countryId, cityId) => {
      await start();
      await destination(country, city);
      await submit(countryId, cityId);
    });
  it.each([["Iran", "Tehran", "Turkey", "Istanbul", 2, 22], ["Turkey", "Istanbul", "Iran", "Tehran", 1, 11]] as const)(
    "resets and reloads destination from %s (%s)", async (first, firstCity, next, nextCity, id, cityId) => {
      await start();
      await destination(first, firstCity);
      await choose(2, next);
      expect(screen.getAllByRole("combobox")[3]).not.toHaveTextContent(firstCity);
      await userEvent.click(screen.getByRole("button", { name: "shipping.submit" }));
      expect(screen.queryByRole("button", { name: "Confirm request" })).not.toBeInTheDocument();
      expect(api.submitShipmentRequest).not.toHaveBeenCalled();
      await waitFor(() => expect(screen.getAllByRole("combobox")[3]).not.toBeDisabled());
      await choose(3, nextCity);
      expect(api.fetchInternationalCities).toHaveBeenCalledWith(id);
      await submit(id, cityId);
    });
});
