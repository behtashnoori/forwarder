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
  it("renders a KPI value and coverage without calculating it locally", () => { renderWidget({state:"VALUE",response}); expect(screen.getByText("۴")).toBeInTheDocument(); expect(screen.getByText(/پوشش نمونه/)).toBeInTheDocument(); });
  it("does not render unknown as zero", () => { renderWidget({state:"UNKNOWN"}); expect(screen.getByText("مقدار قابل تعیین نیست.")).toBeInTheDocument(); expect(screen.queryByText("۰")).not.toBeInTheDocument(); });
  it("renders an explicit backend failure state", () => { renderWidget({state:"ERROR",error:"backend unavailable"}); expect(screen.getByRole("alert")).toHaveTextContent("backend unavailable"); });
});
