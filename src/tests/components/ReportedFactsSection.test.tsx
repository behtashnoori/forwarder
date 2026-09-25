import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ReportedFactsSection from "@/components/ReportedFactsSection";
import { listReportedFacts, recordReportedFact, type ReportFact, type ReportList } from "@/lib/reportedFactApi";

vi.mock("@/lib/reportedFactApi", () => ({ listReportedFacts: vi.fn(), recordReportedFact: vi.fn() }));
const fixture = (canManage = true): ReportList => ({ items: [], reported_locations: [], total: 0, page: 1, can_manage: canManage,
  options: { SHIPMENT: [], ROUTE_STAGE: [], EXECUTION_UNIT: [{ public_id: "unit-a", label: "وسیله اول" }], CARGO: [{ public_id: "cargo-a", label: "کالای من" }], cargo: [{ public_id: "cargo-a", label: "کالای من" }] } });
beforeEach(() => { vi.clearAllMocks(); vi.mocked(listReportedFacts).mockResolvedValue({ data: fixture() }); });

describe("scoped operational reports", () => {
  it("preserves retry key and keeps occurred time and safe text explicit", async () => {
    vi.mocked(recordReportedFact).mockRejectedValueOnce(new Error("network")).mockResolvedValueOnce({ public_id: "report", created: true });
    render(<ReportedFactsSection shipmentId="shipment" />);
    fireEvent.click(await screen.findByRole("button", { name: "گزارش تازه" }));
    fireEvent.change(screen.getByLabelText("بخش مربوط به گزارش"), { target: { value: "unit-a" } });
    fireEvent.change(screen.getByLabelText("زمان وقوع گزارش"), { target: { value: "2026-09-20T10:30" } });
    fireEvent.change(screen.getByLabelText("موقعیت گزارش‌شده"), { target: { value: "نزدیک مرز" } });
    fireEvent.change(screen.getByLabelText("یادداشت داخلی گزارش"), { target: { value: "علت خصوصی" } });
    fireEvent.click(screen.getByLabelText("کالای من"));
    fireEvent.click(screen.getByRole("button", { name: "ثبت گزارش", exact: true }));
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "ثبت گزارش", exact: true }));
    await screen.findByText("گزارش ثبت شد.");
    const calls = vi.mocked(recordReportedFact).mock.calls;
    expect(calls).toHaveLength(2);
    expect(calls[0][2]).toBe(calls[1][2]);
    expect(calls[0][1]).toMatchObject({ source: "INTERNAL_EXPERT", scope: "EXECUTION_UNIT", target_public_id: "unit-a", customer_message: null, internal_note: "علت خصوصی", impacted_cargo_public_ids: ["cargo-a"] });
    expect(calls[0][1].occurred_at).toBe(new Date("2026-09-20T10:30").toISOString());
    expect(calls[0][1]).not.toHaveProperty("recorded_at");
  });

  it("shows separate units and retained correction history in read-only oversight", async () => {
    const first = { public_id: "r1", scope: "EXECUTION_UNIT", target_public_id: "a", kind: "LOCATION", source: "DRIVER_REPORT", source_label: "گزارش راننده", scope_label: "وسیله اول", location: "مرز اول", occurred_at: "2026-09-20T10:30:00Z", recorded_at: "2026-09-21T10:30:00Z", actor_user_id: 1, actor_label: "کارشناس", customer_effect: "CHANGE", impacted_cargo_public_ids: [], internal_note: null, customer_message: null, status: "CURRENT" } as ReportFact;
    const second = { ...first, public_id: "r2", target_public_id: "b", scope_label: "وسیله دوم", location: "مرز دوم" };
    vi.mocked(listReportedFacts).mockResolvedValue({ data: { ...fixture(false), items: [first, second, { ...first, public_id: "old", status: "SUPERSEDED" }], reported_locations: [first, second], total: 3 } });
    render(<ReportedFactsSection shipmentId="shipment" />);
    await screen.findByText("آخرین موقعیت گزارش‌شده: مرز اول");
    expect(screen.getByText("آخرین موقعیت گزارش‌شده: مرز دوم")).toBeInTheDocument();
    expect(screen.getByText("اصلاح‌شده؛ محفوظ در سابقه")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("button", { name: "اصلاح گزارش" })).not.toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "گزارش تازه" })).not.toBeInTheDocument();
  });
});
