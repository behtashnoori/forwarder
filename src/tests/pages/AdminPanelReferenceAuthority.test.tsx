import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { I18nProvider } from "@/i18n";
import AdminPanel from "@/pages/AdminPanel";
import * as api from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchAdminDashboard: vi.fn(),
  };
});
vi.mock("@/components/ReleaseIdentity", () => ({ default: () => <span>release</span> }));

const dashboard: api.AdminDashboardStats = {
  total_requests: 0,
  requests_per_transport_method: {},
  requests_per_status: {},
  last_7_days_count: 0,
  last_24h_count: 0,
  unassigned_count: 0,
  top_provinces: [],
};

const renderFor = (authority: "ORGANIZATION_ADMIN" | "PLATFORM_ADMIN") => {
  localStorage.setItem("expert_token", "token");
  localStorage.setItem("expert_user", JSON.stringify({ authority, full_name: "Admin" }));
  return render(<I18nProvider><MemoryRouter><AdminPanel /></MemoryRouter></I18nProvider>);
};

describe("AdminPanel reference authority", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchAdminDashboard).mockResolvedValue(dashboard);
  });
  afterEach(() => {
    cleanup();
    localStorage.clear();
  });

  it("shows organization activation and tenant cargo only to Organization Admin", async () => {
    renderFor("ORGANIZATION_ADMIN");
    expect(await screen.findByRole("tab", { name: "تعاریف قابل استفاده سازمان" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "کاتالوگ کالا" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "تعاریف مرکزی" })).not.toBeInTheDocument();
  });

  it("shows the central catalog only to Platform Admin", async () => {
    renderFor("PLATFORM_ADMIN");
    expect(await screen.findByRole("tab", { name: "تعاریف مرکزی" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "تعاریف قابل استفاده سازمان" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "کاتالوگ کالا" })).not.toBeInTheDocument();
  });
});
