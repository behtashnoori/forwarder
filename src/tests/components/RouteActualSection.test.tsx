import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import RouteActualSection from "../../components/RouteActualSection";
import * as api from "../../lib/api";

vi.mock("../../components/OperationalPermission", () => ({ default: ({ children }: { children: React.ReactNode }) => children }));
vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, fetchProvinces: vi.fn(), searchIranDestinations: vi.fn(), listLogisticsPoints: vi.fn(), fetchCountries: vi.fn(), fetchInternationalCityPage: vi.fn(), recordActualRouteTraversal: vi.fn() };
});

const shipmentId = "11111111-1111-4111-8111-111111111111";
const plan: api.RoutePlanDetail = {
  id: 12, revision_number: 2, status: "active", is_active: true, version: 2,
  legs: [{ id: 21, sequence_number: 1, branch_label: "بخش مشترک", origin: { display_name: "تهران", canonical_reference: { source_type: "province", source_id: 1 } }, destination: { display_name: "تبریز", canonical_reference: { source_type: "province", source_id: 2 } }, transport_mode: "road", planned_departure: "2026-01-01T00:00:00Z", planned_arrival: "2026-01-02T00:00:00Z", status: "planned", version: 1 }],
  checkpoints: [], dependencies: [], cargo_destinations: [], is_complete: true, incomplete_fields: [],
  actual_route: [{ id: 30, public_id: "33333333-3333-4333-8333-333333333333", sequence_number: 1, planned_route_leg_id: 21, origin: { display_name: "قم" }, destination: { display_name: "تبریز" }, departed_at: "2026-01-01T01:00:00Z", arrived_at: "2026-01-01T03:00:00Z", notes: "تغییر مسیر", is_deviation: true, version: 1, recorded_at: "2026-01-01T03:01:00Z" }],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.fetchProvinces).mockResolvedValue([{ id: 1, name: "تهران" }, { id: 2, name: "تبریز" }]);
  vi.mocked(api.searchIranDestinations).mockResolvedValue({ data: [], meta: { count: 0, limit: 50 } });
  vi.mocked(api.listLogisticsPoints).mockResolvedValue({ items: [], page: 1, pages: 1, total: 0 });
  vi.mocked(api.fetchCountries).mockResolvedValue([]);
  vi.mocked(api.recordActualRouteTraversal).mockResolvedValue({ data: plan.actual_route![0] });
});

describe("actual route facts", () => {
  it("shows plan deviation separately and appends a fact without changing the plan", async () => {
    const reload = vi.fn(async () => true);
    render(<RouteActualSection shipmentId={shipmentId} plan={plan} reload={reload} />);
    expect(screen.getByText("متفاوت از برنامه")).toBeInTheDocument();
    expect(screen.getByText(/به‌تنهایی مورد استثنا ایجاد نمی‌کند/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "افزودن پیمایش واقعی" }));
    expect(await screen.findAllByRole("option", { name: "استان · تهران" })).toHaveLength(2);
    fireEvent.change(screen.getByLabelText("بخش برنامه مرتبط (اختیاری)"), { target: { value: "21" } });
    fireEvent.change(screen.getByLabelText("زمان واقعی حرکت"), { target: { value: "2026-01-01T04:00" } });
    fireEvent.click(screen.getByRole("button", { name: "ثبت واقعیت پیمایش" }));
    await waitFor(() => expect(api.recordActualRouteTraversal).toHaveBeenCalledWith(shipmentId, plan.id, expect.objectContaining({
      planned_route_leg_id: 21,
      origin: { source_type: "province", source_id: 1 },
      destination: { source_type: "province", source_id: 2 },
    })));
    expect(reload).toHaveBeenCalled();
  });
});
