import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PersistedDashboard from "@/pages/PersistedDashboard";
import { operationsControlTower } from "@/dashboard/control-tower";
import * as api from "@/lib/api";

vi.mock("@/lib/api", async () => ({ ...(await vi.importActual<typeof import("@/lib/api")>("@/lib/api")), getDashboard: vi.fn() }));
vi.mock("@/pages/OperationsControlTower", () => ({ default: ({ definition, allowClone, sourceContext }: { definition: unknown; allowClone: boolean; sourceContext: string }) => <output data-testid="shared-runtime">{JSON.stringify({ definition, allowClone, sourceContext })}</output> }));

const dashboard = (overrides = {}) => ({ public_id: "db-1", name: "شخصی", description: "توضیح", status: "ACTIVE", semantic_version: "analytics-semantic-v1", dashboard_schema_version: "dashboard-definition-v1", definition: operationsControlTower, ...overrides });
const renderRoute = (path = "/dashboards/db-1") => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[path]}><Routes><Route path="/dashboards/:public_id" element={<PersistedDashboard />} /></Routes></MemoryRouter></QueryClientProvider>);

describe("persisted dashboard route", () => {
  beforeEach(() => vi.clearAllMocks());
  it("loads directly by the public id and passes the definition to the shared runtime", async () => {
    vi.mocked(api.getDashboard).mockResolvedValue({ data: dashboard() } as never);
    renderRoute();
    expect(await screen.findByTestId("shared-runtime")).toHaveTextContent("نسخهٔ شخصی");
    expect(api.getDashboard).toHaveBeenCalledWith("db-1");
    expect(screen.getByTestId("shared-runtime")).toHaveTextContent('"allowClone":false');
  });
  it("shows a retryable access-safe failure", async () => {
    vi.mocked(api.getDashboard).mockRejectedValue(new Error("not found"));
    renderRoute();
    expect(await screen.findByRole("button", { name: "تلاش دوباره" })).toBeInTheDocument();
  });
  it.each([["semantic_version", "analytics-semantic-v2", "لایهٔ معنایی"], ["dashboard_schema_version", "dashboard-definition-v2", "ساختار"], ["status", "ARCHIVED", "بایگانی"]])("renders explicit persisted state for %s", async (key, value, label) => {
    vi.mocked(api.getDashboard).mockResolvedValue({ data: dashboard({ [key]: value }) } as never);
    renderRoute();
    expect(await screen.findByText(new RegExp(label))).toBeInTheDocument();
  });
});
