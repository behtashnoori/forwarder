import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import UserManagement from "@/pages/UserManagement";

const jsonResponse = (status: number, payload: unknown) =>
  new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });

describe("UserManagement API boundary", () => {
  beforeEach(() => {
    localStorage.setItem("expert_token", "organization-admin-token");
    vi.restoreAllMocks();
  });

  it("renders users when nullable array fields are absent", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(jsonResponse(200, { users: [{ id: 1, username: "admin", full_name: "Samand Admin", role: "admin", is_active: true }] }))
      .mockResolvedValueOnce(jsonResponse(200, { transport_methods: null }))
      .mockResolvedValueOnce(jsonResponse(200, { assignment_rules: undefined }))
      .mockResolvedValueOnce(jsonResponse(200, { total_assignments: 0, expert_workloads: null })));

    render(<UserManagement />);

    expect(await screen.findByText("Samand Admin")).toBeInTheDocument();
    expect(screen.getByText(/تخصص‌ها: 0/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("explains current workload without implying default least-workload assignment", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(jsonResponse(200, { users: [{ id: 2, username: "expert", full_name: "Expert A", role: "expert", is_active: true, workload: 3 }] }))
      .mockResolvedValueOnce(jsonResponse(200, { transport_methods: [] }))
      .mockResolvedValueOnce(jsonResponse(200, { assignment_rules: [] }))
      .mockResolvedValueOnce(jsonResponse(200, { expert_workloads: [{ expert_id: 2, expert_name: "Expert A", workload: 3 }] })));

    render(<UserManagement />);
    expect(await screen.findByText("بار کاری فعلی: 3 پرونده فعال")).toBeInTheDocument();
    expect(await screen.findByText(/تخصیص پیش‌فرض بر اساس نوبت‌گردشی/)).toBeInTheDocument();
  });

  it("renders the backend error and status instead of crashing", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(jsonResponse(500, { error: "tenant user query failed" }))
      .mockResolvedValueOnce(jsonResponse(200, { transport_methods: [] }))
      .mockResolvedValueOnce(jsonResponse(200, { assignment_rules: [] }))
      .mockResolvedValueOnce(jsonResponse(200, { expert_workloads: [] })));

    render(<UserManagement />);

    expect(await screen.findByRole("alert")).toHaveTextContent("tenant user query failed");
    expect(screen.getByRole("alert")).toHaveTextContent("500");
  });
});
