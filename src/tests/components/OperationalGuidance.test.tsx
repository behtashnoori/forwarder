import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import OperationalGuidance from "@/components/OperationalGuidance";
import type { OperationalProjection } from "@/lib/api";

const projection: OperationalProjection = {
  identity: {label:"P-1042",source:"PROJECT_CODE",technical_id:"shipment",requested_route:null},
  overall_state:"in_progress", operational_route:null,
  stage_progress:{completed:2,total:5,current:{public_id:"stage-customs",code:"CUSTOMS",display_name_fa:"تشریفات گمرکی",status:"STARTED",required_for_completion:true},items:[
    {public_id:"stage-intake",code:"INTAKE",display_name_fa:"پذیرش",status:"COMPLETED",required_for_completion:true},
    {public_id:"stage-plan",code:"PLAN",display_name_fa:"برنامه‌ریزی",status:"COMPLETED",required_for_completion:true},
    {public_id:"stage-customs",code:"CUSTOMS",display_name_fa:"تشریفات گمرکی",status:"STARTED",required_for_completion:true},
  ],can_record:true,configured:true},
  tasks:[{key:"documents",label:"مدارک الزامی",status:"NEEDS_ACTION",section:"documents",required:true}],
  attention:[{key:"documents",severity:"BLOCKER",label:"مدارک الزامی کامل نیست",reason:"یک سند هنوز آماده نیست.",section:"documents"}],
  recommended_action:{rank:10,section:"documents",label:"تکمیل مدارک الزامی",reason:"یک سند الزامی کامل نیست.",href:"/operations/shipments/shipment/documents"},
  secondary_actions:[],readiness:{completed:3,total:8,percent:38,blocker_count:1,warning_count:0,closure_ready:false},
  current_operation:{latest_position:null,eta:{available:false,reason:"PROGRESS_UNDEFINED",message:"پیشرفت کافی ثبت نشده است.",earliest:null,latest:null}},
  priority:{band:"BLOCKED",score:100},
  meta:{projection_version:"guided-operational-workspace-v1",calculated_at:"2026-10-01T10:00:00Z",source_updated_at:"2026-10-01T09:00:00Z",lag_seconds:3600,freshness:"ON_REQUEST",rebuild:"recompute",sources:["OperationalShipment"],limitations:[]},
};

describe("OperationalGuidance", () => {
  it("separates process progress from task readiness and exposes one primary action", () => {
    render(<MemoryRouter><OperationalGuidance projection={projection}/></MemoryRouter>);
    expect(screen.getByRole("progressbar", {name:"پیشرفت مراحل عملیاتی"})).toHaveAttribute("aria-valuenow", "2");
    expect(screen.getByText("مرحله فرایند با آمادگی کارها یکی نیست.", {exact:false})).toBeInTheDocument();
    const action = screen.getByRole("link", {name:"رفتن به اقدام"});
    expect(action).toHaveAttribute("href", "/operations/shipments/shipment/documents");
    expect(screen.getAllByRole("link", {name:"رفتن به اقدام"})).toHaveLength(1);
    expect(screen.getByText("پیشرفت کافی ثبت نشده است.")).toBeInTheDocument();
  });

  it("does not invent an action for a closed or unauthorized projection", () => {
    render(<MemoryRouter><OperationalGuidance projection={{...projection,recommended_action:null,overall_state:"closed"}}/></MemoryRouter>);
    expect(screen.getByText("اقدام مجازی پیشنهاد نمی‌شود")).toBeInTheDocument();
    expect(screen.queryByRole("link", {name:"رفتن به اقدام"})).not.toBeInTheDocument();
  });
});
