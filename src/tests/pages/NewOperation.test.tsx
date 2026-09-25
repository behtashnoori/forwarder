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
    fetchInternationalCityPage: vi.fn(),
    searchOperationalCustomers: vi.fn(),
    searchOperationalProjects: vi.fn(),
    searchAcceptedOperationalQuotes: vi.fn(),
    searchIranDestinations: vi.fn(),
    getShipmentCargoOptions: vi.fn(),
    listLogisticsPoints: vi.fn(),
    listProjectLogisticsPoints: vi.fn(),
    createDirectOperationalShipment: vi.fn(),
    createQuoteOperationalShipment: vi.fn(),
    createShipmentCargoItem: vi.fn(),
  };
});
const province = { id: 1, name: "Tehran", code: "THR" };
const countries = [
  { id: 10, name: "Iran", name_en: "Iran", code: "IR" },
  { id: 20, name: "Germany", name_en: "Germany", code: "DE" },
];
const logisticsPoint = (
  publicId: string,
  name: string,
): api.LogisticsPointView =>
  ({
    public_id: publicId,
    immutable_code: publicId.toUpperCase(),
    fa_name: name,
    en_name: name,
    is_active: true,
    version: 1,
    point_type: {
      public_id: "warehouse-type",
      immutable_code: "WAREHOUSE",
      fa_name: "Warehouse",
      en_name: "Warehouse",
      display_order: 1,
      is_active: true,
      version: 1,
    },
    country: { code: "IR", fa_name: "Iran", en_name: "Iran" },
  });
const preferredPoint = logisticsPoint("preferred-point", "Preferred depot");
const organizationPoint = logisticsPoint("organization-point", "Organization depot");
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.fetchProvinces).mockResolvedValue([province]);
  vi.mocked(api.fetchCountries).mockResolvedValue(countries);
  vi.mocked(api.fetchInternationalCityPage).mockResolvedValue({
    items: [{
      id: 30,
      name: "Hamburg",
      name_en: "Hamburg",
      un_locode: "DEHAM",
      city_type: "city",
      is_major_port: true,
      is_major_airport: false,
    }],
    offset: 0,
    limit: 50,
    has_more: false,
  });
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
        identity: { type: "international_city", id: 66 },
        label: "بندرعباس — international_city — ایران",
        province: null,
        secondary_label: "international_city — ایران",
      },
      {
        identity: { type: "international_city", id: 64 },
        label: "تهران — international_city — ایران",
        province: null,
        secondary_label: "international_city — ایران",
      },
      {
        identity: { type: "international_city", id: 65 },
        label:
          "فرودگاه بین‌المللی امام خمینی تهران — international_city — ایران",
        province: null,
        secondary_label: "international_city — ایران",
      },
      {
        identity: { type: "port", id: 8 },
        label: "Bandar — port — Hormozgan",
        province: { id: 2, name: "Hormozgan" },
        secondary_label: "port — Hormozgan",
      },
    ],
    meta: { count: 1, limit: 50 },
  });
  vi.mocked(api.getShipmentCargoOptions).mockImplementation(async (projectId) => ({
    catalog: [
      {
        public_id: "catalog-active",
        code: "CAT-1",
        name: "Active catalog cargo",
        cargo_type_public_id: "cargo-type-1",
        default_uom_public_id: "uom-ea",
        preferred: Boolean(projectId),
      },
      {
        public_id: "catalog-fallback",
        code: "CAT-2",
        name: "Organization fallback cargo",
        cargo_type_public_id: "cargo-type-1",
        default_uom_public_id: "uom-ea",
        preferred: false,
      },
    ],
    cargo_types: [
      { public_id: "cargo-type-1", code: "GENERAL", name: "General" },
    ],
    uoms: [
      { public_id: "uom-ea", code: "EA", name: "Each", symbol: "ea" },
    ],
  }));
  vi.mocked(api.listLogisticsPoints).mockResolvedValue({
    items: [organizationPoint, preferredPoint],
    page: 1,
    pages: 1,
    total: 2,
  });
  vi.mocked(api.listProjectLogisticsPoints).mockResolvedValue({
    items: [
      {
        public_id: "association-1",
        project_role: "DESTINATION",
        sequence_number: 1,
        is_active: true,
        version: 1,
        logistics_point: preferredPoint,
      },
    ],
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
  it.each(["domestic", "international"] as const)(
    "defaults %s routes to a facility and clears hidden location state when switching modes",
    async (kind) => {
      const user = userEvent.setup();
      vi.mocked(api.getOperationalContext).mockResolvedValue({
        data: { organization_id: 1, permissions: ["operational_shipment.create_direct"] },
      });
      renderPage("/operations/shipments/new?source=direct");
      await screen.findByRole("option", { name: "Canonical Co" });
      if (kind === "international") {
        await user.selectOptions(screen.getByLabelText("Origin route type"), "international");
      }
      const mode = screen.getByLabelText("Origin روش تعیین مکان");
      expect(mode).toHaveValue("facility");
      expect(screen.getAllByRole("option", { name: "فقط موقعیت جغرافیایی" })).toHaveLength(2);
      const facility = await screen.findByLabelText("Origin operational facility");
      await waitFor(() => expect(facility).not.toBeDisabled());
      await user.selectOptions(facility, "preferred-point");
      expect(facility).toHaveValue("preferred-point");
      await user.selectOptions(mode, "geography");
      expect(screen.queryByLabelText("Origin operational facility")).not.toBeInTheDocument();
      const geographic = kind === "domestic" ? "Origin province" : "Origin country";
      await user.selectOptions(screen.getByLabelText(geographic), kind === "domestic" ? "1" : "20");
      await user.selectOptions(mode, "facility");
      expect(screen.queryByLabelText(geographic)).not.toBeInTheDocument();
      expect(screen.getByLabelText("Origin operational facility")).toHaveValue("");
      await user.selectOptions(mode, "geography");
      expect(screen.getByLabelText(geographic)).toHaveValue("");
    },
  );

  it("explains the empty facility list while retaining the geography fallback", async () => {
    vi.mocked(api.getOperationalContext).mockResolvedValue({
      data: { organization_id: 1, permissions: ["operational_shipment.create_direct"] },
    });
    vi.mocked(api.listLogisticsPoints).mockResolvedValue({ items: [], page: 1, pages: 1, total: 0 });
    renderPage("/operations/shipments/new?source=direct");
    expect(await screen.findAllByRole("option", { name: "نقطه عملیاتی فعالی برای این سازمان ثبت نشده است." })).toHaveLength(2);
    expect(screen.getByLabelText("Origin روش تعیین مکان")).toHaveValue("facility");
    expect(screen.getByLabelText("Destination روش تعیین مکان")).toHaveValue("facility");
  });

  it("uses one facility selector for private and adopted organization points", async () => {
    vi.mocked(api.getOperationalContext).mockResolvedValue({
      data: { organization_id: 1, permissions: ["operational_shipment.create_direct"] },
    });
    const adopted = {
      ...preferredPoint,
      global_source: {
        global_point_public_id: "global-point",
        adoption_public_id: "adoption",
        fa_name: "Reference depot",
        en_name: "Reference depot",
        platform_lifecycle_status: "ACTIVE",
        adoption_status: "ACTIVE",
      },
    };
    vi.mocked(api.listLogisticsPoints).mockResolvedValue({
      items: [organizationPoint, adopted], page: 1, pages: 1, total: 2,
    });
    renderPage("/operations/shipments/new?source=direct");
    await waitFor(() => expect(api.listLogisticsPoints).toHaveBeenCalledWith({ active: "true", per_page: 100 }));
    const origin = await screen.findByLabelText("Origin operational facility");
    await waitFor(() => expect(origin).not.toBeDisabled());
    expect(origin).toHaveTextContent("Organization depot");
    expect(origin).toHaveTextContent("Preferred depot");
    expect(screen.getAllByLabelText(/operational facility/)).toHaveLength(2);
  });

  it.each([
    new api.ApiError(403, "FORBIDDEN_OPERATION", "You are not allowed to perform this operation."),
    new Error("Network unavailable"),
  ])("shows a contextual Persian facility error for %s", async (failure) => {
    vi.mocked(api.getOperationalContext).mockResolvedValue({
      data: { organization_id: 1, permissions: ["operational_shipment.create_direct"] },
    });
    vi.mocked(api.listLogisticsPoints).mockRejectedValue(failure);
    renderPage("/operations/shipments/new?source=direct");
    expect(await screen.findAllByText("امکان دریافت نقاط عملیاتی وجود ندارد.")).toHaveLength(2);
    expect(screen.getAllByRole("option", { name: "دریافت نقاط عملیاتی ناموفق بود." })).toHaveLength(2);
    expect(screen.queryByText("You do not have permission to create this operation.")).not.toBeInTheDocument();
    expect(screen.queryByText("Network unavailable")).not.toBeInTheDocument();
  });

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
    await screen.findByRole("option", { name: "Canonical Co" }, { timeout: 5000 });
    await user.selectOptions(screen.getByLabelText("Customer"), "7");
    await waitFor(() =>
      expect(api.searchOperationalProjects).toHaveBeenCalledWith("", 7),
    );
    await screen.findByRole("option", { name: /P-1/ });
    await user.selectOptions(
      screen.getByLabelText("Project (optional)"),
      "project-public",
    );
    await user.selectOptions(screen.getByLabelText("Origin روش تعیین مکان"), "geography");
    await user.selectOptions(screen.getByLabelText("Destination روش تعیین مکان"), "geography");
    fireEvent.change(screen.getByLabelText("Origin province"), {
      target: { value: "1" },
    });
    await user.selectOptions(
      screen.getByLabelText("Destination"),
      "international_city:66",
    );
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
      destination: { source_type: "international_city", source_id: 66 },
    });
    expect(submit).toBeDisabled();
  });
  it("ranks project facilities but keeps organization points selectable and submits typed facility identities", async () => {
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
    await screen.findByRole("option", { name: /P-1/ });
    await user.selectOptions(
      screen.getByLabelText("Project (optional)"),
      "project-public",
    );
    await waitFor(() =>
      expect(api.getShipmentCargoOptions).toHaveBeenCalledWith(
        "project-public",
        "",
      ),
    );
    expect(screen.getByRole("group", { name: "Preferred for this project" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Organization fallback cargo/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Manual cargo/ })).toBeInTheDocument();
    await waitFor(() =>
      expect(api.listProjectLogisticsPoints).toHaveBeenCalledWith(
        "project-public",
      ),
    );

    const origin = screen.getByLabelText(
      "Origin operational facility",
    ) as HTMLSelectElement;
    const destination = screen.getByLabelText(
      "Destination operational facility",
    ) as HTMLSelectElement;
    await waitFor(() => expect(origin.options[1]).toHaveValue("preferred-point"));
    expect(origin).toHaveTextContent("Organization depot");
    await user.selectOptions(origin, "preferred-point");
    await user.selectOptions(destination, "organization-point");
    expect(origin).toHaveValue("preferred-point");
    expect(destination).toHaveValue("organization-point");
    expect(screen.getAllByText(/موقعیت جغرافیایی نقطه عملیاتی از داده مرجع سازمان/)).toHaveLength(2);

    fireEvent.change(screen.getByLabelText("Planned departure"), {
      target: { value: "2026-08-10T10:00" },
    });
    fireEvent.change(screen.getByLabelText("Planned arrival"), {
      target: { value: "2026-08-10T11:00" },
    });
    await user.click(screen.getByRole("button", { name: "Create operation" }));
    await waitFor(() =>
      expect(api.createDirectOperationalShipment).toHaveBeenCalledWith(
        expect.objectContaining({
          origin: {
            source_type: "logistics_point",
            source_id: "preferred-point",
          },
          destination: {
            source_type: "logistics_point",
            source_id: "organization-point",
          },
        }),
        expect.any(String),
      ),
    );
  });
  it("requires and reviews an Iran origin province", async () => {
    vi.mocked(api.getOperationalContext).mockResolvedValue({
      data: {
        organization_id: 1,
        permissions: ["operational_shipment.create_direct"],
      },
    });
    renderPage("/operations/shipments/new?source=direct");
    fireEvent.change(await screen.findByLabelText("Origin روش تعیین مکان"), { target: { value: "geography" } });
    fireEvent.change(await screen.findByLabelText("Origin route type"), {
      target: { value: "international" },
    });
    fireEvent.change(screen.getByLabelText("Origin روش تعیین مکان"), { target: { value: "geography" } });
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
    fireEvent.change(await screen.findByLabelText("Destination روش تعیین مکان"), { target: { value: "geography" } });
    fireEvent.change(await screen.findByLabelText("Destination route type"), {
      target: { value: "international" },
    });
    fireEvent.change(screen.getByLabelText("Destination روش تعیین مکان"), { target: { value: "geography" } });
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
  it("uses the governed Iran selector for a domestic Tehran to Bandar Abbas operation", async () => {
    const user = userEvent.setup();
    vi.mocked(api.getOperationalContext).mockResolvedValue({
      data: {
        organization_id: 1,
        permissions: ["operational_shipment.create_direct"],
      },
    });
    vi.mocked(api.createDirectOperationalShipment).mockResolvedValue({
      data: { public_id: "11111111-1111-4111-8111-111111111111" },
      meta: { created: true, replayed: false },
    } as never);
    renderPage("/operations/shipments/new?source=direct");
    await screen.findByRole("option", { name: "Canonical Co" });
    expect(api.searchIranDestinations).toHaveBeenCalledWith();
    await user.selectOptions(screen.getByLabelText("Origin روش تعیین مکان"), "geography");
    await user.selectOptions(screen.getByLabelText("Destination روش تعیین مکان"), "geography");
    await user.selectOptions(screen.getByLabelText("Customer"), "7");
    await user.selectOptions(screen.getByLabelText("Origin province"), "1");
    expect(screen.getByLabelText("Destination")).toHaveTextContent(
      "تهران — international_city — ایران",
    );
    expect(screen.getByLabelText("Destination")).toHaveTextContent(
      "فرودگاه بین‌المللی امام خمینی تهران",
    );
    await user.selectOptions(
      screen.getByLabelText("Destination"),
      "international_city:66",
    );
    fireEvent.change(screen.getByLabelText("Planned departure"), {
      target: { value: "2026-08-10T10:00" },
    });
    fireEvent.change(screen.getByLabelText("Planned arrival"), {
      target: { value: "2026-08-10T11:00" },
    });
    await user.click(screen.getByRole("button", { name: "Create operation" }));
    await waitFor(() =>
      expect(api.createDirectOperationalShipment).toHaveBeenCalledWith(
        expect.objectContaining({
          origin: { source_type: "province", source_id: 1 },
          destination: { source_type: "international_city", source_id: 66 },
        }),
        expect.any(String),
      ),
    );
  });
  it.each(["direct", "accepted_quote"] as const)(
    "persists selected active catalog cargo before leaving the %s creation flow",
    async (source) => {
      const user = userEvent.setup();
      vi.mocked(api.getOperationalContext).mockResolvedValue({
        data: {
          organization_id: 1,
          permissions: [
            source === "direct"
              ? "operational_shipment.create_direct"
              : "operational_shipment.create_from_quote",
          ],
        },
      });
      const shipment = {
        data: { public_id: "11111111-1111-4111-8111-111111111111" },
        meta: { created: true, replayed: false },
      };
      vi.mocked(api.createDirectOperationalShipment).mockResolvedValue(
        shipment as never,
      );
      vi.mocked(api.createQuoteOperationalShipment).mockResolvedValue(
        shipment as never,
      );
      vi.mocked(api.createShipmentCargoItem).mockResolvedValue({ item: {} } as never);
      renderPage(
        source === "direct"
          ? "/operations/shipments/new?source=direct"
          : "/operations/shipments/new?source=accepted_quote&accepted_quote_id=9&request_ref=REQ-9",
      );
      if (source === "direct") {
        await screen.findByRole("option", { name: "Canonical Co" });
        await user.selectOptions(screen.getByLabelText("Customer"), "7");
      } else {
        await waitFor(() =>
          expect(screen.getByLabelText("Accepted quote")).toHaveValue("9"),
        );
      }
      fireEvent.change(screen.getByLabelText("Origin روش تعیین مکان"), { target: { value: "geography" } });
      fireEvent.change(screen.getByLabelText("Destination روش تعیین مکان"), { target: { value: "geography" } });
      fireEvent.change(screen.getByLabelText("Origin province"), {
        target: { value: "1" },
      });
      await user.selectOptions(
        screen.getByLabelText("Destination"),
        "international_city:66",
      );
      fireEvent.change(screen.getByLabelText("Planned departure"), {
        target: { value: "2026-08-10T10:00" },
      });
      fireEvent.change(screen.getByLabelText("Planned arrival"), {
        target: { value: "2026-08-10T11:00" },
      });
      await user.selectOptions(
        await screen.findByLabelText("Catalog item"),
        "catalog-active",
      );
      await user.type(screen.getByLabelText("Cargo quantity"), "4.5");
      expect(screen.getByLabelText("Unit of measure")).toHaveValue("uom-ea");
      await user.click(screen.getByRole("button", { name: "Create operation" }));
      await waitFor(() =>
        expect(api.createShipmentCargoItem).toHaveBeenCalledWith(
          "11111111-1111-4111-8111-111111111111",
          {
            line_number: 1,
            catalog_item_public_id: "catalog-active",
            cargo_type_public_id: "cargo-type-1",
            quantity: "4.5",
            planned_quantity: "4.5",
            uom_public_id: "uom-ea",
            ...(source === "direct" ? { cargo_owner_customer_id: 7 } : {}),
          },
        ),
      );
      expect(await screen.findByText("created detail")).toBeInTheDocument();
    },
  );
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
