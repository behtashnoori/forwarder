import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ShipmentOperationalStages from "@/components/ShipmentOperationalStages";
import ShipmentStageConfigurationTab from "@/components/ShipmentStageConfigurationTab";

const api = vi.hoisted(() => ({ configuration: vi.fn(), save: vi.fn(), stages: vi.fn(), event: vi.fn() }));
vi.mock("@/lib/shipmentStagesApi", () => ({
  getShipmentStageConfiguration: api.configuration,
  saveShipmentStageConfiguration: api.save,
  getShipmentOperationalStages: api.stages,
  recordShipmentStageEvent: api.event,
}));

const canonical = [
  ["PREPARATION_LOADING", "آماده‌سازی / بارگیری"],
  ["ORIGIN_DEPARTURE", "خروج از مبدأ"],
  ["IN_TRANSIT", "در مسیر"],
  ["DESTINATION_ARRIVAL", "رسیدن به مقصد"],
  ["UNLOADING", "تخلیه"],
].map(([code, display_name_fa]) => ({code, display_name_fa}));

const configured = canonical.map((stage, index) => ({
  ...stage,
  public_id: `stage-${index + 1}`,
  configuration_public_id: `configured-${index + 1}`,
  sequence: index + 1,
  active: true,
  required_for_completion: true,
}));

describe("Organization Shipment stages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.configuration.mockResolvedValue({data: {canonical_stages: canonical, versions: []}});
    api.save.mockResolvedValue({data: {public_id: "version", created: true}});
    api.stages.mockResolvedValue({data: {
      configuration: {public_id: "policy-1", version: 1, effective_from: "2026-09-01T00:00:00Z", recorded_at: "2026-09-01T00:00:00Z", stages: configured},
      pinned: false,
      instance_public_id: null,
      stages: configured.map(stage => ({...stage, status: "NOT_STARTED", started_at: null, completed_at: null})),
      can_record: true,
      project_required: false,
    }});
    api.event.mockResolvedValue({data: {public_id: "event", created: true}});
  });

  it("publishes exactly the five canonical active required stages from Organization Admin", async () => {
    render(<ShipmentStageConfigurationTab />);
    fireEvent.click(await screen.findByRole("button", {name: "تعریف نسخه تازه مراحل"}));
    expect(screen.getAllByText("الزامی برای تکمیل")).toHaveLength(5);
    fireEvent.change(screen.getByLabelText("شروع اعتبار (زمان محلی)"), {target: {value: "2030-01-01T09:00"}});
    fireEvent.click(screen.getByRole("button", {name: "انتشار نسخه مراحل"}));
    await waitFor(() => expect(api.save).toHaveBeenCalled());
    const payload = api.save.mock.calls[0][0];
    expect(payload.stages).toHaveLength(5);
    expect(payload.stages.map((stage: {code: string}) => stage.code)).toEqual(canonical.map(stage => stage.code));
    expect(payload.stages.every((stage: {active: boolean; required_for_completion: boolean}) => stage.active && stage.required_for_completion)).toBe(true);
  });

  it("shows a project-independent explicit chain and records only the selected event", async () => {
    render(<ShipmentOperationalStages shipmentId="shipment" />);
    expect(await screen.findByText(/این زنجیره به پروژه وابسته نیست/)).toBeInTheDocument();
    expect(screen.getAllByText(/شروع‌نشده/)).toHaveLength(5);
    fireEvent.change(screen.getByLabelText("زمان رخداد مرحله"), {target: {value: "2026-09-30T09:00"}});
    fireEvent.click(screen.getAllByRole("button", {name: "شروع مرحله"})[0]);
    await waitFor(() => expect(api.event).toHaveBeenCalledWith(
      "shipment",
      "stage-1",
      expect.objectContaining({event_type: "STARTED", expected_policy_version_public_id: "policy-1"}),
      expect.any(String),
    ));
  });
});
