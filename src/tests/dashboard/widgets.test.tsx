import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { TooltipProvider } from "@/components/ui/tooltip";
import { DashboardWidget } from "@/dashboard/DashboardWidgets";
import { operationsControlTower } from "@/dashboard/control-tower";

const widget = operationsControlTower.widgets[0];
const response = { semantic_version:"analytics-semantic-v1", normalized_query:{metrics:["ACTIVE_SHIPMENT_COUNT"]}, query:{metrics:["ACTIVE_SHIPMENT_COUNT"]}, columns:[{key:"ACTIVE_SHIPMENT_COUNT",business_name:"محموله فعال",kind:"metric" as const,data_type:"number",unit:"count"}], rows:[{ACTIVE_SHIPMENT_COUNT:{state:"VALUE",value:4}}],coverage:[{coverage_key:"x",definition:"پوشش نمونه",eligible_count:10,covered_count:8,coverage_percent:80,state:"VALUE" as const}],warnings:[],pagination:{limit:20,next_cursor:null},execution:{read_only:true as const,organization_scoped:true as const} };
describe("Dashboard widgets", () => {
  const renderWidget = (result: Parameters<typeof DashboardWidget>[0]["result"]) => render(<TooltipProvider><MemoryRouter><DashboardWidget widget={widget} result={result} /></MemoryRouter></TooltipProvider>);
  it("renders the server-provided KPI value and business coverage statistic", () => { renderWidget({state:"VALUE",response}); expect(screen.getByText("۴")).toBeInTheDocument(); expect(screen.getByText("پوشش داده: ۸۰٪ (۸ از ۱۰)")).toBeInTheDocument(); });
  it("does not render unknown as zero", () => { renderWidget({state:"UNKNOWN"}); expect(screen.getByText("مقدار قابل تعیین نیست.")).toBeInTheDocument(); expect(screen.queryByText("۰")).not.toBeInTheDocument(); });
  it("renders an explicit backend failure state", () => { renderWidget({state:"ERROR",error:"backend unavailable"}); expect(screen.getByRole("alert")).toHaveTextContent("backend unavailable"); });
  it("renders a governed ROWSET table in server order without aggregate reinterpretation", () => {
    const rowsetWidget = {...widget, widget_type:"TABLE" as const, query:{...widget.query, query_kind:"ROWSET" as const, semantic_version:"analytics-semantic-v2", population:"SHIPMENTS" as const, columns:["CUSTOMER","SHIPMENT_STATUS"], metric_keys:[], dimension_keys:[]}};
    const rowset = {semantic_version:"analytics-semantic-v2",result_kind:"ROWSET" as const,normalized_query:{query_kind:"ROWSET" as const},query:{query_kind:"ROWSET" as const},columns:[{key:"CUSTOMER",business_name:"مشتری",kind:"dimension" as const,data_type:"string"},{key:"SHIPMENT_STATUS",business_name:"وضعیت",kind:"dimension" as const,data_type:"string"}],rows:[{shipment_public_id:"shipment-2",CUSTOMER:"دوم",SHIPMENT_STATUS:"planned"},{shipment_public_id:"shipment-1",CUSTOMER:"اول",SHIPMENT_STATUS:"completed"}],coverage:[],warnings:[],pagination:{limit:20,next_cursor:null},returned_row_count:2,execution:{read_only:true as const,organization_scoped:true as const}};
    render(<TooltipProvider><MemoryRouter><DashboardWidget widget={rowsetWidget} result={{state:"VALUE",response:rowset}} /></MemoryRouter></TooltipProvider>);
    expect(screen.getByText("دوم").compareDocumentPosition(screen.getByText("اول")) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.queryByText("محموله فعال")).not.toBeInTheDocument();
  });
});
