import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ExpertConsole from "@/pages/ExpertConsole";
import * as api from "@/lib/api";

const toast = vi.hoisted(() => vi.fn());
const i18n = vi.hoisted(() => ({
  locale: "en-US",
  statusLabel: (value: string) => value,
  t: (key: string) => key,
  tf: (key: string, values: { count: number }) => `${key}:${values.count}`,
  transportLabel: (value: string) => value,
}));
vi.mock("@/hooks/use-toast", () => ({ useToast: () => ({ toast }) }));
vi.mock("@/components/PageNav", () => ({ default: () => null }));
vi.mock("@/components/OperationsNav", () => ({ default: () => null }));
vi.mock("@/components/ui/dropdown-menu", () => ({
  DropdownMenu: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children }: { children: ReactNode }) => <>{children}</>,
  DropdownMenuContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DropdownMenuItem: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));
vi.mock("@/components/ui/select", () => ({
  Select: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SelectTrigger: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SelectValue: () => null,
  SelectContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SelectItem: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));
vi.mock("@/components/ui/tabs", () => ({
  Tabs: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  TabsList: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  TabsTrigger: ({ children }: { children: ReactNode }) => <button>{children}</button>,
  TabsContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));
vi.mock("@/i18n", () => ({ useI18n: () => i18n }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchExpertRequests: vi.fn(),
    fetchKPIs: vi.fn(),
    fetchExperts: vi.fn(),
    assignRequestToMe: vi.fn(),
    changeRequestStatus: vi.fn(),
  };
});

const requestRow: api.ExpertRequest = {
  id: 1,
  public_id: "11111111-1111-4111-8111-111111111111",
  tracking_number: "SR-B4-UI",
  status: "new",
  priority: "normal",
  created_at: "2026-09-20T00:00:00Z",
  sla_status: "on_time",
  customer: { name: "Needle Customer", phone: "09120000000" },
  route: { shipping_type: "domestic", origin: {}, destination: {} },
  transport_method: "road",
  cargo: {},
  has_unread: false,
};

describe("Expert Console canonical count/list refresh", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.localStorage.setItem(
      "expert_user",
      JSON.stringify({ id: 9, full_name: "Expert Nine", role: "expert" }),
    );
    vi.mocked(api.fetchExpertRequests).mockResolvedValue({
      requests: [requestRow],
      pagination: {
        page: 1,
        per_page: 50,
        total: 1,
        pages: 1,
        has_next: false,
        has_prev: false,
      },
    });
    vi.mocked(api.fetchKPIs).mockResolvedValue({
      counts: {
        total_visible: 1,
        new: 1,
        in_progress: 0,
        waiting_for_customer: 0,
        closed_today: 0,
      },
      sla: { overdue: 0, due_soon: 0 },
    });
    vi.mocked(api.fetchExperts).mockResolvedValue({ experts: [] });
  });

  it("refreshes list and canonical counts together and applies the same search", async () => {
    render(
      <MemoryRouter>
        <ExpertConsole />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(api.fetchExpertRequests).toHaveBeenCalledTimes(1);
      expect(api.fetchKPIs).toHaveBeenCalledWith(undefined, undefined);
    });

    fireEvent.click(screen.getByRole("button", { name: "common.refresh" }));
    await waitFor(() => {
      expect(api.fetchExpertRequests).toHaveBeenCalledTimes(2);
      expect(api.fetchKPIs).toHaveBeenCalledTimes(2);
    });

    fireEvent.change(screen.getByPlaceholderText("expert.searchPlaceholder"), {
      target: { value: "Needle" },
    });
    await waitFor(() => {
      expect(api.fetchExpertRequests).toHaveBeenLastCalledWith(
        expect.objectContaining({ status: "new", search: "Needle" }),
      );
      expect(api.fetchKPIs).toHaveBeenLastCalledWith(undefined, "Needle");
    });
  });
});
