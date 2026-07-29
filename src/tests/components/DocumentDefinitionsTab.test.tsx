import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DocumentDefinitionsTab from "../../components/DocumentDefinitionsTab";
import * as api from "../../lib/api";

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return {...actual, fetchDocumentDefinitions: vi.fn(), createDocumentDefinition: vi.fn(), updateDocumentDefinition: vi.fn(), setDocumentDefinitionActive: vi.fn()};
});

describe("DocumentDefinitionsTab", () => {
  beforeEach(() => vi.mocked(api.fetchDocumentDefinitions).mockResolvedValue({items:[]} as never));
  it("uses a controlled safe-format catalog and admin policy fields", async () => {
    render(<DocumentDefinitionsTab/>);
    expect(await screen.findByText("تصویر JPG/JPEG")).toBeInTheDocument();
    expect(screen.getByText("فایل PDF")).toBeInTheDocument();
    expect(screen.getByText("فایل Word")).toBeInTheDocument();
    expect(screen.getByLabelText("کد داخلی")).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/MIME/i)).not.toBeInTheDocument();
  });
});
