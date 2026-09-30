import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import ShipmentClosure from "@/components/ShipmentClosure";
import ClosurePolicyTab from "@/components/ClosurePolicyTab";
import { ApiError } from "@/lib/api";
import type { ClosureView } from "@/lib/closureApi";
const api=vi.hoisted(()=>({get:vi.fn(),close:vi.fn(),config:vi.fn(),save:vi.fn()}));
vi.mock("@/i18n",()=>({useI18n:()=>({transportLabel:(value:string)=>value})}));
vi.mock("@/lib/closureApi",()=>({getClosure:api.get,closeShipment:api.close,getClosureConfiguration:api.config,saveClosurePolicy:api.save}));
const view:ClosureView={assessment:{policy:{public_id:"policy-1",version:1,effective_from:"2026-09-01T00:00:00Z",effective_until:null,recorded_at:"2026-09-01T00:00:00Z",criteria:[]},shipment_version:3,lifecycle_status:"completed",assessed_at:"2026-09-26T10:00:00Z",modes:["road"],items:[{code:"ACTUAL_QUANTITY_KNOWN",label:"مقدار واقعی مشخص باشد",mandatory:true,state:"PASS",criteria:[]}],missing:[],normal_ready:true,message:null,fingerprint:"basis-1"},decision:null,can_close:true,can_close_exceptionally:false};
const reload=vi.fn().mockResolvedValue(undefined);
describe("explicit completed-only closure",()=>{
  beforeEach(()=>{vi.clearAllMocks();api.get.mockResolvedValue({data:view});api.close.mockResolvedValue({data:{public_id:"decision",created:true}});api.config.mockResolvedValue({data:{versions:[],criteria:{FINAL_DELIVERY_EXISTS:"تحویل نهایی",REQUIRED_OPERATIONAL_STAGES_COMPLETE:"مراحل الزامی",NO_BLOCKING_OPERATIONAL_ISSUE:"بدون مشکل مسدودکننده",REQUIRED_DOCUMENTS_READY:"مدارک الزامی",ACTUAL_CARGO_UNKNOWN:"مقدار واقعی نامشخص",ACTUAL_ALLOCATION_DIFFERS_FROM_PLANNED:"اختلاف تخصیص",DELIVERED_DIFFERS_FROM_PLANNED:"اختلاف تحویل",OPTIONAL_DOCUMENTS_ABSENT:"مدارک اختیاری",ETA_UNAVAILABLE:"ETA ناموجود",NON_BLOCKING_OPERATIONAL_WARNINGS:"هشدارهای عملیاتی"},scopes:["GENERAL","road"]}});api.save.mockResolvedValue({data:{public_id:"version",created:true}});});
  it("requires an explicit review and confirmation and sends the assessed version",async()=>{
    render(<ShipmentClosure shipment="shipment" reload={reload}/>);
    fireEvent.click(await screen.findByRole("button",{name:"بستن پرونده"}));
    expect(api.close).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button",{name:"تأیید نهایی بستن"}));
    await waitFor(()=>expect(api.close).toHaveBeenCalledWith("shipment",view.assessment,"NORMAL","",expect.any(String)));
    await waitFor(()=>expect(reload).toHaveBeenCalled());
  });
  it.each(["planned","in_progress","cancelled"])("offers neither normal nor exceptional close for %s",async status=>{
    api.get.mockResolvedValue({data:{...view,can_close_exceptionally:true,assessment:{...view.assessment,lifecycle_status:status}}});
    render(<ShipmentClosure shipment="shipment" reload={reload}/>);
    expect(await screen.findByText("بستن فقط پس از تکمیل پرونده ممکن است.")).toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"بستن با استثنای مدیر"})).not.toBeInTheDocument();
  });
  it("blocks missing mandatory facts, requires an Admin reason and keeps missing history",async()=>{
    const missing={...view.assessment.items[0],state:"UNKNOWN" as const};
    api.get.mockResolvedValue({data:{...view,can_close_exceptionally:true,assessment:{...view.assessment,items:[missing],missing:[missing],normal_ready:false}}});
    render(<ShipmentClosure shipment="shipment" reload={reload}/>);
    expect(await screen.findByRole("button",{name:"بستن پرونده"})).toBeDisabled();
    fireEvent.click(screen.getByRole("button",{name:"بستن با استثنای مدیر"}));
    fireEvent.click(screen.getByRole("button",{name:"تأیید نهایی بستن"}));
    expect(api.close).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("دلیل بستن با استثنا (الزامی)"),{target:{value:"exception reason"}});
    fireEvent.click(screen.getByRole("button",{name:"تأیید نهایی بستن"}));
    await waitFor(()=>expect(api.close).toHaveBeenCalledWith("shipment",expect.objectContaining({missing:[missing]}),"EXCEPTIONAL","exception reason",expect.any(String)));
  });
  it("rejects stale assessment and removes the old confirmation",async()=>{
    api.close.mockRejectedValue(new ApiError(409,"STALE_CLOSURE_ASSESSMENT","internal detail"));
    render(<ShipmentClosure shipment="shipment" reload={reload}/>);
    fireEvent.click(await screen.findByRole("button",{name:"بستن پرونده"}));
    fireEvent.click(screen.getByRole("button",{name:"تأیید نهایی بستن"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("اطلاعات تغییر کرده است");
    await waitFor(()=>expect(screen.queryByRole("button",{name:"تأیید نهایی بستن"})).not.toBeInTheDocument());
    expect(screen.queryByText("internal detail")).not.toBeInTheDocument();
  });
  it("discards a delayed private decision after switching shipment",async()=>{
    let finish!:(result:{data:ClosureView})=>void;
    api.get.mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
    const mounted=render(<ShipmentClosure shipment="one" reload={reload}/>);
    mounted.rerender(<ShipmentClosure shipment="two" reload={reload}/>);
    await screen.findByText("مقدار واقعی مشخص باشد");
    await act(async()=>finish({data:{...view,assessment:{...view.assessment,message:"PRIVATE STALE DECISION"}}}));
    expect(screen.queryByText(/PRIVATE STALE/)).not.toBeInTheDocument();
  });
  it("has no automatic policy seed and creates only the Admin-selected version",async()=>{
    render(<ClosurePolicyTab/>);
    expect(await screen.findByText(/قواعد هنوز تعریف نشده است/)).toBeInTheDocument();
    expect(api.save).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button",{name:"تعریف نسخه V1 قواعد"}));
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("شروع اعتبار (زمان محلی)"),{target:{value:"2030-01-01T09:00"}});
    fireEvent.click(screen.getByRole("button",{name:"ثبت نسخه قواعد"}));
    await waitFor(()=>expect(api.save).toHaveBeenCalledWith(expect.objectContaining({expected_version:0,criteria:expect.arrayContaining([
      {scope:"GENERAL",code:"FINAL_DELIVERY_EXISTS",mandatory:true},
      {scope:"GENERAL",code:"REQUIRED_OPERATIONAL_STAGES_COMPLETE",mandatory:true},
      {scope:"GENERAL",code:"ACTUAL_CARGO_UNKNOWN",mandatory:false},
      {scope:"GENERAL",code:"DELIVERED_DIFFERS_FROM_PLANNED",mandatory:false},
    ])}),expect.any(String)));
    expect(api.save.mock.calls[0][0].criteria).toHaveLength(10);
  });
});
