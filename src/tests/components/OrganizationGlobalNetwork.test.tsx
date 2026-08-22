import {fireEvent,render,screen,waitFor} from "@testing-library/react";
import {beforeEach,describe,expect,it,vi} from "vitest";
import OrganizationGlobalNetworkTab from "@/components/OrganizationGlobalNetworkTab";

const api=vi.hoisted(()=>({listOrganizationGlobalPoints:vi.fn(),adoptOrganizationGlobalPoint:vi.fn(),
 updateOrganizationGlobalPointAdoption:vi.fn(),transitionOrganizationGlobalPointAdoption:vi.fn()}));
vi.mock("@/lib/api",()=>api);
const adoption={public_id:"adoption-opaque",status:"ACTIVE",version:2,global_point_public_id:"global-opaque",platform_lifecycle_status:"ACTIVE",display_label:"Local"};
const point=(state:string,adopt:unknown=null)=>({public_id:"global-opaque",immutable_code:"XZ-PORT",fa_name:"بندر",en_name:"Port",
 point_type:{code:"PORT",fa_name:"بندر",en_name:"Port"},country:{code:"XZ",fa_name:"کشور",en_name:"Country"},
 geography:{city:"City"},supported_modes:["SEA"],corridor_tags:[],organization_state:state,adoption:adopt});

describe("Organization Global Network",()=>{
 beforeEach(()=>{vi.clearAllMocks();vi.spyOn(window,"confirm").mockReturnValue(true);api.listOrganizationGlobalPoints.mockResolvedValue({items:[point("AVAILABLE")],page:1,pages:1,total:1});api.adoptOrganizationGlobalPoint.mockResolvedValue({item:adoption});api.updateOrganizationGlobalPointAdoption.mockResolvedValue({item:{...adoption,version:3}});api.transitionOrganizationGlobalPointAdoption.mockResolvedValue({item:{...adoption,status:"INACTIVE",version:3}})});
 it("filters, adopts, and exposes only organization metadata editing",async()=>{render(<OrganizationGlobalNetworkTab/>);await screen.findByText(/XZ-PORT/);fireEvent.change(screen.getByLabelText("Global country"),{target:{value:"XZ"}});await waitFor(()=>expect(api.listOrganizationGlobalPoints).toHaveBeenLastCalledWith(expect.objectContaining({country:"XZ"})));fireEvent.click(screen.getByText(/XZ-PORT/));expect(screen.queryByLabelText("Canonical Persian name")).toBeNull();fireEvent.change(screen.getByLabelText("Organization display label"),{target:{value:"My Port"}});fireEvent.click(screen.getByRole("button",{name:"Adopt"}));await waitFor(()=>expect(api.adoptOrganizationGlobalPoint).toHaveBeenCalledWith("global-opaque",expect.objectContaining({display_label:"My Port"})))});
 it("updates with adoption version and deactivates",async()=>{api.listOrganizationGlobalPoints.mockResolvedValue({items:[point("ADOPTED",adoption)],page:1,pages:1,total:1});render(<OrganizationGlobalNetworkTab/>);await screen.findByText(/XZ-PORT/);fireEvent.click(screen.getByText(/XZ-PORT/));fireEvent.click(screen.getByRole("button",{name:"Save organization metadata"}));await waitFor(()=>expect(api.updateOrganizationGlobalPointAdoption).toHaveBeenCalledWith(adoption,expect.any(Object)));fireEvent.click(screen.getByRole("button",{name:"Deactivate adoption"}));await waitFor(()=>expect(api.transitionOrganizationGlobalPointAdoption).toHaveBeenCalledWith(adoption,"deactivate"))});
 it.each([["INACTIVE_FOR_ORGANIZATION","Reactivate adoption"],["PLATFORM_DEPRECATED",null]])("renders %s lifecycle safely",async(state,button)=>{api.listOrganizationGlobalPoints.mockResolvedValue({items:[point(state,{...adoption,status:"INACTIVE"})],page:1,pages:1,total:1});render(<OrganizationGlobalNetworkTab/>);await screen.findByText(/XZ-PORT/);fireEvent.click(screen.getByText(/XZ-PORT/));if(button)expect(screen.getByRole("button",{name:button})).toBeTruthy();else{expect(screen.getByText(/Platform deprecated/)).toBeTruthy();expect(screen.queryByRole("button",{name:"Reactivate adoption"})).toBeNull()}});
});
