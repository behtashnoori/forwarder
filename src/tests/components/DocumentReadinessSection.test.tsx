import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DocumentReadinessSection from "@/components/DocumentReadinessSection";

const api = vi.hoisted(() => ({
  preview: vi.fn(), requirements: vi.fn(), next: vi.fn(), eligible: vi.fn(), associate: vi.fn(), remove: vi.fn(),
}));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getDocumentMaterializationPreview: api.preview,
    listDocumentReadinessRequirements: api.requirements,
    getNextTransitionReadiness: api.next,
    listEligibleDocumentArtifacts: api.eligible,
    associateDocumentArtifact: api.associate,
    removeDocumentArtifactAssociation: api.remove,
  };
});

const requirement = {
  public_id: "req-opaque", title: "بارنامه", document_code: "BOL",
  document_definition_public_id: "definition-opaque", requirement_level: "REQUIRED" as const,
  applicability_state: "APPLICABLE" as const, applicability_reason: null,
  required_assessment_level: "VERIFIED" as const, target_milestone_type: "CUSTOMS", target_status: "READY",
  version: 1, readiness_status: "MISSING" as const, artifact: null,
};

describe("shipment document readiness", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.preview.mockResolvedValue({ data: { initialized: true, requirements: [], findings: [], confirmation_allowed: false } });
    api.requirements.mockResolvedValue({ data: [requirement] });
    api.eligible.mockResolvedValue({ data: [{ artifact_public_id: "file-opaque", filename: "bol.pdf", version: 2 }] });
    api.next.mockResolvedValue({ data: { allowed: false, target_action: "READY", blocking_requirements: [{ code: "DOC_ARTIFACT_MISSING", requirement_public_id: "req-opaque", title: "بارنامه" }], warnings: [] } });
    api.associate.mockResolvedValue({ data: {} });
    api.remove.mockResolvedValue({ data: {} });
  });

  it("renders Persian concepts, authoritative status counts, and contextual ownership help", async () => {
    render(<DocumentReadinessSection shipmentPublicId="shipment-opaque" shipmentVersion={3} />);
    expect((await screen.findAllByText("بارنامه")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("کسری")).toHaveLength(2);
    expect(screen.getByText(/مالک فایل همچنان پرونده درخواست است/)).toBeInTheDocument();
    expect(screen.getByText(/برای همین محموله ثبت شده است/)).toBeInTheDocument();
    expect(screen.getByText(/تغییرات بعدی در سیاست فعلی اسناد/)).toBeInTheDocument();
    expect(screen.getByText(/DOC_ARTIFACT_MISSING/)).toBeInTheDocument();
  });

  it("selects an eligible exact file version instead of requiring an opaque ID", async () => {
    render(<DocumentReadinessSection shipmentPublicId="shipment-opaque" shipmentVersion={3} />);
    const selector = await screen.findByLabelText("فایل موجود در پرونده");
    fireEvent.change(selector, { target: { value: "file-opaque" } });
    fireEvent.click(screen.getByRole("button", { name: "ارتباط با این محموله" }));
    await waitFor(() => expect(api.associate).toHaveBeenCalledWith("shipment-opaque", expect.objectContaining({ public_id: "req-opaque" }), "file-opaque"));
  });

  it("shows the empty requirement state", async () => {
    api.requirements.mockResolvedValue({ data: [] });
    render(<DocumentReadinessSection shipmentPublicId="shipment-opaque" shipmentVersion={3} />);
    expect(await screen.findByText("برای این محموله الزام سندی اعمال نشده است.")).toBeInTheDocument();
    expect(screen.queryByText(/برای همین محموله ثبت شده است/)).toBeNull();
  });

  it("retains required and optional evidence in the closed read-only workspace", async () => {
    api.requirements.mockResolvedValue({ data: [
      { ...requirement, readiness_status: "SATISFIED", artifact: { filename: "bol.pdf", version: 2, assessment: "VERIFIED", associated_at: "2026-10-01T09:00:00Z" } },
      { ...requirement, public_id: "optional", title: "تصویر اطلاع‌رسانی", requirement_level: "OPTIONAL" },
    ] });
    render(<DocumentReadinessSection shipmentPublicId="shipment-opaque" shipmentVersion={3} readOnly />);
    expect(await screen.findByText("تصویر اطلاع‌رسانی")).toBeInTheDocument();
    expect(screen.getByText(/الزام سند: اختیاری/)).toBeInTheDocument();
    expect(screen.getByText(/bol.pdf.*نسخه 2/)).toBeInTheDocument();
    expect(screen.queryByLabelText("فایل موجود در پرونده")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.queryByText("وضعیت اسناد برای اقدام بعدی")).toBeNull();
    expect(api.associate).not.toHaveBeenCalled();
    expect(api.remove).not.toHaveBeenCalled();
  });
});
