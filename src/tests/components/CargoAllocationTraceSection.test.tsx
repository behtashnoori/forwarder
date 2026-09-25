import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CargoAllocationTraceSection from "../../components/CargoAllocationTraceSection";
import * as api from "../../lib/api";

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return {
    ...actual,
    listShipmentCargoItems: vi.fn(),
    listRouteStageTransportExecutions: vi.fn(),
    getCargoAllocationTrace: vi.fn(),
    setStageCargoAllocation: vi.fn(),
    transferCargoAllocation: vi.fn(),
  };
});

const shipment = "11111111-1111-4111-8111-111111111111";
const cargo = "22222222-2222-4222-8222-222222222222";
const stageA = "33333333-3333-4333-8333-333333333333";
const stageB = "44444444-4444-4444-8444-444444444444";
const row = (stage: string, dimension: "PLANNED" | "ACTUAL", quantity: string, version = 1): api.StageCargoAllocation => ({ public_id: `${stage}-${dimension}`, stage_execution_public_id: stage, execution_unit_public_id: stage, dimension, quantity, version, current: true });
const trace: api.CargoAllocationTrace = {
  cargo: { public_id: cargo, name: "قطعات موتور", requested_quantity: "100", planned_quantity: "100", actual_quantity: "95", uom: "کارتن" },
  stages: [{
    route_plan_id: 12, route_leg_id: 21, sequence_number: 1,
    origin: { display_name: "چین" }, destination: { display_name: "خورگوس" },
    planned_total: "90", actual_total: "95", planned_remaining: "10", actual_unrecorded: "0",
    planned_recorded: true, actual_recorded: true,
    warnings: [{ code: "PLAN_UNDER", difference: "10" }, { code: "ACTUAL_VS_PLAN", difference: "5" }],
    executions: [
      { stage_execution_public_id: stageA, execution_unit_public_id: stageA, unit_code: "UNIT-A", means: "کامیون", means_identifier: "TRUCK-12", equipment: [], allocations: [row(stageA, "PLANNED", "60"), row(stageA, "ACTUAL", "55")] },
      { stage_execution_public_id: stageB, execution_unit_public_id: stageB, unit_code: "UNIT-B", means: "کامیون", means_identifier: "TRUCK-18", equipment: [], allocations: [row(stageB, "PLANNED", "30"), row(stageB, "ACTUAL", "40")] },
    ],
  }],
  legacy_allocations: [], transfers: [],
  history: [{ public_id: "history-1", allocation_public_id: "allocation-1", action: "ACTUAL_CORRECTION", before: "50", after: "48", occurred_at: "2026-09-25T10:00:00Z", recorded_at: "2026-09-25T10:01:00Z", actor_name: "کارشناس", reason: "بازشماری", transfer_public_id: null }],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listShipmentCargoItems).mockResolvedValue({ items: [{ public_id: cargo }] } as Awaited<ReturnType<typeof api.listShipmentCargoItems>>);
  vi.mocked(api.listRouteStageTransportExecutions).mockResolvedValue({ data: { can_manage: true } } as Awaited<ReturnType<typeof api.listRouteStageTransportExecutions>>);
  vi.mocked(api.getCargoAllocationTrace).mockResolvedValue({ trace });
  vi.mocked(api.setStageCargoAllocation).mockResolvedValue({ allocation: row(stageB, "PLANNED", "40", 2), replayed: false });
});

describe("Cargo allocation trace", () => {
  it("shows stage totals, remaining quantity, non-blocking warnings and correction history", async () => {
    render(<CargoAllocationTraceSection shipmentId={shipment} planId={12} />);
    expect(await screen.findByText(/10 کارتن در برنامه این بخش هنوز تخصیص ندارد/)).toBeInTheDocument();
    const paragraph = (content: string) => screen.getByText((_, element) => element?.tagName === "P" && element.textContent?.includes(content) === true);
    expect(paragraph("جمع برنامه: 90")).toBeInTheDocument();
    expect(paragraph("جمع واقعی: 95")).toBeInTheDocument();
    expect(paragraph("مانده نسبت به برنامه کل کالا: 10")).toBeInTheDocument();
    fireEvent.click(screen.getByText("تاریخچه تخصیص و انتقال"));
    expect(screen.getByText(/بازشماری/)).toBeInTheDocument();
  });

  it("submits an explicit plan revision with the current version", async () => {
    render(<CargoAllocationTraceSection shipmentId={shipment} planId={12} />);
    await screen.findByLabelText("اجرای حمل برای تخصیص");
    fireEvent.change(screen.getByLabelText("اجرای حمل برای تخصیص"), { target: { value: stageB } });
    fireEvent.change(screen.getByLabelText("مقدار تخصیص مرحله"), { target: { value: "40" } });
    fireEvent.change(screen.getByLabelText("دلیل اصلاح تخصیص"), { target: { value: "برنامه تازه" } });
    fireEvent.click(screen.getByRole("button", { name: "ذخیره تخصیص" }));
    await waitFor(() => expect(api.setStageCargoAllocation).toHaveBeenCalledWith(shipment, cargo, stageB, { dimension: "PLANNED", quantity: "40", expected_version: 1, reason: "برنامه تازه" }, expect.any(String)));
  });
});
