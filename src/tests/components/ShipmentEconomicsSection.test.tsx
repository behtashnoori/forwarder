import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ShipmentEconomicsSection from "../../components/ShipmentEconomicsSection";
import * as api from "../../lib/api";

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return {
    ...actual,
    getEconomicProjection: vi.fn(),
    listEconomicLines: vi.fn(),
    previewCommercialEconomics: vi.fn(),
  };
});

vi.mock("../../components/OperationalPermission", () => ({
  default: ({ children }: { children: React.ReactNode }) => children,
}));

const projection = {
  shipment_public_id: "shipment-public",
  calculated_at: "2026-08-09T00:00:00Z",
  stages: {
    ESTIMATE: { revenue: { amount: "100.000000", currency: "USD" }, cost: null, margin: null, currency: "USD", completeness: "INCOMPLETE" as const, missing_inputs: ["COST_VISIBILITY_RESTRICTED"], source_observation_ids: [], applied_fx_rate_ids: [] },
    COMMITMENT: { revenue: null, cost: null, margin: null, currency: null, completeness: "INCOMPLETE" as const, missing_inputs: [], source_observation_ids: [], applied_fx_rate_ids: [] },
    ACTUAL: { revenue: null, cost: null, margin: null, currency: null, completeness: "INCOMPLETE" as const, missing_inputs: [], source_observation_ids: [], applied_fx_rate_ids: [] },
  },
};

describe("ShipmentEconomicsSection capability isolation", () => {
  beforeEach(() => {
    vi.mocked(api.getEconomicProjection).mockResolvedValue({ data: projection });
    vi.mocked(api.listEconomicLines).mockResolvedValue({ data: [] });
    vi.mocked(api.previewCommercialEconomics).mockRejectedValue(new Error("forbidden"));
  });

  it("keeps authorized projection and line reads visible when optional preview is forbidden", async () => {
    render(<ShipmentEconomicsSection shipmentPublicId="shipment-public" />);
    expect(await screen.findByText("Revenue: 100.000000 USD")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByText(/Accepted commercial intent/)).not.toBeInTheDocument();
    expect(api.getEconomicProjection).toHaveBeenCalledWith("shipment-public");
    expect(api.listEconomicLines).toHaveBeenCalledWith("shipment-public");
    expect(api.previewCommercialEconomics).toHaveBeenCalledWith("shipment-public");
  });

  it("still surfaces a core projection failure", async () => {
    vi.mocked(api.getEconomicProjection).mockRejectedValue(new Error("projection forbidden"));
    render(<ShipmentEconomicsSection shipmentPublicId="shipment-public" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("projection forbidden");
  });
});
