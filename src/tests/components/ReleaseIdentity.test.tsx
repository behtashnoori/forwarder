import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ReleaseIdentity, { compareReleaseIdentity } from "@/components/ReleaseIdentity";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({ getReleaseIdentity: vi.fn() }));
vi.mock("@/i18n", () => ({ useI18n: () => ({ t: (key: string) => ({
  "operations.systemInformation":"System information",
  "operations.frontendVersion":"Frontend Version",
  "operations.backendVersion":"Backend Version",
  "operations.releaseTag":"Release Tag",
  "operations.shortCommit":"Short Commit",
  "operations.databaseRevision":"Database Revision",
  "operations.matchStatus":"Match status",
  "operations.unavailable":"Unavailable",
} as Record<string,string>)[key] || key }) }));

describe("ReleaseIdentity", () => {
  beforeEach(() => vi.resetAllMocks());
  it("classifies match, mismatch, missing identity and backend failure", () => {
    expect(compareReleaseIdentity("1.9.3", {projection:"normal",data:{application_version:"1.9.3"}})).toBe("MATCH");
    expect(compareReleaseIdentity("1.9.3", {projection:"support",data:{application_version:"1.9.2",backend_version:"1.9.2"}})).toBe("MISMATCH");
    expect(compareReleaseIdentity("1.9.3")).toBe("IDENTITY_UNAVAILABLE");
    expect(compareReleaseIdentity("1.9.3", undefined, true)).toBe("BACKEND_UNAVAILABLE");
  });
  it("always renders the compile-time label and exposes sanitized support details", async () => {
    vi.mocked(api.getReleaseIdentity).mockResolvedValue({projection:"support",data:{application_version:"1.9.5",backend_version:"1.9.5",release_tag:"v1.9.5",short_commit:"1234567890ab",database_revision:"head"}});
    render(<ReleaseIdentity details />);
    expect(screen.getByText("Forwarder 1.9.5")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("MATCH")).toBeInTheDocument());
    expect(screen.getByText("1234567890ab")).toBeInTheDocument();
  });
  it("does not block the visible version when backend identity is unavailable", async () => {
    vi.mocked(api.getReleaseIdentity).mockRejectedValue(new Error("offline"));
    render(<ReleaseIdentity details />);
    expect(screen.getByText("Forwarder 1.9.5")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("BACKEND_UNAVAILABLE")).toBeInTheDocument());
  });
});
