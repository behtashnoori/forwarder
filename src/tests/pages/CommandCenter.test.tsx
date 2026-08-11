import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Index, { trackingRouteFor } from "@/pages/Index";
import { I18nProvider } from "@/i18n";
import { SiteSettingsProvider } from "@/contexts/SiteSettingsContext";

vi.mock("@/lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/api")>();
  return { ...original, fetchSiteSettings: vi.fn().mockResolvedValue({}) };
});

const renderPage = () => render(
  <MemoryRouter initialEntries={["/"]}>
    <I18nProvider><SiteSettingsProvider><Routes>
      <Route path="/" element={<Index />} />
      <Route path="/customer/track/:code" element={<p>request destination</p>} />
      <Route path="/project/track/:code" element={<p>project destination</p>} />
    </Routes></SiteSettingsProvider></I18nProvider>
  </MemoryRouter>,
);

describe("Forwarder Command Center", () => {
  beforeEach(() => localStorage.clear());

  it("presents the integrated platform with one dedicated tracking form", () => {
    renderPage();
    expect(screen.getByRole("heading", { name: "عملیات حمل، یکپارچه و هوشمند" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "شروع یک حمل جدید" })).toBeInTheDocument();
    expect(screen.getByLabelText("کد رهگیری")).toBeInTheDocument();
    expect(screen.getAllByLabelText("کد رهگیری")).toHaveLength(1);
    expect(document.querySelectorAll("form input#command-tracking")).toHaveLength(1);
    expect(document.querySelectorAll("h1")).toHaveLength(1);
    expect(screen.getByText("نرخ‌گذاری")).toBeInTheDocument();
  });

  it("locks the English public brand and platform positioning", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "تغییر زبان به انگلیسی" }));
    expect(screen.getAllByText("Forwarderet").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Transport operations, connected and intelligent" })).toBeInTheDocument();
    expect(screen.queryByText("Forwardert")).not.toBeInTheDocument();
  });

  it("uses sign-in as the restrained primary account action", () => {
    renderPage();
    expect(screen.getAllByRole("button", { name: "ورود به سامانه" })).toHaveLength(1);
  });

  it("opens the existing domestic/international request choice from the primary CTA", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "شروع یک حمل جدید" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ثبت درخواست حمل داخلی" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ثبت درخواست حمل بین‌المللی" })).toBeInTheDocument();
  });

  it("validates an empty tracking submission and associates the error", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "پیگیری" }));
    expect(screen.getByRole("alert")).toHaveTextContent("لطفاً کد رهگیری را وارد کنید.");
    expect(screen.getByLabelText("کد رهگیری")).toHaveAttribute("aria-invalid", "true");
  });

  it("submits a request tracking code with Enter", async () => {
    renderPage();
    const input = screen.getByLabelText("کد رهگیری");
    await userEvent.type(input, "SR-A7K2M9{Enter}");
    expect(screen.getByText("request destination")).toBeInTheDocument();
  });

  it("routes opaque Project codes without changing the backend contract", async () => {
    renderPage();
    await userEvent.type(screen.getByLabelText("کد رهگیری"), "opaque-project-code{Enter}");
    expect(screen.getByText("project destination")).toBeInTheDocument();
  });

  it("preserves documented request and Project route compatibility", () => {
    expect(trackingRouteFor("SR-ABC123")).toBe("/customer/track/SR-ABC123");
    expect(trackingRouteFor("12345")).toBe("/customer/track/12345");
    expect(trackingRouteFor("opaque/project code")).toBe("/project/track/opaque%2Fproject%20code");
  });
});
