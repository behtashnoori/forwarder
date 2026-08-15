import {fireEvent,render,screen,waitFor} from "@testing-library/react";
import {beforeEach,describe,expect,it,vi} from "vitest";
import OrganizationDocumentPolicyTab from "../../components/OrganizationDocumentPolicyTab";
import * as api from "../../lib/api";

vi.mock("../../lib/api",async()=>{const actual=await vi.importActual<typeof import("../../lib/api")>("../../lib/api");return {...actual,fetchOrganizationDocumentPolicy:vi.fn(),updateOrganizationDocumentPolicy:vi.fn()}});
const item={document_definition_public_id:"d1",code:"bill",title:"بارنامه",global_is_active:true,global_default_required:true,applicability_scope:"all" as const,policy_public_id:null,requirement_level:null,is_active:null,version:null};

describe("OrganizationDocumentPolicyTab",()=>{
 beforeEach(()=>{vi.clearAllMocks();vi.mocked(api.fetchOrganizationDocumentPolicy).mockResolvedValue({mode:"COMPATIBILITY_FALLBACK",items:[item]});vi.mocked(api.updateOrganizationDocumentPolicy).mockResolvedValue({...item,requirement_level:"REQUIRED",is_active:true,version:1})});
 it("renders nullable policy safely and saves only the selected global definition",async()=>{render(<OrganizationDocumentPolicyTab/>);expect(await screen.findByText("بارنامه")).toBeInTheDocument();expect(screen.getByText(/رفتار سازگار قبلی/)).toBeInTheDocument();fireEvent.change(screen.getByLabelText("سطح الزام بارنامه"),{target:{value:"REQUIRED"}});fireEvent.click(screen.getByRole("button",{name:"ذخیره"}));await waitFor(()=>expect(api.updateOrganizationDocumentPolicy).toHaveBeenCalledWith("d1",{requirement_level:"REQUIRED",is_active:true}));});
 it("renders a controlled API error",async()=>{vi.mocked(api.fetchOrganizationDocumentPolicy).mockRejectedValue(new Error("policy unavailable"));render(<OrganizationDocumentPolicyTab/>);expect(await screen.findByRole("alert")).toHaveTextContent("policy unavailable")});
});
