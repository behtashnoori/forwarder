import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CargoCatalogAdminTab from "@/components/CargoCatalogAdminTab";
import LogisticsNetworkAdminTab from "@/components/LogisticsNetworkAdminTab";

const api=vi.hoisted(()=>({
 listCargoCatalog:vi.fn(),createCargoCatalogItem:vi.fn(),updateCargoCatalogItem:vi.fn(),setCargoCatalogActive:vi.fn(),createCargoAlias:vi.fn(),updateCargoAlias:vi.fn(),getCargoCatalogShipmentUsage:vi.fn(),
 listLogisticsPoints:vi.fn(),listLogisticsPointTypes:vi.fn(),createLogisticsPoint:vi.fn(),createLogisticsPointType:vi.fn(),setLogisticsPointActive:vi.fn(),setLogisticsPointTypeActive:vi.fn(),updateLogisticsPoint:vi.fn(),updateLogisticsPointType:vi.fn(),
}));
vi.mock("@/lib/api",()=>api);

describe("expert terminology guidance",()=>{
 beforeEach(()=>{vi.clearAllMocks();api.listCargoCatalog.mockResolvedValue({items:[]});api.listLogisticsPoints.mockResolvedValue({items:[]});api.listLogisticsPointTypes.mockResolvedValue({items:[]});});
 it("explains reusable cargo master data and its first use",async()=>{render(<CargoCatalogAdminTab/>);expect(await screen.findByText(/اطلاعات آن‌ها یک‌بار تعریف می‌شود/)).toBeInTheDocument();expect(screen.getByText(/هنوز کالای استانداردی تعریف نشده/)).toBeInTheDocument();});
 it("explains reusable logistics locations without promising route creation",async()=>{render(<LogisticsNetworkAdminTab/>);expect(await screen.findByText(/در پیکربندی پروژه و ثبت موقعیت محموله قابل استفاده مجدد/)).toBeInTheDocument();});
});
