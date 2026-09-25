import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import RouteStageTransportExecutionSection from "../../components/RouteStageTransportExecutionSection";
import * as api from "../../lib/api";

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return {
    ...actual,
    getTransportExecutionOptions: vi.fn(),
    listRouteStageTransportExecutions: vi.fn(),
    createRouteStageTransportExecution: vi.fn(),
    reviseRouteStageTransportExecution: vi.fn(),
  };
});

const shipmentId = "11111111-1111-4111-8111-111111111111";
const ref = (public_id: string, code: string, fa_name: string) => ({
  public_id, code, fa_name, en_name: code,
});
const options: api.TransportExecutionOptions = {
  means: [ref("means-truck", "TRUCK", "کامیون"), ref("means-train", "TRAIN", "قطار")],
  equipment: [ref("equipment-trailer", "TRAILER", "تریلر"), ref("equipment-wagon", "WAGON", "واگن"), ref("equipment-container", "CONTAINER", "کانتینر")],
  carriers: [{ id: 1, label: "شرکت الف" }, { id: 2, label: "شرکت ب" }],
};
const revision = (
  number: number,
  identifier: string,
  incomplete_fields: string[] = [],
): api.TransportExecutionRevision => ({
  public_id: `revision-${number}`,
  revision_number: number,
  means: { ...options.means[0], currently_active: true },
  carrier: { id: 1, label: "شرکت الف", currently_active: true },
  means_identifier: identifier,
  means_details: null,
  driver: { name: null, contact: null },
  equipment: [{
    sequence: 1,
    type: { ...options.equipment[0], currently_active: true },
    identifier: number === 1 ? "T-01" : null,
    details: null,
  }],
  effective_at: "2026-09-25T10:00:00Z",
  recorded_at: "2026-09-25T10:01:00Z",
  recorded_by_user_id: 9,
  reason: number === 1 ? null : "تعویض وسیله",
  incomplete_fields,
});
const truck: api.RouteStageTransportExecution = {
  public_id: "assignment-truck",
  execution_public_id: "11111111-1111-4111-8111-111111111112",
  unit_version: 3,
  created_at: "2026-09-25T10:00:00Z",
  current: revision(2, "TRUCK-B", ["EQUIPMENT_IDENTIFIER"]),
  history: [revision(2, "TRUCK-B", ["EQUIPMENT_IDENTIFIER"]), revision(1, "TRUCK-A")],
};
const trainRevision: api.TransportExecutionRevision = {
  ...revision(1, "TRAIN-C"),
  public_id: "rail-revision",
  means: { ...options.means[1], currently_active: true },
  carrier: { id: 2, label: "شرکت ب", currently_active: true },
  equipment: [
    { sequence: 1, type: { ...options.equipment[1], currently_active: true }, identifier: "W-01", details: null },
    { sequence: 2, type: { ...options.equipment[2], currently_active: true }, identifier: "C-01", details: null },
  ],
  incomplete_fields: [],
};
const rail: api.RouteStageTransportExecution = {
  public_id: "assignment-rail",
  execution_public_id: "11111111-1111-4111-8111-111111111113",
  unit_version: 1,
  created_at: "2026-09-25T11:00:00Z",
  current: trainRevision,
  history: [trainRevision],
};
const list: api.RouteStageTransportExecutionList = {
  plan: { id: 12, revision_number: 3, status: "active", is_active: true },
  can_manage: true,
  stages: [{
    id: 21,
    sequence_number: 2,
    branch_label: "مرحله ریلی",
    origin: { display_name: "خرگوس" },
    destination: { display_name: "آکتائو" },
    executions: [truck, rail],
  }],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.getTransportExecutionOptions).mockResolvedValue({ data: options });
  vi.mocked(api.listRouteStageTransportExecutions).mockResolvedValue({ data: list });
  vi.mocked(api.createRouteStageTransportExecution).mockResolvedValue({ data: rail, meta: { created: true } });
  vi.mocked(api.reviseRouteStageTransportExecution).mockResolvedValue({ data: truck, meta: { created: true } });
});

describe("route-stage transport execution", () => {
  it("renders independent executions, a rail chain, neutral incompleteness, and history", async () => {
    render(<RouteStageTransportExecutionSection shipmentId={shipmentId} planId={12} />);
    expect(await screen.findByText("مرحله ریلی", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("TRUCK-B", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("TRAIN-C", { exact: false })).toBeInTheDocument();
    expect(screen.getByText(/واگن · W-01/)).toBeInTheDocument();
    expect(screen.getByText(/کانتینر · C-01/)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("مسئله عملیاتی محسوب نمی‌شود");
    expect(screen.getByText("دلیل آخرین تغییر: تعویض وسیله")).toBeInTheDocument();
    fireEvent.click(screen.getByText("سابقه تغییرات (1)"));
    expect(screen.getByText("TRUCK-A", { exact: false })).toBeInTheDocument();
    expect(screen.getByText(/کالا در این بخش تخصیص داده نمی‌شود/)).toBeInTheDocument();
  });

  it("creates a progressive rail execution with ordered wagon and container", async () => {
    render(<RouteStageTransportExecutionSection shipmentId={shipmentId} planId={12} />);
    const summary = await screen.findByText("افزودن اجرای حمل دیگر");
    fireEvent.click(summary);
    const createPanel = summary.parentElement as HTMLElement;
    fireEvent.change(within(createPanel).getByLabelText("نوع وسیله حمل"), { target: { value: "means-train" } });
    fireEvent.change(within(createPanel).getByLabelText("شرکت حمل"), { target: { value: "2" } });
    fireEvent.click(within(createPanel).getByRole("button", { name: "افزودن واحد یا ظرف" }));
    fireEvent.click(within(createPanel).getByRole("button", { name: "افزودن واحد یا ظرف" }));
    fireEvent.change(within(createPanel).getByLabelText("نوع واحد حمل 1"), { target: { value: "equipment-wagon" } });
    fireEvent.change(within(createPanel).getByLabelText("نوع واحد حمل 2"), { target: { value: "equipment-container" } });
    fireEvent.click(within(createPanel).getByRole("button", { name: "ثبت اجرای حمل" }));
    await waitFor(() => expect(api.createRouteStageTransportExecution).toHaveBeenCalledWith(
      shipmentId,
      12,
      21,
      expect.objectContaining({
        transport_means_type_public_id: "means-train",
        carrier_customer_id: 2,
        means_identifier: null,
        equipment: [
          expect.objectContaining({ type_public_id: "equipment-wagon" }),
          expect.objectContaining({ type_public_id: "equipment-container" }),
        ],
      }),
      expect.any(String),
    ));
  });

  it("records a new immutable version with optimistic concurrency", async () => {
    render(<RouteStageTransportExecutionSection shipmentId={shipmentId} planId={12} />);
    const cards = await screen.findAllByRole("article");
    fireEvent.click(within(cards[0]).getByText("تکمیل یا تغییر اطلاعات"));
    fireEvent.change(within(cards[0]).getByLabelText("شناسه وسیله حمل"), { target: { value: "TRUCK-C" } });
    fireEvent.click(within(cards[0]).getByRole("button", { name: "ثبت نسخه تازه" }));
    await waitFor(() => expect(api.reviseRouteStageTransportExecution).toHaveBeenCalledWith(
      shipmentId,
      12,
      truck.execution_public_id,
      expect.objectContaining({ expected_version: 3, means_identifier: "TRUCK-C" }),
      expect.any(String),
    ));
  });
});
