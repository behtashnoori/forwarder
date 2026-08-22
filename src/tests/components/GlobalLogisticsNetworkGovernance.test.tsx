import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import GlobalLogisticsNetworkAdminTab from "@/components/GlobalLogisticsNetworkAdminTab";

const api = vi.hoisted(() => ({
  listGlobalLogisticsPoints: vi.fn(), listLogisticsPointTypes: vi.fn(),
  createGlobalLogisticsPoint: vi.fn(), updateGlobalLogisticsPoint: vi.fn(),
  transitionGlobalLogisticsPoint: vi.fn(),
}));
vi.mock("@/lib/api", async (original) => ({ ...(await original<typeof import("@/lib/api")>()), ...api }));

const row = { public_id:"opaque-point",immutable_code:"CN-PORT-1",fa_name:"بندر",en_name:"Port",
  facility_identity_key:"port-1",lifecycle_status:"DRAFT",verification_status:"UNVERIFIED",version:1,
  point_type:{public_id:"type-1",code:"PORT",fa_name:"بندر",en_name:"Port"},
  country:{code:"CN",fa_name:"چین",en_name:"China"},geography:{city:"Shanghai",timezone:"Asia/Shanghai"},
  aliases:[],supported_modes:["SEA"],corridor_tags:[],external_codes:[],
  sources:[{organization:"Authority",reference:"ref",version:"1"}] };

describe("Global Logistics Network governance UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listGlobalLogisticsPoints.mockResolvedValue({items:[row],page:1,pages:1,total:1});
    api.listLogisticsPointTypes.mockResolvedValue({items:[{public_id:"type-1",immutable_code:"PORT"}]});
    api.createGlobalLogisticsPoint.mockResolvedValue({item:row});
    api.updateGlobalLogisticsPoint.mockResolvedValue({item:{...row,version:2}});
    api.transitionGlobalLogisticsPoint.mockResolvedValue({item:{...row,verification_status:"REVIEWED",version:2}});
    vi.spyOn(window, "prompt").mockReturnValue("governance:evidence");
  });

  it("supports filters, draft creation, opaque detail, and governed actions", async () => {
    render(<GlobalLogisticsNetworkAdminTab/>);
    await screen.findByText("CN-PORT-1");
    fireEvent.change(screen.getByLabelText("Country filter"), {target:{value:"CN"}});
    await waitFor(() => expect(api.listGlobalLogisticsPoints).toHaveBeenLastCalledWith(expect.objectContaining({country:"CN"})));
    fireEvent.click(screen.getByText("CN-PORT-1"));
    expect(screen.getByText(/Opaque ID: opaque-point/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", {name:"Review"}));
    await waitFor(() => expect(api.transitionGlobalLogisticsPoint).toHaveBeenCalledWith(row,"review",expect.objectContaining({evidence_reference:expect.any(String)})));
    fireEvent.click(screen.getByRole("button", {name:"ایجاد پیش‌نویس"}));
    fireEvent.change(screen.getByLabelText("کد ثابت"), {target:{value:"CN-NEW-PORT"}});
    fireEvent.click(screen.getByRole("button", {name:"ایجاد DRAFT"}));
    await waitFor(() => expect(api.createGlobalLogisticsPoint).toHaveBeenCalledWith(expect.objectContaining({immutable_code:"CN-NEW-PORT"})));
  });

  it("sends expected versions and confirms deprecation", async () => {
    vi.spyOn(window,"confirm").mockReturnValue(true);
    api.listGlobalLogisticsPoints.mockResolvedValue({items:[{...row,lifecycle_status:"ACTIVE",verification_status:"VERIFIED",version:4}],page:1,pages:1,total:1});
    render(<GlobalLogisticsNetworkAdminTab/>); await screen.findByText("CN-PORT-1"); fireEvent.click(screen.getByText("CN-PORT-1"));
    fireEvent.click(screen.getByRole("button", {name:"Deprecate"}));
    await waitFor(() => expect(api.transitionGlobalLogisticsPoint).toHaveBeenCalledWith(expect.objectContaining({version:4}),"deprecate",expect.any(Object)));
  });
});
