import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "@/i18n";
import CustomerRequestDetail from "@/pages/CustomerRequestDetail";
import RequestDetail from "@/pages/RequestDetail";
import * as api from "@/lib/api";

const toast = vi.hoisted(() => vi.fn());
vi.mock("@/hooks/use-toast", () => ({ useToast: () => ({ toast }) }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchCustomerWorkflow: vi.fn(),
    fetchExpertRequestDetail: vi.fn(),
    listOperationalShipments: vi.fn(),
  };
});

const storedTransport = {
  shipping_type: "domestic",
  transport_method: "road",
  domestic_transport_method: "Rail Transport",
  international_transport_method: "Sea Freight",
  transport_method_preference: "customer_choice",
};

describe("request transport role consistency", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.localStorage.setItem("forwarder.language", "fa");
    window.localStorage.setItem("customer_panel_id", "7");

    vi.mocked(api.fetchCustomerWorkflow).mockResolvedValue({
      id: 12,
      request_id: 12,
      customer_id: 7,
      tracking_code: "TRACK-12",
      ...storedTransport,
      status: "new",
      created_at: "2026-09-20T00:00:00Z",
      assigned_expert: null,
      workflow_steps: [],
      workflow_steps_simple: [],
      total_points_earned: 0,
      completed_steps: 0,
      total_steps: 0,
      latest_quote: null,
    });
    vi.mocked(api.fetchExpertRequestDetail).mockResolvedValue({
      id: 12,
      public_id: "request-12",
      tracking_number: "TRACK-12",
      status: "new",
      priority: "normal",
      created_at: "2026-09-20T00:00:00Z",
      sla_status: "on_time",
      customer: { phone: "09120000000", full_name: "مشتری" },
      route: { shipping_type: storedTransport.shipping_type, origin: {}, destination: {} },
      transport_method: storedTransport.transport_method,
      domestic_transport_method: storedTransport.domestic_transport_method,
      international_transport_method: storedTransport.international_transport_method,
      transport_method_preference: storedTransport.transport_method_preference,
      dates: {},
      timeline: [],
      messages: [],
      has_unread: false,
      latest_quote: null,
    });
    vi.mocked(api.listOperationalShipments).mockResolvedValue({ data: [], pagination: { page: 1, per_page: 100, total: 0, pages: 0 } });
  });

  afterEach(cleanup);

  it("shows the same localized stored request fact to Customer and Expert", async () => {
    render(
      <I18nProvider>
        <MemoryRouter initialEntries={["/customer/requests/12"]}>
          <Routes><Route path="/customer/requests/:requestId" element={<CustomerRequestDetail />} /></Routes>
        </MemoryRouter>
      </I18nProvider>,
    );
    const customerLabel = (await screen.findByText("حمل ریلی")).textContent;
    expect(screen.queryByText("Rail Transport")).not.toBeInTheDocument();

    cleanup();
    render(
      <I18nProvider>
        <MemoryRouter initialEntries={["/expert/requests/12"]}>
          <Routes><Route path="/expert/requests/:id" element={<RequestDetail />} /></Routes>
        </MemoryRouter>
      </I18nProvider>,
    );
    const expertLabel = (await screen.findByText("حمل ریلی")).textContent;

    expect(expertLabel).toBe(customerLabel);
    expect(screen.queryByText("Rail Transport")).not.toBeInTheDocument();
    expect(screen.queryByText("جاده‌ای")).not.toBeInTheDocument();
  });
});
