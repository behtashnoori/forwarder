import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import OperationalConditionsSection from "@/components/OperationalConditionsSection";

const api = vi.hoisted(() => ({
  conditions: vi.fn(), reasons: vi.fn(), context: vi.fn(), create: vi.fn(), resolve: vi.fn(),
}));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, listExecutionConditions: api.conditions, listExecutionReasons: api.reasons,
    getOperationalContext: api.context, createExecutionCondition: api.create, resolveExecutionCondition: api.resolve };
});

const shipment = "11111111-1111-4111-8111-111111111111";
const reason = { public_id: "reason-1", fa_name: "تأخیر گمرکی", is_active: true };
describe("shipment operational conditions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.conditions.mockResolvedValue({ data: [] });
    api.reasons.mockResolvedValue({ data: [reason] });
    api.context.mockResolvedValue({ data: { permissions: ["operational_execution.manage"] } });
    api.create.mockResolvedValue({ data: [] });
    api.resolve.mockResolvedValue({ data: {} });
  });
  it("records an explicit delay with a governed reason and reloads authoritative cases", async () => {
    const user = userEvent.setup();
    render(<OperationalConditionsSection shipmentPublicId={shipment} />);
    await screen.findByRole("button", { name: "ثبت تأخیر عملیاتی" });
    await user.selectOptions(screen.getByLabelText("دلیل مصوب تأخیر"), "reason-1");
    await user.type(screen.getAllByLabelText("زمان وقوع")[0], "2026-09-14T10:00");
    await user.click(screen.getByRole("button", { name: "ثبت تأخیر عملیاتی" }));
    await waitFor(() => expect(api.create).toHaveBeenCalledWith(shipment, "delay", expect.objectContaining({ reason_public_id: "reason-1", started_at: expect.any(String) })));
    await waitFor(() => expect(api.conditions).toHaveBeenCalledTimes(4));
  });
  it("keeps resolved history visible and hides commands without the backend capability", async () => {
    api.context.mockResolvedValue({ data: { permissions: [] } });
    api.conditions.mockImplementation(async (_shipment: string, kind: string) => ({ data: kind === "delay" ? [{ public_id: "delay-1", reason, started_at: "2026-09-14T10:00:00Z", resolved_at: "2026-09-14T11:00:00Z", active: false }] : [] }));
    render(<OperationalConditionsSection shipmentPublicId={shipment} />);
    expect(await screen.findByText("رفع‌شده", { exact: false })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "ثبت تأخیر عملیاتی" })).not.toBeInTheDocument();
  });
  it("records and presents the bounded impact and evidence of an exception", async () => {
    const user = userEvent.setup();
    render(<OperationalConditionsSection shipmentPublicId={shipment} />);
    await screen.findByRole("button", { name: "ثبت استثنا عملیاتی" });
    await user.selectOptions(screen.getByLabelText("دلیل مصوب استثنا"), "reason-1");
    await user.type(screen.getAllByLabelText("زمان وقوع")[1], "2026-09-14T10:00");
    await user.type(screen.getByLabelText("اثر بر عملیات"), "نیاز به هماهنگی مجدد");
    await user.type(screen.getByLabelText("شواهد موجود"), "گزارش ثبت‌شده");
    await user.click(screen.getByRole("button", { name: "ثبت استثنا عملیاتی" }));
    await waitFor(() => expect(api.create).toHaveBeenCalledWith(
      shipment,
      "exception",
      expect.objectContaining({
        impact_summary: "نیاز به هماهنگی مجدد",
        evidence_summary: "گزارش ثبت‌شده",
      }),
    ));
  });
});
