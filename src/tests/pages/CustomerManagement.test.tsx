import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CustomerManagement from "@/pages/CustomerManagement";
import * as api from "@/lib/api";

vi.mock("@/components/PageNav", () => ({ default: () => <div>بازگشت</div> }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchCustomers: vi.fn(), createCustomer: vi.fn() };
});

const renderPage = () => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><CustomerManagement /></MemoryRouter></QueryClientProvider>);

describe("CustomerManagement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem("expert_user", JSON.stringify({ authority: "ORGANIZATION_ADMIN", role: "expert" }));
    vi.mocked(api.fetchCustomers).mockResolvedValue({ customers: [{ id: 9, name: "نماینده ایران خودرو", company_name: "ایران خودرو", customer_type: "prospect", status: "active", created_at: "2026-01-01", total_opportunities: 0, total_activities: 0 }], pagination: { page: 1, per_page: 100, total: 1, pages: 1, has_next: false, has_prev: false } });
  });

  it("shows tenant customer navigation surface and list", async () => {
    renderPage();
    expect(await screen.findByRole("heading", { name: "مشتریان" })).toBeInTheDocument();
    expect(screen.getByText("ایران خودرو")).toBeInTheDocument();
    expect(api.fetchCustomers).toHaveBeenCalledWith(expect.objectContaining({ per_page: 100 }));
  });

  it("requires a company identity before creating", async () => {
    const user = userEvent.setup(); renderPage();
    await screen.findByText("ایران خودرو");
    await user.click(screen.getByRole("button", { name: "ایجاد مشتری" }));
    await user.click(screen.getByRole("button", { name: "ثبت مشتری" }));
    expect(api.createCustomer).not.toHaveBeenCalled();
  });

  it("creates and refreshes the server customer list", async () => {
    const user = userEvent.setup(); vi.mocked(api.createCustomer).mockResolvedValue({ message: "مشتری با موفقیت ایجاد شد", customer_id: 10 }); renderPage();
    await screen.findByText("ایران خودرو"); await user.click(screen.getByRole("button", { name: "ایجاد مشتری" }));
    await user.type(screen.getByLabelText("نام شرکت *"), "ایران خودرو");
    await user.click(screen.getByRole("button", { name: "ثبت مشتری" }));
    await waitFor(() => expect(api.createCustomer).toHaveBeenCalledWith(expect.objectContaining({ company_name: "ایران خودرو", duplicate_acknowledged: false })));
    await waitFor(() => expect(api.fetchCustomers).toHaveBeenCalledTimes(2));
  });

  it("requires an explicit retry after a duplicate warning", async () => {
    const user = userEvent.setup();
    vi.mocked(api.createCustomer).mockRejectedValueOnce(new api.ApiError(409, "DUPLICATE_CUSTOMER_CONFIRMATION_REQUIRED", "duplicate"));
    renderPage(); await screen.findByText("ایران خودرو"); await user.click(screen.getByRole("button", { name: "ایجاد مشتری" }));
    await user.type(screen.getByLabelText("نام شرکت *"), "ایران خودرو");
    await user.click(screen.getByRole("button", { name: "ثبت مشتری" }));
    expect(await screen.findByText("مشتری مشابهی در همین سازمان پیدا شد. پس از بررسی، دوباره ایجاد را تایید کنید.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "تایید و ایجاد مشتری" })).toBeInTheDocument();
  });

  it("does not render for Platform Admin", () => {
    localStorage.setItem("expert_user", JSON.stringify({ authority: "PLATFORM_ADMIN", role: "admin" })); renderPage();
    expect(screen.queryByRole("heading", { name: "مشتریان" })).not.toBeInTheDocument();
  });

  it("does not render for an ordinary Expert", () => {
    localStorage.setItem("expert_user", JSON.stringify({ authority: "EXPERT", role: "expert" })); renderPage();
    expect(screen.queryByRole("heading", { name: "مشتریان" })).not.toBeInTheDocument();
    expect(api.fetchCustomers).not.toHaveBeenCalled();
  });
});
