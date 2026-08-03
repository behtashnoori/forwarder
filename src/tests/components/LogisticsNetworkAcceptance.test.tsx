import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LogisticsNetworkAdminTab from "@/components/LogisticsNetworkAdminTab";
import ProjectLogisticsNetwork from "@/components/ProjectLogisticsNetwork";

const api = vi.hoisted(() => ({
  createLogisticsPoint: vi.fn(), createLogisticsPointType: vi.fn(), listLogisticsPoints: vi.fn(),
  listLogisticsPointTypes: vi.fn(), setLogisticsPointActive: vi.fn(), setLogisticsPointTypeActive: vi.fn(),
  updateLogisticsPoint: vi.fn(), updateLogisticsPointType: vi.fn(), createProjectLogisticsPoint: vi.fn(),
  listProjectLogisticsPoints: vi.fn(), reorderProjectLogisticsPoints: vi.fn(), setProjectLogisticsPointActive: vi.fn(),
}));
vi.mock("@/lib/api", () => api);

const type = { public_id: "type-1", immutable_code: "WAREHOUSE", fa_name: "انبار", en_name: "Warehouse", display_order: 1, is_active: true, version: 1 };
const point = { public_id: "point-1", immutable_code: "LP-1", fa_name: "انبار مرکزی", en_name: "Central", is_active: true, version: 1, point_type: type, country: { code: "IR", fa_name: "ایران", en_name: "Iran" } };
const second = { ...point, public_id: "point-2", immutable_code: "LP-2", fa_name: "انبار دوم" };
const rows = [point, second].map((logistics_point, index) => ({ public_id: `assoc-${index + 1}`, project_role: index ? "DESTINATION" : "ORIGIN", sequence_number: index + 1, is_active: true, version: 1, logistics_point }));

describe("Release 1.7.0 logistics network acceptance", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listLogisticsPointTypes.mockResolvedValue({ items: [type] });
    api.listLogisticsPoints.mockResolvedValue({ items: [point, second], page: 1, pages: 1, total: 2 });
    api.listProjectLogisticsPoints.mockResolvedValue({ items: rows });
    api.createLogisticsPoint.mockResolvedValue({ item: point });
    api.updateLogisticsPoint.mockResolvedValue({ item: { ...point, version: 2 } });
    api.setLogisticsPointActive.mockResolvedValue({ item: { ...point, is_active: false } });
    api.createProjectLogisticsPoint.mockResolvedValue({ item: rows[0] });
    api.reorderProjectLogisticsPoints.mockResolvedValue({ items: [...rows].reverse() });
    api.setProjectLogisticsPointActive.mockResolvedValue({ item: { ...rows[0], is_active: false } });
  });

  it("covers admin create, update, lifecycle, and probable duplicate confirmation", async () => {
    render(<LogisticsNetworkAdminTab />);
    await screen.findByText("LP-1");
    fireEvent.change(screen.getByPlaceholderText("Immutable code"), { target: { value: "LP-3" } });
    fireEvent.change(screen.getByPlaceholderText("Persian name"), { target: { value: "نقطه سوم" } });
    fireEvent.change(screen.getByDisplayValue("Point type"), { target: { value: type.public_id } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(api.createLogisticsPoint).toHaveBeenCalledWith(expect.objectContaining({ immutable_code: "LP-3", point_type_public_id: type.public_id })));

    fireEvent.click(screen.getAllByRole("button", { name: "Edit" })[0]);
    fireEvent.change(screen.getByLabelText("Persian name"), { target: { value: "نام جدید" } });
    fireEvent.change(screen.getByLabelText("English name"), { target: { value: "Updated" } });
    fireEvent.change(screen.getByLabelText("Short address"), { target: { value: "Address" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(api.updateLogisticsPoint).toHaveBeenCalledWith(point.public_id, expect.objectContaining({ version: 1, fa_name: "نام جدید" })));
    fireEvent.click(screen.getAllByRole("button", { name: "Deactivate" })[0]);
    await waitFor(() => expect(api.setLogisticsPointActive).toHaveBeenCalledWith(point, false));

    api.createLogisticsPoint.mockRejectedValueOnce(new Error("Probable duplicate requires explicit confirmation"));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByRole("button", { name: "Confirm distinct point" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Confirm distinct point" }));
    await waitFor(() => expect(api.createLogisticsPoint).toHaveBeenLastCalledWith(expect.objectContaining({ confirm_probable_duplicate: true })));
  });

  it("selects governed points, assigns role/sequence, reorders, and toggles without free-text master creation", async () => {
    render(<ProjectLogisticsNetwork projectId="project-1" />);
    await screen.findByText("LP-1", { exact: false });
    expect(screen.queryByPlaceholderText("Immutable code")).toBeNull();
    const selects = screen.getAllByRole("combobox");
    fireEvent.change(selects[1], { target: { value: point.public_id } });
    fireEvent.change(selects[2], { target: { value: "LOADING" } });
    fireEvent.change(screen.getByRole("spinbutton"), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: /existing|موجود/i }));
    await waitFor(() => expect(api.createProjectLogisticsPoint).toHaveBeenCalledWith("project-1", expect.objectContaining({ logistics_point_public_id: point.public_id, project_role: "LOADING", sequence_number: 3 })));
    fireEvent.click(screen.getAllByRole("button", { name: "↓" })[0]);
    await waitFor(() => expect(api.reorderProjectLogisticsPoints).toHaveBeenCalledWith("project-1", [rows[1], rows[0]]));
    fireEvent.click(screen.getAllByRole("button").at(-1)!);
    await waitFor(() => expect(api.setProjectLogisticsPointActive).toHaveBeenCalled());
  });

  it("reorders active rows correctly when an inactive row is interleaved", async () => {
    const mixedRows = [rows[0], { ...rows[0], public_id: "assoc-inactive", is_active: false }, rows[1]];
    api.listProjectLogisticsPoints.mockResolvedValue({ items: mixedRows });
    render(<ProjectLogisticsNetwork projectId="project-1" />);
    await screen.findByText("LP-1", { exact: false });

    fireEvent.click(screen.getAllByRole("button", { name: "↑" })[1]);

    await waitFor(() => expect(api.reorderProjectLogisticsPoints).toHaveBeenCalledWith("project-1", [rows[1], rows[0]]));
  });
});
