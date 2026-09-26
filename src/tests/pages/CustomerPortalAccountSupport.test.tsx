import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CustomerPortalAccountSupport from "@/pages/CustomerPortalAccountSupport";
import { listAdminPortalAccounts, type AdminPortalAccount } from "@/lib/customerPortalApi";

vi.mock("@/lib/customerPortalApi", async importOriginal => ({
  ...await importOriginal<typeof import("@/lib/customerPortalApi")>(),
  listAdminPortalAccounts: vi.fn(),
}));

const account = (publicId: string, email: string): AdminPortalAccount => ({
  public_id: publicId,
  email,
  phone: "09000000000",
  first_name: null,
  last_name: null,
  account_status: "ACTIVE",
  enrollment_state: "ENROLLED",
  request_count: 0,
  linkage_source: "tenant",
});

describe("CustomerPortalAccountSupport request freshness", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem("expert_user", JSON.stringify({ authority: "ORGANIZATION_ADMIN" }));
  });

  it("does not let the older initial list overwrite a newer search", async () => {
    let resolveInitial!: (value: { items: AdminPortalAccount[] }) => void;
    vi.mocked(listAdminPortalAccounts)
      .mockImplementationOnce(() => new Promise(resolve => { resolveInitial = resolve; }))
      .mockResolvedValueOnce({ items: [account("target", "target@example.test")] });

    render(<MemoryRouter><CustomerPortalAccountSupport /></MemoryRouter>);
    fireEvent.change(screen.getByLabelText("جستجوی حساب پرتال"), { target: { value: "target@example.test" } });
    fireEvent.click(screen.getByRole("button", { name: "جستجو" }));
    expect(await screen.findByText("target@example.test")).toBeInTheDocument();

    await act(async () => resolveInitial({ items: [account("old", "old@example.test")] }));
    expect(screen.getByText("target@example.test")).toBeInTheDocument();
    expect(screen.queryByText("old@example.test")).not.toBeInTheDocument();
  });
});
