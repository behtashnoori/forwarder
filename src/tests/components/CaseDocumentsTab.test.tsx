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

const multiPayload = {...payload, requirements: [{...payload.requirements[0], max_active_file_count: 3}]};

describe("CaseDocumentsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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

  it("adds selected files independently and shows the outcome of every file", async () => {
    vi.mocked(api.fetchCaseDocuments).mockResolvedValue(multiPayload as never);
    vi.mocked(api.uploadCaseDocument).mockResolvedValueOnce({} as never).mockRejectedValueOnce(new Error("اندازه فایل مجاز نیست"));
    render(<CaseDocumentsTab caseId="00000000-0000-4000-8000-000000000010"/>);
    const input = await screen.findByLabelText("افزودن فایل به فاکتور");
    const good = new File(["one"], "صفحه-۱.pdf", {type:"application/pdf"});
    const bad = new File(["two"], "صفحه-۲.pdf", {type:"application/pdf"});
    fireEvent.change(input, {target:{files:[good,bad]}});
    await waitFor(() => expect(api.uploadCaseDocument).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("صفحه-۱.pdf: ثبت شد")).toBeInTheDocument();
    expect(screen.getByText(/صفحه-۲.pdf: ثبت نشد/)).toBeInTheDocument();
    expect(api.uploadCaseDocument).toHaveBeenNthCalledWith(1, "00000000-0000-4000-8000-000000000010", 5, expect.any(FormData), false);
    expect(api.uploadCaseDocument).toHaveBeenNthCalledWith(2, "00000000-0000-4000-8000-000000000010", 5, expect.any(FormData), false);
  });

  it("keeps separately selected same-name files as separate visible outcomes", async () => {
    vi.mocked(api.fetchCaseDocuments).mockResolvedValue(multiPayload as never);
    vi.mocked(api.uploadCaseDocument).mockResolvedValueOnce({} as never).mockRejectedValueOnce(new Error("خطا"));
    render(<CaseDocumentsTab caseId="00000000-0000-4000-8000-000000000010"/>);
    const input = await screen.findByLabelText("افزودن فایل به فاکتور");
    fireEvent.change(input, {target:{files:[new File(["one"], "مدرک.pdf"), new File(["two"], "مدرک.pdf")]}});
    await waitFor(() => expect(api.uploadCaseDocument).toHaveBeenCalledTimes(2));
    expect(screen.getAllByText(/مدرک\.pdf:/)).toHaveLength(2);
  });
});
