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

const latestQuote = {
  id: 91,
  amount: 1234567,
  currency: "EUR",
  note: "EUR quote",
  valid_until: "2026-09-30",
  created_at: "2026-09-20T00:00:00Z",
  customer_response: null,
  responded_at: null,
};

describe("EUR quote presentation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.localStorage.setItem("forwarder.language", "en");
    window.localStorage.setItem("customer_panel_id", "7");
    vi.mocked(api.fetchCustomerWorkflow).mockResolvedValue({
      id: 12,
      request_id: 12,
      customer_id: 7,
      tracking_code: "TRACK-12",
      status: "waiting_for_customer",
      shipping_type: "domestic",
      created_at: "2026-09-20T00:00:00Z",
      assigned_expert: null,
      cargo_items: [],
      legacy_cargo: { description: null, weight: null, volume: null, value: null, special_instructions: null },
      workflow_steps: [],
      workflow_steps_simple: [],
      total_points_earned: 0,
      completed_steps: 0,
      total_steps: 0,
      latest_quote: latestQuote,
    });
    vi.mocked(api.fetchExpertRequestDetail).mockResolvedValue({
      id: 12,
      public_id: "request-12",
      tracking_number: "TRACK-12",
      status: "waiting_for_customer",
      priority: "normal",
      created_at: "2026-09-20T00:00:00Z",
      sla_status: "on_time",
      customer: { phone: "09120000000", full_name: "Customer" },
      route: { shipping_type: "domestic", origin: { province: null, county: null, city: null }, destination: { province: null, county: null, city: null } },
      cargo: {},
      dates: {},
      timeline: [],
      messages: [],
      has_unread: false,
      latest_quote: latestQuote,
    });
    vi.mocked(api.listOperationalShipments).mockResolvedValue({
      data: [],
      meta: { page: 1, has_more: false },
    });
  });

  afterEach(cleanup);

  it("uses the shared B2 money formatter for Customer and Expert views", async () => {
    render(
      <I18nProvider>
        <MemoryRouter initialEntries={["/customer/requests/12"]}>
          <Routes><Route path="/customer/requests/:requestId" element={<CustomerRequestDetail />} /></Routes>
        </MemoryRouter>
      </I18nProvider>,
    );
    expect(await screen.findByText("1,234,567 EUR")).toBeInTheDocument();
    expect(document.body).toHaveTextContent("Sep 30, 2026 (Mehr 8, 1405 AP)");

    cleanup();
    render(
      <I18nProvider>
        <MemoryRouter initialEntries={["/expert/requests/12"]}>
          <Routes><Route path="/expert/requests/:id" element={<RequestDetail />} /></Routes>
        </MemoryRouter>
      </I18nProvider>,
    );
    expect(await screen.findByText("1,234,567 EUR")).toBeInTheDocument();
    expect(document.body).toHaveTextContent("Sep 30, 2026 (Mehr 8, 1405 AP)");
    expect(screen.queryByText(/USD|IRR/)).not.toBeInTheDocument();
  });
});
