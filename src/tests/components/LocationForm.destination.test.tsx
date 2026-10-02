import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import LocationForm from "@/components/LocationForm";
import * as api from "@/lib/api";
import * as portalApi from "@/lib/customerPortalApi";

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
  fetchCountries: vi.fn(), fetchInternationalCityPage: vi.fn(), fetchTransportMethodOptions: vi.fn(), fetchRequestCargoOptions: vi.fn(),
  fetchProvinces: vi.fn(), fetchCounties:vi.fn(), fetchCities:vi.fn(), fetchIranPorts: vi.fn(), fetchBorderCustoms: vi.fn(),
  fetchCanonicalCountries:vi.fn(), fetchCanonicalAdmin1:vi.fn(), fetchCanonicalCities:vi.fn(),
  submitShipmentRequest: vi.fn(),
}));
vi.mock("@/lib/customerPortalApi", async () => ({
  ...await vi.importActual<typeof import("@/lib/customerPortalApi")>("@/lib/customerPortalApi"),
  submitShipmentRequestForCurrentCustomer: vi.fn(),
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
  vi.mocked(api.fetchCanonicalCountries).mockResolvedValue({items:[{id:1,code:"IR",name_fa:"ایران",name_en:"Iran"}]});
  vi.mocked(api.fetchCanonicalAdmin1).mockResolvedValue({items:[
    {source_id:101,geoname_id:418862,code:"04",name_fa:"اصفهان",name_en:"Isfahan"},
    {source_id:102,geoname_id:131222,code:"11",name_fa:"هرمزگان",name_en:"Hormozgan"},
    {source_id:103,geoname_id:110791,code:"26",name_fa:"تهران",name_en:"Tehran"},
  ]});
  vi.mocked(api.fetchCanonicalCities).mockImplementation(async admin=>({items:
    admin===418862?[{source_id:201,geoname_id:418863,name_fa:"اصفهان",name_en:"Isfahan",latitude:"32",longitude:"51"}]:
    admin===131222?[{source_id:202,geoname_id:141681,name_fa:"بندرعباس",name_en:"Bandar Abbas",latitude:"27",longitude:"56"}]:
    [{source_id:203,geoname_id:112931,name_fa:"تهران",name_en:"Tehran",latitude:"35",longitude:"51"}]
  }));
  vi.mocked(api.fetchInternationalCityPage).mockImplementation(async (id) => ({
    items: [{ id: id === 1 ? 11 : 22, name: id === 1 ? "Tehran" : "Istanbul", name_en: id === 1 ? "Tehran" : "Istanbul", un_locode: id === 1 ? "IRTHR" : "TRIST", city_type: "city", is_major_port: false, is_major_airport: false }],
    offset: 0, limit: 50, has_more: false,
  }));
  vi.mocked(api.fetchTransportMethodOptions).mockResolvedValue({
    international_methods: [], domestic_methods: [],
    preference_options: [{ value: "forwarder_suggestion", label: "Forwarder chooses", description: "" }],
  });
  vi.mocked(api.fetchRequestCargoOptions).mockResolvedValue({
    cargo_types: [{ public_id: "cargo-type", code: "GENERAL", fa_name: "عمومی", en_name: "General" }],
    uoms: [{ public_id: "kg", code: "KG", fa_name: "کیلوگرم", en_name: "Kilogram", symbol: "kg", measurement_dimension: "WEIGHT" }],
  });
  vi.mocked(api.submitShipmentRequest).mockResolvedValue({ id: 1, tracking_code: "SR2-AAAAAAAAAAAAAAAAAAAAAA", message: "Created", request_transport_intent: null, cargo_items: [] });
  vi.mocked(portalApi.submitShipmentRequestForCurrentCustomer).mockImplementation(async (payload) => ({
    response: await api.submitShipmentRequest(payload),
    customerAuthenticated: false,
  }));
});

async function choose(index: number, option: string) {
  const user = userEvent.setup();
  const control = screen.getAllByRole("combobox")[index];
  if (control.tagName === "SELECT") {
    const selected = await waitFor(() => within(control).getByRole("option", { name: new RegExp(`^${option}`) }));
    await user.selectOptions(control, selected);
    return;
  }
  await user.click(control);
  await user.click(await screen.findByRole("option", { name: new RegExp(`^${option}`) }));
}
async function start() {
  render(<MemoryRouter><LocationForm shippingType="international" onBack={vi.fn()} /></MemoryRouter>);
  // The real Radix controls are ordered: origin country/city, destination country/city, preference.
  await choose(0, "Turkey");
  await waitFor(() => expect(screen.getAllByRole("combobox")[1]).not.toBeDisabled());
  await choose(1, "Istanbul");
  fireEvent.change(screen.getByLabelText(/common.phone/), { target: { value: "09123456789" } });
  await choose(4, "requestForm.forwarderSuggestionOption");
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
    dest_country_id: countryId, dest_international_city_id: cityId, contact_phone: "09123456789", cargo_items: [] });
  expect(Object.keys(payload).filter(key => key.startsWith("iran_"))).toEqual([]);
  expect(api.fetchIranPorts).not.toHaveBeenCalled();
  expect(api.fetchBorderCustoms).not.toHaveBeenCalled();
  expect(api.fetchProvinces).not.toHaveBeenCalled();
  await screen.findByText("SR2-AAAAAAAAAAAAAAAAAAAAAA");
  expect(screen.queryByText("SR000001")).not.toBeInTheDocument();
}

describe("public destination business flow", () => {
  it("uses canonical Admin1 to City identity for a domestic customer request without a County dependency", async()=>{
    const select=async(label:string,option:string)=>{
      const user=userEvent.setup();
      await user.click(screen.getByLabelText(label));
      await user.click(await screen.findByRole("option",{name:new RegExp(`^${option}`)}));
    };
    vi.mocked(api.fetchTransportMethodOptions).mockResolvedValue({
      international_methods:[],domestic_methods:[{id:1,name:"road",name_fa:"جاده‌ای",is_active:true}],
      preference_options:[{value:"customer_choice",label:"انتخاب مشتری",description:""}],
    });
    render(<MemoryRouter><LocationForm shippingType="domestic" onBack={vi.fn()}/></MemoryRouter>);
    await waitFor(()=>expect(api.fetchCanonicalAdmin1).toHaveBeenCalledWith("IR"));
    await select("requestForm.originProvince","اصفهان");
    await userEvent.click(screen.getByRole("button",{name:/requestForm.showOriginDetails/}));
    await waitFor(()=>expect(api.fetchCanonicalCities).toHaveBeenCalledWith(418862));
    await select("requestForm.originCity","اصفهان");
    await select("requestForm.destinationProvince","هرمزگان");
    await userEvent.click(screen.getByRole("button",{name:/requestForm.showDestinationDetails/}));
    await waitFor(()=>expect(api.fetchCanonicalCities).toHaveBeenCalledWith(131222));
    await select("requestForm.destinationCity","بندرعباس");
    expect(api.fetchCounties).not.toHaveBeenCalled();
    expect(api.fetchCities).not.toHaveBeenCalled();
    expect(screen.getByLabelText("requestForm.originProvince")).toHaveTextContent("اصفهان");
    expect(screen.getByLabelText("requestForm.originCity")).toHaveTextContent("اصفهان");
    expect(screen.getByLabelText("requestForm.destinationProvince")).toHaveTextContent("هرمزگان");
    expect(screen.getByLabelText("requestForm.destinationCity")).toHaveTextContent("بندرعباس");
  });
  it("contains transport choices locally at mobile width and preserves RTL without global overflow hiding", async () => {
    vi.mocked(api.fetchTransportMethodOptions).mockResolvedValue({
      international_methods: [{ id: 9, name: "road", name_fa: "حمل زمینی", description: "A deliberately long method description used to exercise wrapping", is_active: true }],
      domestic_methods: [],
      preference_options: [
        { value: "customer_choice", label: "Old API label", description: "" },
        { value: "forwarder_suggestion", label: "Old API suggestion", description: "" },
      ],
    });
    render(<MemoryRouter><div dir="rtl" style={{ width: 390 }}><LocationForm shippingType="international" onBack={vi.fn()} /></div></MemoryRouter>);
    const section = await screen.findByTestId("transport-method-section");
    expect(section).toHaveClass("min-w-0", "overflow-x-clip");
    expect(section.closest("[dir='rtl']")).toBeInTheDocument();
    expect(section.querySelectorAll("[class*='overflow-hidden']").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("requestForm.transportPreference")).toBeInTheDocument();
    expect(screen.queryByText("Old API label")).not.toBeInTheDocument();
    expect(screen.getAllByRole("combobox")).toHaveLength(6);
  });

  it("offers Combined Transport as one ordinary customer intent choice", async () => {
    vi.mocked(api.fetchTransportMethodOptions).mockResolvedValue({
      international_methods: [{ id: 7, name: "Combined Transport", name_fa: "حمل ترکیبی", description: "Customer intent only", is_active: true }],
      domestic_methods: [{ id: 7, name: "Combined Transport", name_fa: "حمل ترکیبی", description: "Customer intent only", is_active: true }],
      preference_options: [{ value: "customer_choice", label: "Customer chooses", description: "" }],
    });
    render(<MemoryRouter><LocationForm shippingType="international" onBack={vi.fn()} /></MemoryRouter>);
    await waitFor(() => expect(screen.getAllByRole("combobox")).toHaveLength(6));
    await userEvent.click(screen.getAllByRole("combobox")[5]);
    const combined = await screen.findByRole("option", { name: /Combined Transport/ });
    await userEvent.click(combined);
    expect(screen.getAllByRole("combobox")[5]).toHaveTextContent("Combined Transport");
    expect(screen.queryByText("first transport mode")).not.toBeInTheDocument();
  });

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
      expect(api.fetchInternationalCityPage).toHaveBeenCalledWith(id, "", 0);
      await submit(id, cityId);
    });

  it("submits multiple optional cargo items without converting exact quantity to Number", async () => {
    await start();
    await destination("Turkey", "Istanbul");
    await userEvent.click(screen.getByRole("button", { name: /requestForm.cargoOptional/ }));
    await userEvent.click(screen.getByRole("button", { name: /requestForm.addCargoItem/ }));
    await userEvent.click(screen.getByRole("button", { name: /requestForm.addCargoItem/ }));
    const descriptions = screen.getAllByLabelText("requestForm.cargoDescription");
    await userEvent.type(descriptions[0], "Medical devices");
    await userEvent.type(descriptions[1], "Precision cargo");
    await userEvent.type(screen.getAllByLabelText("requestForm.cargoQuantity")[1], "3.250000");
    await userEvent.selectOptions(screen.getAllByLabelText("requestForm.cargoUnit")[1], "kg");

    await userEvent.click(screen.getByRole("button", { name: "shipping.submit" }));
    await userEvent.click(await screen.findByRole("button", { name: "Confirm request" }));
    await waitFor(() => expect(api.submitShipmentRequest).toHaveBeenCalledTimes(1));
    expect(vi.mocked(api.submitShipmentRequest).mock.calls[0][0].cargo_items).toEqual([
      { description: "Medical devices" },
      { description: "Precision cargo", quantity: "3.250000", uom_public_id: "kg" },
    ]);
  }, 15_000);

  it("keeps an empty voluntarily-added item on the form and blocks submission", async () => {
    await start();
    await destination("Turkey", "Istanbul");
    await userEvent.click(screen.getByRole("button", { name: /requestForm.cargoOptional/ }));
    await userEvent.click(screen.getByRole("button", { name: /requestForm.addCargoItem/ }));
    await userEvent.click(screen.getByRole("button", { name: "shipping.submit" }));
    expect(screen.getByText("requestForm.cargoItemEmpty")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm request" })).not.toBeInTheDocument();
    expect(api.submitShipmentRequest).not.toHaveBeenCalled();
  });

  it.each([
    [{ display_name: "کارشناس آزمون" }, "کارشناس آزمون"],
    [null, "customer.assignmentPending"],
  ] as const)("uses committed assignment truth in authenticated confirmation", async (assignedExpert, expected) => {
    vi.mocked(portalApi.submitShipmentRequestForCurrentCustomer).mockResolvedValue({
      customerAuthenticated: true,
      response: {
        id: 1,
        tracking_code: "SR2-AUTHENTICATED",
        message: "Created",
        request_transport_intent: null,
        cargo_items: [],
        request_public_id: "request-public",
        customer_workspace_path: "/customer/requests/request-public",
        assigned_expert: assignedExpert,
      },
    });
    await start();
    await destination("Turkey", "Istanbul");
    await userEvent.click(screen.getByRole("button", { name: "shipping.submit" }));
    await userEvent.click(await screen.findByRole("button", { name: "Confirm request" }));
    expect(await screen.findByText(expected)).toBeInTheDocument();
    expect(screen.getByText("customer.requestAssignee")).toBeInTheDocument();
    expect(screen.getByText("SR2-AUTHENTICATED")).toBeInTheDocument();
  });
});
