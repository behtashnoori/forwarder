import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import OperationalShipments from "../../pages/OperationalShipments";
import OperationalShipmentDetail from "../../pages/OperationalShipmentDetail";
import OperationalWorkQueue from "../../pages/OperationalWorkQueue";
import * as api from "../../lib/api";
vi.mock("../../i18n", () => ({
  useI18n: () => ({ t: (k: string) => k, direction: "ltr", locale: "en-US" }),
}));
vi.mock("../../components/OperationalPermission", () => ({
  default: ({ children }: { children: unknown }) => children,
}));
vi.mock("../../lib/api", async () => {
  const actual =
    await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return {
    ...actual,
    listOperationalShipments: vi.fn(),
    createOperationalShipment: vi.fn(),
    getOperationalShipment: vi.fn(),
    recordOperationalEvent: vi.fn(),
    verifyOperationalMilestone: vi.fn(),
    correctOperationalMilestone: vi.fn(),
    listRoutePlans: vi.fn(),
    getRoutePlan: vi.fn(),
    getRouteTimeline: vi.fn(),
    reconcileRouteTimeline: vi.fn(),
    replanRoute: vi.fn(),
    commandRouteCheckpoint: vi.fn(),
    verifyRouteMilestone: vi.fn(),
    correctRouteMilestone: vi.fn(),
    listRouteExceptions: vi.fn(),
    reconcileRouteExceptions: vi.fn(),
    resolveRouteException: vi.fn(),
    listOperationalWorkItems: vi.fn(),
    resolveOperationalWorkItem: vi.fn(),
  };
});
const shipment = {
  id: 1,
  public_id: "11111111-1111-4111-8111-111111111111",
  status: "planned",
  version: 1,
  customer: "UAT Customer",
  overdue: true,
  overdue_since: "2026-01-01T00:00:00Z",
  open_work_item_count: 1,
  current_milestone: "departure",
  source: { accepted_quote_id: 2, shipment_request_id: 3 },
  route_leg: {
    id: 4,
    origin: { display_name: "Origin" },
    destination: { display_name: "Destination" },
    transport_mode: "road",
    planned_departure: "2026-01-01T00:00:00Z",
    planned_arrival: "2026-01-02T00:00:00Z",
    version: 1,
  },
  milestones: [
    {
      id: 5,
      type: "departure",
      planned_at: "2026-01-01T00:00:00Z",
      verification_state: "reported",
      version: 2,
    },
  ],
  recent_events: [],
  open_work_items: [
    {
      id: 6,
      milestone_id: 5,
      type: "OVERDUE_MILESTONE",
      due_at: "2026-01-01T00:00:00Z",
      status: "open",
      version: 1,
    },
  ],
  audit_summary: [],
};
const routePlan = {
  id: 20, revision_number: 2, status: "active", is_active: true, version: 4,
  legs: [
    { ...shipment.route_leg, id: 21, sequence_number: 1, status: "completed", projected_departure: null, projected_arrival: null, actual_departure: "2026-01-01T00:00:00Z", actual_arrival: "2026-01-02T00:00:00Z" },
    { ...shipment.route_leg, id: 22, sequence_number: 2, status: "planned", origin: { display_name: "Hub" }, destination: { display_name: "Port" } },
    { ...shipment.route_leg, id: 23, sequence_number: 3, status: "planned", origin: { display_name: "Port" }, destination: { display_name: "Destination" } },
  ],
  checkpoints: [{
    id: 30, route_leg_id: 21, sequence_number: 1, checkpoint_type: "origin",
    status: "arrived", verification_state: "reported", version: 2,
    planned_arrival_at: "2026-01-01T00:00:00Z", planned_departure_at: "2026-01-01T01:00:00Z",
    projected_arrival_at: "2026-01-01T00:30:00Z", projected_departure_at: "2026-01-01T01:30:00Z",
    actual_arrival_at: "2026-01-01T00:25:00Z", actual_departure_at: null,
    milestones: [{ id: 31, type: "arrival", planned_at: "2026-01-01T00:00:00Z", projected_at: "2026-01-01T00:30:00Z", occurred_at: "2026-01-01T00:25:00Z", verification_state: "reported", version: 2 }],
  }],
  dependencies: [],
};
const timeline = {
  route_plan_id: 20, route_plan_revision: 2, reconciliation_version: 4, reconciled_at: "2026-01-01T02:00:00Z",
  planned: [{ checkpoint_id: 30, arrival_at: "2026-01-01T00:00:00Z", departure_at: "2026-01-01T01:00:00Z" }],
  projected: [{ checkpoint_id: 30, arrival_at: "2026-01-01T00:30:00Z", departure_at: "2026-01-01T01:30:00Z" }],
  actual: [{ checkpoint_id: 30, arrival_at: "2026-01-01T00:25:00Z", departure_at: null }],
  effective: [{ checkpoint_id: 30, arrival_at: "2026-01-01T00:25:00Z", departure_at: "2026-01-01T01:30:00Z", arrival_source: "actual", departure_source: "projected" }],
  delays: [{ checkpoint_id: 30, seconds: 1800 }], dependencies: [], open_exceptions: [],
};
beforeEach(() => {
  vi.clearAllMocks();
  (api.listRoutePlans as ReturnType<typeof vi.fn>).mockResolvedValue({ data: [routePlan] });
  (api.getRoutePlan as ReturnType<typeof vi.fn>).mockResolvedValue({ data: routePlan });
  (api.getRouteTimeline as ReturnType<typeof vi.fn>).mockResolvedValue({ data: timeline });
  (api.listRouteExceptions as ReturnType<typeof vi.fn>).mockResolvedValue({ data: [] });
});
describe("Phase 1A operational pages", () => {
  it("renders loading then list data and filters", async () => {
    let release: (v: unknown) => void = () => {};
    (api.listOperationalShipments as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise((r) => (release = r)),
    );
    render(
      <MemoryRouter>
        <OperationalShipments />
      </MemoryRouter>,
    );
    expect(screen.getByText("operations.loading")).toBeInTheDocument();
    release({ data: [shipment], meta: { page: 1, has_more: false } });
    expect(await screen.findByText("UAT Customer")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /UAT Customer/ })).toHaveLength(1);
    expect(screen.getByRole("link", { name: /UAT Customer/ })).toHaveAttribute(
      "href", "/operations/shipments/11111111-1111-4111-8111-111111111111",
    );
    expect(screen.queryByText(/Quote #2|Request #3|#1/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("status")).toBeInTheDocument();
  });
  it("prevents duplicate create submissions", async () => {
    (
      api.listOperationalShipments as ReturnType<typeof vi.fn>
    ).mockResolvedValue({ data: [], meta: { page: 1, has_more: false } });
    (api.createOperationalShipment as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise(() => {}),
    );
    render(
      <MemoryRouter>
        <OperationalShipments />
      </MemoryRouter>,
    );
    for (const [label, value] of [
      ["quote", "2"],
      ["origin", "1"],
      ["destination", "2"],
      ["departure", "2026-01-01T00:00"],
      ["arrival", "2026-01-02T00:00"],
    ])
      fireEvent.change(document.querySelector(`#create-${label}`) as HTMLInputElement, { target: { value } });
    const button = screen.getByRole("button", { name: "operations.create" });
    fireEvent.click(button);
    fireEvent.click(button);
    await waitFor(() =>
      expect(api.createOperationalShipment).toHaveBeenCalledTimes(1),
    );
    expect(button).toBeDisabled();
  });
  it("shows a friendly validation error for invalid route times", async () => {
    (api.listOperationalShipments as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [],
      meta: { page: 1, has_more: false },
    });
    render(
      <MemoryRouter>
        <OperationalShipments />
      </MemoryRouter>,
    );
    for (const [label, value] of [
      ["quote", "2"],
      ["origin", "1"],
      ["destination", "2"],
      ["departure", "not-a-time"],
      ["arrival", "also-not-a-time"],
    ])
      fireEvent.change(document.querySelector(`#create-${label}`) as HTMLInputElement, { target: { value } });
    fireEvent.click(screen.getByRole("button", { name: "operations.create" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("operations.invalidTime");
    expect(api.createOperationalShipment).not.toHaveBeenCalled();
  });
  it("renders detail milestones, work and audit sections", async () => {
    (api.getOperationalShipment as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: shipment,
    });
    render(
      <MemoryRouter initialEntries={["/operations/shipments/11111111-1111-4111-8111-111111111111"]}>
        <Routes>
          <Route
            path="/operations/shipments/:id"
            element={<OperationalShipmentDetail />}
          />
        </Routes>
      </MemoryRouter>,
    );
    expect(
      await screen.findByText("UAT Customer", { exact: false }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("arrival", { exact: false }).length).toBeGreaterThan(0);
    expect(screen.getByText("operations.workQueue")).toBeInTheDocument();
    expect(screen.queryByText(/Quote #2|Request #3|plan #20|Checkpoint #30|#6/)).not.toBeInTheDocument();
    expect(api.getOperationalShipment).toHaveBeenCalledWith(
      "11111111-1111-4111-8111-111111111111",
    );
  });
  it("renders and resolves a work item", async () => {
    (
      api.listOperationalWorkItems as ReturnType<typeof vi.fn>
    ).mockResolvedValue({
      data: [
        {
          id: 6,
          shipment_id: 1,
          shipment_public_id: "11111111-1111-4111-8111-111111111111",
          milestone_id: 5,
          type: "OVERDUE_MILESTONE",
          status: "open",
          due_at: "2026-01-01T00:00:00Z",
          planned_at: "2026-01-01T00:00:00Z",
          milestone_type: "departure",
          overdue_seconds: 3600,
          customer: "UAT Customer",
          route_leg: shipment.route_leg,
          reason: "late",
          version: 1,
        },
      ],
      meta: { page: 1, has_more: false },
    });
    (
      api.resolveOperationalWorkItem as ReturnType<typeof vi.fn>
    ).mockResolvedValue({});
    render(
      <MemoryRouter>
        <OperationalWorkQueue />
      </MemoryRouter>,
    );
    expect(
      await screen.findByText("UAT Customer", { exact: false }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "operations.resolve" }));
    await waitFor(() =>
      expect(api.resolveOperationalWorkItem).toHaveBeenCalledWith(6, 1),
    );
  });
});
