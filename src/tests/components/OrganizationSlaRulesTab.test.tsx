import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import OrganizationSlaRulesTab from "@/components/OrganizationSlaRulesTab";

const api = vi.hoisted(() => ({ list: vi.fn(), create: vi.fn(), update: vi.fn(), history: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    listOrganizationSlaRules: api.list,
    createOrganizationSlaRule: api.create,
    updateOrganizationSlaRule: api.update,
    getOrganizationSlaRuleHistory: api.history,
  };
});

const process = {
  process_type: "EXCEPTION_RESPONSE" as const,
  label_fa: "رسیدگی به مشکل عملیاتی",
  target_code: "EXCEPTION_RESPONSE",
  domain_context_fa: "مشکل ثبت‌شده برای محموله عملیاتی",
  start_label_fa: "زمان ثبت وقوع مشکل",
  end_label_fa: "زمان حل مشکل",
  start_reference: "OperationalException.occurred_at",
  completion_reference: "OperationalException.resolved_at",
  responsibility: "SHIPMENT_TRANSPORT_EXPERT",
  supported_scope: "OPERATIONAL_EXCEPTION",
  implementation_availability: "AVAILABLE" as const,
};

describe("organization SLA rules", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.list.mockResolvedValue({ data: { catalog: [process], rules: [], unconfigured_processes: [{ process_type: process.process_type, label_fa: process.label_fa, status_label: "SLA تعریف نشده" }] } });
    api.create.mockResolvedValue({ data: {} });
    api.history.mockResolvedValue({ data: [] });
  });

  it("creates only an explicit organization value and explains the prospective clock", async () => {
    const user = userEvent.setup();
    render(<OrganizationSlaRulesTab />);
    expect(await screen.findByText("هنوز برای این فرآیند تنظیمی ثبت نشده است")).toBeInTheDocument();
    expect(screen.getByText("زمان ثبت وقوع مشکل")).toBeInTheDocument();
    expect(screen.getByText("زمان حل مشکل")).toBeInTheDocument();
    await user.type(screen.getByLabelText(`مدت ${process.label_fa}`), "60");
    await user.type(screen.getByLabelText(`هشدار ${process.label_fa}`), "15");
    await user.click(screen.getByRole("button", { name: "ثبت تنظیم" }));
    await waitFor(() => expect(api.create).toHaveBeenCalledWith({
      process_type: "EXCEPTION_RESPONSE",
      organization_alias: null,
      duration_minutes: 60,
      warning_minutes: 15,
      is_active: true,
    }));
  });
});
