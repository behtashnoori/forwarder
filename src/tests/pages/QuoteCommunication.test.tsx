import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
    submitQuoteResponse: vi.fn(),
    fetchExpertRequestDetail: vi.fn(),
    listOperationalShipments: vi.fn(),
  };
});

const q1 = {
  public_id: "11111111-1111-4111-8111-111111111111",
  amount: 1_250_000,
  currency: "EUR",
  note: "پیشنهاد رسمی اول",
  valid_until: "2026-10-20",
  created_at: "2026-09-20T09:00:00Z",
  customer_response: null,
  customer_response_message: null,
  responded_at: null,
} as const;

const customerWorkflow = {
  id: 42,
  request_id: 42,
  customer_id: 7,
  tracking_code: "QC-BROWSER-42",
  status: "waiting_for_customer",
  shipping_type: "domestic",
  created_at: "2026-09-20T08:00:00Z",
  assigned_expert: null,
  cargo_items: [],
  legacy_cargo: {
    description: null,
    weight: null,
    volume: null,
    value: null,
    special_instructions: null,
  },
  workflow_steps: [],
  workflow_steps_simple: [],
  total_points_earned: 0,
  completed_steps: 0,
  total_steps: 0,
  latest_quote: q1,
  quote_history: [q1],
};

const expertRequest = {
  id: 42,
  public_id: "request-42",
  tracking_number: "QC-BROWSER-42",
  status: "waiting_for_customer",
  priority: "normal",
  created_at: "2026-09-20T08:00:00Z",
  sla_status: "on_time" as const,
  customer: { phone: "09120000042", full_name: "مشتری آزمون" },
  route: {
    shipping_type: "domestic",
    origin: { province: null, county: null, city: null },
    destination: { province: null, county: null, city: null },
  },
  cargo: {},
  dates: {},
  timeline: [],
  messages: [],
  has_unread: false,
  latest_quote: {
    ...q1,
    id: 102,
    public_id: "22222222-2222-4222-8222-222222222222",
    amount: 1_500_000,
    currency: "USD",
    created_at: "2026-09-21T11:00:00Z",
    customer_response: "discussion" as const,
    customer_response_message: "شرایط پرداخت نیاز به هماهنگی دارد",
    responded_at: "2026-09-21T10:30:00Z",
  },
  quote_history: [
    {
      ...q1,
      id: 102,
      public_id: "22222222-2222-4222-8222-222222222222",
      amount: 1_500_000,
      currency: "USD",
      created_at: "2026-09-21T11:00:00Z",
      customer_response: "discussion" as const,
      customer_response_message: "شرایط پرداخت نیاز به هماهنگی دارد",
      responded_at: "2026-09-21T10:30:00Z",
    },
    {
      ...q1,
      id: 101,
      customer_response: "discussion" as const,
      customer_response_message: "درخواست بازنگری نسخه اول",
      responded_at: "2026-09-20T10:00:00Z",
    },
  ],
};

function renderCustomer() {
  return render(
    <I18nProvider>
      <MemoryRouter initialEntries={["/customer/requests/42"]}>
        <Routes>
          <Route path="/customer/requests/:requestId" element={<CustomerRequestDetail />} />
        </Routes>
      </MemoryRouter>
    </I18nProvider>,
  );
}

describe("Simple Quote Communication surfaces", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.localStorage.setItem("forwarder.language", "fa");
    window.localStorage.setItem("customer_panel_id", "7");
    vi.mocked(api.fetchCustomerWorkflow).mockResolvedValue(customerWorkflow);
    vi.mocked(api.submitQuoteResponse).mockResolvedValue({
      code: "QUOTE_RESPONSE_RECORDED",
      latest_quote: q1,
    });
    vi.mocked(api.fetchExpertRequestDetail).mockResolvedValue(expertRequest);
    vi.mocked(api.listOperationalShipments).mockResolvedValue({
      data: [],
      meta: { page: 1, has_more: false },
    });
  });

  afterEach(cleanup);

  it("offers exactly three clear actions and sends only a bounded discussion message", async () => {
    const user = userEvent.setup();
    renderCustomer();

    expect(await screen.findByRole("button", { name: "تأیید پیشنهاد" })).toBeVisible();
    expect(screen.getByRole("button", { name: "نیاز به گفتگو" })).toBeVisible();
    expect(screen.getByRole("button", { name: "رد پیشنهاد" })).toBeVisible();
    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "نیاز به گفتگو" }));
    const message = screen.getByLabelText("پیام کوتاه برای کارشناس");
    expect(message).toHaveAttribute("maxlength", "500");
    expect(screen.getByText("این پیام مبلغ یا ارز پیشنهاد رسمی را تغییر نمی‌دهد.")).toBeVisible();
    expect(screen.getByRole("button", { name: "ارسال درخواست گفتگو" })).toBeDisabled();

    await user.type(message, "لطفاً درباره زمان پرداخت صحبت کنیم");
    await user.click(screen.getByRole("button", { name: "ارسال درخواست گفتگو" }));
    await waitFor(() =>
      expect(api.submitQuoteResponse).toHaveBeenCalledWith(
        q1.public_id,
        "QC-BROWSER-42",
        7,
        "discussion",
        "لطفاً درباره زمان پرداخت صحبت کنیم",
      ),
    );
  });

  it("renders persisted discussion safely, with dual-calendar time and no response actions", async () => {
    vi.mocked(api.fetchCustomerWorkflow).mockResolvedValue({
      ...customerWorkflow,
      latest_quote: {
        ...q1,
        customer_response: "discussion",
        customer_response_message: "<script>این فقط متن است</script>",
        responded_at: "2026-09-21T10:30:00Z",
      },
    });
    renderCustomer();

    expect(await screen.findByText("<script>این فقط متن است</script>")).toBeVisible();
    expect(document.querySelector("script")).toBeNull();
    expect(document.body).toHaveTextContent("۲۰۲۶");
    expect(document.body).toHaveTextContent("۱۴۰۵");
    expect(screen.queryByRole("button", { name: "تأیید پیشنهاد" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "نیاز به گفتگو" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "رد پیشنهاد" })).not.toBeInTheDocument();
    expect(document.documentElement.dir).toBe("rtl");
  });

  it("does not offer response controls for a terminal Request", async () => {
    vi.mocked(api.fetchCustomerWorkflow).mockResolvedValue({
      ...customerWorkflow,
      status: "closed",
    });
    renderCustomer();

    expect(await screen.findByText("پیشنهاد (قیمت)")).toBeVisible();
    expect(screen.queryByRole("button", { name: "تأیید پیشنهاد" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "نیاز به گفتگو" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "رد پیشنهاد" })).not.toBeInTheDocument();
  });

  it("shows the expert the discussion, immutable quote history, and official revision action", async () => {
    render(
      <I18nProvider>
        <MemoryRouter initialEntries={["/expert/requests/42"]}>
          <Routes>
            <Route path="/expert/requests/:id" element={<RequestDetail />} />
          </Routes>
        </MemoryRouter>
      </I18nProvider>,
    );

    expect((await screen.findAllByText("مشتری نیاز به گفتگو دارد")).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("شرایط پرداخت نیاز به هماهنگی دارد")).toBeVisible();
    expect(screen.getByRole("button", { name: "صدور پیشنهاد بازنگری‌شده" })).toBeVisible();
    expect(screen.getByText("تاریخچه پیشنهادها")).toBeVisible();
    expect(screen.getByText("درخواست بازنگری نسخه اول")).toBeVisible();
    expect(document.body).toHaveTextContent("۱٬۲۵۰٬۰۰۰ EUR");
    expect(document.body).toHaveTextContent("۱٬۵۰۰٬۰۰۰ USD");
    expect(document.body).toHaveTextContent("۲۰۲۶");
    expect(document.body).toHaveTextContent("۱۴۰۵");
  });
});
