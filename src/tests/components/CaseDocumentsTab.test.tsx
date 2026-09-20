import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CaseDocumentsTab from "../../components/CaseDocumentsTab";
import { ApiError } from "../../lib/api";
import * as api from "../../lib/api";

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, fetchCaseDocuments: vi.fn(), uploadCaseDocument: vi.fn(), deleteCaseDocument: vi.fn(), downloadCaseDocument: vi.fn() };
});

const activeFile = {
  public_id: "file-current-a",
  logical_file_public_id: "file-root-a",
  original_filename: "existing.pdf",
  canonical_extension: "pdf",
  detected_mime_type: "application/pdf",
  file_size_bytes: 100,
  version_number: 1,
  lineage_version: 1,
  status: "active" as const,
  current: true,
  uploaded_at: "2026-09-20T10:00:00",
  uploader_label: "Expert",
  history: [],
  is_miscellaneous: false,
  sha256_hash: "hash",
};

const payload = {
  can_manage_documents: true,
  summary: { total_requirements: 1, required_requirements: 1, uploaded_requirements: 0, missing_required_requirements: 1, miscellaneous_file_count: 0 },
  requirements: [{
    id: 5,
    definition_public_id: "definition-public-id",
    source_definition_revision: 3,
    code: "invoice",
    title: "فاکتور",
    description: "راهنما",
    is_required: true,
    allowed_formats: ["pdf"],
    max_file_size_bytes: 1048576,
    max_active_file_count: 4,
    has_current_file: false,
    complete: false,
    current_files: [],
    inactive_lineages: [],
    active_files: [],
    versions: [],
  }],
  miscellaneous: [],
};

describe("CaseDocumentsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchCaseDocuments).mockResolvedValue(payload as never);
    vi.mocked(api.uploadCaseDocument).mockResolvedValue(activeFile as never);
  });

  it("renders governed language, capacity, and a multi-select add control", async () => {
    render(<CaseDocumentsTab caseId="request-public-id" />);
    expect(await screen.findByText("فاکتور")).toBeInTheDocument();
    expect(screen.getByText(/به معنی رد یا عدم آمادگی عملیاتی نیست/)).toBeInTheDocument();
    const input = screen.getByLabelText("افزودن فایل‌ها برای فاکتور") as HTMLInputElement;
    expect(input.multiple).toBe(true);
    expect(screen.queryByText(/دانلود همه|دریافت همه|ZIP/i)).not.toBeInTheDocument();
  });

  it("uploads A/B/C as independent append commands in selection order", async () => {
    render(<CaseDocumentsTab caseId="request-public-id" />);
    const input = await screen.findByLabelText("افزودن فایل‌ها برای فاکتور");
    const files = ["A.pdf", "B.pdf", "C.pdf"].map((name) => new File([name], name, { type: "application/pdf" }));
    fireEvent.change(input, { target: { files } });

    await waitFor(() => expect(api.uploadCaseDocument).toHaveBeenCalledTimes(3));
    expect(vi.mocked(api.uploadCaseDocument).mock.calls.map((call) => (call[2] as FormData).get("file"))).toEqual(files);
    expect(vi.mocked(api.uploadCaseDocument).mock.calls.every((call) => call[3] === undefined)).toBe(true);
    expect(await screen.findAllByText("موفق")).toHaveLength(3);
  });

  it("targets exactly the selected current file for replacement", async () => {
    vi.mocked(api.fetchCaseDocuments).mockResolvedValue({
      ...payload,
      summary: { ...payload.summary, uploaded_requirements: 1, missing_required_requirements: 0 },
      requirements: [{ ...payload.requirements[0], has_current_file: true, complete: true, current_files: [activeFile], active_files: [activeFile], versions: [activeFile] }],
    } as never);
    render(<CaseDocumentsTab caseId="request-public-id" />);
    const input = await screen.findByLabelText("جایگزینی existing.pdf");
    const replacement = new File(["A2"], "A2.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [replacement] } });
    await waitFor(() => expect(api.uploadCaseDocument).toHaveBeenCalledTimes(1));
    expect(vi.mocked(api.uploadCaseDocument).mock.calls[0][3]).toBe("file-current-a");
  });

  it("retries only a known failed item and never resubmits successful siblings", async () => {
    vi.mocked(api.uploadCaseDocument)
      .mockResolvedValueOnce(activeFile as never)
      .mockRejectedValueOnce(new ApiError(503, "DOCUMENT_STORAGE_UNAVAILABLE", "storage unavailable"))
      .mockResolvedValueOnce(activeFile as never)
      .mockResolvedValueOnce(activeFile as never);
    render(<CaseDocumentsTab caseId="request-public-id" />);
    const files = ["E.pdf", "F.pdf", "G.pdf"].map((name) => new File([name], name, { type: "application/pdf" }));
    fireEvent.change(await screen.findByLabelText("افزودن فایل‌ها برای فاکتور"), { target: { files } });
    const retry = await screen.findByRole("button", { name: /تلاش دوباره فقط همین فایل/ });
    expect(api.uploadCaseDocument).toHaveBeenCalledTimes(3);
    fireEvent.click(retry);
    await waitFor(() => expect(api.uploadCaseDocument).toHaveBeenCalledTimes(4));
    expect((vi.mocked(api.uploadCaseDocument).mock.calls[3][2] as FormData).get("file")).toBe(files[1]);
  });

  it("marks a lost response unknown and offers inspect without Retry", async () => {
    vi.mocked(api.uploadCaseDocument).mockRejectedValueOnce(new TypeError("Failed to fetch"));
    render(<CaseDocumentsTab caseId="request-public-id" />);
    const file = new File(["U"], "unknown.pdf", { type: "application/pdf" });
    fireEvent.change(await screen.findByLabelText("افزودن فایل‌ها برای فاکتور"), { target: { files: [file] } });
    expect(await screen.findByText("نتیجه نامشخص")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /تازه‌سازی و بررسی/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /تلاش دوباره/ })).not.toBeInTheDocument();
    expect(api.uploadCaseDocument).toHaveBeenCalledTimes(1);
  });

  it("preserves Admin read UI while hiding every mutation control", async () => {
    vi.mocked(api.fetchCaseDocuments).mockResolvedValue({
      ...payload,
      can_manage_documents: false,
      requirements: [{ ...payload.requirements[0], has_current_file: true, current_files: [activeFile], active_files: [activeFile], versions: [activeFile] }],
    } as never);
    render(<CaseDocumentsTab caseId="request-public-id" />);
    expect(await screen.findByText("existing.pdf")).toBeInTheDocument();
    expect(screen.queryByLabelText(/افزودن فایل‌ها|جایگزینی/)).not.toBeInTheDocument();
    expect(screen.queryByText("غیرفعال‌سازی")).not.toBeInTheDocument();
  });
});
