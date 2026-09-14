import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import RouteAuthoringSection from "../../components/RouteAuthoringSection";
import * as api from "../../lib/api";

const permissions = vi.hoisted(() => new Set<string>());
vi.mock("../../i18n", () => ({ useI18n: () => ({ businessLabel: (value: string) => value, transportLabel: (value: string) => value }) }));
vi.mock("../../components/OperationalPermission", () => ({ default: ({ permission, children }: { permission: string; children: React.ReactNode }) => permissions.has(permission) ? children : null }));
vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual,
    createRoutePlan: vi.fn(), addRouteLeg: vi.fn(), updateRouteLeg: vi.fn(), addRouteCheckpoint: vi.fn(), updateRouteCheckpoint: vi.fn(), validateRoutePlan: vi.fn(), activateRoutePlan: vi.fn(),
    fetchProvinces: vi.fn(), searchIranDestinations: vi.fn(), listLogisticsPoints: vi.fn(), fetchCountries: vi.fn(), fetchInternationalCities: vi.fn(),
  };
});

const shipmentId = "11111111-1111-4111-8111-111111111111";
const draft: api.RoutePlanDetail = {
  id: 12, revision_number: 1, status: "draft", is_active: false, version: 4,
  legs: [{ id: 21, sequence_number: 1, origin: { display_name: "Tehran" }, destination: { display_name: "Tabriz" }, transport_mode: "road", carrier_reference: null, planned_departure: "2026-01-01T00:00:00Z", planned_arrival: "2026-01-02T00:00:00Z", status: "planned", version: 2 }],
  checkpoints: [{ id: 31, route_leg_id: 21, canonical_location_id: 100, sequence_number: 1, checkpoint_type: "origin_loading", status: "planned", verification_state: "unreported", version: 3, planned_arrival_at: "2026-01-01T00:00:00Z", planned_departure_at: "2026-01-01T01:00:00Z", responsible_party: "Old", notes: "Old note", milestones: [] }],
  dependencies: [],
};
const reload = vi.fn(async () => true);
const renderDraft = (value = draft) => render(<RouteAuthoringSection shipmentId={shipmentId} draft={value} hasDraft reload={reload} />);
beforeEach(() => {
  vi.clearAllMocks();
  permissions.clear();
  for (const permission of ["route_plan.create", "route_leg.manage", "checkpoint.report", "route_plan.activate"]) permissions.add(permission);
  vi.mocked(api.fetchProvinces).mockResolvedValue([{ id: 1, name: "Tehran" }, { id: 2, name: "Tabriz" }]);
  vi.mocked(api.searchIranDestinations).mockResolvedValue({ data: [{ identity: { type: "city", id: 7 }, label: "Qom", province: null, secondary_label: "" }], meta: { count: 1, limit: 50 } });
  vi.mocked(api.listLogisticsPoints).mockResolvedValue({ items: [{ public_id: "facility-1", fa_name: "Depot", is_active: true, point_type: { fa_name: "Depot" } } as api.LogisticsPointView], page: 1, pages: 1, total: 1 });
  vi.mocked(api.fetchCountries).mockResolvedValue([]);
  vi.mocked(api.fetchInternationalCities).mockResolvedValue([]);
});

describe("governed route authoring", () => {
  it("offers draft creation without a route and hides it without capability", async () => {
    vi.mocked(api.createRoutePlan).mockResolvedValue({ data: draft });
    const { rerender } = render(<RouteAuthoringSection shipmentId={shipmentId} hasDraft={false} reload={reload} />);
    fireEvent.click(screen.getByRole("button", { name: "ایجاد مسیر عملیات" }));
    await waitFor(() => expect(api.createRoutePlan).toHaveBeenCalledWith(shipmentId));
    expect(reload).toHaveBeenCalledTimes(1);
    permissions.clear();
    rerender(<RouteAuthoringSection shipmentId={shipmentId} hasDraft={false} reload={reload} />);
    expect(screen.queryByRole("button", { name: "ایجاد مسیر عملیات" })).not.toBeInTheDocument();
    expect(screen.getByText(/هنوز برنامه مسیر فعالی/)).toBeInTheDocument();
  });

  it("never offers a second create command while a draft detail is loading", () => {
    render(<RouteAuthoringSection shipmentId={shipmentId} hasDraft reload={reload} />);
    expect(screen.queryByRole("button", { name: "ایجاد مسیر عملیات" })).not.toBeInTheDocument();
  });

  it("blocks a repeat create when the write succeeds but authoritative reload fails", async () => {
    vi.mocked(api.createRoutePlan).mockResolvedValue({ data: draft });
    reload.mockResolvedValueOnce(false);
    render(<RouteAuthoringSection shipmentId={shipmentId} hasDraft={false} reload={reload} />);
    fireEvent.click(screen.getByRole("button", { name: "ایجاد مسیر عملیات" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("دریافت وضعیت تازه مسیر ممکن نشد");
    expect(screen.getByRole("button", { name: "ایجاد مسیر عملیات" })).toBeDisabled();
    expect(api.createRoutePlan).toHaveBeenCalledTimes(1);
  });

  it("checks authoritative state before retrying an uncertain draft creation", async () => {
    vi.mocked(api.createRoutePlan).mockRejectedValue(new Error("Network unavailable"));
    reload.mockResolvedValueOnce(false);
    render(<RouteAuthoringSection shipmentId={shipmentId} hasDraft={false} reload={reload} />);
    fireEvent.click(screen.getByRole("button", { name: "ایجاد مسیر عملیات" }));
    await waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("button", { name: "ایجاد مسیر عملیات" })).toBeDisabled();
    expect(screen.queryByText("Network unavailable")).not.toBeInTheDocument();
  });

  it("adds a leg with distinct canonical geography and optional facility identity", async () => {
    vi.mocked(api.addRouteLeg).mockResolvedValue({ data: draft.legs[0] });
    renderDraft();
    fireEvent.click(screen.getByRole("button", { name: "افزودن بخش مسیر" }));
    await screen.findAllByRole("option", { name: "استان · Tehran" });
    fireEvent.change(screen.getByLabelText("مبدأ"), { target: { value: "province:1" } });
    fireEvent.change(screen.getByLabelText("مقصد"), { target: { value: "logistics_point:facility-1" } });
    fireEvent.change(screen.getByLabelText("حرکت برنامه‌ریزی‌شده"), { target: { value: "2026-01-03T10:00" } });
    fireEvent.change(screen.getByLabelText("رسیدن برنامه‌ریزی‌شده"), { target: { value: "2026-01-04T10:00" } });
    fireEvent.click(screen.getByRole("button", { name: "ذخیره بخش مسیر" }));
    await waitFor(() => expect(api.addRouteLeg).toHaveBeenCalledWith(shipmentId, draft.id, expect.objectContaining({ sequence_number: 2, origin: { source_type: "province", source_id: 1 }, destination: { source_type: "logistics_point", source_id: "facility-1" }, planned_departure: new Date("2026-01-03T10:00").toISOString() })));
    expect(reload).toHaveBeenCalled();
  });

  it("starts the first leg at sequence one while leaving validation to the backend", async () => {
    vi.mocked(api.addRouteLeg).mockResolvedValue({ data: draft.legs[0] });
    renderDraft({ ...draft, legs: [], checkpoints: [] });
    fireEvent.click(screen.getByRole("button", { name: "افزودن بخش مسیر" }));
    await screen.findAllByRole("option", { name: "استان · Tehran" });
    expect(screen.getByLabelText("ترتیب بخش مسیر")).toHaveValue(1);
    fireEvent.change(screen.getByLabelText("مبدأ"), { target: { value: "province:1" } });
    fireEvent.change(screen.getByLabelText("مقصد"), { target: { value: "province:2" } });
    fireEvent.change(screen.getByLabelText("حرکت برنامه‌ریزی‌شده"), { target: { value: "2026-01-03T10:00" } });
    fireEvent.change(screen.getByLabelText("رسیدن برنامه‌ریزی‌شده"), { target: { value: "2026-01-04T10:00" } });
    fireEvent.click(screen.getByRole("button", { name: "ذخیره بخش مسیر" }));
    await waitFor(() => expect(api.addRouteLeg).toHaveBeenCalledWith(shipmentId, draft.id, expect.objectContaining({ sequence_number: 1 })));
  });

  it("loads governed international cities for the selected country", async () => {
    vi.mocked(api.fetchCountries).mockResolvedValue([{ id: 9, name: "Turkey", name_en: "Turkey", code: "TR" }]);
    vi.mocked(api.fetchInternationalCities).mockResolvedValue([{ id: 19, name: "Istanbul", name_en: "Istanbul", city_type: "city", is_major_port: false, is_major_airport: false }]);
    vi.mocked(api.addRouteLeg).mockResolvedValue({ data: draft.legs[0] });
    renderDraft();
    fireEvent.click(screen.getByRole("button", { name: "افزودن بخش مسیر" }));
    await screen.findAllByRole("option", { name: "Turkey" });
    fireEvent.change(screen.getByLabelText("مبدأ کشور شهر بین‌المللی"), { target: { value: "9" } });
    await waitFor(() => expect(api.fetchInternationalCities).toHaveBeenCalledWith(9));
    await screen.findByRole("option", { name: "شهر بین‌المللی · Istanbul" });
    fireEvent.change(screen.getByLabelText("مبدأ"), { target: { value: "international_city:19" } });
    fireEvent.change(screen.getByLabelText("مقصد"), { target: { value: "province:1" } });
    fireEvent.change(screen.getByLabelText("حرکت برنامه‌ریزی‌شده"), { target: { value: "2026-01-03T10:00" } });
    fireEvent.change(screen.getByLabelText("رسیدن برنامه‌ریزی‌شده"), { target: { value: "2026-01-04T10:00" } });
    fireEvent.click(screen.getByRole("button", { name: "ذخیره بخش مسیر" }));
    await waitFor(() => expect(api.addRouteLeg).toHaveBeenCalledWith(shipmentId, draft.id, expect.objectContaining({ origin: { source_type: "international_city", source_id: 19 } })));
  });

  it("edits only the leg fields supported by the backend and sends its version", async () => {
    vi.mocked(api.updateRouteLeg).mockResolvedValue({ data: draft.legs[0] });
    renderDraft();
    fireEvent.click(screen.getByRole("button", { name: "ویرایش بخش مسیر" }));
    fireEvent.change(screen.getByLabelText("ترتیب بخش مسیر"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "ذخیره بخش مسیر" }));
    await waitFor(() => expect(api.updateRouteLeg).toHaveBeenCalledWith(shipmentId, draft.id, 21, expect.objectContaining({ expected_version: 2, sequence_number: 2 })));
    expect(screen.queryByLabelText("حرکت برنامه‌ریزی‌شده")).not.toBeInTheDocument();
  });

  it("adds a checkpoint with authoritative leg association and edits supported fields", async () => {
    vi.mocked(api.addRouteCheckpoint).mockResolvedValue({ data: draft.checkpoints[0] });
    vi.mocked(api.updateRouteCheckpoint).mockResolvedValue({ data: draft.checkpoints[0] });
    renderDraft();
    fireEvent.click(screen.getByRole("button", { name: "افزودن نقطه کنترل" }));
    await screen.findByRole("option", { name: "استان · Tehran" });
    fireEvent.change(screen.getByLabelText("مکان نقطه کنترل"), { target: { value: "province:1" } });
    fireEvent.change(screen.getByLabelText("بخش مسیر مرتبط (اختیاری)"), { target: { value: "21" } });
    fireEvent.change(screen.getByLabelText("رسیدن برنامه‌ریزی‌شده"), { target: { value: "2026-01-03T10:00" } });
    fireEvent.click(screen.getByRole("button", { name: "ذخیره نقطه کنترل" }));
    await waitFor(() => expect(api.addRouteCheckpoint).toHaveBeenCalledWith(shipmentId, draft.id, expect.objectContaining({ sequence_number: 2, location: { source_type: "province", source_id: 1 }, route_leg_id: 21 })));
    fireEvent.click(screen.getByRole("button", { name: "ویرایش نقطه کنترل" }));
    fireEvent.change(screen.getByLabelText("مسئول (اختیاری)"), { target: { value: "New" } });
    fireEvent.click(screen.getByRole("button", { name: "ذخیره نقطه کنترل" }));
    await waitFor(() => expect(api.updateRouteCheckpoint).toHaveBeenCalledWith(shipmentId, draft.id, 31, { expected_version: 3, responsible_party: "New", notes: "Old note" }));
  });

  it("shows backend validation findings and activates only after valid response", async () => {
    vi.mocked(api.validateRoutePlan).mockResolvedValueOnce({ data: { valid: false, errors: [{ code: "ROUTE_SEQUENCE_GAP", field: "sequence_number", severity: "error" }] } }).mockResolvedValueOnce({ data: { valid: true, errors: [] } });
    vi.mocked(api.activateRoutePlan).mockResolvedValue({});
    renderDraft();
    fireEvent.click(screen.getByRole("button", { name: "بررسی و اعتبارسنجی مسیر" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("ترتیب بخش‌های مسیر باید پیوسته باشد");
    expect(screen.queryByRole("button", { name: "فعال‌سازی مسیر" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "بررسی و اعتبارسنجی مسیر" }));
    fireEvent.click(await screen.findByRole("button", { name: "فعال‌سازی مسیر" }));
    await waitFor(() => expect(api.activateRoutePlan).toHaveBeenCalledWith(shipmentId, draft.id, draft.version));
    expect(reload).toHaveBeenCalled();
  });

  it("reloads a stale plan and shows a safe conflict message", async () => {
    vi.mocked(api.updateRouteLeg).mockRejectedValue(new api.ApiError(409, "STALE_ROUTE_VERSION", "database detail"));
    renderDraft();
    fireEvent.click(screen.getByRole("button", { name: "ویرایش بخش مسیر" }));
    fireEvent.click(screen.getByRole("button", { name: "ذخیره بخش مسیر" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("نسخه تازه بارگذاری شد");
    expect(screen.queryByText("database detail")).not.toBeInTheDocument();
    expect(reload).toHaveBeenCalled();
  });

  it("requires fresh validation after an activation version conflict", async () => {
    vi.mocked(api.validateRoutePlan).mockResolvedValue({ data: { valid: true, errors: [] } });
    vi.mocked(api.activateRoutePlan).mockRejectedValue(new api.ApiError(409, "STALE_ROUTE_VERSION", "database detail"));
    renderDraft();
    fireEvent.click(screen.getByRole("button", { name: "بررسی و اعتبارسنجی مسیر" }));
    fireEvent.click(await screen.findByRole("button", { name: "فعال‌سازی مسیر" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("نسخه تازه بارگذاری شد");
    expect(screen.queryByRole("button", { name: "فعال‌سازی مسیر" })).not.toBeInTheDocument();
    expect(reload).toHaveBeenCalled();
  });

  it.each([
    ["ROUTE_SEQUENCE_DUPLICATE", "شماره ترتیب"],
    ["INVALID_ROUTE_TIMELINE", "ترتیب زمانی"],
    ["LOCATION_MAPPING_REQUIRED", "مکان انتخاب‌شده"],
  ])("explains %s without exposing backend details", async (code, message) => {
    vi.mocked(api.updateRouteLeg).mockRejectedValue(new api.ApiError(409, code, "database detail"));
    renderDraft();
    fireEvent.click(screen.getByRole("button", { name: "ویرایش بخش مسیر" }));
    fireEvent.click(screen.getByRole("button", { name: "ذخیره بخش مسیر" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.queryByText("database detail")).not.toBeInTheDocument();
  });

  it("keeps draft state readable when structural permissions are absent", () => {
    permissions.clear();
    renderDraft();
    expect(screen.getByText(/پیش‌نویس برنامه مسیر/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "افزودن بخش مسیر" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "افزودن نقطه کنترل" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "فعال‌سازی مسیر" })).not.toBeInTheDocument();
  });

  it("keeps actual-bearing draft segments read-only", () => {
    renderDraft({ ...draft, legs: [{ ...draft.legs[0], actual_departure: "2026-01-01T00:00:00Z" }], checkpoints: [{ ...draft.checkpoints[0], actual_arrival_at: "2026-01-01T00:00:00Z" }] });
    expect(screen.getAllByText("دارای رخداد واقعی؛ فقط خواندنی")).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "ویرایش بخش مسیر" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "ویرایش نقطه کنترل" })).not.toBeInTheDocument();
  });
});
