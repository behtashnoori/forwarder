import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CaseDocumentsTab from "../../components/CaseDocumentsTab";
import * as api from "../../lib/api";

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return {...actual, fetchCaseDocuments: vi.fn(), uploadCaseDocument: vi.fn(), deleteCaseDocument: vi.fn(), downloadCaseDocument: vi.fn()};
});

const payload = {
  summary: {total_requirements:1,required_requirements:1,uploaded_requirements:0,missing_required_requirements:1,miscellaneous_file_count:0},
  requirements: [{id:5,code:"invoice",title:"فاکتور",description:"راهنما",is_required:true,allowed_formats:["pdf"],max_file_size_bytes:1048576,max_active_file_count:1,complete:false,active_files:[],versions:[]}],
  miscellaneous: [],
};

describe("CaseDocumentsTab", () => {
  beforeEach(() => {
    vi.mocked(api.fetchCaseDocuments).mockResolvedValue(payload as never);
    vi.mocked(api.uploadCaseDocument).mockResolvedValue({} as never);
  });

  it("renders requirements, warning, direct upload and no bulk download", async () => {
    render(<CaseDocumentsTab caseId="00000000-0000-4000-8000-000000000010"/>);
    expect(await screen.findByText("فاکتور")).toBeInTheDocument();
    expect(screen.getByText(/این هشدار مانع ادامه/)).toBeInTheDocument();
    expect(screen.queryByText(/دانلود همه|دریافت همه|ZIP/i)).not.toBeInTheDocument();
    expect(screen.getAllByText("سایر مستندات").length).toBeGreaterThan(0);
  });

  it("requires a miscellaneous title before file selection", async () => {
    render(<CaseDocumentsTab caseId="00000000-0000-4000-8000-000000000010"/>);
    await screen.findAllByText("سایر مستندات");
    const miscFile = document.querySelector('input[type="file"]:disabled');
    expect(miscFile).toBeTruthy();
    fireEvent.change(screen.getByPlaceholderText("عنوان الزامی"), {target:{value:"سند تکمیلی"}});
    await waitFor(() => expect(document.querySelector('input[type="file"]:disabled')).toBeNull());
  });

  it("characterizes the current single-file replacement UI even when the requirement cap exceeds one", async () => {
    const activeFile = {
      id: 9,
      original_filename: "existing.pdf",
      version_number: 1,
      file_size_bytes: 100,
      status: "active",
    };
    vi.mocked(api.fetchCaseDocuments).mockResolvedValue({
      ...payload,
      requirements: [{
        ...payload.requirements[0],
        max_active_file_count: 3,
        complete: true,
        active_files: [activeFile],
        versions: [activeFile],
      }],
    } as never);

    const { container } = render(<CaseDocumentsTab caseId="00000000-0000-4000-8000-000000000010"/>);
    await screen.findByText(/existing\.pdf/);
    expect([...container.querySelectorAll("p")].some((node) => node.textContent?.includes("حداکثر 1 MB · 3 فایل"))).toBe(true);
    const requirementInput = container.querySelectorAll<HTMLInputElement>('input[type="file"]')[0];
    expect(requirementInput.multiple).toBe(false);

    const first = new File(["first"], "first.pdf", { type: "application/pdf" });
    const ignoredSecond = new File(["second"], "second.pdf", { type: "application/pdf" });
    fireEvent.change(requirementInput, { target: { files: [first, ignoredSecond] } });

    await waitFor(() => expect(api.uploadCaseDocument).toHaveBeenCalledTimes(1));
    const [caseId, requirementId, formData, replace] = vi.mocked(api.uploadCaseDocument).mock.calls[0];
    expect([caseId, requirementId, replace]).toEqual(["00000000-0000-4000-8000-000000000010", 5, true]);
    expect((formData as FormData).get("file")).toBe(first);
    expect([...((formData as FormData).keys())]).toEqual(["file"]);
  });
});
