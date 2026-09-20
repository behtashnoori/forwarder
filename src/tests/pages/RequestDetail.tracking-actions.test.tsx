import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "@/i18n";
import RequestDetail from "@/pages/RequestDetail";
import * as api from "@/lib/api";

const toast = vi.hoisted(() => vi.fn());
vi.mock("@/hooks/use-toast", () => ({ useToast: () => ({ toast }) }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchExpertRequestDetail: vi.fn(),
    listOperationalShipments: vi.fn(),
    fetchTrackingManagement: vi.fn(),
    fetchTrackingLogisticsPoints: vi.fn(),
    fetchTrackingLocations: vi.fn(),
    updateTrackingUnitMetadata: vi.fn(),
    addTrackingUnitUpdate: vi.fn(),
  };
});

const request = {
  id: 12,
  public_id: "request-12",
  tracking_number: "TRACK-12",
  status: "accepted",
  priority: "normal",
  created_at: "2026-09-20T00:00:00Z",
  sla_status: "on_time" as const,
  customer: { phone: "09120000000", full_name: "مشتری" },
  route: { shipping_type: "domestic", origin: { province: null, county: null, city: null }, destination: { province: null, county: null, city: null } },
  cargo: {},
  dates: {},
  timeline: [],
  messages: [],
  has_unread: false,
  latest_quote: null,
};

const tracking = (units: api.InternalTransportUnitTracking[]): api.TrackingManagementData => ({
  eligible: true,
  request_status: "accepted",
  tracking_code: "TRACK-12",
  enabled: true,
  unit_tracking: {
    enabled: true,
    enabled_at: "2026-09-20T01:00:00Z",
    aggregate_status: "in_progress",
    summary: {
      total_units: units.length,
      without_updates: 0,
      not_started: 0,
      loading: 0,
      in_transit: units.length,
      delayed: 0,
      arrived: 0,
      delivered: 0,
      cancelled: 0,
    },
    last_updated_at: "2026-09-20T02:00:00Z",
    units,
  },
});

const mappedUnit: api.InternalTransportUnitTracking = {
  id: 41,
  unit_code: "EXEC-41",
  unit_type: "truck",
  display_name: "واحد اجرایی متصل",
  vehicle_reference: "IR-41",
  is_active: true,
  latest_status: "in_transit",
  latest_location: "تهران",
  latest_event_at: "2026-09-20T02:00:00Z",
  allocated_cargo: [],
};

async function openTrackingTab() {
  const user = userEvent.setup();
  render(
    <I18nProvider>
      <MemoryRouter initialEntries={["/expert/requests/12"]}>
        <Routes><Route path="/expert/requests/:id" element={<RequestDetail />} /></Routes>
      </MemoryRouter>
    </I18nProvider>,
  );
  await user.click(await screen.findByRole("tab", { name: "مدیریت رهگیری محموله" }));
  await waitFor(() => expect(api.fetchTrackingManagement).toHaveBeenCalledWith("request-12"));
}

beforeAll(() => {
  HTMLElement.prototype.scrollIntoView = vi.fn();
  HTMLElement.prototype.hasPointerCapture = () => false;
  HTMLElement.prototype.setPointerCapture = vi.fn();
  HTMLElement.prototype.releasePointerCapture = vi.fn();
});

describe("retired tracking action reachability", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.localStorage.setItem("forwarder.language", "fa");
    vi.mocked(api.fetchExpertRequestDetail).mockResolvedValue(request);
    vi.mocked(api.listOperationalShipments).mockResolvedValue({
      data: [],
      meta: { page: 1, has_more: false },
    });
    vi.mocked(api.fetchTrackingLogisticsPoints).mockResolvedValue({ items: [], limit: 20, offset: 0, has_more: false });
    vi.mocked(api.fetchTrackingLocations).mockResolvedValue({ items: [] });
    vi.mocked(api.fetchTrackingManagement).mockResolvedValue(tracking([mappedUnit]));
    vi.mocked(api.addTrackingUnitUpdate).mockResolvedValue(tracking([mappedUnit]));
  });

  afterEach(cleanup);

  it("removes the retired add-unit form while keeping mapped update actions and unit reads", async () => {
    await openTrackingTab();

    expect(await screen.findByText("واحد اجرایی متصل")).toBeInTheDocument();
    expect(screen.getByText("ویرایش بخش قابل رهگیری")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "ثبت به‌روزرسانی" })).toBeInTheDocument();
    expect(screen.queryByText("افزودن بخش قابل رهگیری")).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText("کد بخش")).not.toBeInTheDocument();
  });

  it("uses a canonical-workflow empty state without restoring a responsive or alternate add action", async () => {
    vi.mocked(api.fetchTrackingManagement).mockResolvedValue(tracking([]));
    await openTrackingTab();

    expect(await screen.findByText(/فقط از مسیر بخش‌های اجرایی پروژه/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "افزودن بخش قابل رهگیری" })).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText("کد بخش")).not.toBeInTheDocument();
  });

  it("selects a same-tenant private point and submits its governed identity", async () => {
    vi.mocked(api.fetchTrackingLogisticsPoints).mockResolvedValue({
      items: [{
        public_id: "private-point-1",
        fa_name: "انبار خصوصی",
        en_name: "Private warehouse",
        immutable_code: "PRIVATE-WH",
        selector_kind: "organization_private",
        type: { code: "WAREHOUSE", label: "انبار" },
        country: { code: "IR", label: "ایران" },
        province: "تهران",
        city: "تهران",
      }],
      limit: 20,
      offset: 0,
      has_more: false,
    });
    await openTrackingTab();
    const user = userEvent.setup();
    const selector = await screen.findByLabelText("انتخاب مکان رخداد");
    await waitFor(() => expect(selector).not.toBeDisabled());
    await user.selectOptions(selector, "private:private-point-1");
    const unitSelector = screen.getAllByRole("combobox")[1];
    await user.click(unitSelector);
    await user.click(await screen.findByRole("option", { name: "واحد اجرایی متصل" }));
    await user.click(screen.getByRole("button", { name: "ثبت به‌روزرسانی" }));
    await waitFor(() => expect(api.addTrackingUnitUpdate).toHaveBeenCalledWith(
      "request-12",
      41,
      expect.objectContaining({
        logistics_point_public_id: "private-point-1",
        location_reference_id: undefined,
        location_text: undefined,
      }),
    ));
  });
});
