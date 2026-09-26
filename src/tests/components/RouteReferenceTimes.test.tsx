import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import RouteReferenceTimes from "@/components/RouteReferenceTimes";
import OrganizationRouteTimesTab from "@/components/OrganizationRouteTimesTab";
import { timeRange, type LegTime, type TimeVersion } from "@/lib/routeTimeApi";
const api=vi.hoisted(()=>({get:vi.fn(),select:vi.fn(),list:vi.fn(),revise:vi.fn()}));
vi.mock("@/i18n",()=>({useI18n:()=>({transportLabel:(value:string)=>value,businessLabel:(value:string)=>value})}));
vi.mock("@/lib/routeTimeApi",async()=>({...await vi.importActual<typeof import("@/lib/routeTimeApi")>("@/lib/routeTimeApi"),getPlanTimes:api.get,selectPlanTime:api.select,listRouteTimes:api.list,reviseRouteTime:api.revise}));
const version:TimeVersion={public_id:"version-1",version:1,movement_min_minutes:1200,movement_max_minutes:1440,stop_min_minutes:240,stop_max_minutes:480,effective_from:"2026-09-01T00:00:00Z",effective_until:null,recorded_at:"2026-09-01T00:00:00Z",actor_user_id:2,recorded_by:"مدیر سازمان"};
const leg:LegTime={leg_id:3,leg_version:1,sequence_number:1,origin_label:"خورگوس",destination_label:"آکتائو",transport_mode:"rail",reference_at:"2027-10-01T00:00:00Z",time_basis:"PLANNED_DEPARTURE",applicable:version,selected:null,selection_matches_leg:false,history:[],can_select:true};
const plans=[{id:1,revision_number:1,status:"draft"}];
const response=(item:LegTime)=>({data:{plan_id:1,plan_revision:1,plan_status:"draft",items:[item]}});
describe("explicit route reference basis",()=>{
  beforeEach(()=>{vi.clearAllMocks();api.get.mockResolvedValue(response(leg));api.select.mockResolvedValue({data:{public_id:"selection",created:true}});api.list.mockResolvedValue({data:{items:[],page:1,total:0,has_next:false}});});
  it("shows undefined without invented zero and keeps movement separate from stop",async()=>{
    api.get.mockResolvedValue(response({...leg,applicable:null}));render(<RouteReferenceTimes shipmentId="shipment" plans={plans}/>);
    expect(await screen.findByText("مرجع قابل استفاده")).toBeInTheDocument();
    expect(screen.getAllByText("تعریف نشده")).toHaveLength(4);
    expect(screen.getByRole("button",{name:"ثبت این نسخه برای برنامه"})).toBeDisabled();
    expect(timeRange(1200,1440)).toBe("۲۰ ساعت تا ۲۴ ساعت");
    expect(timeRange(0,0)).toBe("۰ ساعت");
    expect(timeRange(null,null)).toBe("تعریف نشده");
  });
  it("keeps version one visible after admin supplies version two, until explicit selection",async()=>{
    const selected={public_id:"selection-1",selection_revision:1,reference_at:leg.reference_at,recorded_at:version.recorded_at,actor_user_id:1,reference:version};
    api.get.mockResolvedValue(response({...leg,selected,selection_matches_leg:true,history:[selected],applicable:{...version,public_id:"version-2",version:2,movement_min_minutes:1500}}));
    render(<RouteReferenceTimes shipmentId="shipment" plans={plans}/>);
    expect(await screen.findByText("مبنای ثبت‌شده برنامه · نسخه مرجع 1")).toBeInTheDocument();
    expect(screen.getByText("مرجع قابل استفاده · نسخه 2")).toBeInTheDocument();
    expect(api.select).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button",{name:"ثبت این نسخه برای برنامه"}));
    await waitFor(()=>expect(api.select).toHaveBeenCalledWith("shipment",1,expect.objectContaining({selected:expect.objectContaining({selection_revision:1}),applicable:expect.objectContaining({public_id:"version-2"})}),expect.any(String)));
  });
  it("does not expose configuration or selection action for a read-only plan",async()=>{
    api.get.mockResolvedValue(response({...leg,can_select:false}));render(<RouteReferenceTimes shipmentId="shipment" plans={plans}/>);
    expect(await screen.findByText("مبنای این برنامه فقط خواندنی است.")).toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"ثبت این نسخه برای برنامه"})).not.toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"ثبت نسخه تازه"})).not.toBeInTheDocument();
  });
  it("discards a delayed result after switching plans",async()=>{
    let finish!:(value:ReturnType<typeof response>)=>void;
    api.get.mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;})).mockResolvedValue(response({...leg,origin_label:"برنامه دوم"}));
    render(<RouteReferenceTimes shipmentId="shipment" plans={[...plans,{id:2,revision_number:2,status:"draft"}]}/>);
    fireEvent.change(screen.getByLabelText("برنامه مبنای زمان"),{target:{value:"2"}});
    expect(await screen.findByText(/برنامه دوم/)).toBeInTheDocument();
    finish(response({...leg,origin_label:"پاسخ قدیمی"}));
    await waitFor(()=>expect(screen.queryByText(/پاسخ قدیمی/)).not.toBeInTheDocument());
  });
  it("Admin shows no configured default and preserves version history on update",async()=>{
    const reference={public_id:"reference",origin_label:"خورگوس",destination_label:"آکتائو",transport_mode:"rail",latest_version:1,current:version,versions:[version]};
    api.list.mockResolvedValue({data:{items:[reference],page:1,total:1,has_next:false}});
    api.revise.mockResolvedValue({data:{public_id:"version-2",created:true}});
    render(<OrganizationRouteTimesTab/>);
    fireEvent.click(await screen.findByRole("button",{name:"ثبت نسخه تازه"}));
    fireEvent.change(screen.getByLabelText("حداقل حرکت (ساعت)"),{target:{value:"25"}});
    fireEvent.change(screen.getByLabelText("حداکثر حرکت (ساعت)"),{target:{value:"30"}});
    fireEvent.change(screen.getByLabelText("شروع اعتبار"),{target:{value:"2030-01-01T09:00"}});
    fireEvent.click(screen.getByRole("button",{name:"ثبت زمان مرجع"}));
    await waitFor(()=>expect(api.revise).toHaveBeenCalledWith("reference",expect.objectContaining({expected_version:1,movement_min_minutes:1500,movement_max_minutes:1800,stop_min_minutes:240,stop_max_minutes:480}),expect.any(String)));
    expect(reference.versions[0].movement_min_minutes).toBe(1200);
  });
});
