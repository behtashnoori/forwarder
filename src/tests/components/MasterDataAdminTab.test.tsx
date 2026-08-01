import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import MasterDataAdminTab from "@/components/MasterDataAdminTab";

const api = vi.hoisted(() => ({
  fetchMasterData: vi.fn(), createMasterData: vi.fn(), updateMasterData: vi.fn(), setMasterDataActive: vi.fn(),
}));
vi.mock("@/lib/api", () => api);

const item = { id: 1, public_id: "public-1", immutable_code: "GENERAL", fa_name: "عمومی", en_name: "General", description: null, display_order: 0, is_active: true, version: 1, created_at: "2026-08-01", updated_at: "2026-08-01" };

describe("MasterDataAdminTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.fetchMasterData.mockResolvedValue({ items: [item], page: 1, per_page: 10, total: 1, pages: 1 });
    api.setMasterDataActive.mockResolvedValue({ item: { ...item, is_active: false, version: 2 } });
  });

  it("loads, searches, filters, and activates through the reusable grid", async () => {
    render(<MasterDataAdminTab />);
    expect(await screen.findByText("GENERAL")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("جستجو"), { target: { value: "gen" } });
    await waitFor(() => expect(api.fetchMasterData).toHaveBeenCalledWith("cargo-types", expect.objectContaining({ q: "gen" })));
    fireEvent.click(screen.getByRole("button", { name: "غیرفعال‌سازی" }));
    await waitFor(() => expect(api.setMasterDataActive).toHaveBeenCalledWith("cargo-types", item, false));
  });

  it("opens the create dialog with immutable code and bilingual names", async () => {
    render(<MasterDataAdminTab />);
    await screen.findByText("GENERAL");
    fireEvent.click(screen.getByRole("button", { name: "ایجاد" }));
    expect((screen.getByPlaceholderText("کد ثابت") as HTMLInputElement).disabled).toBe(false);
    expect(screen.getByPlaceholderText("نام فارسی")).toBeTruthy();
    expect(screen.getByPlaceholderText("نام انگلیسی")).toBeTruthy();
  });
});
