import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import OperationalWorkspace from "@/pages/OperationalWorkspace";
import { ApiError, getOperationalWorkspace, type OperationalWorkspaceSnapshot } from "@/lib/api";

vi.mock("@/components/OperationsNav", () => ({ default: () => <nav>operations navigation</nav> }));
vi.mock("@/i18n", () => ({
  useI18n: () => ({
    direction: "rtl",
    locale: "fa-IR",
    businessLabel: (value: string) => value,
  }),
}));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, getOperationalWorkspace: vi.fn() };
});

const shipment = {
  public_id: "11111111-1111-4111-8111-111111111111",
  status: "in_transit",
  customer: "مشتری آزمایشی",
  responsible_expert: { display_name: "کارشناس مالک" },
  route_summary: {
    origin: { display_name: "تهران" },
    destination: { display_name: "تبریز" },
    transport_modes: ["road"],
    leg_count: 1,
  },
  current_milestone: "departure",
  latest_update: {
    event_type: "milestone_reported",
    label: "خروج ثبت شد",
    milestone_type: "departure",
    occurred_at: "2026-09-24T07:00:00Z",
    recorded_at: "2026-09-24T07:05:00Z",
    source: "expert",
  },
  overdue: true,
  overdue_since: "2026-09-24T06:00:00Z",
  open_work_item_count: 1,
  sla: { status: "WARNING" as const, status_label: "نزدیک به نقض SLA", commitments: [] },
  updated_at: "2026-09-24T07:05:00Z",
};

const populated: OperationalWorkspaceSnapshot = {
  data: {
    active_shipments: [shipment],
    attention_items: [{
      identity: "attention-stable-id",
      shipment,
      kind: "OVERDUE_MILESTONE",
      label: "مرحله عقب‌افتاده",
      why: "تأیید مرحله هنوز ثبت نشده است.",
      time_effect: "موعد این مرحله گذشته است.",
      next_action: "وضعیت مرحله را پیگیری کنید.",
      severity: "warning",
      detected_at: "2026-09-24T06:00:00Z",
      due_at: "2026-09-24T06:00:00Z",
      source: { type: "OperationalWorkItem", version: 3, status: "open" },
      freshness: { status: "FRESH", calculated_at: "2026-09-24T08:00:00Z" },
      source_path: "/operations/shipments/11111111-1111-4111-8111-111111111111",
    }],
    recent_updates: [{
      event_public_id: "22222222-2222-4222-8222-222222222222",
      shipment_public_id: shipment.public_id,
      customer: shipment.customer,
      label: "خروج ثبت شد",
      milestone_type: "departure",
      occurred_at: "2026-09-24T07:00:00Z",
      recorded_at: "2026-09-24T07:05:00Z",
      source: "expert",
    }],
  },
  meta: {
    active_shipment_count: 1,
    open_follow_up_count: 1,
    attention_available: true,
    attention_projection: { state: "FRESH", calculated_at: "2026-09-24T08:00:00Z" },
    calculated_at: "2026-09-24T08:00:00Z",
    projection_version: "operational-workspace-phase-2-v1",
    sources: ["OperationalShipment", "OperationalWorkItem", "OperationalEvent"],
    limitations: ["No SLA inference"],
  },
};

const empty = (attentionAvailable = true): OperationalWorkspaceSnapshot => ({
  data: { active_shipments: [], attention_items: [], recent_updates: [] },
  meta: {
    ...populated.meta,
    active_shipment_count: 0,
    open_follow_up_count: attentionAvailable ? 0 : null,
    attention_available: attentionAvailable,
  },
});

function renderWorkspace() {
  return render(<MemoryRouter><OperationalWorkspace /></MemoryRouter>);
}

describe("OperationalWorkspace", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders a sourced overview and links every operational item to its shipment", async () => {
    vi.mocked(getOperationalWorkspace).mockResolvedValue(populated);
    renderWorkspace();

    expect(screen.getByRole("status")).toHaveTextContent("در حال آماده‌سازی");
    expect((await screen.findAllByText("مشتری آزمایشی", { exact: false })).length).toBeGreaterThan(0);
    expect(screen.getByText("کارشناس مسئول ثابت: کارشناس مالک")).toBeInTheDocument();
    expect(screen.getAllByText("تهران ← تبریز", { exact: false }).length).toBeGreaterThan(0);
    expect(screen.getByText("آخرین به‌روزرسانی:", { exact: false })).toHaveTextContent("خروج ثبت شد");
    expect(screen.getByText("منبع: OperationalWorkItem · نسخه 3 · تازگی: FRESH")).toBeInTheDocument();
    expect(screen.getByText((_, element) => element?.textContent === "چرا: تأیید مرحله هنوز ثبت نشده است.")).toBeInTheDocument();
    expect(screen.getByText((_, element) => element?.textContent === "پیگیری بعدی: وضعیت مرحله را پیگیری کنید.")).toBeInTheDocument();
    expect(screen.getByText("نزدیک به نقض SLA")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /باز کردن منبع پیگیری/ })).toHaveAttribute(
      "href",
      `/operations/shipments/${shipment.public_id}`,
    );
    expect(screen.getByRole("link", { name: /مشاهده محموله/ })).toHaveAttribute(
      "href",
      `/operations/shipments/${shipment.public_id}`,
    );
    expect(screen.getByText(/نبود داده به‌معنی سلامت یا رعایت SLA تلقی نمی‌شود/)).toBeInTheDocument();
  });

  it("shows honest empty and permission-limited attention states", async () => {
    vi.mocked(getOperationalWorkspace).mockResolvedValue(empty(false));
    renderWorkspace();

    expect(await screen.findByText("جزئیات پیگیری‌ها با دسترسی فعلی شما قابل نمایش نیست.")).toBeInTheDocument();
    expect(screen.getByText("محموله فعالی در دامنه دسترسی شما وجود ندارد.")).toBeInTheDocument();
    expect(screen.getByText("محدود")).toBeInTheDocument();
  });

  it("distinguishes a forbidden response from a temporary loading failure", async () => {
    vi.mocked(getOperationalWorkspace).mockRejectedValue(
      new ApiError(403, "FORBIDDEN_OPERATION", "denied"),
    );
    renderWorkspace();
    expect(await screen.findByRole("alert")).toHaveTextContent("اجازه مشاهده فضای کار عملیاتی را ندارید");
  });

  it("recovers through the visible retry action", async () => {
    vi.mocked(getOperationalWorkspace)
      .mockRejectedValueOnce(new Error("temporary"))
      .mockResolvedValueOnce(empty());
    renderWorkspace();

    expect(await screen.findByRole("alert")).toHaveTextContent("در حال حاضر بارگذاری نشد");
    await userEvent.click(screen.getByRole("button", { name: "تلاش دوباره" }));
    await waitFor(() => expect(getOperationalWorkspace).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("در داده‌های فعلی، پیگیری عملیاتی بازی برای محموله‌های فعال قابل مشاهده ثبت نشده است.")).toBeInTheDocument();
  });
});
