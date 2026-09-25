import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ShipmentDocuments from "@/components/ShipmentDocuments";

const api = vi.hoisted(() => ({
  list: vi.fn(), options: vi.fn(), upload: vi.fn(), change: vi.fn(), history: vi.fn(),
}));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchShipmentDocuments: api.list,
    fetchDocumentContextOptions: api.options,
    uploadShipmentDocument: api.upload,
    changeShipmentDocumentContext: api.change,
    fetchShipmentDocumentContextHistory: api.history,
  };
});

const document = {
  public_id: "file-1", business_document_type: "بارنامه", filename: "bol.pdf", version: 1,
  recorded_at: "2026-09-25T12:00:00Z", actor: "کارشناس", owner: "SHIPMENT",
  lifecycle_state: "active", description: null, references: [], requirements: [],
  context: { public_id: "context-1", type: "CARGO", target_public_id: "cargo-1",
    visibility: "CARGO_OWNER", version: 1, audiences: [] },
};
const options = {
  shipment: [{ id: "shipment-1", label: "پرونده حمل" }],
  cargo: [{ id: "cargo-1", label: "کالا ۱" }],
  route_leg: [{ id: "1", label: "مرحله ۱" }],
  execution_unit: [{ id: "unit-1", label: "وسیله ۱" }],
  audience: [{ id: "account-a", label: "مشتری الف" }],
};

describe("contextual Shipment documents", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.list.mockResolvedValue({ data: [document], can_manage_documents: true });
    api.options.mockResolvedValue({ data: options });
    api.upload.mockResolvedValue({ data: document });
    api.history.mockResolvedValue({ data: [] });
  });

  it("shows context separately from visibility and keeps customer authority wording bounded", async () => {
    render(<ShipmentDocuments shipmentPublicId="shipment-1" />);
    expect(await screen.findByText(/مربوط به: کالای مشتری/)).toBeInTheDocument();
    expect(screen.getByText(/چه کسانی می‌توانند ببینند؟ مشتری صاحب کالا، پس از احراز مجوز هویتی/)).toBeInTheDocument();
  });

  it("reports each file outcome and leaves only the failed file retryable", async () => {
    api.upload.mockImplementationOnce(async () => ({ data: document }))
      .mockImplementationOnce(async () => { throw new Error("فرمت نامعتبر"); });
    render(<ShipmentDocuments shipmentPublicId="shipment-1" />);
    await screen.findByLabelText("Document upload context");
    fireEvent.change(screen.getByLabelText("نوع یا دسته تجاری سند"), { target: { value: "بارنامه" } });
    const a = new File(["%PDF-1.4"], "a.pdf", { type: "application/pdf" });
    const b = new File(["bad"], "b.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByLabelText("انتخاب فایل سند"), { target: { files: [a, b] } });
    fireEvent.click(screen.getByRole("button", { name: "بارگذاری 2 فایل" }));
    expect(await screen.findByText("a.pdf: ثبت شد")).toBeInTheDocument();
    expect(screen.getByText(/b.pdf: ناموفق/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "بارگذاری سند" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "بارگذاری سند" }));
    await waitFor(() => expect(api.upload).toHaveBeenCalledTimes(3));
    const retryForm = api.upload.mock.calls[2][1] as FormData;
    expect((retryForm.get("file") as File).name).toBe("b.pdf");
    expect(api.upload.mock.calls[2][2]).toBe(api.upload.mock.calls[1][2]);
  });
});
