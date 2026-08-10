import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import NewOperation from "@/pages/NewOperation";
import * as api from "@/lib/api";
const labels: Record<string, string> = {
  "operations.newOperation": "New Operation",
  "operations.source.direct": "Direct operation",
  "operations.source.directHelp": "No commercial request or quote",
  "operations.source.quote": "From accepted quote",
  "operations.source.quoteHelp": "Choose a governed eligible quote",
  "operations.noCreatePermission": "No operation creation permission.",
  "operations.changeSource": "Change source",
  "operations.customerProject": "Canonical customer and optional project",
  "operations.customer": "Customer",
  "operations.projectOptional": "Project (optional)",
  "operations.eligibleQuote": "Eligible accepted quote",
  "operations.acceptedQuote": "Accepted quote",
  "operations.routeSchedule": "Route and schedule",
  "operations.origin": "Origin",
  "operations.destination": "Destination",
  "operations.routeType": "route type",
  "operations.domesticIran": "Domestic Iran",
  "operations.international": "International",
  "operations.country": "country",
  "operations.province": "province",
  "operations.internationalCity": "international city",
  "operations.iranOriginProvince": "Origin Iran province",
  "operations.iranDestination": "Destination",
  "operations.derivedProvince": "Derived province",
  "operations.transportMode": "Transport mode",
  "operations.plannedDeparture": "Planned departure",
  "operations.plannedArrival": "Planned arrival",
  "operations.review": "Review",
  "operations.source": "Source",
  "operations.notApplicable": "Not applicable",
  "operations.required": "required",
  "operations.search": "Search",
  "operations.select": "Select…",
  "operations.noResults": "No results",
  "operations.loading": "Loading…",
  "operations.creating": "Creating…",
  "operations.cancel": "Cancel",
  "operations.create": "Create operation",
  "operations.validation.customer": "Select a canonical customer.",
  "operations.validation.quote": "Select an eligible accepted quote.",
  "operations.validation.origin": "Select a valid origin.",
  "operations.validation.destination": "Select a valid destination.",
  "operations.validation.departure": "Enter the planned departure.",
  "operations.validation.arrival": "Enter the planned arrival.",
  "operations.validation.timeline": "Planned arrival must be after departure.",
  "operations.validation.iranProvince": "Select the Iran origin province.",
  "operations.linkedQuoteUnavailable":
    "The linked quote is no longer eligible.",
};
vi.mock("@/i18n", () => ({
  useI18n: () => ({ direction: "ltr", t: (key: string) => labels[key] || key }),
}));
vi.mock("@/components/OperationsNav", () => ({ default: () => null }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getOperationalContext: vi.fn(),
    fetchProvinces: vi.fn(),
    fetchCountries: vi.fn(),
    fetchInternationalCities: vi.fn(),
    searchOperationalCustomers: vi.fn(),
    searchOperationalProjects: vi.fn(),
    searchAcceptedOperationalQuotes: vi.fn(),
    searchIranDestinations: vi.fn(),
    createDirectOperationalShipment: vi.fn(),
    createQuoteOperationalShipment: vi.fn(),
  };
});
const province = { id: 1, name: "Tehran", code: "THR" };
const countries = [
  { id: 10, name: "Iran", name_en: "Iran", code: "IR" },
  { id: 20, name: "Germany", name_en: "Germany", code: "DE" },
];
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.fetchProvinces).mockResolvedValue([province]);
  vi.mocked(api.fetchCountries).mockResolvedValue(countries);
  vi.mocked(api.fetchInternationalCities).mockResolvedValue([
    {
      id: 30,
      name: "Hamburg",
      name_en: "Hamburg",
      city_type: "city",
      is_major_port: true,
      is_major_airport: false,
    },
  ]);
  vi.mocked(api.searchOperationalCustomers).mockResolvedValue({
    items: [{ id: 7, label: "Canonical Co" }],
    meta: { count: 1, limit: 25 },
  });
  vi.mocked(api.searchOperationalProjects).mockResolvedValue({
    items: [
      {
        public_id: "project-public",
        label: "P-1",
        project_code: "P-1",
        primary_customer_id: 7,
        lifecycle_status: "in_progress",
      },
    ],
    meta: { count: 1, limit: 25 },
  });
  vi.mocked(api.searchAcceptedOperationalQuotes).mockResolvedValue({
    items: [
      {
        id: 9,
        request_public_id: "REQ-9",
        customer_label: "Canonical Co",
        route_label: "A → B",
        quote_label: "100 IRR",
        accepted_at: null,
      },
    ],
    meta: { count: 1, limit: 100 },
  });
  vi.mocked(api.searchIranDestinations).mockResolvedValue({
    data: [
      {
        identity: { type: "port", id: 8 },
        label: "Bandar — port — Hormozgan",
        province: { id: 2, name: "Hormozgan" },
        secondary_label: "port — Hormozgan",
      },
    ],
    meta: { count: 1, limit: 50 },
  });
});
const renderPage = (url = "/operations/shipments/new") =>
  render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/operations/shipments/new" element={<NewOperation />} />
        <Route
          path="/operations/shipments/:id"
          element={<p>created detail</p>}
        />
      </Routes>
    </MemoryRouter>,
  );
describe("Slice 5 governed creation", () => {
  it.each([
    [["operational_shipment.create_direct"], true, false],
    [["operational_shipment.create_from_quote"], false, true],
    [["operational_shipment.create"], false, true],
    [
      [
        "operational_shipment.create_direct",
        "operational_shipment.create_from_quote",
      ],
      true,
      true,
    ],
    [[], false, false],
  ])("renders permission matrix", async (permissions, direct, quote) => {
    vi.mocked(api.getOperationalContext).mockResolvedValue({
      data: { organization_id: 1, permissions },
    });
    renderPage();
    await waitFor(() => expect(api.getOperationalContext).toHaveBeenCalled());
    expect(!!screen.queryByText("Direct operation")).toBe(direct);
    expect(!!screen.queryByText("From accepted quote")).toBe(quote);
  });
  it("preselects the governed quote from request deep link", async () => {
    vi.mocked(api.getOperationalContext).mockResolvedValue({
      data: {
        organization_id: 1,
        permissions: ["operational_shipment.create_from_quote"],
      },
    });
    renderPage(
      "/operations/shipments/new?source=accepted_quote&accepted_quote_id=9&request_ref=REQ-9",
    );
    await waitFor(() =>
      expect(api.searchAcceptedOperationalQuotes).toHaveBeenCalledWith(
        "REQ-9",
        100,
      ),
    );
    expect(await screen.findByLabelText("Accepted quote")).toHaveValue("9");
  });
  it("creates direct with canonical customer, optional project, canonical route and one in-flight key", async () => {
    const user = userEvent.setup();
    vi.mocked(api.getOperationalContext).mockResolvedValue({
      data: {
        organization_id: 1,
        permissions: ["operational_shipment.create_direct"],
      },
    });
    vi.mocked(api.createDirectOperationalShipment).mockReturnValue(
      new Promise(() => {}),
    );
    renderPage("/operations/shipments/new?source=direct");
    await screen.findByRole("option", { name: "Canonical Co" });
    await user.selectOptions(screen.getByLabelText("Customer"), "7");
    await waitFor(() =>
      expect(api.searchOperationalProjects).toHaveBeenCalledWith("", 7),
    );
    await screen.findByRole("option", { name: /P-1/ });
    await user.selectOptions(
      screen.getByLabelText("Project (optional)"),
      "project-public",
    );
    fireEvent.change(screen.getByLabelText("Origin province"), {
      target: { value: "1" },
    });
    fireEvent.change(screen.getByLabelText("Destination province"), {
      target: { value: "1" },
    });
    fireEvent.change(screen.getByLabelText("Planned departure"), {
      target: { value: "2026-08-10T10:00" },
    });
    fireEvent.change(screen.getByLabelText("Planned arrival"), {
      target: { value: "2026-08-10T11:00" },
    });
    const submit = screen.getByRole("button", { name: "Create operation" });
    fireEvent.click(submit);
    fireEvent.click(submit);
    await waitFor(() =>
      expect(api.createDirectOperationalShipment).toHaveBeenCalledTimes(1),
    );
    expect(
      vi.mocked(api.createDirectOperationalShipment).mock.calls[0][0],
    ).toMatchObject({
      source_type: "direct",
      customer_id: 7,
      project_public_id: "project-public",
      origin: { source_type: "province", source_id: 1 },
      destination: { source_type: "province", source_id: 1 },
    });
    expect(submit).toBeDisabled();
  });
  it("requires and reviews an Iran origin province", async () => {
    vi.mocked(api.getOperationalContext).mockResolvedValue({
      data: {
        organization_id: 1,
        permissions: ["operational_shipment.create_direct"],
      },
    });
    renderPage("/operations/shipments/new?source=direct");
    fireEvent.change(await screen.findByLabelText("Origin route type"), {
      target: { value: "international" },
    });
    fireEvent.change(screen.getByLabelText("Origin country"), {
      target: { value: "10" },
    });
    expect(await screen.findByLabelText("Origin Iran province")).toBeRequired();
    fireEvent.change(screen.getByLabelText("Origin Iran province"), {
      target: { value: "1" },
    });
    expect(screen.getAllByText(/Tehran/).length).toBeGreaterThan(1);
  });
  it("uses one typed Iran destination selector with derived province", async () => {
    vi.mocked(api.getOperationalContext).mockResolvedValue({
      data: {
        organization_id: 1,
        permissions: ["operational_shipment.create_direct"],
      },
    });
    renderPage("/operations/shipments/new?source=direct");
    fireEvent.change(await screen.findByLabelText("Destination route type"), {
      target: { value: "international" },
    });
    fireEvent.change(screen.getByLabelText("Destination country"), {
      target: { value: "10" },
    });
    expect(await screen.findByLabelText("Destination")).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Destination province"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: /Hormozgan/ }),
    ).toBeInTheDocument();
  });
  it("associates required errors and focuses the first invalid control", async () => {
    vi.mocked(api.getOperationalContext).mockResolvedValue({
      data: {
        organization_id: 1,
        permissions: ["operational_shipment.create_direct"],
      },
    });
    renderPage("/operations/shipments/new?source=direct");
    await screen.findByRole("option", { name: "Canonical Co" });
    fireEvent.click(screen.getByRole("button", { name: "Create operation" }));
    const customer = screen.getByLabelText("Customer");
    await waitFor(() => expect(customer).toHaveFocus());
    expect(customer).toHaveAttribute("aria-invalid", "true");
    expect(customer).toHaveAttribute("aria-describedby", "customer-error");
    expect(screen.getByText("⚠ Select a canonical customer.")).toHaveAttribute(
      "role",
      "alert",
    );
  });
});
