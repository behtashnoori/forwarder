import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CargoCatalogAdminTab from "@/components/CargoCatalogAdminTab";
import ShipmentCargoItems from "@/components/ShipmentCargoItems";

const api = vi.hoisted(() => ({
  listCargoCatalog: vi.fn(), createCargoCatalogItem: vi.fn(), updateCargoCatalogItem: vi.fn(),
  setCargoCatalogActive: vi.fn(), createCargoAlias: vi.fn(), updateCargoAlias: vi.fn(),
  getCargoCatalogShipmentUsage: vi.fn(),
  listShipmentCargoItems: vi.fn(), createShipmentCargoItem: vi.fn(), updateShipmentCargoItem: vi.fn(), searchOperationalCustomers: vi.fn(), request: vi.fn(), getShipmentCargoOptions: vi.fn(),
  getCargoTransportAllocations: vi.fn(), createCargoTransportAllocation: vi.fn(),
  deleteCargoTransportAllocation: vi.fn(), getOperationalTransportTracking: vi.fn(),
  enableOperationalTransportTracking: vi.fn(), addOperationalTransportTrackingUpdate: vi.fn(),
  getCanonicalShipmentTransportUnits: vi.fn(), createCanonicalShipmentTransportUnit: vi.fn(),
  getCanonicalCargoAllocations: vi.fn(), createCanonicalCargoAllocation: vi.fn(),
  updateCanonicalCargoAllocation: vi.fn(), deleteCanonicalCargoAllocation: vi.fn(),
}));
vi.mock("@/lib/api", () => api);

const catalog = {
  public_id:"catalog-1", immutable_code:"ITEM-1", fa_name:"کالا", en_name:"Item",
  part_number:"PN-1", customer_item_code:"CC-1", hs_code:null, brand:null, model:null,
  description:null, is_active:true, version:1,
  cargo_type:{public_id:"ct-1",code:"CARGO_GENERAL",fa_name:"عمومی",en_name:"General"},
  default_uom:{public_id:"uom-1",code:"UOM_EA",symbol:"ea"}, aliases:[],
};
const shipmentItem = {
  public_id:"line-1", line_number:1, source:"catalog", catalog_item_public_id:"catalog-1",
  cargo_type_public_id:"ct-1", uom_public_id:"uom-1", quantity:"2.000000",
  display_name_snapshot:"کالا", cargo_type_code_snapshot:"CARGO_GENERAL",
  cargo_type_fa_snapshot:"عمومی", cargo_type_en_snapshot:"General",
  uom_code_snapshot:"UOM_EA", uom_symbol_snapshot:"ea", part_number_snapshot:"PN-1",
  customer_item_code_snapshot:"CC-1", hs_code_snapshot:null, brand_snapshot:null,
  model_snapshot:null, description_snapshot:"Historical snapshot", version:1,
  cargo_owner:null,
};

describe("Cargo foundation UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listCargoCatalog.mockResolvedValue({items:[catalog],page:1,per_page:20,total:1,pages:1});
    api.listShipmentCargoItems.mockResolvedValue({items:[shipmentItem]});
    api.request.mockResolvedValue({catalog:[{public_id:"catalog-1",code:"ITEM-1",name:"کالا",cargo_type_public_id:"ct-1",default_uom_public_id:"uom-1"}],cargo_types:[{public_id:"ct-1",code:"CARGO_GENERAL",name:"عمومی"}],uoms:[{public_id:"uom-1",code:"UOM_EA",name:"عدد",symbol:"ea"}]});
    api.getShipmentCargoOptions.mockResolvedValue({catalog:[{public_id:"catalog-1",code:"ITEM-1",name:"کالا",cargo_type_public_id:"ct-1",default_uom_public_id:"uom-1",preferred:true},{public_id:"catalog-2",code:"ITEM-2",name:"کالای سازمان",cargo_type_public_id:"ct-1",default_uom_public_id:"uom-1",preferred:false}],cargo_types:[{public_id:"ct-1",code:"CARGO_GENERAL",name:"عمومی"}],uoms:[{public_id:"uom-1",code:"UOM_EA",name:"عدد",symbol:"ea"}]});
    api.searchOperationalCustomers.mockResolvedValue({items:[{id:1,label:"Customer A"}],meta:{count:1,limit:100}});
    api.updateShipmentCargoItem.mockResolvedValue({item:{...shipmentItem,quantity:"3",version:2}});
    api.getCargoTransportAllocations.mockResolvedValue({allocations:[],transport_units:[]});
    api.getOperationalTransportTracking.mockResolvedValue({source_type:"direct",tracking:null});
    api.getCanonicalShipmentTransportUnits.mockResolvedValue({units:[]});
    api.getCanonicalCargoAllocations.mockResolvedValue({allocations:[],items:[shipmentItem]});
    api.getCargoCatalogShipmentUsage.mockResolvedValue({cargo_item:catalog,summary:{shipment_count:1,active_shipment_count:1},items:[{operational_shipment_public_id:"shipment-1",project_public_id:"project-1",project_code:"PRJ-1",shipment_request_reference:null,quantity:"2.000000",uom:"ea",status:"in_progress",current_location:"Border",location_source:"operational_event",latest_event_at:"2026-08-20T09:25:00Z",shipment_cargo_line_public_id:"line-1",display_name_snapshot:"کالا"}],limit:50,offset:0});
  });

  it("opens shipment usage and renders quantity, status, and location", async () => {
    render(<CargoCatalogAdminTab/>);
    fireEvent.click(await screen.findByRole("button",{name:"مشاهده محموله‌های دارای این کالا"}));
    expect(await screen.findByText("PRJ-1")).toBeTruthy();
    expect(screen.getByText(/2 ea/)).toBeTruthy();
    expect(screen.getByText(/Border/)).toBeTruthy();
  });

  it("renders shipment usage empty and error states", async () => {
    api.getCargoCatalogShipmentUsage.mockResolvedValueOnce({cargo_item:catalog,summary:{shipment_count:0,active_shipment_count:0},items:[],limit:50,offset:0});
    render(<CargoCatalogAdminTab/>);
    fireEvent.click(await screen.findByRole("button",{name:"مشاهده محموله‌های دارای این کالا"}));
    expect(await screen.findByText("این کالا هنوز در هیچ محموله‌ای استفاده نشده است.")).toBeTruthy();
  });

  it("reports shipment usage API errors", async () => {
    api.getCargoCatalogShipmentUsage.mockRejectedValueOnce(new Error("forbidden"));
    render(<CargoCatalogAdminTab/>);
    fireEvent.click(await screen.findByRole("button",{name:"مشاهده محموله‌های دارای این کالا"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("بارگذاری محموله‌های کالا انجام نشد.");
  });

  it("keeps immutable catalog code read-only during edit and uses governed aliases", async () => {
    render(<CargoCatalogAdminTab/>);
    expect(await screen.findByText("ITEM-1")).toBeTruthy();
    fireEvent.click(screen.getByRole("button",{name:"ویرایش کالا"}));
    expect(screen.getByLabelText("کد ثابت کالا").hasAttribute("readonly")).toBe(true);
    fireEvent.change(screen.getByLabelText("Alias for ITEM-1"),{target:{value:"Alias"}});
    fireEvent.click(screen.getByRole("button",{name:/Add alias/}));
    await waitFor(()=>expect(api.createCargoAlias).toHaveBeenCalledWith("catalog-1",expect.objectContaining({alias_type:"COMMON_NAME",language:"und"})));
  });

  it("shows legacy cargo separately and updates quantity without snapshot fields", async () => {
    render(<ShipmentCargoItems shipmentPublicId="shipment-1" projectPublicId="project-1" legacyDescription="Legacy machinery"/>);
    expect(await screen.findByText("Legacy machinery")).toBeTruthy();
    expect(api.getShipmentCargoOptions).toHaveBeenCalledWith("project-1","");
    expect(screen.getByRole("group",{name:"کالاهای ترجیحی پروژه"})).toBeTruthy();
    expect(screen.getByRole("option",{name:/ITEM-2/})).toBeTruthy();
    expect(screen.getByRole("option",{name:"ورود دستی کالا"})).toBeTruthy();
    expect(screen.getByText("Historical snapshot")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Edit quantity line 1"),{target:{value:"3"}});
    fireEvent.click(screen.getByRole("button",{name:/Save/}));
    await waitFor(()=>expect(api.updateShipmentCargoItem).toHaveBeenCalledWith("shipment-1","line-1",{quantity:"3",cargo_owner_customer_id:null,version:1}));
  });

  it("uses explicit Persian quantity allocation and preserves remaining cargo", async () => {
    api.getCanonicalShipmentTransportUnits.mockResolvedValue({units:[{public_id:"truck-1",unit_code:"U-0001",unit_type:"truck",display_name:"کامیون ۱",vehicle_reference:null,version:1},{public_id:"truck-2",unit_code:"U-0002",unit_type:"truck",display_name:"کامیون ۲",vehicle_reference:null,version:1}]});
    api.listShipmentCargoItems.mockResolvedValue({items:[{...shipmentItem,quantity:"1000",allocated_quantity:"600",remaining_quantity:"400"}]});
    render(<ShipmentCargoItems shipmentPublicId="shipment-1"/>);
    const selects = await screen.findAllByRole("combobox");
    fireEvent.change(selects.find((element) => element.getAttribute("aria-label") === "وسیله حمل برای تخصیص")!, {target:{value:"truck-2"}});
    fireEvent.change(screen.getByLabelText("کالا برای تخصیص"), {target:{value:"line-1"}});
    fireEvent.change(screen.getByLabelText("مقدار تخصیص"), {target:{value:"400"}});
    fireEvent.click(screen.getByRole("button",{name:"تخصیص کالا"}));
    await waitFor(()=>expect(api.createCanonicalCargoAllocation).toHaveBeenCalledWith("shipment-1",{execution_unit_public_id:"truck-2",cargo_item_public_id:"line-1",allocated_quantity:"400"}));
  });

  it("keeps the canonical shipment execution-unit creation path available", async () => {
    render(<ShipmentCargoItems shipmentPublicId="shipment-1" projectPublicId="project-1"/>);
    fireEvent.click(await screen.findByText("افزودن وسیله حمل"));
    fireEvent.change(screen.getByLabelText("نام وسیله حمل"), {target:{value:"کامیون اصلی"}});
    fireEvent.change(screen.getByLabelText("شناسه وسیله حمل"), {target:{value:"IR-77"}});
    fireEvent.click(screen.getByRole("button", {name:"افزودن کامیون"}));
    await waitFor(()=>expect(api.createCanonicalShipmentTransportUnit).toHaveBeenCalledWith("shipment-1",{
      unit_type:"truck",display_name:"کامیون اصلی",vehicle_reference:"IR-77",
    }));
  });

  it("renders and persists Cargo Owners by unique Customer identity", async () => {
    const consoleError = vi.spyOn(console, "error");
    const ownedItem = {...shipmentItem,cargo_owner:{id:1,label:"Same Name"}};
    api.listShipmentCargoItems
      .mockResolvedValueOnce({items:[ownedItem]})
      .mockResolvedValue({items:[{...ownedItem,cargo_owner:{id:2,label:"Multi-role Customer"},version:2}]});
    api.searchOperationalCustomers.mockResolvedValue({
      items:[
        {id:1,label:"Same Name"},
        {id:2,label:"Multi-role Customer"},
        {id:2,label:"Multi-role Customer"},
        {id:3,label:"Same Name"},
      ],
      meta:{count:4,limit:100},
    });

    render(<ShipmentCargoItems shipmentPublicId="shipment-1" projectPublicId="project-1"/>);

    const selector = await screen.findByLabelText("Cargo owner line 1") as HTMLSelectElement;
    expect(selector.querySelectorAll('option[value="1"]')).toHaveLength(1);
    expect(selector.querySelectorAll('option[value="2"]')).toHaveLength(1);
    expect(selector.querySelectorAll('option[value="3"]')).toHaveLength(1);
    expect(Array.from(selector.options).filter((option)=>option.text === "Same Name")).toHaveLength(2);
    expect(consoleError).not.toHaveBeenCalled();

    fireEvent.change(selector,{target:{value:"2"}});
    fireEvent.click(screen.getByRole("button",{name:/Save/}));
    await waitFor(()=>expect(api.updateShipmentCargoItem).toHaveBeenCalledWith("shipment-1","line-1",{
      quantity:"2.000000",cargo_owner_customer_id:"2",version:1,
    }));
    await waitFor(()=>expect((screen.getByLabelText("Cargo owner line 1") as HTMLSelectElement).value).toBe("2"));
    consoleError.mockRestore();
  });

  it("qualifies tracking-unit render identity by source domain without masking same-domain duplicates", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const unit = (source:"canonical_execution"|"historical_legacy", id:number, code:string) => ({
      source,id,unit_code:code,unit_type:"truck",latest_status:"in_transit",
      allocated_cargo:[],history:[],
    });
    api.getOperationalTransportTracking
      .mockResolvedValueOnce({source_type:"direct",tracking:{enabled:true,units:[
        unit("historical_legacy",2,"LEGACY-2"),unit("canonical_execution",2,"CANONICAL-2"),
      ]}})
      .mockResolvedValueOnce({source_type:"direct",tracking:{enabled:true,units:[
        unit("canonical_execution",3,"CANONICAL-3"),unit("historical_legacy",2,"LEGACY-2"),
      ]}})
      .mockResolvedValueOnce({source_type:"direct",tracking:{enabled:true,units:[
        unit("canonical_execution",2,"CANONICAL-2-A"),unit("canonical_execution",2,"CANONICAL-2-B"),
      ]}});

    render(<ShipmentCargoItems shipmentPublicId="shipment-1" projectPublicId="project-1"/>);
    expect((await screen.findAllByText("LEGACY-2")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("CANONICAL-2").length).toBeGreaterThan(0);
    expect(consoleError).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Search cargo catalog"),{target:{value:"reload"}});
    expect((await screen.findAllByText("CANONICAL-3")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("LEGACY-2").length).toBeGreaterThan(0);
    expect(consoleError).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Search cargo catalog"),{target:{value:"duplicate"}});
    expect((await screen.findAllByText("CANONICAL-2-B")).length).toBeGreaterThan(0);
    await waitFor(()=>expect(consoleError).toHaveBeenCalledWith(expect.stringContaining("same key"),"canonical_execution:2"));
    consoleError.mockRestore();
  });

});
