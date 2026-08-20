import {render,screen,waitFor} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {MemoryRouter,Route,Routes} from "react-router";
import {beforeEach,describe,expect,it,vi} from "vitest";
import ExecutionUnits from "@/pages/ExecutionUnits";
import ProjectTracking from "@/pages/ProjectTracking";
import * as api from "@/lib/api";

vi.mock("@/lib/api",()=>({
 listExecutionUnits:vi.fn(),createExecutionUnit:vi.fn(),getExecutionUnitTimeline:vi.fn(),createExecutionUnitEvent:vi.fn(),
 getPublicProjectSummary:vi.fn(),listPublicExecutionUnits:vi.fn(),getPublicExecutionTimeline:vi.fn(),
}));
const unit={public_id:"opaque-unit",unit_code:"U-0001",unit_type:"road",display_name:"Truck 1",vehicle_reference:"ABC",lifecycle_status:"in_progress",is_active:true,version:1,latest_checkpoint:"Border",last_update_at:"2026-07-31T12:00:00Z",alerts:{attention_required:false,delayed:true,stale:false}};
const page={page:1,per_page:25,total:1,pages:1};

describe("Release 1.2.0 execution unit pages",()=>{
 beforeEach(()=>{vi.clearAllMocks();vi.mocked(api.listExecutionUnits).mockResolvedValue({data:[unit],meta:page});vi.mocked(api.getExecutionUnitTimeline).mockResolvedValue({data:[],meta:{...page,total:0,pages:0}});vi.mocked(api.getPublicProjectSummary).mockResolvedValue({data:{project_public_id:"project",project_code:"PRJ-1",status:"in_progress",total_units:1,delivered_units:0,in_progress_units:1,delayed_units:1,attention_required:0,units_without_recent_update:0,progress_percentage:0,last_update_at:null,threshold_policy:{version:"stale-v1",stale_after_hours:24}}});vi.mocked(api.listPublicExecutionUnits).mockResolvedValue({data:[unit],meta:page});vi.mocked(api.getPublicExecutionTimeline).mockResolvedValue({data:[],meta:{...page,total:0,pages:0}})});
 it("renders localized expert terminology and lazy-loads the timeline",async()=>{render(<MemoryRouter initialEntries={["/operations/projects/project/units"]}><Routes><Route path="/operations/projects/:projectId/units" element={<ExecutionUnits/>}/></Routes></MemoryRouter>);expect(await screen.findByText("بخش‌های اجرایی حمل")).toBeInTheDocument();expect(screen.getByText("U-0001")).toHaveAttribute("dir","ltr");expect(api.getExecutionUnitTimeline).not.toHaveBeenCalled();await userEvent.click(screen.getByRole("button",{name:"مشاهده"}));await waitFor(()=>expect(api.getExecutionUnitTimeline).toHaveBeenCalledWith("project","opaque-unit"));expect(screen.getByText("هنوز رویدادی ثبت نشده است.")).toBeInTheDocument()});
 it("renders customer aggregate, filters, disclosure, and lazy timeline",async()=>{render(<MemoryRouter initialEntries={["/project/track/code"]}><Routes><Route path="/project/track/:trackingCode" element={<ProjectTracking/>}/></Routes></MemoryRouter>);expect(await screen.findByText("Project PRJ-1")).toBeInTheDocument();expect(screen.getByText("This is process and event tracking, not GPS or live map tracking.")).toBeInTheDocument();expect(api.getPublicExecutionTimeline).not.toHaveBeenCalled();await userEvent.click(screen.getByRole("button",{name:"View timeline"}));await waitFor(()=>expect(api.getPublicExecutionTimeline).toHaveBeenCalledWith("code","opaque-unit"));expect(screen.queryByText(/internal/i)).not.toBeInTheDocument()});
});
