import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import OperationalShipmentDetail from "../../pages/OperationalShipmentDetail";
import * as api from "../../lib/api";

const controls = vi.hoisted(() => ({ permissions: new Set<string>() }));
vi.mock("../../i18n", () => ({
  useI18n: () => ({ t: (key: string) => key, direction: "ltr", locale: "en-US" }),
}));
vi.mock("../../components/OperationalPermission", () => ({
  default: ({ permission, children }: { permission: string; children: unknown }) =>
    controls.permissions.has(permission) ? children : null,
}));
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
  id: 1, public_id: "uat", status: "active", version: 3, customer: "UAT Customer",
  overdue: true, open_work_item_count: 1, source: { accepted_quote_id: 2, shipment_request_id: 3 },
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
    expect(screen.getByText("Leg 3")).toBeInTheDocument();
    expect(screen.getByText("Actionable", { exact: false })).toBeInTheDocument();
    expect(container.querySelector("main")).toHaveClass("overflow-x-hidden", "p-3");
    expect(container.querySelector(".overflow-x-auto")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Report arrival" })).toHaveClass("min-h-11");
  });

  it("reconciles a timeline and reports success", async () => {
    vi.mocked(api.reconcileRouteTimeline).mockResolvedValue({ data: { route_plan_id: 20, revision: 2, version: 5, reconciled_at: null, updated_checkpoints: 1, actual_override_count: 1, replayed: false } });
    renderDetail();
    fireEvent.click(await screen.findByRole("button", { name: "Reconcile timeline" }));
    await waitFor(() => expect(api.reconcileRouteTimeline).toHaveBeenCalledWith("uat", 4, expect.any(String)));
    expect(await screen.findByRole("status")).toHaveTextContent("Timeline reconciled.");
  });

  it("reports a reconciliation no-op", async () => {
    vi.mocked(api.reconcileRouteTimeline).mockResolvedValue({ data: { route_plan_id: 20, revision: 2, version: 4, reconciled_at: null, updated_checkpoints: 0, actual_override_count: 0, replayed: false } });
    renderDetail();
    fireEvent.click(await screen.findByRole("button", { name: "Reconcile timeline" }));
    expect(await screen.findByRole("status")).toHaveTextContent("No timeline changes were required.");
  });

  it("sanitizes stale timeline conflicts", async () => {
    vi.mocked(api.reconcileRouteTimeline).mockRejectedValue(new api.ApiError(409, "STALE_ROUTE_PLAN_VERSION", "database detail"));
    renderDetail();
    fireEvent.click(await screen.findByRole("button", { name: "Reconcile timeline" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The record changed. Refresh and try again.");
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
    expect(screen.getByRole("alert")).toHaveTextContent("A reason is required.");
    expect(screen.queryByRole("button", { name: "Report arrival" })).not.toBeInTheDocument();
    expect(api.correctRouteMilestone).not.toHaveBeenCalled();
  });

  it("requires correction and replan reasons", async () => {
    renderDetail();
    fireEvent.click(await screen.findByRole("button", { name: "Correct" }));
    expect(screen.getByRole("alert")).toHaveTextContent("A reason is required.");
    expect(api.correctRouteMilestone).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Replan future segments" }));
    expect(api.replanRoute).not.toHaveBeenCalled();
  });

  it("sends checkpoint version and idempotency keys", async () => {
    vi.mocked(api.commandRouteCheckpoint).mockResolvedValue({});
    vi.mocked(api.verifyRouteMilestone).mockResolvedValue({});
    renderDetail();
    fireEvent.click(await screen.findByRole("button", { name: "Report arrival" }));
    await waitFor(() => expect(api.commandRouteCheckpoint).toHaveBeenCalledWith("uat", 30, "arrive", expect.any(String), 7, expect.any(String)));
    fireEvent.click(screen.getByRole("button", { name: "Verify / re-verify" }));
    await waitFor(() => expect(api.verifyRouteMilestone).toHaveBeenCalledWith("uat", 30, 31, 5, expect.any(String)));
  });

  it("renders open/resolved exception history and validates manual resolution", async () => {
    vi.mocked(api.resolveRouteException).mockResolvedValue({});
    renderDetail();
    expect((await screen.findAllByText("CHECKPOINT_OVERDUE")).length).toBe(2);
    expect(screen.getByText("Source: manual", { exact: false })).toHaveTextContent("carrier confirmed");
    fireEvent.click(screen.getByRole("button", { name: "Resolve manually" }));
    expect(screen.getByRole("alert")).toHaveTextContent("A reason is required.");
    fireEvent.change(screen.getByLabelText("Resolution reason for CHECKPOINT_OVERDUE"), { target: { value: "Reviewed evidence" } });
    fireEvent.click(screen.getByRole("button", { name: "Resolve manually" }));
    await waitFor(() => expect(api.resolveRouteException).toHaveBeenCalledWith(40, 2, "Reviewed evidence", expect.any(String)));
  });

  it.each([
    [403, "You do not have permission"],
    [404, "no longer available"],
    [409, "record changed"],
  ])("sanitizes %s command errors", async (status, expected) => {
    vi.mocked(api.reconcileRouteTimeline).mockRejectedValue(new api.ApiError(status, "INTERNAL_CODE", "sensitive database message"));
    renderDetail();
    fireEvent.click(await screen.findByRole("button", { name: "Reconcile timeline" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(expected);
    expect(screen.queryByText("sensitive database message")).not.toBeInTheDocument();
  });
});
