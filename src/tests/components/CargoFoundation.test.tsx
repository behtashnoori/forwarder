import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CargoCatalogAdminTab from "@/components/CargoCatalogAdminTab";
import ShipmentCargoItems from "@/components/ShipmentCargoItems";

const api = vi.hoisted(() => ({
  listCargoCatalog: vi.fn(), createCargoCatalogItem: vi.fn(), updateCargoCatalogItem: vi.fn(),
  setCargoCatalogActive: vi.fn(), createCargoAlias: vi.fn(), updateCargoAlias: vi.fn(),
  listShipmentCargoItems: vi.fn(), createShipmentCargoItem: vi.fn(), updateShipmentCargoItem: vi.fn(), request: vi.fn(),
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
};

describe("Cargo foundation UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listCargoCatalog.mockResolvedValue({items:[catalog],page:1,per_page:20,total:1,pages:1});
    api.listShipmentCargoItems.mockResolvedValue({items:[shipmentItem]});
    api.request.mockResolvedValue({catalog:[{public_id:"catalog-1",code:"ITEM-1",name:"کالا",cargo_type_public_id:"ct-1",default_uom_public_id:"uom-1"}],cargo_types:[{public_id:"ct-1",code:"CARGO_GENERAL",name:"عمومی"}],uoms:[{public_id:"uom-1",code:"UOM_EA",name:"عدد",symbol:"ea"}]});
    api.updateShipmentCargoItem.mockResolvedValue({item:{...shipmentItem,quantity:"3",version:2}});
  });

  it("keeps immutable catalog code read-only during edit and uses governed aliases", async () => {
    render(<CargoCatalogAdminTab/>);
    expect(await screen.findByText("ITEM-1")).toBeTruthy();
    fireEvent.click(screen.getByRole("button",{name:/Edit/}));
    expect(screen.getByLabelText("immutable code").hasAttribute("readonly")).toBe(true);
    fireEvent.change(screen.getByLabelText("Alias for ITEM-1"),{target:{value:"Alias"}});
    fireEvent.click(screen.getByRole("button",{name:/Add alias/}));
    await waitFor(()=>expect(api.createCargoAlias).toHaveBeenCalledWith("catalog-1",expect.objectContaining({alias_type:"COMMON_NAME",language:"und"})));
  });

  it("shows legacy cargo separately and updates quantity without snapshot fields", async () => {
    render(<ShipmentCargoItems shipmentPublicId="shipment-1" legacyDescription="Legacy machinery"/>);
    expect(await screen.findByText("Legacy machinery")).toBeTruthy();
    expect(screen.getByText("Historical snapshot")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Edit quantity line 1"),{target:{value:"3"}});
    fireEvent.click(screen.getByRole("button",{name:/Save/}));
    await waitFor(()=>expect(api.updateShipmentCargoItem).toHaveBeenCalledWith("shipment-1","line-1",{quantity:"3",version:1}));
  });
});
