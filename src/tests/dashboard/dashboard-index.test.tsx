import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DashboardIndex from "@/pages/DashboardIndex";
import { operationsControlTower } from "@/dashboard/control-tower";
import * as api from "@/lib/api";

vi.mock("@/lib/api", async () => ({...(await vi.importActual<typeof import("@/lib/api")>("@/lib/api")), getOperationalContext:vi.fn(), listDashboards:vi.fn(), cloneSystemDashboard:vi.fn()}));
const row = {public_id:"db-1",dashboard_type:"PERSONAL" as const,name:"داشبورد من",description:"",visibility:"PRIVATE" as const,status:"ACTIVE" as const,semantic_version:"analytics-semantic-v1",dashboard_schema_version:"dashboard-definition-v1",version:1,definition:operationsControlTower};
const renderPage = () => render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}})}><MemoryRouter initialEntries={["/dashboards"]}><Routes><Route path="/dashboards" element={<DashboardIndex/>}/><Route path="/dashboards/:id/edit" element={<p>editor</p>}/></Routes></MemoryRouter></QueryClientProvider>);

describe("personal dashboard index", () => {
  beforeEach(() => { vi.clearAllMocks(); vi.mocked(api.getOperationalContext).mockResolvedValue({data:{organization_id:1,permissions:["personal_dashboard.read","personal_dashboard.manage"]}}); vi.mocked(api.listDashboards).mockResolvedValue({data:[]}); vi.mocked(api.cloneSystemDashboard).mockResolvedValue({data:row}); });
  it("shows an intentional empty state and creates through the governed template", async () => { renderPage(); expect(await screen.findByText("هنوز داشبورد شخصی ندارید")).toBeInTheDocument(); await userEvent.click(screen.getByRole("button",{name:/ایجاد داشبورد شخصی/})); expect(await screen.findByText("editor")).toBeInTheDocument(); expect(api.cloneSystemDashboard).toHaveBeenCalledTimes(1); });
  it("lists and opens owned dashboards", async () => { vi.mocked(api.listDashboards).mockResolvedValueOnce({data:[row]}); renderPage(); expect(await screen.findByText("داشبورد من")).toBeInTheDocument(); expect(screen.getByRole("link",{name:"باز کردن"})).toHaveAttribute("href","/dashboards/db-1"); });
  it("does not expose create without manage", async () => { vi.mocked(api.getOperationalContext).mockResolvedValueOnce({data:{organization_id:1,permissions:["personal_dashboard.read"]}}); renderPage(); await screen.findByText("هنوز داشبورد شخصی ندارید"); expect(screen.queryByRole("button",{name:/ایجاد داشبورد شخصی/})).not.toBeInTheDocument(); });
});
