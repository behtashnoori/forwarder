import type { ReactNode } from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CustomerPortalShipments, { CustomerPortalShipmentDetail } from "@/pages/CustomerPortalShipments";
import { customerRequest, CustomerPortalApiError, downloadCustomerSharedDocument } from "@/lib/customerPortalApi";
import type { CustomerShipmentDetail } from "@/lib/customerShipmentApi";

vi.mock("@/components/CustomerPortalLayout", () => ({ default: ({ children }: { children: ReactNode }) => <main>{children}</main> }));
vi.mock("@/lib/customerPortalApi", async original => ({ ...await original<typeof import("@/lib/customerPortalApi")>(), customerRequest: vi.fn(), downloadCustomerSharedDocument: vi.fn() }));
const empty = { items: [], page: 1, has_prev: false, has_next: false };
const authorization = { authorization_revision: "scope-a" };
const fixture = (): CustomerShipmentDetail => ({ ...authorization, public_id: "shipment-a", created_at: "2026-09-21T08:00:00Z", status: "in_progress", shared_transport: true,
  cargo: [{ public_id: "cargo-a", label: "کالای اول", customer_label: "مشتری الف", type_label: "قطعات", uom_symbol: "کارتن", requested: null, planned: "100", known_actual: null, delivered: "60", remaining: null, excess: null, has_delivery: true }],
  routes: [{ cargo_public_id: "cargo-a", legs: [] }], reported_locations: [], timeline: empty, deliveries: empty,
  documents: { ...empty, items: [{ public_id: "doc-a", filename: "document-v1.pdf", version: 1, context_type: "CARGO" }] } });
const renderDetail = () => render(<MemoryRouter initialEntries={["/customer/shipments/shipment-a"]}><Routes><Route path="/customer/shipments/:shipmentId" element={<CustomerPortalShipmentDetail />} /><Route path="/customer" element={<p>ورود مشتری</p>} /></Routes></MemoryRouter>);
beforeEach(() => { vi.resetAllMocks(); Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" }); });

describe("private Customer Shipment freshness", () => {
  it("shows honest unknowns and clears the entire projection when a download is revoked", async () => {
    vi.mocked(customerRequest).mockResolvedValue(fixture());
    vi.mocked(downloadCustomerSharedDocument).mockRejectedValue(new CustomerPortalApiError(404, "NOT_FOUND", "دسترسی سند لغو شده است"));
    renderDetail();
    await screen.findByRole("heading", { name: "کالاهای من" });
    expect(screen.getAllByText("نامشخص").length).toBe(3);
    expect(screen.getByText("مسیر این کالا هنوز تعریف نشده است.")).toBeInTheDocument();
    expect(screen.queryByText(/GPS/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "دریافت سند" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("دسترسی سند لغو شده است");
    expect(screen.queryByRole("heading", { name: "کالاهای من" })).not.toBeInTheDocument();
    expect(downloadCustomerSharedDocument).toHaveBeenCalledWith("doc-a", "document-v1.pdf");
  });

  it("ignores a late successful request after pageshow reauthorization denies access", async () => {
    let stale: (value: CustomerShipmentDetail) => void = () => undefined;
    vi.mocked(customerRequest).mockImplementationOnce(() => new Promise(resolve => { stale = resolve; }))
      .mockRejectedValueOnce(new CustomerPortalApiError(404, "NOT_FOUND", "پرونده حمل در دسترس نیست."));
    renderDetail();
    fireEvent(window, new Event("pageshow"));
    await screen.findByRole("alert");
    await act(async () => stale(fixture()));
    expect(screen.queryByText("کالای اول")).not.toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("پرونده حمل در دسترس نیست.");
    expect(vi.mocked(customerRequest).mock.calls[0][1]?.signal?.aborted).toBe(true);
    expect(customerRequest).toHaveBeenCalledWith(expect.stringContaining("/api/customer/shipments/"), expect.objectContaining({ cache: "no-store", signal: expect.any(AbortSignal) }));
  });

  it("clears before browser hiding and uses fresh authorization on return and session revoke", async () => {
    vi.mocked(customerRequest).mockResolvedValueOnce(fixture()).mockResolvedValueOnce(authorization).mockRejectedValueOnce(new CustomerPortalApiError(401, "SESSION_REVOKED", "نشست پایان یافته است"));
    renderDetail(); await screen.findByRole("heading", { name: "کالاهای من" });
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
    fireEvent(document, new Event("visibilitychange"));
    expect(screen.queryByText("کالای اول")).not.toBeInTheDocument();
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
    fireEvent(document, new Event("visibilitychange"));
    await screen.findByText("ورود مشتری");
  });

  it("clears stale list rows before focus refresh and retains only the newly authorized union", async () => {
    vi.mocked(customerRequest).mockResolvedValueOnce({ ...authorization, items: [fixture()], pagination: { page: 1, total: 1, has_prev: false, has_next: false } })
      .mockResolvedValueOnce(authorization)
      .mockResolvedValueOnce({ ...authorization, items: [], pagination: { page: 1, total: 0, has_prev: false, has_next: false } }).mockResolvedValueOnce(authorization);
    render(<MemoryRouter><CustomerPortalShipments /></MemoryRouter>);
    await screen.findByRole("link", { name: "مشاهده پرونده حمل" });
    fireEvent(window, new Event("focus"));
    expect(screen.queryByRole("link", { name: "مشاهده پرونده حمل" })).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("حملی در این فهرست برای شما در دسترس نیست.")).toBeInTheDocument());
    expect(customerRequest).toHaveBeenCalledTimes(4);
  });

  it("reauthorizes a delayed detail before render without needing a browser event", async () => {
    let complete: (value: CustomerShipmentDetail) => void = () => undefined;
    const b = { ...fixture(), authorization_revision: "scope-b", cargo: [{ ...fixture().cargo[0], label: "کالای دوم" }] };
    vi.mocked(customerRequest).mockImplementationOnce(() => new Promise(resolve => { complete = resolve; }))
      .mockResolvedValueOnce({ authorization_revision: "scope-b" }).mockResolvedValueOnce(b)
      .mockResolvedValueOnce({ authorization_revision: "scope-b" });
    renderDetail();
    await act(async () => complete(fixture()));
    await screen.findAllByText("کالای دوم");
    expect(screen.queryByText("کالای اول")).not.toBeInTheDocument();
    expect(customerRequest).toHaveBeenCalledTimes(4);
  });

  it("rejects a delayed list when its acceptance check observes revoked session generation", async () => {
    vi.mocked(customerRequest).mockResolvedValueOnce({ ...authorization, items: [fixture()], pagination: { page: 1, total: 1, has_prev: false, has_next: false } })
      .mockRejectedValueOnce(new CustomerPortalApiError(401, "SESSION_REVOKED", "نشست پایان یافته است"));
    render(<MemoryRouter initialEntries={["/customer/shipments"]}><Routes><Route path="/customer/shipments" element={<CustomerPortalShipments />} /><Route path="/customer" element={<p>ورود مشتری</p>} /></Routes></MemoryRouter>);
    await screen.findByText("ورود مشتری");
    expect(screen.queryByRole("link", { name: "مشاهده پرونده حمل" })).not.toBeInTheDocument();
  });
});
