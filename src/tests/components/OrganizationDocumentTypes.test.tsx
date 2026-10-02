import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import OrganizationDocumentTypes from "@/components/OrganizationDocumentTypes";

const api = vi.hoisted(() => ({list: vi.fn(), save: vi.fn()}));
vi.mock("@/lib/api", () => ({fetchOrganizationDocumentTypes: api.list, saveOrganizationDocumentType: api.save}));
const own = {public_id: "own", code: "org_stable", name_fa: "راهنامه CMR", name_en: "CMR", description: null, ownership: "ORGANIZATION", is_active: true, revision: 1};
const system = {...own, public_id: "global", name_fa: "بارنامه", ownership: "SYSTEM"};

describe("organization document catalog", () => {
  beforeEach(() => {vi.clearAllMocks(); api.list.mockResolvedValue({items: [system]}); api.save.mockResolvedValue(own);});
  it("creates a simple type and permits deactivation only for the organization-owned row", async () => {
    render(<OrganizationDocumentTypes />);
    await screen.findByText("بارنامه");
    expect(screen.queryByRole("button", {name: "غیرفعال کردن"})).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("نام فارسی"), {target: {value: "راهنامه CMR"}});
    fireEvent.change(screen.getByLabelText("نام انگلیسی (اختیاری)"), {target: {value: "CMR"}});
    api.list.mockResolvedValue({items: [system, own]});
    fireEvent.click(screen.getByRole("button", {name: "افزودن نوع سند"}));
    await screen.findByText("راهنامه CMR");
    expect(api.save.mock.calls[0][0]).toEqual({name_fa: "راهنامه CMR", name_en: "CMR", description: ""});
    expect(api.save.mock.calls[0][2]).toBeUndefined();
    api.list.mockResolvedValue({items: [system, {...own, is_active: false, revision: 2}]});
    fireEvent.click(screen.getByRole("button", {name: "غیرفعال کردن"}));
    await waitFor(() => expect(api.save).toHaveBeenCalledTimes(2));
    expect(api.save.mock.calls[1][0]).toEqual({is_active: false, expected_revision: 1});
    expect(api.save.mock.calls[1][2]).toBe("own");
    expect(await screen.findByText("غیرفعال")).toBeInTheDocument();
    expect(within(screen.getByText("بارنامه").closest("li")!).queryByRole("button")).not.toBeInTheDocument();
  });
  it("retains input and the same retry key after an unknown failed save", async () => {
    api.save.mockRejectedValueOnce(new Error("قطع ارتباط"));
    render(<OrganizationDocumentTypes />); await screen.findByText("بارنامه");
    fireEvent.change(screen.getByLabelText("نام فارسی"), {target: {value: "راهنامه"}});
    fireEvent.click(screen.getByRole("button", {name: "افزودن نوع سند"}));
    expect(await screen.findByRole("alert")).toHaveTextContent("قطع ارتباط");
    expect(screen.getByLabelText("نام فارسی")).toHaveValue("راهنامه");
    fireEvent.click(screen.getByRole("button", {name: "افزودن نوع سند"}));
    await waitFor(() => expect(api.save).toHaveBeenCalledTimes(2));
    expect(api.save.mock.calls[0][1]).toBe(api.save.mock.calls[1][1]);
  });
});
