import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { I18nProvider } from "@/i18n";
import { ApiError } from "@/lib/api";
import UnifiedShipmentHistory from "@/components/UnifiedShipmentHistory";

const api = vi.hoisted(() => ({ history: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, getShipmentHistory: api.history };
});
const shipment = "11111111-1111-4111-8111-111111111111";
const page = { page: 1, per_page: 25, total: 26, has_more: true, ordering: "business_time_desc_kind_phase_id", items: [
  { history_id: "delay:1:created", category: "DELAY", business_type: "operational_delay.created", occurred_at: "2026-09-14T10:00:00Z", recorded_at: "2026-09-14T10:01:00Z", actor: "Operator", reason_label: "توقف بندر" },
  { history_id: "event:2:recorded", category: "ROUTE_OCCURRENCE", business_type: "corrected", occurred_at: "2026-09-14T09:00:00Z", recorded_at: "2026-09-14T11:00:00Z", actor: "Verifier", route_revision: 1, supersedes_event_public_id: "prior" },
] };
const renderHistory = () => render(<MemoryRouter><I18nProvider><UnifiedShipmentHistory shipmentPublicId={shipment} /></I18nProvider></MemoryRouter>);

describe("unified shipment history", () => {
  beforeEach(() => { vi.clearAllMocks(); api.history.mockResolvedValue({ data: page }); });
  it("renders business labels, occurrence versus recording time, lineage, filters, and bounded pages read-only", async () => {
    const user = userEvent.setup();
    renderHistory();
    expect(document.querySelector('[aria-label="تاریخچه عملیات حمل"]')).toHaveAttribute("dir", "rtl");
    expect(await screen.findByText("ثبت تأخیر عملیاتی")).toBeInTheDocument();
    expect(screen.getByText(/توقف بندر/)).toBeInTheDocument();
    expect(screen.getByText(/این رخداد جایگزین گزارش پیشین شده است/)).toBeInTheDocument();
    expect(screen.getAllByText(/ثبت سیستمی/)).toHaveLength(2);
    expect(screen.queryByRole("button", { name: /ویرایش|حذف|اصلاح|تأیید/ })).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("دسته‌بندی"), "DELAY");
    expect(screen.queryByText(/این رخداد جایگزین/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "صفحه بعد" }));
    await waitFor(() => expect(api.history).toHaveBeenCalledWith(shipment, 2));
  });
  it("shows distinct empty, denied, and error states", async () => {
    api.history.mockResolvedValueOnce({ data: { ...page, items: [], total: 0, has_more: false } });
    const first = renderHistory();
    expect(await screen.findByText(/سابقه‌ای برای این محموله ثبت نشده/)).toBeInTheDocument();
    first.unmount();
    api.history.mockRejectedValueOnce(new ApiError(403, "FORBIDDEN", "private"));
    const second = renderHistory();
    expect(await screen.findByText(/دسترسی ندارید/)).toBeInTheDocument();
    second.unmount();
    api.history.mockRejectedValueOnce(new Error("database detail"));
    renderHistory();
    expect(await screen.findByRole("alert")).toHaveTextContent("دریافت تاریخچه عملیات ممکن نشد");
    expect(screen.queryByText("database detail")).not.toBeInTheDocument();
  });
});
