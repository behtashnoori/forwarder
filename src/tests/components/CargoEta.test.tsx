import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CargoEta, { CargoEtaPanel, type EtaSnapshot } from "@/components/CargoEta";

const api = vi.hoisted(() => ({ internal: vi.fn(), customer: vi.fn() }));
vi.mock("@/lib/api", () => ({ request: api.internal, listShipmentCargoItems: vi.fn() }));
vi.mock("@/lib/customerPortalApi", () => ({ customerRequest: api.customer }));
const estimate = (): EtaSnapshot => ({
  public_id: "estimate-1", sequence: 1, ruleset: "ETA_RULESET_V1", calculated_at: "2026-09-26T09:00:00Z",
  next: { available: true, target: "مقصد بعدی", earliest: "2026-09-26T10:00:00Z", latest: "2026-09-26T12:00:00Z", message: null },
  final: { available: false, target: "مقصد نهایی", earliest: null, latest: null, message: "زمان مرجع بخش باقی‌مانده تعریف نشده است." },
  as_of: "2026-09-25T08:00:00Z", recorded_at: "2026-09-26T08:00:00Z", basis_label: "گزارش موقعیت عملیاتی",
  unquantified_effect: true, planned_distance: null, authorization_revision: "scope-a",
});
beforeEach(() => {
  vi.resetAllMocks();
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
  api.internal.mockResolvedValue(estimate());
});

describe("Cargo ETA private range and history", () => {
  it("ensures only when its own panel is opened, shows independent results and distinct times", async () => {
    render(<CargoEtaPanel shipmentId="shipment" cargoId="cargo" />);
    expect(api.internal).not.toHaveBeenCalled();
    const details = screen.getByText("زمان تقریبی رسیدن کالا").parentElement as HTMLDetailsElement;
    details.open = true; fireEvent(details, new Event("toggle"));
    expect(await screen.findByText("زمان مرجع بخش باقی‌مانده تعریف نشده است.")).toBeInTheDocument();
    expect(screen.getByText(/زمان داده عملیاتی:/)).toBeInTheDocument();
    expect(screen.getByText(/زمان ثبت گزارش:/)).toBeInTheDocument();
    expect(screen.getByText(/مدت اثر عملیاتی/)).toBeInTheDocument();
    expect(screen.getByText("فاصله برنامه‌ریزی‌شده: تعریف نشده")).toBeInTheDocument();
    expect(api.internal).toHaveBeenCalledWith(expect.stringContaining("/eta/ensure"), expect.objectContaining({ method: "POST", body: "{}", cache: "no-store" }));
  });

  it("loads bounded history through a pure GET and retains a historical unavailable result", async () => {
    const old = { ...estimate(), public_id: "old", sequence: 2 };
    api.internal.mockImplementation((path: string) => Promise.resolve(path.includes("history") ? { items: [old], page: 1, has_next: false } : estimate()));
    render(<CargoEta shipmentId="shipment" cargoId="cargo" />);
    await screen.findByText(/زمان داده عملیاتی:/);
    fireEvent.click(screen.getByRole("button", { name: "برآوردهای قبلی" }));
    await screen.findByText(/برآورد قبلی ۲/);
    const call = api.internal.mock.calls.find(([path]) => path.includes("history"));
    expect(call?.[0]).toContain("history?page=1");
    expect(call?.[1].method).toBeUndefined();
    expect(screen.getByRole("button", { name: "صفحه بعد" })).toBeDisabled();
  });

  it("rechecks a delayed Customer response and renders only the new authorization revision", async () => {
    let complete!: (value: EtaSnapshot) => void;
    api.customer.mockImplementationOnce(() => new Promise(resolve => { complete = resolve; }))
      .mockResolvedValueOnce({ authorization_revision: "scope-b" })
      .mockResolvedValueOnce({ ...estimate(), authorization_revision: "scope-b", next: { ...estimate().next, target: "مقصد جدید" } })
      .mockResolvedValueOnce({ authorization_revision: "scope-b" });
    render(<CargoEta shipmentId="shipment" cargoId="cargo" customer />);
    await act(async () => complete(estimate()));
    await screen.findByText(/مقصد جدید/);
    expect(screen.queryByText(/نقطه مهم بعدی · مقصد بعدی/)).not.toBeInTheDocument();
    expect(api.customer).toHaveBeenCalledTimes(4);
  });

  it("clears on hide and does not restore cached estimates after a revoked session", async () => {
    api.customer.mockResolvedValueOnce(estimate()).mockResolvedValueOnce({ authorization_revision: "scope-a" })
      .mockRejectedValue(new Error("نشست پایان یافته است"));
    render(<CargoEta shipmentId="shipment" cargoId="cargo" customer />);
    await screen.findByText(/نقطه مهم بعدی · مقصد بعدی/);
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
    fireEvent(document, new Event("visibilitychange"));
    expect(screen.queryByText(/مقصد بعدی/)).not.toBeInTheDocument();
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
    fireEvent(document, new Event("visibilitychange"));
    expect(await screen.findByRole("alert")).toHaveTextContent("نشست پایان یافته است");
    expect(screen.queryByText(/مقصد بعدی/)).not.toBeInTheDocument();
  });

  it("discards a late response for a previously selected Cargo", async () => {
    let complete!: (value: EtaSnapshot) => void;
    api.internal.mockImplementationOnce(() => new Promise(resolve => { complete = resolve; }));
    const { rerender } = render(<CargoEta shipmentId="shipment" cargoId="cargo-a" />);
    api.internal.mockResolvedValue({ ...estimate(), next: { ...estimate().next, target: "کالای دوم" } });
    rerender(<CargoEta shipmentId="shipment" cargoId="cargo-b" />);
    await screen.findByText(/کالای دوم/);
    await act(async () => complete(estimate()));
    await waitFor(() => expect(screen.queryByText(/مقصد بعدی/)).not.toBeInTheDocument());
  });
});
