import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import ShipmentOwnerTransfer from "@/components/ShipmentOwnerTransfer";
import { ApiError } from "@/lib/api";
import type { OwnerTransferView } from "@/lib/ownerTransferApi";
const api = vi.hoisted(() => ({get: vi.fn(), candidates: vi.fn(), transfer: vi.fn()}));
vi.mock("@/lib/ownerTransferApi", () => ({getOwnerTransfers: api.get, getOwnerCandidates: api.candidates, transferOwner: api.transfer}));
const view: OwnerTransferView = {shipment_public_id: "shipment", shipment_version: 7,
  current_owner: {id: 1, display_name: "Current owner"}, initial_owner: {id: 1, display_name: "Initial owner", provenance: "PERSISTED_OWNER_WITHOUT_TRANSFER", occurred_at: null},
  transfers: [], page: 1, has_more: false, capabilities: {TRANSFER_OWNER: true}, available: true, old_owner_open_work_count: 3};
async function choose() {
  await screen.findByRole("option", {name: "Target expert"});
  fireEvent.change(screen.getByLabelText("کارشناس مسئول جدید"), {target: {value: "2"}});
  fireEvent.change(screen.getByLabelText("دلیل انتقال (الزامی)"), {target: {value: "Explicit reason"}});
  await waitFor(() => expect(screen.getByRole("button", {name: "بررسی انتقال مسئول"})).toBeEnabled());
  fireEvent.click(screen.getByRole("button", {name: "بررسی انتقال مسئول"}));
}
describe("exceptional owner transfer", () => {
  beforeEach(() => {
    vi.clearAllMocks(); api.get.mockResolvedValue({data: view});
    api.candidates.mockResolvedValue({data: {candidates: [{id: 2, display_name: "Target expert"}], page: 1, has_more: false}});
    api.transfer.mockResolvedValue({data: {public_id: "receipt", created: true}});
  });
  it("requires target, reason and explicit final confirmation with pinned version", async () => {
    render(<ShipmentOwnerTransfer shipment="shipment" />);
    expect(await screen.findByRole("button", {name: "بررسی انتقال مسئول"})).toBeDisabled();
    expect(screen.getByText(/کارهای بازِ مسئول فعلی/)).toHaveTextContent("3");
    await choose(); expect(api.transfer).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", {name: "تأیید نهایی انتقال"}));
    await waitFor(() => expect(api.transfer).toHaveBeenCalledWith("shipment", {expected_owner_id: 1, target_owner_id: 2, expected_version: 7, reason: "Explicit reason"}, expect.any(String)));
  });
  it("keeps the idempotency key after an uncertain response and requires review again", async () => {
    api.transfer.mockRejectedValue(new Error("Lost response"));
    render(<ShipmentOwnerTransfer shipment="shipment" />); await choose();
    fireEvent.click(screen.getByRole("button", {name: "تأیید نهایی انتقال"}));
    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByRole("button", {name: "بررسی انتقال مسئول"})).toBeEnabled());
    fireEvent.click(screen.getByRole("button", {name: "بررسی انتقال مسئول"}));
    fireEvent.click(screen.getByRole("button", {name: "تأیید نهایی انتقال"}));
    await waitFor(() => expect(api.transfer).toHaveBeenCalledTimes(2));
    expect(api.transfer.mock.calls[0][2]).toBe(api.transfer.mock.calls[1][2]);
  });
  it("removes confirmation and revalidates after a stale owner conflict", async () => {
    api.transfer.mockRejectedValue(new ApiError(409, "OWNER_TRANSFER_STALE", "PRIVATE DATABASE DETAIL"));
    render(<ShipmentOwnerTransfer shipment="shipment" />); await choose();
    api.get.mockResolvedValue({data: {...view, shipment_version: 8, current_owner: {id: 3, display_name: "Concurrent owner"}}});
    fireEvent.click(screen.getByRole("button", {name: "تأیید نهایی انتقال"}));
    await screen.findByText("Concurrent owner");
    expect(screen.queryByRole("button", {name: "تأیید نهایی انتقال"})).not.toBeInTheDocument();
    expect(screen.queryByText("PRIVATE DATABASE DETAIL")).not.toBeInTheDocument();
  });
  it.each(["expert", "unsafe database"])("offers no transfer command for %s", async scenario => {
    api.get.mockResolvedValue({data: {...view, available: false, capabilities: {TRANSFER_OWNER: scenario !== "expert"}}});
    render(<ShipmentOwnerTransfer shipment="shipment" />); await screen.findByText("Current owner");
    expect(screen.queryByLabelText("کارشناس مسئول جدید")).not.toBeInTheDocument();
    expect(api.candidates).not.toHaveBeenCalled(); expect(api.transfer).not.toHaveBeenCalled();
  });
  it("rejects late private history after focus detects revoked access", async () => {
    let finish!: (value: {data: OwnerTransferView}) => void;
    api.get.mockImplementationOnce(() => new Promise(resolve => {finish = resolve;}));
    render(<ShipmentOwnerTransfer shipment="shipment" />);
    api.get.mockRejectedValue(new ApiError(404, "NOT_FOUND", ""));
    fireEvent.focus(window); await screen.findByRole("alert");
    await act(async () => finish({data: view}));
    expect(screen.queryByText("Current owner")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("دلیل انتقال (الزامی)")).not.toBeInTheDocument();
  });
});
