import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DocumentDefinitionsTab from "../../components/DocumentDefinitionsTab";
import * as api from "../../lib/api";

vi.mock("../../lib/api", async () => ({
  ...(await vi.importActual<typeof import("../../lib/api")>("../../lib/api")),
  fetchDocumentCatalog: vi.fn(), fetchDocumentCatalogDefinition: vi.fn(),
  createDocumentDefinition: vi.fn(), updateDocumentCatalogDefinition: vi.fn(), transitionDocumentCatalogDefinition: vi.fn(),
}));

const item: api.DocumentCatalogDefinition = {
  public_id:"doc-1",code:"BILL_OF_LADING",title:"بارنامه",name_fa:"بارنامه دریایی",name_en:"Bill of Lading",
  description_fa:"شرح فارسی",description_en:"English description",family_code:"TRANSPORT",expiry_applicable:false,
  organization_overridable:true,catalog_lifecycle_status:"SOURCE_CONFIRMED",source_review_status:"VERIFIED",is_active:false,is_required:false,
  applicability_scope:"international",revision:3,aliases:[{display_value:"B/L",locale:"en",alias_kind:"ABBREVIATION",is_active:true}],
  jurisdictions:[{kind:"INTERNATIONAL",key:"INTERNATIONAL"}],modes:["SEA"],stages:["IN_TRANSIT"],business_scopes:["OPERATIONAL_SHIPMENT"],
  provenance:[{source_authority_code:"UNECE",source_authority_name:"UNECE",source_title:"Code list",source_reference:"https://example.test/evidence",review_status:"VERIFIED"}],
};

describe("DocumentDefinitionsTab governed catalog",()=>{
  beforeEach(()=>{vi.clearAllMocks();localStorage.clear();vi.mocked(api.fetchDocumentCatalog).mockResolvedValue({items:[item]})});
  it("renders bilingual identity, governance distinctions and server filters",async()=>{
    render(<DocumentDefinitionsTab/>);
    expect(await screen.findByText("بارنامه دریایی")).toBeInTheDocument();
    expect(screen.getByText("Bill of Lading")).toHaveAttribute("dir","ltr");
    expect(screen.getByText(/وجود یک نوع سند در این فهرست/)).toBeInTheDocument();
    expect(screen.getByText("نوع سند ≠ فایل")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("جستجوی کاتالوگ"),{target:{value:"B/L"}});
    await waitFor(()=>expect(api.fetchDocumentCatalog).toHaveBeenLastCalledWith(expect.objectContaining({q:"B/L"})),{timeout:1000});
    fireEvent.change(screen.getByLabelText("خانواده"),{target:{value:"TRANSPORT"}});
    await waitFor(()=>expect(api.fetchDocumentCatalog).toHaveBeenLastCalledWith(expect.objectContaining({family_code:"TRANSPORT"})));
  });
  it("shows detail sections, aliases, provenance and separate statuses",async()=>{
    render(<DocumentDefinitionsTab/>); await screen.findByText("بارنامه دریایی");
    fireEvent.click(screen.getByText("مشاهده جزئیات"));
    expect(screen.getByText("۴. نام‌های جایگزین")).toBeInTheDocument(); expect(screen.getByText("B/L")).toHaveAttribute("dir","ltr");
    expect(screen.getByText("۵. منابع و مستندات مرجع")).toBeInTheDocument(); expect(screen.getByText("Code list")).toBeInTheDocument();
    expect(screen.getByText("۶. وضعیت بررسی منبع")).toBeInTheDocument(); expect(screen.getByText("۷. چرخه حیات")).toBeInTheDocument();
    expect(screen.getByText(/فعال بودن یک نوع سند/)).toBeInTheDocument();
  });
  it("distinguishes empty catalog, no results and backend errors",async()=>{
    vi.mocked(api.fetchDocumentCatalog).mockResolvedValueOnce({items:[]}); const {unmount}=render(<DocumentDefinitionsTab/>);
    expect(await screen.findByText("هنوز نوع سندی در کاتالوگ ثبت نشده است.")).toBeInTheDocument(); unmount();
    vi.mocked(api.fetchDocumentCatalog).mockRejectedValueOnce(new Error("Forbidden")); render(<DocumentDefinitionsTab/>);
    expect(await screen.findByText("Forbidden")).toBeInTheDocument();
  });
  it("honors expected revision and presents stale-write conflict",async()=>{
    vi.mocked(api.updateDocumentCatalogDefinition).mockRejectedValue(new Error("Document definition revision conflict"));
    render(<DocumentDefinitionsTab/>);await screen.findByText("بارنامه دریایی");fireEvent.click(screen.getByText("مشاهده جزئیات"));fireEvent.click(screen.getByText("ویرایش فراداده"));fireEvent.click(screen.getByText("ذخیره"));
    expect(await screen.findByText(/این رکورد پس از باز شدن صفحه تغییر کرده است/)).toBeInTheDocument();
    expect(api.updateDocumentCatalogDefinition).toHaveBeenCalledWith("doc-1",expect.objectContaining({expected_revision:3}),expect.any(String));
  });
  it("requires an explicit lifecycle confirmation and surfaces activation blocks",async()=>{
    vi.mocked(api.transitionDocumentCatalogDefinition).mockRejectedValue(new Error("Jurisdiction classification is required"));
    render(<DocumentDefinitionsTab/>);await screen.findByText("بارنامه دریایی");fireEvent.click(screen.getByText("مشاهده جزئیات"));fireEvent.click(screen.getByText("ارتقا/تغییر به «فعال»"));
    expect(screen.getByText(/فعال‌سازی فقط پس از/)).toBeInTheDocument();fireEvent.click(screen.getByText("تأیید و اجرا"));
    expect(await screen.findByText("قلمرو کاربرد باید مشخص شود.")).toBeInTheDocument();
  });
  it("shows creation only to Platform Admin and keeps it absent for Organization Admin",async()=>{
    localStorage.setItem("expert_user",JSON.stringify({authority:"PLATFORM_ADMIN"}));const {unmount}=render(<DocumentDefinitionsTab/>);
    expect(await screen.findByRole("button",{name:"ایجاد نوع سند"})).toBeInTheDocument();unmount();
    localStorage.setItem("expert_user",JSON.stringify({authority:"ORGANIZATION_ADMIN"}));render(<DocumentDefinitionsTab/>);
    expect(screen.queryByRole("button",{name:"ایجاد نوع سند"})).not.toBeInTheDocument();
  });
  it("validates the compact draft form, prevents duplicate submits, refreshes, and opens the created item",async()=>{
    localStorage.setItem("expert_user",JSON.stringify({authority:"PLATFORM_ADMIN"}));let resolveCreate:(value:api.DocumentDefinition)=>void=()=>{};
    vi.mocked(api.createDocumentDefinition).mockImplementation(()=>new Promise(resolve=>{resolveCreate=resolve;}));vi.mocked(api.fetchDocumentCatalogDefinition).mockResolvedValue({...item,public_id:"new-doc",code:"new_document",title:"سند جدید",name_fa:"سند جدید"});
    render(<DocumentDefinitionsTab/>);await screen.findByText("بارنامه دریایی");fireEvent.click(screen.getByRole("button",{name:"ایجاد نوع سند"}));
    fireEvent.click(screen.getByRole("button",{name:"ایجاد نوع سند"}));expect(await screen.findByRole("alert")).toHaveTextContent("کد سیستمی");
    fireEvent.change(screen.getByLabelText("کد سیستمی"),{target:{value:"new_document"}});fireEvent.change(screen.getByLabelText("نام سند"),{target:{value:"سند جدید"}});fireEvent.click(screen.getByRole("button",{name:"ایجاد نوع سند"}));
    expect(screen.getByRole("button",{name:"در حال ایجاد..."})).toBeDisabled();fireEvent.click(screen.getByRole("button",{name:"در حال ایجاد..."}));expect(api.createDocumentDefinition).toHaveBeenCalledTimes(1);
    resolveCreate({id:2,public_id:"new-doc",code:"new_document",title:"سند جدید",is_required:false,allowed_formats:["pdf"],max_file_size_bytes:10*1024*1024,max_active_file_count:1,sort_order:0,is_active:true,applicability_scope:"all",revision:1,usage_count:0});
    expect(await screen.findByText("سند جدید")).toBeInTheDocument();expect(api.fetchDocumentCatalog).toHaveBeenCalledTimes(2);expect(api.fetchDocumentCatalogDefinition).toHaveBeenCalledWith("new-doc");
  });
  it("keeps entered values after a create error and does not change existing rows",async()=>{
    localStorage.setItem("expert_user",JSON.stringify({authority:"PLATFORM_ADMIN"}));vi.mocked(api.createDocumentDefinition).mockRejectedValue(new Error("duplicate"));render(<DocumentDefinitionsTab/>);await screen.findByText("بارنامه دریایی");fireEvent.click(screen.getByRole("button",{name:"ایجاد نوع سند"}));fireEvent.change(screen.getByLabelText("کد سیستمی"),{target:{value:"new_document"}});fireEvent.change(screen.getByLabelText("نام سند"),{target:{value:"سند جدید"}});fireEvent.click(screen.getByRole("button",{name:"ایجاد نوع سند"}));expect(await screen.findByRole("alert")).toHaveTextContent("اطلاعات واردشده");expect(screen.getByLabelText("کد سیستمی")).toHaveValue("new_document");expect(screen.getByText("بارنامه دریایی")).toBeInTheDocument();
  });
});
