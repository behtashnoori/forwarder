import { render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../pages/OperationalShipments", () => ({ default: () => <p>operational shipments</p> }));
vi.mock("../pages/OperationalWorkspace", () => ({ default: () => <p>operational workspace</p> }));
vi.mock("../components/ProtectedRoute", () => ({ default: ({ children }: { children: ReactNode }) => children }));
vi.mock("../components/ErrorBoundary", () => ({ default: ({ children }: { children: ReactNode }) => children }));
vi.mock("../components/RouteScrollManager", () => ({ default: () => null }));
vi.mock("../components/ui/toaster", () => ({ Toaster: () => null }));
vi.mock("../components/ui/sonner", () => ({ Toaster: () => null }));
vi.mock("../contexts/SiteSettingsContext", () => ({ SiteSettingsProvider: ({ children }: { children: ReactNode }) => children }));
vi.mock("../pages/Index", () => ({ default: () => <p>public index</p> }));

import App from "../App";

describe("App operational routing", () => {
  beforeEach(() => {
    localStorage.clear();
    window.history.pushState({}, "", "/operations/shipments");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: "ok" }) }));
  });

  it("allows organization-scoped users to reach operational routes", async () => {
    localStorage.setItem("expert_user", JSON.stringify({ authority: "ORGANIZATION_ADMIN" }));
    render(<App />);
    expect(await screen.findByText("operational shipments")).toBeInTheDocument();
  });

  it("makes the operational workspace available to organization-scoped users", async () => {
    localStorage.setItem("expert_user", JSON.stringify({ authority: "EXPERT" }));
    window.history.pushState({}, "", "/operations");
    render(<App />);
    expect(await screen.findByText("operational workspace")).toBeInTheDocument();
  });

  it("blocks a platform admin that has no tenant context", async () => {
    localStorage.setItem("expert_user", JSON.stringify({ authority: "PLATFORM_ADMIN" }));
    render(<App />);
    expect(await screen.findByText("این سطح عملیاتی به یک سازمان مشخص نیاز دارد.")).toBeInTheDocument();
    expect(screen.queryByText("operational shipments")).not.toBeInTheDocument();
  });

  it("redirects malformed stored authentication state to the public route", async () => {
    localStorage.setItem("expert_user", "{");
    render(<App />);
    expect(await screen.findByText("public index")).toBeInTheDocument();
  });

  it("freezes the complete Golden route inventory and catch-all ordering", () => {
    const source = readFileSync("src/App.tsx", "utf8");
    const routes = [...source.matchAll(/<Route\s+path="([^"]+)"/g)].map((match) => match[1]);

    expect(routes).toEqual([
      "/",
      "/about",
      "/contact",
      "/expert",
      "/expert/requests/:id",
      "/crm",
      "/admin",
      "/admin/customers",
      "/admin/customer-portal-accounts",
      "/customers",
      "/user-management",
      "/operations",
      "/operations/shipments",
      "/operations/shipments/new",
      "/operations/shipments/:id",
      "/operations/work-queue",
      "/operations/control-tower",
      "/dashboards",
      "/dashboards/:public_id",
      "/dashboards/:public_id/edit",
      "/operations/intelligence/:id",
      "/operations/projects/:projectId/units",
      "/customer",
      "/customer/forgot-password",
      "/customer/reset-password",
      "/customer/enroll",
      "/customer/requests",
      "/customer/shipments",
      "/customer/shipments/:shipmentId",
      "/customer/documents",
      "/customer/requests/:requestId",
      "/customer/profile",
      "/customer/change-password",
      "/customer/:customerId",
      "/request/:requestId",
      "/customer/track/:requestId",
      "/project/track/:trackingCode",
      "/verify-email",
      "*",
    ]);
    expect(routes.at(-1)).toBe("*");
  });
});
