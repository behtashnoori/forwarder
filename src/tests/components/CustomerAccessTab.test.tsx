import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CustomerAccessTab from "@/components/CustomerAccessTab";
import { fetchCustomerAccess, grantCustomerAccess, revokeCustomerAccess } from "@/lib/customerEntitlementApi";

vi.mock("@/lib/customerEntitlementApi", () => ({
  fetchCustomerAccess: vi.fn(), grantCustomerAccess: vi.fn(), revokeCustomerAccess: vi.fn(),
}));
const grant = { public_id: "grant-a", portal_account_public_id: "account-a", account_label: "a@example.test",
  customer_id: 1, customer_label: "شرکت الف", status: "ACTIVE" as const,
  granted_at: "2026-09-25T10:00:00Z", granted_by: 1, revoked_at: null, revoked_by: null };
const configuration = { accounts: [{ public_id: "account-a", label: "a@example.test" }],
  customers: [{ id: 1, label: "شرکت الف" }], grants: [] as typeof grant[] };
beforeEach(() => { vi.resetAllMocks(); vi.mocked(fetchCustomerAccess).mockResolvedValue(configuration); });
describe("Customer access administration", () => {
  it("grants explicitly, reloads current configuration and revokes with history", async () => {
    vi.mocked(grantCustomerAccess).mockResolvedValue({ item: grant });
    vi.mocked(revokeCustomerAccess).mockResolvedValue({ item: { ...grant, status: "REVOKED" } });
    render(<CustomerAccessTab />);
    expect(await screen.findByText("هنوز دسترسی‌ای ثبت نشده است.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("حساب پورتال"), { target: { value: "account-a" } });
    fireEvent.change(screen.getByLabelText("مشتری / شرکت"), { target: { value: "1" } });
    vi.mocked(fetchCustomerAccess).mockResolvedValue({ ...configuration, grants: [grant] });
    fireEvent.click(screen.getByRole("button", { name: "اعطای دسترسی" }));
    await waitFor(() => expect(grantCustomerAccess).toHaveBeenCalledWith("account-a", 1, expect.any(String)));
    const revoke = await screen.findByRole("button", { name: "لغو دسترسی" });
    fireEvent.click(revoke);
    await waitFor(() => expect(revokeCustomerAccess).toHaveBeenCalledWith("grant-a"));
    expect(await screen.findByText(/دسترسی لغو شد/)).toBeInTheDocument();
  });
  it("shows failed grants without pretending success and preserves the retry command", async () => {
    vi.mocked(grantCustomerAccess).mockRejectedValue(new Error("ارتباط قطع شد"));
    render(<CustomerAccessTab />);
    await screen.findByLabelText("حساب پورتال");
    fireEvent.change(screen.getByLabelText("حساب پورتال"), { target: { value: "account-a" } });
    fireEvent.change(screen.getByLabelText("مشتری / شرکت"), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "اعطای دسترسی" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("ارتباط قطع شد");
    fireEvent.click(screen.getByRole("button", { name: "اعطای دسترسی" }));
    await waitFor(() => expect(grantCustomerAccess).toHaveBeenCalledTimes(2));
    expect(vi.mocked(grantCustomerAccess).mock.calls[0][2]).toBe(vi.mocked(grantCustomerAccess).mock.calls[1][2]);
  });
});
