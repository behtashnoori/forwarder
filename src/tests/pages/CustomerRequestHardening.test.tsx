import type { ReactNode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CustomerPortalNewRequest from "@/pages/CustomerPortalNewRequest";
import CustomerPortalRequestDetail from "@/pages/CustomerPortalRequestDetail";
import * as portalApi from "@/lib/customerPortalApi";
import type { CustomerRequestDetail } from "@/lib/customerPortalApi";

vi.mock("@/components/CustomerPortalLayout", () => ({
  default: ({ children }: { children: ReactNode }) => <main dir="rtl">{children}</main>,
}));
vi.mock("@/components/LocationForm", () => ({
  default: ({ shippingType }: { shippingType: string }) => <p>existing-{shippingType}-form</p>,
}));
vi.mock("@/lib/customerPortalApi", async (original) => ({
  ...await original<typeof import("@/lib/customerPortalApi")>(),
  fetchCustomerSession: vi.fn(),
  fetchCustomerRequest: vi.fn(),
  respondToCustomerQuote: vi.fn(),
}));
vi.mock("@/lib/dualCalendar", () => ({
  formatDualCalendarDate: (value: string) => value,
  formatDualCalendarInstant: (value: string) => value,
}));
vi.mock("@/i18n", () => ({
  useI18n: () => ({
    language: "fa",
    locale: "fa-IR",
    t: (key: string) => ({
      "command.requestTypeTitle": "نوع درخواست حمل",
      "command.requestTypeDescription": "نوع درخواست را انتخاب کنید",
      "shipping.domestic.title": "ثبت درخواست حمل داخلی",
      "shipping.international.title": "ثبت درخواست حمل بین‌المللی",
      "customer.requestDetails": "جزئیات درخواست",
      "customer.requestAssignee": "کارشناس مسئول درخواست",
      "customer.assignmentPending": "در حال تخصیص",
      "customer.pendingAssignmentConfirmation": "درخواست شما ثبت شد و به‌زودی به کارشناس مربوط ارجاع می‌شود.",
      "customer.requestRoute": "مسیر / مبدا و مقصد",
      "customer.iranDestination": "مقصد در ایران",
      "customer.transportSelection": "روش حمل",
      "customer.transportSelectionPolicy": "نحوه انتخاب روش حمل",
      "customer.selectedTransportMethod": "روش حمل انتخاب‌شده",
      "customer.cargoItems": "اقلام کالا",
      "customer.requestDates": "بازه زمانی",
      "customer.fromDate": "از تاریخ",
      "customer.toDate": "تا تاریخ",
      "customer.specialInstructions": "دستورالعمل ویژه",
      "customer.quoteTitle": "پیشنهاد قیمت",
      "customer.quoteHistory": "تاریخچه پیشنهادها",
      "customer.noQuote": "هنوز پیشنهاد قیمتی ثبت نشده است.",
      "customer.quoteAwaitingResponse": "در انتظار پاسخ شما",
      "customer.quoteAccepted": "پیشنهاد پذیرفته شد",
      "customer.quoteDiscussion": "نیاز به گفتگو ثبت شد",
      "customer.quoteDeclined": "پیشنهاد رد شد",
      "customer.quoteValidUntil": "اعتبار پیشنهاد",
      "customer.quoteAccept": "پذیرش پیشنهاد",
      "customer.quoteNeedsDiscussion": "نیاز به گفتگو",
      "customer.quoteDecline": "رد پیشنهاد",
      "customer.quoteDiscussionMessage": "پیام گفتگو",
      "customer.quoteDiscussionPlaceholder": "توضیح خود را بنویسید",
      "customer.quoteSendDiscussion": "ارسال پیام گفتگو",
      "customer.backToPanel": "بازگشت به درخواست‌ها",
      "requestForm.forwarderSuggestionOption": "انتخاب روش مناسب را به فورواردر می‌سپارم",
      "requestForm.customerChoiceOption": "خودم روش حمل را انتخاب می‌کنم",
      "requestForm.cargoType": "نوع کالا",
      "common.trackingNumber": "کد رهگیری",
      "common.shippingType": "نوع درخواست",
      "common.createdAt": "تاریخ ثبت",
      "common.origin": "مبدا",
      "common.destination": "مقصد",
      "common.notRegistered": "ثبت نشده",
    } as Record<string, string>)[key] || key,
    statusLabel: (value: string) => value === "new" ? "جدید" : value,
    shippingTypeLabel: (value: string) => value === "domestic" ? "حمل داخلی" : "حمل بین‌المللی",
    transportLabel: (value: string) => value === "road" ? "حمل زمینی" : value,
  }),
}));

const detailFixture = (assigned = true): CustomerRequestDetail => ({
  public_id: "request-public",
  tracking_code: "SR2-CUSTOMER",
  shipping_type: "domestic",
  status: "new",
  created_at: "2026-09-27T10:00:00Z",
  assigned_expert: assigned ? { display_name: "علی رضایی" } : null,
  route: {
    origin: { province: "تهران", county: "تهران", city: "تهران" },
    destination: { province: "اصفهان", county: "اصفهان", city: "اصفهان" },
  },
  transport_method: null,
  domestic_transport_method: "road",
  international_transport_method: null,
  transport_method_preference: "customer_choice",
  cargo_items: [{
    public_id: "cargo-public",
    position: 1,
    description: "قطعات صنعتی",
    cargo_type: { public_id: "type-public", code: "GENERAL", fa_name: "کالای عمومی", en_name: "General cargo" },
    quantity: "12.500000",
    uom: { public_id: "uom-public", code: "KG", fa_name: "کیلوگرم", en_name: "Kilogram", symbol: "kg", measurement_dimension: "WEIGHT" },
  }],
  legacy_cargo: {},
  special_instructions: "با هماهنگی قبلی تحویل شود",
  pickup_date: "2026-10-01",
  delivery_date: "2026-10-04",
  latest_quote: null,
  quote_history: [],
});

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(portalApi.fetchCustomerSession).mockResolvedValue({ authenticated: true, csrf_token: "csrf" });
});

describe("authenticated Customer request hardening", () => {
  it.each([
    ["ثبت درخواست حمل داخلی", "existing-domestic-form"],
    ["ثبت درخواست حمل بین‌المللی", "existing-international-form"],
  ])("opens the direct chooser and enters the existing flow for %s", async (choice, expectedForm) => {
    render(<MemoryRouter initialEntries={["/customer/requests/new"]}><CustomerPortalNewRequest /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "نوع درخواست حمل" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: choice }));
    expect(screen.getByText(expectedForm)).toBeInTheDocument();
  });

  it("prioritizes the commercial state and keeps submitted facts available on demand", async () => {
    const user = userEvent.setup();
    vi.mocked(portalApi.fetchCustomerRequest).mockResolvedValue(detailFixture());
    render(<MemoryRouter initialEntries={["/customer/requests/request-public"]}><Routes><Route path="/customer/requests/:requestId" element={<CustomerPortalRequestDetail />} /></Routes></MemoryRouter>);
    expect((await screen.findAllByText("علی رضایی")).length).toBeGreaterThanOrEqual(1);
    await user.click(screen.getAllByText("جزئیات درخواست")[0]);
    const routeCard = screen.getByRole("heading", { name: "مسیر / مبدا و مقصد" }).closest(".rounded-lg");
    expect(routeCard).toHaveTextContent("تهران");
    expect(routeCard).toHaveTextContent("اصفهان");
    expect(screen.getByText("خودم روش حمل را انتخاب می‌کنم")).toBeInTheDocument();
    expect(screen.getByText("حمل زمینی")).toBeInTheDocument();
    expect(screen.getByText(/قطعات صنعتی/)).toBeInTheDocument();
    expect(screen.getByText("12.500000 kg")).toBeInTheDocument();
    expect(screen.getByText("2026-10-01")).toBeInTheDocument();
    expect(screen.getByText("2026-10-04")).toBeInTheDocument();
    expect(screen.getByText("با هماهنگی قبلی تحویل شود")).toBeInTheDocument();
    const cargoHeading = screen.getByRole("heading", { name: "اقلام کالا" });
    const noQuote = screen.getAllByText("هنوز پیشنهاد قیمتی ثبت نشده است.")[0];
    expect(noQuote.compareDocumentPosition(cargoHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("shows truthful pending assignment when no Expert is committed", async () => {
    vi.mocked(portalApi.fetchCustomerRequest).mockResolvedValue(detailFixture(false));
    render(<MemoryRouter initialEntries={["/customer/requests/request-public"]}><Routes><Route path="/customer/requests/:requestId" element={<CustomerPortalRequestDetail />} /></Routes></MemoryRouter>);
    expect((await screen.findAllByText("در حال تخصیص")).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("درخواست شما ثبت شد و به‌زودی به کارشناس مربوط ارجاع می‌شود.")).toBeInTheDocument();
    await waitFor(() => expect(portalApi.fetchCustomerRequest).toHaveBeenCalledWith("request-public"));
  });

  it("shows a submitted structured Iran destination on international detail", async () => {
    vi.mocked(portalApi.fetchCustomerRequest).mockResolvedValue({
      ...detailFixture(),
      shipping_type: "international",
      route: {
        origin: { country: "چین", international_city: "شانگهای" },
        destination: { country: "ایران" },
        iran_destination: { type: "port", label: "بندرعباس", province: "هرمزگان" },
      },
      domestic_transport_method: null,
      international_transport_method: "sea freight",
    });
    render(<MemoryRouter initialEntries={["/customer/requests/request-public"]}><Routes><Route path="/customer/requests/:requestId" element={<CustomerPortalRequestDetail />} /></Routes></MemoryRouter>);
    expect(await screen.findByText("بندرعباس، هرمزگان")).toBeInTheDocument();
    expect(screen.getByText("مقصد در ایران")).toBeInTheDocument();
  });

  it("shows one dominant response action and removes response controls after commercial closure", async () => {
    const currentQuote = {
      public_id: "quote-public",
      response_version: 1,
      amount: 1250000,
      currency: "IRR",
      created_at: "2026-09-27T11:00:00Z",
      customer_response: null,
    };
    vi.mocked(portalApi.fetchCustomerRequest).mockResolvedValue({
      ...detailFixture(),
      status: "in_progress",
      latest_quote: currentQuote,
      quote_history: [currentQuote],
    });
    const { unmount } = render(<MemoryRouter initialEntries={["/customer/requests/request-public"]}><Routes><Route path="/customer/requests/:requestId" element={<CustomerPortalRequestDetail />} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "پیگیری درخواست و پیشنهاد" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "مشاهده و پاسخ به پیشنهاد" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "پذیرش پیشنهاد" })).toBeInTheDocument();
    unmount();

    vi.mocked(portalApi.fetchCustomerRequest).mockResolvedValue({
      ...detailFixture(),
      status: "won",
      latest_quote: { ...currentQuote, customer_response: "accepted" },
      quote_history: [{ ...currentQuote, customer_response: "accepted" }],
    });
    render(<MemoryRouter initialEntries={["/customer/requests/request-public"]}><Routes><Route path="/customer/requests/:requestId" element={<CustomerPortalRequestDetail />} /></Routes></MemoryRouter>);
    expect(await screen.findByText("فرایند تجاری جمع‌بندی شده است")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "پذیرش پیشنهاد" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "نیاز به گفتگو" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "رد پیشنهاد" })).not.toBeInTheDocument();
  });
});
