import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import OperationsNav from "@/components/OperationsNav";
import { I18nProvider } from "@/i18n";
import * as api from "@/lib/api";

vi.mock("@/components/ReleaseIdentity", () => ({ default: () => <div>release</div> }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, getOperationalContext: vi.fn() };
});

function renderNav(authority: string, permissions = ["operational_shipment.create_direct"], route = "/operations") {
  localStorage.setItem("expert_user", JSON.stringify({ authority, role: "expert" }));
  vi.mocked(api.getOperationalContext).mockResolvedValue({ data: { organization_id: 1, permissions } });
  return render(<MemoryRouter initialEntries={[route]}><I18nProvider><OperationsNav /></I18nProvider></MemoryRouter>);
}

describe("OperationsNav tenant customer maintenance", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows مشتریان for Organization Admin without a legacy CRM role", async () => {
    renderNav("ORGANIZATION_ADMIN");
    expect(await screen.findByRole("link", { name: "مشتریان" })).toHaveAttribute("href", "/customers");
  });

  it.each(["PLATFORM_ADMIN", "EXPERT"])("does not show مشتریان for %s", async (authority) => {
    renderNav(authority);
    await waitFor(() => expect(api.getOperationalContext).toHaveBeenCalled());
    expect(screen.queryByRole("link", { name: "مشتریان" })).not.toBeInTheDocument();
  });

  it("freezes permission-driven operational links for an organization admin", async () => {
    renderNav("ORGANIZATION_ADMIN", [
      "operational_shipment.read",
      "operational_shipment.create_direct",
      "oip.read",
      "personal_dashboard.read",
    ]);

    await waitFor(() => expect(api.getOperationalContext).toHaveBeenCalled());
    expect(screen.getAllByRole("link").map((link) => link.getAttribute("href"))).toEqual([
      "/operations",
      "/expert",
      "/operations/shipments",
      "/operations/control-tower",
      "/dashboards",
      "/operations/work-queue",
      "/customers",
      "/operations/shipments/new",
    ]);
  });

  it("keeps tenant customer maintenance hidden from an Expert with operational permissions", async () => {
    renderNav("EXPERT", [
      "operational_shipment.read",
      "operational_shipment.create_direct",
      "oip.read",
      "personal_dashboard.read",
    ]);

    await waitFor(() => expect(api.getOperationalContext).toHaveBeenCalled());
    expect(screen.getAllByRole("link").map((link) => link.getAttribute("href"))).toEqual([
      "/operations",
      "/expert",
      "/operations/shipments",
      "/operations/control-tower",
      "/dashboards",
      "/operations/work-queue",
      "/operations/shipments/new",
    ]);
  });

  it("does not expose the workspace link without shipment read permission", async () => {
    renderNav("EXPERT", ["oip.read"]);
    await waitFor(() => expect(api.getOperationalContext).toHaveBeenCalled());
    expect(screen.queryByRole("link", { name: "فضای کار امروز" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "درخواست‌ها و قیمت‌ها" })).toHaveAttribute("href", "/expert");
  });

  it("marks the request area current and never marks the create action current", async () => {
    renderNav("EXPERT", ["operational_shipment.read", "operational_shipment.create_direct"], "/expert/requests/request-public-id");
    await waitFor(() => expect(api.getOperationalContext).toHaveBeenCalled());
    expect(screen.getByRole("link", { name: "درخواست‌ها و قیمت‌ها" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /عملیات جدید/ })).not.toHaveAttribute("aria-current");
  });
});
