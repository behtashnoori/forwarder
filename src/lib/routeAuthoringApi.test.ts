import { beforeEach, describe, expect, it, vi } from "vitest";
import { activateRoutePlan, addRouteCheckpoint, addRouteLeg, createRoutePlan, updateRouteCheckpoint, updateRouteLeg, validateRoutePlan } from "./api";

const shipment = "11111111-1111-4111-8111-111111111111";
const base = `/api/operational-shipments/${shipment}/route-plans`;
const calls: Array<{ url: string; init: RequestInit }> = [];
beforeEach(() => {
  calls.length = 0;
  localStorage.clear();
  vi.stubGlobal("fetch", vi.fn(async (url: RequestInfo | URL, init: RequestInit = {}) => {
    calls.push({ url: String(url), init });
    return new Response(JSON.stringify({ data: { valid: true, errors: [] } }), { status: 200, headers: { "Content-Type": "application/json" } });
  }));
});

describe("route authoring client contract", () => {
  it("uses shipment-scoped draft, validation and activation commands", async () => {
    await createRoutePlan(shipment);
    await validateRoutePlan(shipment, 12);
    await activateRoutePlan(shipment, 12, 4);
    expect(calls.map((call) => [call.url, call.init.method])).toEqual([
      [base, "POST"], [base + "/12/validate", "POST"], [base + "/12/activate", "POST"],
    ]);
    expect(JSON.parse(String(calls[2].init.body))).toEqual({ expected_version: 4 });
  });

  it("keeps typed location identity and expected versions in structural writes", async () => {
    const leg = { sequence_number: 1, origin: { source_type: "province" as const, source_id: 1 }, destination: { source_type: "logistics_point" as const, source_id: "point-uuid" }, transport_mode: "road", planned_departure: "2026-01-01T00:00:00Z", planned_arrival: "2026-01-02T00:00:00Z" };
    await addRouteLeg(shipment, 12, leg);
    await updateRouteLeg(shipment, 12, 21, { expected_version: 3, sequence_number: 2 });
    await addRouteCheckpoint(shipment, 12, { sequence_number: 1, checkpoint_type: "origin_loading", location: { source_type: "province", source_id: 1 }, route_leg_id: 21, planned_arrival_at: "2026-01-01T00:00:00Z" });
    await updateRouteCheckpoint(shipment, 12, 31, { expected_version: 2, notes: "Reviewed" });
    expect(calls.map((call) => [call.url, call.init.method])).toEqual([
      [base + "/12/legs", "POST"], [base + "/12/legs/21", "PATCH"],
      [base + "/12/checkpoints", "POST"], [base + "/12/checkpoints/31", "PATCH"],
    ]);
    expect(JSON.parse(String(calls[0].init.body))).toEqual(leg);
    expect(JSON.parse(String(calls[1].init.body))).toEqual({ expected_version: 3, sequence_number: 2 });
    expect(JSON.parse(String(calls[2].init.body)).location).toEqual({ source_type: "province", source_id: 1 });
    expect(JSON.parse(String(calls[3].init.body))).toEqual({ expected_version: 2, notes: "Reviewed" });
  });
});
