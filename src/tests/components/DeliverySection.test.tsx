import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DeliverySection from "@/components/DeliverySection";
import { listDeliveries, recordDelivery, type DeliveryFact, type DeliveryList } from "@/lib/deliveryApi";
import { uploadShipmentDocument } from "@/lib/api";

vi.mock("@/lib/deliveryApi", () => ({ listDeliveries: vi.fn(), recordDelivery: vi.fn() }));
vi.mock("@/lib/api", async importOriginal => ({ ...await importOriginal<typeof import("@/lib/api")>(), uploadShipmentDocument: vi.fn(), downloadShipmentDocument: vi.fn() }));
const fixture = (canManage = true): DeliveryList => ({ items: [], total: 0, page: 1, can_manage: canManage,
  cargo: [{ public_id: "cargo-a", label: "کالای اول", customer_label: "مشتری الف", uom_public_id: "carton", uom_symbol: "کارتن", known_actual: "100", delivered: "0", remaining: "100", excess: "0", has_delivery: false, can_record: true },
    { public_id: "cargo-b", label: "کالای دوم", customer_label: "مشتری ب", uom_public_id: "carton", uom_symbol: "کارتن", known_actual: "25", delivered: "0", remaining: "25", excess: "0", has_delivery: false, can_record: true }] });
const fact: DeliveryFact = { public_id: "delivery", cargo_public_id: "cargo-a", quantity: "60", uom_symbol: "کارتن", destination_text: "انبار الف", occurred_at: "2026-09-21T08:00:00Z", recorded_at: "2026-09-22T08:00:00Z", revision: 1, status: "CURRENT", is_correction: false, actor_label: "کارشناس", reason: null, corrects_public_id: null, evidence: [] };
beforeEach(() => { vi.clearAllMocks(); vi.mocked(listDeliveries).mockResolvedValue({ data: fixture() }); });

describe("partial cargo deliveries", () => {
  it("accepts excess reality and preserves command key through an uncertain retry", async () => {
    vi.mocked(recordDelivery).mockRejectedValueOnce(new Error("خطای شبکه")).mockResolvedValueOnce({ public_id: "delivery", revision: 1, created: true });
    render(<DeliverySection shipmentId="shipment" />);
    fireEvent.click(await screen.findByRole("button", { name: "تحویل تازه برای کالای اول" }));
    expect(screen.getByLabelText("مقصد تحویل")).toHaveValue("");
    fireEvent.change(screen.getByLabelText("مقدار تحویل"), { target: { value: "102" } });
    fireEvent.change(screen.getByLabelText("مقصد تحویل"), { target: { value: "انبار الف" } });
    fireEvent.change(screen.getByLabelText("زمان وقوع تحویل"), { target: { value: "2026-09-21T10:30" } });
    fireEvent.click(screen.getByRole("button", { name: "ثبت تحویل" }));
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "ثبت تحویل" }));
    await screen.findByText("تحویل ثبت شد؛ وضعیت پرونده حمل تغییری نکرد.");
    const calls = vi.mocked(recordDelivery).mock.calls;
    expect(calls).toHaveLength(2); expect(calls[0][2]).toBe(calls[1][2]);
    expect(calls[0][1]).toEqual({ cargo_public_id: "cargo-a", quantity: "102", uom_public_id: "carton", destination_text: "انبار الف", occurred_at: new Date("2026-09-21T10:30").toISOString(), expected_version: 0 });
  });

  it("shows independent cargo warnings and preserves history in read-only oversight", async () => {
    const data = fixture(false); data.cargo[0] = { ...data.cargo[0], delivered: "102", remaining: "0", excess: "2", has_delivery: true };
    data.items = [fact, { ...fact, public_id: "old", status: "SUPERSEDED", quantity: "62" }]; data.total = 2;
    vi.mocked(listDeliveries).mockResolvedValue({ data });
    render(<DeliverySection shipmentId="shipment" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("۲ کارتن بیش از مقدار واقعی شناخته‌شده");
    expect(screen.getByText("سابقه تحویل‌های اصلاح‌شده")).toBeInTheDocument();
    expect(screen.getByText("هنوز تحویلی ثبت نشده است.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "اصلاح تحویل" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /تحویل تازه برای/ })).not.toBeInTheDocument();
  });

  it("corrects the selected version and uploads evidence to that exact delivery", async () => {
    const data = { ...fixture(), items: [fact], total: 1 };
    vi.mocked(listDeliveries).mockResolvedValue({ data });
    vi.mocked(recordDelivery).mockResolvedValue({ public_id: "correction", revision: 2, created: true });
    vi.mocked(uploadShipmentDocument).mockResolvedValue({ data: {} } as Awaited<ReturnType<typeof uploadShipmentDocument>>);
    render(<DeliverySection shipmentId="shipment" />);
    fireEvent.click(await screen.findByRole("button", { name: "اصلاح تحویل" }));
    fireEvent.change(screen.getByLabelText("مقدار تحویل"), { target: { value: "58" } });
    fireEvent.change(screen.getByLabelText("دلیل اصلاح تحویل"), { target: { value: "بازشماری" } });
    fireEvent.click(screen.getByRole("button", { name: "ثبت اصلاح تحویل" }));
    await waitFor(() => expect(recordDelivery).toHaveBeenCalled());
    expect(vi.mocked(recordDelivery).mock.calls[0][1]).toMatchObject({ quantity: "58", expected_version: 1, corrects_public_id: "delivery", occurred_at: fact.occurred_at, reason: "بازشماری" });
    fireEvent.click(screen.getByText("افزودن مدرک تحویل"));
    const file = new File(["%PDF-1.4"], "proof.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByLabelText("فایل مدرک تحویل"), { target: { files: [file] } });
    // jsdom does not update a file input's native validity from synthetic files.
    fireEvent.submit(screen.getByLabelText("فایل مدرک تحویل").closest("form")!);
    await waitFor(() => expect(uploadShipmentDocument).toHaveBeenCalled());
    const submitted = vi.mocked(uploadShipmentDocument).mock.calls[0][1];
    expect(submitted.get("context_type")).toBe("DELIVERY"); expect(submitted.get("context_target_public_id")).toBe("delivery");
    expect(submitted.get("visibility")).toBe("INTERNAL"); expect(submitted.get("file")).toBe(file);
  });
});
