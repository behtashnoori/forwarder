import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../pages/OperationalShipments", () => ({ default: () => <p>operational shipments</p> }));
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
});
