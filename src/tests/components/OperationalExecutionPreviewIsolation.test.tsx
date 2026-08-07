import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import OperationalExecutionSection from "@/components/OperationalExecutionSection";

const api = vi.hoisted(() => ({
  preview: vi.fn(), milestones: vi.fn(), progress: vi.fn(), events: vi.fn(),
  conditions: vi.fn(), reasons: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getExecutionPreview: api.preview,
    listExecutionMilestones: api.milestones,
    getExecutionProgress: api.progress,
    listExecutionEvents: api.events,
    listExecutionConditions: api.conditions,
    listExecutionReasons: api.reasons,
  };
});

beforeEach(() => {
  vi.clearAllMocks();
  api.preview.mockResolvedValue({ data: { initialized: false, existing_count: 0, milestones: [{ definition_public_id: "22222222-2222-4222-8222-222222222222" }], findings: [], confirmation_allowed: true } });
  api.milestones.mockResolvedValue({ data: [] });
  api.progress.mockResolvedValue({ data: { initialized: false, total: 0, counts: {}, current_milestone: null, completion_percentage: 0, completion_rule: "rule", active_delay_count: 0, active_exception_count: 0 } });
  api.events.mockRejectedValue(new Error("secondary read failed"));
  api.conditions.mockResolvedValue({ data: [] });
  api.reasons.mockResolvedValue({ data: [] });
});

describe("operational execution initialization preview", () => {
  it("retains the successful preview when an auxiliary read fails", async () => {
    render(<OperationalExecutionSection shipmentPublicId="11111111-1111-4111-8111-111111111110" shipmentVersion={1} />);
    expect(await screen.findByText("1 expected milestones")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm initialization" })).toBeEnabled();
    expect(screen.getByRole("alert")).toHaveTextContent("secondary read failed");
  });
});

