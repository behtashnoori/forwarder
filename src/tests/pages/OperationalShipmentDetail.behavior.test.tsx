import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import OperationalShipmentDetail from "../../pages/OperationalShipmentDetail";
import * as api from "../../lib/api";

const controls = vi.hoisted(() => ({ permissions: new Set<string>() }));
vi.mock("../../i18n", () => ({
  useI18n: () => ({ t: (key: string) => ({
    "operations.activeRoutePlan":"Active route plan",
    "operations.timelineReconciliation":"Timeline reconciliation",
    "operations.lifecycle":"Checkpoints and milestone lifecycle",
    "operations.routeExceptions":"Route exceptions and work items",
  } as Record<string,string>)[key] || key, direction: "ltr", locale: "en-US", businessLabel: (value: string) => value, transportLabel: (value: string) => value }),
}));
vi.mock("../../components/OperationalPermission", () => ({
  default: ({ permission, children }: { permission: string; children: unknown }) =>
    controls.permissions.has(permission) ? children : null,
}));
vi.mock("../../components/ShipmentCargoItems", () => ({ default: () => <><h2>کالا و وسایل حمل</h2><h2>وضعیت و پیگیری حمل</h2></> }));
vi.mock("../../components/OperationalExecutionSection", () => ({ default: () => <p>اجرای عملیاتی</p> }));
vi.mock("../../components/DocumentReadinessSection", () => ({ default: () => <p>آمادگی اسناد</p> }));
vi.mock("../../components/ShipmentEconomicsSection", () => ({ default: () => null }));
vi.mock("../../components/ShipmentExternalReferences", () => ({ default: () => null }));
vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return {
    ...actual,
    getOperationalShipment: vi.fn(), listRoutePlans: vi.fn(), getRoutePlan: vi.fn(),
    getRouteTimeline: vi.fn(), listRouteExceptions: vi.fn(),
    reconcileRouteTimeline: vi.fn(), replanRoute: vi.fn(), commandRouteCheckpoint: vi.fn(),
    verifyRouteMilestone: vi.fn(), correctRouteMilestone: vi.fn(),
    reconcileRouteExceptions: vi.fn(), resolveRouteException: vi.fn(),
  };
});

const shipment = {
  public_id: "11111111-1111-4111-8111-111111111111", status: "active", version: 3, customer: "UAT Customer",
  overdue: true, open_work_item_count: 1, source: { type: "accepted_quote" as const, accepted_quote_id: 2, shipment_request_id: 3 },
  route_leg: { id: 10, origin: { display_name: "Origin" }, destination: { display_name: "Hub" }, transport_mode: "road", planned_departure: "2026-01-01T00:00:00Z", planned_arrival: "2026-01-02T00:00:00Z", version: 1 },
  milestones: [], recent_events: [],
  open_work_items: [{ id: 90, milestone_id: 31, type: "ROUTE_DEPENDENCY_BLOCKED", due_at: "2026-01-01T00:00:00Z", status: "open", version: 2 }],
  audit_summary: [],
};
const plan = {
  id: 20, revision_number: 2, status: "active", is_active: true, version: 4,
  legs: [
    { ...shipment.route_leg, id: 21, sequence_number: 1, status: "completed", actual_departure: "2026-01-01T00:00:00Z", actual_arrival: "2026-01-02T00:00:00Z" },
    { ...shipment.route_leg, id: 22, sequence_number: 2, status: "planned", origin: { display_name: "Hub" }, destination: { display_name: "Port" } },
    { ...shipment.route_leg, id: 23, sequence_number: 3, status: "planned", origin: { display_name: "Port" }, destination: { display_name: "Destination" } },
  ],
  checkpoints: [{
    id: 30, route_leg_id: 21, sequence_number: 1, checkpoint_type: "origin", status: "planned",
    verification_state: "reported", version: 7, planned_arrival_at: "2026-01-01T00:00:00Z",
    planned_departure_at: "2026-01-01T01:00:00Z", projected_arrival_at: "2026-01-01T00:30:00Z",
    actual_arrival_at: "2026-01-01T00:25:00Z",
    milestones: [
      { id: 31, type: "checkpoint_arrival", planned_at: "2026-01-01T00:00:00Z", projected_at: "2026-01-01T00:30:00Z", occurred_at: "2026-01-01T00:25:00Z", verification_state: "reported", version: 5 },
      { id: 32, type: "checkpoint_departure", planned_at: "2026-01-01T01:00:00Z", projected_at: null, occurred_at: "2026-01-01T01:00:00Z", verification_state: "verified", version: 6 },
    ],
  }],
  dependencies: [],
};
const timeline = {
  route_plan_id: 20, route_plan_revision: 2, reconciliation_version: 4, reconciled_at: null,
  planned: [{ checkpoint_id: 30, arrival_at: "2026-01-01T00:00:00Z", departure_at: "2026-01-01T01:00:00Z" }],
  projected: [{ checkpoint_id: 30, arrival_at: "2026-01-01T00:30:00Z", departure_at: null }],
  actual: [{ checkpoint_id: 30, arrival_at: "2026-01-01T00:25:00Z", departure_at: null }],
  effective: [{ checkpoint_id: 30, arrival_at: "2026-01-01T00:25:00Z", departure_at: "2026-01-01T01:00:00Z", arrival_source: "actual", departure_source: "planned" }],
  delays: [{ checkpoint_id: 30, seconds: 1800 }], dependencies: [], open_exceptions: [],
};
const openException = { id: 40, shipment_public_id: shipment.public_id, route_plan_id: 20, checkpoint_id: 30, type: "CHECKPOINT_OVERDUE", status: "open", severity: "high", due_at: "2026-01-01T00:00:00Z", detected_at: "2026-01-01T01:00:00Z", reason: "late", version: 2 };
const resolvedException = { ...openException, id: 41, status: "resolved", resolved_at: "2026-01-02T00:00:00Z", resolution_source: "manual", resolution_reason: "carrier confirmed", version: 3 };

function renderDetail() {
  return render(<MemoryRouter initialEntries={["/operations/shipments/11111111-1111-4111-8111-111111111111"]}><Routes><Route path="/operations/shipments/:id" element={<OperationalShipmentDetail />} /></Routes></MemoryRouter>);
}
beforeEach(() => {
  vi.clearAllMocks();
  controls.permissions = new Set(["route_plan.replan", "checkpoint.report", "checkpoint.verify", "milestone.correct", "route_exception.manage"]);
  vi.mocked(api.getOperationalShipment).mockResolvedValue({ data: shipment });
  vi.mocked(api.listRoutePlans).mockResolvedValue({ data: [plan] });
  vi.mocked(api.getRoutePlan).mockResolvedValue({ data: plan });
  vi.mocked(api.getRouteTimeline).mockResolvedValue({ data: timeline });
  vi.mocked(api.listRouteExceptions).mockResolvedValue({ data: [openException, resolvedException] });
});

describe("Phase 1B shipment detail behavior", () => {
  it("renders the detailed timeline and mobile-safe containers", async () => {
    const { container } = renderDetail();
    expect(await screen.findByText("Timeline reconciliation")).toBeInTheDocument();
    expect(screen.getAllByText("بخش مسیر 3").length).toBeGreaterThan(0);
    expect(screen.getAllByText("مورد نیازمند رسیدگی", { exact: false }).length).toBeGreaterThan(0);
    expect(container.querySelector("main")).toHaveClass("overflow-x-hidden", "p-3");
    expect(container.querySelector(".overflow-x-auto")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Report arrival" })).toHaveClass("min-h-11");
  });

  it("puts the shipment story first and keeps specialist work in more details", async () => {
    renderDetail();
    expect(await screen.findByRole("heading", { name: "خلاصه محموله" })).toBeInTheDocument();
    expect(screen.getByText("UAT Customer")).toBeInTheDocument();
    expect(screen.getByText("کالا و وسایل حمل")).toBeInTheDocument();
    expect(screen.getByText("وضعیت و پیگیری حمل")).toBeInTheDocument();
    expect(screen.getByText("جزئیات و سوابق بیشتر")).toBeInTheDocument();
    expect(screen.getByText("Active route plan")).toBeInTheDocument();
    expect(screen.getByText("اجرای عملیاتی")).toBeInTheDocument();
  });

  it("renders the same primary detail structure for a direct operation", async () => {
    vi.mocked(api.getOperationalShipment).mockResolvedValue({ data: { ...shipment, source: { type: "direct", accepted_quote_id: null, shipment_request_id: null } } });
    renderDetail();
    expect(await screen.findByRole("heading", { name: "خلاصه محموله" })).toBeInTheDocument();
    expect(screen.getByText("عملیات مستقیم")).toBeInTheDocument();
    expect(screen.getByText("کالا و وسایل حمل")).toBeInTheDocument();
    expect(screen.getByText("وضعیت و پیگیری حمل")).toBeInTheDocument();
    expect(screen.getByText("مراحل وابسته به پروژه برای عملیات مستقیم کاربرد ندارد.")).toBeInTheDocument();
    expect(screen.queryByText("Shipment is not assigned to a Project")).not.toBeInTheDocument();
    expect(screen.queryByText("Project has no active milestone definitions")).not.toBeInTheDocument();
    expect(screen.queryByText("اجرای عملیاتی")).not.toBeInTheDocument();
  });

  it("renders a direct shipment that has not been route-planned yet", async () => {
    vi.mocked(api.getOperationalShipment).mockResolvedValue({ data: { ...shipment, source: { type: "direct", accepted_quote_id: null, shipment_request_id: null }, route_leg: null, route_legs: [] } });
    vi.mocked(api.listRoutePlans).mockResolvedValue({ data: [] });
    vi.mocked(api.getRouteTimeline).mockResolvedValue({ data: { ...timeline, planned: [], projected: [], actual: [], effective: [], delays: [] } });
    vi.mocked(api.listRouteExceptions).mockResolvedValue({ data: [] });
    renderDetail();
    expect(await screen.findByRole("heading", { name: "خلاصه محموله" })).toBeInTheDocument();
    expect(screen.getByText("کالا و وسایل حمل")).toBeInTheDocument();
  });

  it("uses the route UUID for every detail subrequest when the response has no numeric id", async () => {
    renderDetail();
    await screen.findByText("Timeline reconciliation");
    const publicId = shipment.public_id;
    expect(api.getOperationalShipment).toHaveBeenCalledWith(publicId);
    expect(api.listRoutePlans).toHaveBeenCalledWith(publicId);
    expect(api.getRouteTimeline).toHaveBeenCalledWith(publicId);
    expect(api.listRouteExceptions).toHaveBeenCalledWith(publicId);
    expect(api.getRoutePlan).toHaveBeenCalledWith(publicId, plan.id);
    for (const mock of [api.listRoutePlans, api.getRouteTimeline, api.listRouteExceptions, api.getRoutePlan]) {
      expect(vi.mocked(mock).mock.calls.flat()).not.toContain(undefined);
    }
  });

  it("does not request anything for an invalid route identity", async () => {
    render(<MemoryRouter initialEntries={["/operations/shipments/undefined"]}><Routes><Route path="/operations/shipments/:id" element={<OperationalShipmentDetail />} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("alert")).toHaveTextContent("شناسه معتبر");
    expect(api.getOperationalShipment).not.toHaveBeenCalled();
    expect(api.listRoutePlans).not.toHaveBeenCalled();
    expect(api.getRouteTimeline).not.toHaveBeenCalled();
    expect(api.listRouteExceptions).not.toHaveBeenCalled();
  });

  it("stops before subrequests when response public_id disagrees with the route", async () => {
    vi.mocked(api.getOperationalShipment).mockResolvedValue({ data: { ...shipment, public_id: "22222222-2222-4222-8222-222222222222" } });
    renderDetail();
    expect(await screen.findByRole("alert")).toHaveTextContent("یکسان نیست");
    expect(api.listRoutePlans).not.toHaveBeenCalled();
    expect(api.getRouteTimeline).not.toHaveBeenCalled();
    expect(api.listRouteExceptions).not.toHaveBeenCalled();
  });

  it("reconciles a timeline and reports success", async () => {
    vi.mocked(api.reconcileRouteTimeline).mockResolvedValue({ data: { route_plan_id: 20, revision: 2, version: 5, reconciled_at: null, updated_checkpoints: 1, actual_override_count: 1, replayed: false } });
    renderDetail();
    fireEvent.click(await screen.findByRole("button", { name: "به‌روزرسانی برآورد زمانی" }));
    await waitFor(() => expect(api.reconcileRouteTimeline).toHaveBeenCalledWith(shipment.public_id, 4, expect.any(String)));
    expect(await screen.findByRole("status")).toHaveTextContent("برآورد زمانی مسیر به‌روز شد.");
  });

  it("reports a reconciliation no-op", async () => {
    vi.mocked(api.reconcileRouteTimeline).mockResolvedValue({ data: { route_plan_id: 20, revision: 2, version: 4, reconciled_at: null, updated_checkpoints: 0, actual_override_count: 0, replayed: false } });
    renderDetail();
    fireEvent.click(await screen.findByRole("button", { name: "به‌روزرسانی برآورد زمانی" }));
    expect(await screen.findByRole("status")).toHaveTextContent("تغییری در زمان‌بندی مسیر لازم نبود.");
  });

  it("sanitizes stale timeline conflicts", async () => {
    vi.mocked(api.reconcileRouteTimeline).mockRejectedValue(new api.ApiError(409, "STALE_ROUTE_PLAN_VERSION", "database detail"));
    renderDetail();
    fireEvent.click(await screen.findByRole("button", { name: "به‌روزرسانی برآورد زمانی" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("اطلاعات محموله تغییر کرده است");
    expect(screen.queryByText("database detail")).not.toBeInTheDocument();
  });

  it("hides every Phase 1B action without permissions", async () => {
    controls.permissions = new Set();
    renderDetail();
    await screen.findByText("Timeline reconciliation");
    for (const name of ["Reconcile timeline", "Report arrival", "Verify / re-verify", "Correct", "Replan future segments", "Reconcile exceptions", "Resolve manually"]) {
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    }
  });

  it("shows reporter controls without verifier or privileged actions", async () => {
    controls.permissions = new Set(["checkpoint.report"]);
    vi.mocked(api.commandRouteCheckpoint).mockResolvedValue({});
    renderDetail();

    expect(await screen.findByText("Active route plan")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Report arrival" }));
    await waitFor(() => expect(api.commandRouteCheckpoint).toHaveBeenCalledTimes(1));
    for (const name of ["Verify / re-verify", "Correct", "Reconcile timeline", "Replan future segments", "Reconcile exceptions", "Resolve manually"]) {
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    }
    expect(screen.queryByLabelText("Correction reason 32")).not.toBeInTheDocument();
    expect(api.correctRouteMilestone).not.toHaveBeenCalled();
    expect(api.verifyRouteMilestone).not.toHaveBeenCalled();
    expect(api.replanRoute).not.toHaveBeenCalled();
    expect(api.reconcileRouteTimeline).not.toHaveBeenCalled();
    expect(api.reconcileRouteExceptions).not.toHaveBeenCalled();
    expect(api.resolveRouteException).not.toHaveBeenCalled();
  });

  it("shows correction only with the canonical correction permission", async () => {
    controls.permissions = new Set(["milestone.correct"]);
    renderDetail();

    fireEvent.click(await screen.findByRole("button", { name: "Correct" }));
    expect(screen.getByRole("alert")).toHaveTextContent("ثبت دلیل الزامی است.");
    expect(screen.queryByRole("button", { name: "Report arrival" })).not.toBeInTheDocument();
    expect(api.correctRouteMilestone).not.toHaveBeenCalled();
  });

  it("requires correction and replan reasons", async () => {
    renderDetail();
    fireEvent.click(await screen.findByRole("button", { name: "Correct" }));
    expect(screen.getByRole("alert")).toHaveTextContent("ثبت دلیل الزامی است.");
    expect(api.correctRouteMilestone).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Replan future segments" }));
    expect(api.replanRoute).not.toHaveBeenCalled();
  });

  it("sends checkpoint version and idempotency keys", async () => {
    vi.mocked(api.commandRouteCheckpoint).mockResolvedValue({});
    vi.mocked(api.verifyRouteMilestone).mockResolvedValue({});
    renderDetail();
    fireEvent.click(await screen.findByRole("button", { name: "Report arrival" }));
    await waitFor(() => expect(api.commandRouteCheckpoint).toHaveBeenCalledWith(shipment.public_id, 30, "arrive", expect.any(String), 7, expect.any(String)));
    fireEvent.click(screen.getByRole("button", { name: "Verify / re-verify" }));
    await waitFor(() => expect(api.verifyRouteMilestone).toHaveBeenCalledWith(shipment.public_id, 30, 31, 5, expect.any(String)));
  });

  it("renders open/resolved exception history and validates manual resolution", async () => {
    vi.mocked(api.resolveRouteException).mockResolvedValue({});
    renderDetail();
    expect((await screen.findAllByText("استثنای عملیاتی ثبت‌شده", { exact: false })).length).toBeGreaterThan(1);
    expect(screen.getByText("منبع رفع: manual", { exact: false })).toHaveTextContent("carrier confirmed");
    fireEvent.click(screen.getByRole("button", { name: "ثبت رفع دستی" }));
    expect(screen.getByRole("alert")).toHaveTextContent("ثبت دلیل الزامی است.");
    fireEvent.change(screen.getByLabelText("دلیل رفع 40"), { target: { value: "Reviewed evidence" } });
    fireEvent.click(screen.getByRole("button", { name: "ثبت رفع دستی" }));
    await waitFor(() => expect(api.resolveRouteException).toHaveBeenCalledWith(40, 2, "Reviewed evidence", expect.any(String)));
  });

  it.each([
    [403, "اجازه انجام این کار را ندارید"],
    [404, "این محموله دیگر در دسترس نیست"],
    [409, "اطلاعات محموله تغییر کرده است"],
  ])("sanitizes %s command errors", async (status, expected) => {
    vi.mocked(api.reconcileRouteTimeline).mockRejectedValue(new api.ApiError(status, "INTERNAL_CODE", "sensitive database message"));
    renderDetail();
    fireEvent.click(await screen.findByRole("button", { name: "به‌روزرسانی برآورد زمانی" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(expected);
    expect(screen.queryByText("sensitive database message")).not.toBeInTheDocument();
  });
});
