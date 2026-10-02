import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ShipmentDocuments from "@/components/ShipmentDocuments";

const api = vi.hoisted(() => ({
  list: vi.fn(),
  options: vi.fn(),
  upload: vi.fn(),
  change: vi.fn(),
  history: vi.fn(),
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
  public_id: "file-1",
  business_document_type: "بارنامه",
  filename: "bol.pdf",
  version: 1,
  recorded_at: "2026-09-25T12:00:00Z",
  actor: "کارشناس",
  owner: "SHIPMENT",
  lifecycle_state: "active",
  description: null,
  references: [],
  requirements: [],
  context: {
    public_id: "context-1",
    type: "CARGO",
    target_public_id: "cargo-1",
    visibility: "CARGO_OWNER",
    version: 1,
    audiences: [],
  },
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
    api.list.mockResolvedValue({
      data: [document],
      can_manage_documents: true,
    });
    api.options.mockResolvedValue({ data: options });
    api.upload.mockResolvedValue({ data: document });
    api.history.mockResolvedValue({ data: [] });
  });

  it("shows context separately from visibility and keeps customer authority wording bounded", async () => {
    render(<ShipmentDocuments shipmentPublicId="shipment-1" />);
    expect(
      await screen.findByText(/مربوط به: کالای مشتری/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /چه کسانی می‌توانند ببینند؟ مشتری صاحب کالا، پس از احراز مجوز هویتی/,
      ),
    ).toBeInTheDocument();
  });

  it("reports each file outcome and leaves only the failed file retryable", async () => {
    api.upload
      .mockImplementationOnce(async () => ({ data: document }))
      .mockImplementationOnce(async () => {
        throw new Error("فرمت نامعتبر");
      });
    render(<ShipmentDocuments shipmentPublicId="shipment-1" />);
    await screen.findByLabelText("زمینه بارگذاری سند");
    fireEvent.change(screen.getByLabelText("نوع یا دسته تجاری سند"), {
      target: { value: "بارنامه" },
    });
    const a = new File(["%PDF-1.4"], "a.pdf", { type: "application/pdf" });
    const b = new File(["bad"], "b.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByLabelText("انتخاب فایل سند"), {
      target: { files: [a, b] },
    });
    fireEvent.click(screen.getByRole("button", { name: "بارگذاری ۲ فایل" }));
    expect(await screen.findByText("a.pdf: ثبت شد")).toBeInTheDocument();
    expect(screen.getByText(/b.pdf: ناموفق/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "بارگذاری سند" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "بارگذاری سند" }));
    await waitFor(() => expect(api.upload).toHaveBeenCalledTimes(3));
    const retryForm = api.upload.mock.calls[2][1] as FormData;
    expect((retryForm.get("file") as File).name).toBe("b.pdf");
    expect(api.upload.mock.calls[2][2]).toBe(api.upload.mock.calls[1][2]);
  });
  it("keeps closed files readable and suppresses upload, replacement, and context writes",async()=>{
    const {rerender}=render(<ShipmentDocuments shipmentPublicId="shipment-1" readOnly/>);
    await screen.findByText("bol.pdf");
    expect(screen.queryByLabelText("انتخاب فایل سند")).not.toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"جایگزینی این نسخه"})).not.toBeInTheDocument();
    expect(screen.queryByLabelText("زمینه بارگذاری سند")).not.toBeInTheDocument();
    expect(screen.getByText("تاریخچه زمینه و دسترسی")).toBeInTheDocument();
    rerender(<ShipmentDocuments shipmentPublicId="shipment-1" readOnly={false}/>);
    expect(await screen.findByLabelText("انتخاب فایل سند")).toBeInTheDocument();
    expect(api.upload).not.toHaveBeenCalled();
  });

  it("sends the selected catalog identity and preserves explicit historical repair intent", async () => {
    api.list.mockResolvedValue({data: [{...document, document_type_active: false}], can_manage_documents: true,
      document_types: [{public_id: "type-1", name_fa: "راهنامه CMR", is_active: true}, {public_id: "inactive", name_fa: "نوع غیرفعال", is_active: false}]});
    render(<ShipmentDocuments shipmentPublicId="shipment-1" historicalRepair />);
    await screen.findByLabelText("نوع سند");
    expect(screen.queryByRole("option", {name: "نوع غیرفعال"})).not.toBeInTheDocument();
    expect(screen.getByText("نوع سند غیرفعال؛ فایل محفوظ است")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("نوع سند"), {target: {value: "type-1"}});
    fireEvent.change(screen.getByLabelText("انتخاب فایل سند"), {target: {files: [new File(["%PDF-1.4"], "cmr.pdf", {type: "application/pdf"})]}});
    fireEvent.click(screen.getByRole("button", {name: "بارگذاری سند"}));
    await waitFor(() => expect(api.upload).toHaveBeenCalledTimes(1));
    expect(api.upload.mock.calls[0][1].get("document_definition_public_id")).toBe("type-1");
    expect(api.upload.mock.calls[0][1].get("historical_repair")).toBe("true");
  });

});
