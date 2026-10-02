import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import CustomerPortalLayout from "@/components/CustomerPortalLayout";

vi.mock("@/components/Header", () => ({ default: () => <header>header</header> }));
vi.mock("@/i18n", () => ({
  useI18n: () => ({
    t: (key: string) => ({
      "customer.portalNavigation": "ناوبری پنل مشتری",
      "customer.requests": "درخواست‌های من",
      "customer.shipments": "حمل‌های من",
      "customer.documents": "اسناد مشتری",
      "customer.profile": "پروفایل مشتری",
      "customer.changePassword": "تغییر گذرواژه",
    } as Record<string, string>)[key] || key,
  }),
}));

describe("Customer portal navigation", () => {
  it("follows the Customer journey order without changing destinations", () => {
    render(<MemoryRouter initialEntries={["/customer/requests"]}><CustomerPortalLayout privateNav><p>content</p></CustomerPortalLayout></MemoryRouter>);
    const links = screen.getByRole("navigation", { name: "ناوبری پنل مشتری" }).querySelectorAll("a");
    expect([...links].map((link) => [link.textContent, link.getAttribute("href")])).toEqual([
      ["درخواست‌های من", "/customer/requests"],
      ["حمل‌های من", "/customer/shipments"],
      ["اسناد مشتری", "/customer/documents"],
      ["پروفایل مشتری", "/customer/profile"],
      ["تغییر گذرواژه", "/customer/change-password"],
    ]);
    expect(screen.getByRole("link", { name: "درخواست‌های من" })).toHaveAttribute("aria-current", "page");
    expect([...links].every((link) => link.classList.contains("navigation-item"))).toBe(true);
  });
});
