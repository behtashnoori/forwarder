import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "@/i18n";
import PublicTracking from "@/pages/PublicTracking";
import * as api from "@/lib/api";

vi.mock("@/hooks/use-toast", () => ({ useToast: () => ({ toast: vi.fn() }) }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchPublicTracking: vi.fn() };
});

const request = {
  id: 12,
  tracking_number: "SR2-AAAAAAAAAAAAAAAAAAAAAA",
  status: "new",
  created_at: "2026-09-20T00:00:00Z",
  shipping_type: "domestic",
  contact_phone: "09120000000",
  customer_first_name: "مشتری",
  route: {
    origin: { province: "تهران" },
    destination: { province: "فارس" },
  },
  domestic_transport_method: "Rail Transport",
  transport_method: "road",
  workflow_steps_simple: [],
};

describe("public request transport summary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.setItem("forwarder.language", "fa");
    vi.mocked(api.fetchPublicTracking).mockResolvedValue(request);
  });

  it("shows the localized request method exactly once and does not leak the raw value", async () => {
    render(
      <I18nProvider>
        <MemoryRouter initialEntries={["/track/request-12"]}>
          <Routes><Route path="/track/:requestId" element={<PublicTracking />} /></Routes>
        </MemoryRouter>
      </I18nProvider>,
    );

    expect(await screen.findByText("حمل ریلی")).toBeInTheDocument();
    expect(screen.getAllByText("روش حمل درخواست")).toHaveLength(1);
    expect(screen.getAllByText("حمل ریلی")).toHaveLength(1);
    expect(screen.queryByText("Rail Transport")).not.toBeInTheDocument();
    expect(screen.queryByText("جاده‌ای")).not.toBeInTheDocument();
    expect(screen.queryByText("09120000000")).not.toBeInTheDocument();
    expect(screen.queryByText("مشتری")).not.toBeInTheDocument();
    expect(document.body).toHaveTextContent("۲۰ سپتامبر ۲۰۲۶ (۲۹ شهریور ۱۴۰۵)");
  });

  it("shows the same safe unavailable state for a numeric public probe", async () => {
    vi.mocked(api.fetchPublicTracking).mockRejectedValue(new api.PublicTrackingNotFoundError());
    render(
      <I18nProvider>
        <MemoryRouter initialEntries={["/track/10"]}>
          <Routes><Route path="/track/:requestId" element={<PublicTracking />} /></Routes>
        </MemoryRouter>
      </I18nProvider>,
    );

    expect(await screen.findByText("درخواست یافت نشد")).toBeInTheDocument();
    expect(api.fetchPublicTracking).toHaveBeenCalledWith("10");
    expect(screen.queryByText("09120000000")).not.toBeInTheDocument();
  });
});
