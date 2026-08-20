import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DocumentDefinitionsTab from "../../components/DocumentDefinitionsTab";
import * as api from "../../lib/api";

vi.mock("../../lib/api", async () => ({
  ...(await vi.importActual<typeof import("../../lib/api")>("../../lib/api")),
  fetchDocumentCatalog: vi.fn(), fetchDocumentCatalogDefinition: vi.fn(),
  updateDocumentCatalogDefinition: vi.fn(), transitionDocumentCatalogDefinition: vi.fn(),
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
  beforeEach(()=>{vi.clearAllMocks();vi.mocked(api.fetchDocumentCatalog).mockResolvedValue({items:[item]})});
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
});
