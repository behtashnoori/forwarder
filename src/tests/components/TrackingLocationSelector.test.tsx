import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TrackingLocationSelector } from "@/components/TrackingLocationSelector";
import { fetchTrackingLogisticsPoints } from "@/lib/api";

vi.mock("@/lib/api", () => ({ fetchTrackingLogisticsPoints: vi.fn() }));
const point = (id: string) => ({ public_id: id, fa_name: `مکان ${id}`, en_name: `Place ${id}`,
  immutable_code: id, type: { code: "WAREHOUSE", label: "انبار" },
  country: { code: "IR", label: "ایران" }, city: null, province: null });
const page = (id: string, offset = 0, has_more = false) => ({ items: [point(id)], offset, limit: 20, has_more });
const lookup = vi.mocked(fetchTrackingLogisticsPoints);
beforeEach(() => vi.resetAllMocks());

describe("tracking location selection", () => {
  it("reaches a later page and preserves a selected identity across searches", async () => {
    lookup.mockResolvedValueOnce(page("first", 0, true)).mockResolvedValueOnce(page("later", 20)).mockResolvedValueOnce(page("other"));
    const onChange = vi.fn();
    const view = render(<TrackingLocationSelector value="" onChange={onChange} locale="en" />);
    expect(screen.getByRole("status").textContent).toContain("Loading");
    fireEvent.click(await screen.findByRole("button", { name: "More locations" }));
    await screen.findByRole("option", { name: /Place later/ });
    expect(lookup).toHaveBeenLastCalledWith("", 20);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "later" } });
    expect(onChange).toHaveBeenLastCalledWith("later");
    view.rerender(<TrackingLocationSelector value="later" onChange={onChange} locale="en" />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "other" } });
    await screen.findByRole("option", { name: /Place other/ });
    expect(lookup).toHaveBeenLastCalledWith("other", 0);
    expect((screen.getByRole("combobox") as HTMLSelectElement).value).toBe("later");
    expect(screen.getByRole("option", { name: /Place later/ })).toBeTruthy();
  });

  it("distinguishes failed or denied lookup from empty and supports retry", async () => {
    lookup.mockRejectedValueOnce(new Error("403")).mockResolvedValueOnce({ items: [], limit: 20, offset: 0, has_more: false });
    render(<TrackingLocationSelector value="" onChange={vi.fn()} locale="en" />);
    expect((await screen.findByRole("alert")).textContent).toContain("access was denied");
    expect(screen.queryByText(/No eligible/)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByText(/No eligible active/);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("ignores a late response from a previous search", async () => {
    let resolveOld!: (value: ReturnType<typeof page>) => void;
    lookup.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; })).mockResolvedValueOnce(page("new"));
    render(<TrackingLocationSelector value="" onChange={vi.fn()} locale="fa" />);
    await waitFor(() => expect(lookup).toHaveBeenCalledTimes(1));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "new" } });
    await screen.findByRole("option", { name: /مکان new/ });
    await act(async () => resolveOld(page("old")));
    expect(screen.queryByRole("option", { name: /مکان old/ })).toBeNull();
  });
});
