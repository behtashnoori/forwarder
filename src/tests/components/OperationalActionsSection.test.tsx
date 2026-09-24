import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import OperationalActionsSection from "@/components/OperationalActionsSection";

const api = vi.hoisted(() => ({
  context: vi.fn(), list: vi.fn(), exceptions: vi.fn(), create: vi.fn(), followUp: vi.fn(), resolve: vi.fn(), history: vi.fn(),
}));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getOperationalContext: api.context,
    listOperationalActions: api.list,
    listExecutionConditions: api.exceptions,
    createOperationalAction: api.create,
    recordOperationalActionFollowUp: api.followUp,
    resolveOperationalAction: api.resolve,
    getOperationalActionHistory: api.history,
  };
});

const shipment = "11111111-1111-4111-8111-111111111111";
const action = {
  public_id: "22222222-2222-4222-8222-222222222222",
  context: { type: "EXCEPTION" as const, exception_public_id: "exception-1" },
  what: "پیگیری پاسخ طرف عملیاتی",
  expected_result: "دریافت پاسخ ثبت‌شده",
  responsible: { user_id: 10, display_name: "کارشناس مسئول", basis: "SHIPMENT_TRANSPORT_EXPERT" as const },
  due_at: "2026-09-25T10:00:00Z",
  status: "open" as const,
  latest_follow_up: null,
  created_at: "2026-09-24T10:00:00Z",
  updated_at: "2026-09-24T10:00:00Z",
  version: 2,
};

describe("operational actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.context.mockResolvedValue({ data: { permissions: ["work_item.read", "work_item.manage"] } });
    api.list.mockResolvedValue({ data: [action] });
    api.exceptions.mockResolvedValue({ data: [] });
    api.followUp.mockResolvedValue({ data: { ...action, version: 3 } });
    api.resolve.mockResolvedValue({ data: { ...action, status: "resolved" } });
    api.history.mockResolvedValue({ data: [] });
  });

  it("shows the fixed internal owner and records a versioned follow-up", async () => {
    const user = userEvent.setup();
    render(<OperationalActionsSection shipmentPublicId={shipment} />);
    expect(await screen.findByText("مسئول داخلی:", { exact: false })).toHaveTextContent("کارشناس مسئول");
    const note = screen.getByLabelText(`یادداشت پیگیری ${action.what}`);
    await user.type(note, "تماس انجام شد");
    await user.click(screen.getByRole("button", { name: "ثبت پیگیری" }));
    await waitFor(() => expect(api.followUp).toHaveBeenCalledWith(shipment, action, "تماس انجام شد"));
    expect(screen.getByText(/مالک داخلی آن همان کارشناس مسئول ثابت/)).toBeInTheDocument();
  });
});
