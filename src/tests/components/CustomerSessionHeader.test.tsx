import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Header from "@/components/Header";
import { fetchCustomerSession } from "@/lib/customerPortalApi";

vi.mock("@/components/ExpertLogin", () => ({ default: () => <button>ورود به سامانه</button> }));
vi.mock("@/lib/customerPortalApi", () => ({ fetchCustomerSession: vi.fn() }));
vi.mock("@/i18n", () => ({
  useI18n: () => ({
    t: (key: string) => ({
      "brand.name": "فورواردرت", "nav.primary": "ناوبری اصلی", "nav.menu": "منو",
      "nav.capabilities": "قابلیت‌ها", "nav.solutions": "راهکارها", "nav.about": "درباره ما", "nav.contact": "تماس با ما",
      "customer.portalEntry": "ورود مشتری", "customer.portalAuthenticatedEntry": "پنل مشتری",
      "app.language.switchLabel": "تغییر زبان", "app.language.toggle": "English",
    } as Record<string, string>)[key] || key,
    toggleLanguage: vi.fn(),
  }),
}));

beforeEach(() => vi.clearAllMocks());

describe("session-aware Customer header entry", () => {
  it("links an authenticated Customer to the portal and removes the login label", async () => {
    vi.mocked(fetchCustomerSession).mockResolvedValue({ authenticated: true, csrf_token: "csrf" });
    render(<MemoryRouter><Header /></MemoryRouter>);
    const entries = await screen.findAllByRole("link", { name: "پنل مشتری" });
    expect(entries[0]).toHaveAttribute("href", "/customer/requests");
    expect(screen.queryByRole("link", { name: "ورود مشتری" })).not.toBeInTheDocument();
  });

  it("keeps the Customer login entry for an unauthenticated visitor", async () => {
    vi.mocked(fetchCustomerSession).mockResolvedValue({ authenticated: false });
    render(<MemoryRouter><Header /></MemoryRouter>);
    const entries = await screen.findAllByRole("link", { name: "ورود مشتری" });
    expect(entries[0]).toHaveAttribute("href", "/customer");
  });
});
