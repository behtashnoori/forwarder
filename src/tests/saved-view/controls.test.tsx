import {render,screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {beforeEach,describe,expect,it,vi} from "vitest";
import SavedViewControls from "@/components/SavedViewControls";
import {toSavedViewDefinition} from "@/saved-view/operational-shipments-adapter";
import * as api from "@/lib/api";

vi.mock("@/lib/api",async()=>({...await vi.importActual<typeof import("@/lib/api")>("@/lib/api"),listSavedViews:vi.fn(),createSavedView:vi.fn(),updateSavedView:vi.fn(),archiveSavedView:vi.fn()}));
const filters={status:"in_progress",customer:"",origin:"",destination:"",overdue:"",date_from:"",date_to:""};
const view={public_id:"view-1",name:"فعال‌ها",description:"",visibility:"PRIVATE",status:"ACTIVE",semantic_version:"analytics-semantic-v1",saved_view_schema_version:"saved-view-definition-v1",version:1,definition:toSavedViewDefinition(filters)};

describe("Saved View controls",()=>{
 beforeEach(()=>{vi.clearAllMocks();vi.mocked(api.listSavedViews).mockResolvedValue({data:[view]} as never);vi.mocked(api.createSavedView).mockResolvedValue({data:view} as never);});
 it("loads and applies a compatible view",async()=>{const apply=vi.fn();render(<SavedViewControls filters={{...filters,status:""}} onApply={apply}/>);await userEvent.selectOptions(await screen.findByLabelText("نمای ذخیره‌شده"),"view-1");await userEvent.click(screen.getByRole("button",{name:"اعمال نما"}));expect(apply).toHaveBeenCalledWith(filters);});
 it("saves the current governed ROWSET population",async()=>{render(<SavedViewControls filters={filters} onApply={()=>undefined}/>);await userEvent.type(screen.getByLabelText("نام نمای جدید"),"نمای من");await userEvent.click(screen.getByRole("button",{name:"ذخیره نما"}));expect(api.createSavedView).toHaveBeenCalledWith(expect.objectContaining({name:"نمای من",definition:expect.objectContaining({query_definition:expect.objectContaining({query_kind:"ROWSET",population:"SHIPMENTS"})})}));expect(await screen.findByText("نمای ذخیره‌شده با موفقیت ثبت شد.")).toBeInTheDocument();});
});
