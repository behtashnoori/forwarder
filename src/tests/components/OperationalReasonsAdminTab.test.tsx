import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import OperationalReasonsAdminTab from "@/components/OperationalReasonsAdminTab";

const api = vi.hoisted(() => ({
  listExecutionReasons: vi.fn(),
  createExecutionReason: vi.fn(),
  updateExecutionReason: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  ...api,
  ApiError: class ApiError extends Error {
    status = 500;
  },
}));

describe("OperationalReasonsAdminTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listExecutionReasons.mockResolvedValue({ data: [] });
    api.createExecutionReason.mockResolvedValue({});
  });

  it("uses a Persian-first form and leaves the immutable code to the system", async () => {
    render(<OperationalReasonsAdminTab />);
    await screen.findByText(/هنوز دلیلی در این گروه ثبت نشده است/);

    expect(screen.getByLabelText("عنوان دلیل")).toBeInTheDocument();
    expect(screen.queryByLabelText(/کد/)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("عنوان دلیل"), { target: { value: "تأخیر بارگیری" } });
    fireEvent.click(screen.getByRole("button", { name: "افزودن دلیل" }));

    await waitFor(() => expect(api.createExecutionReason).toHaveBeenCalledWith("delay", {
      fa_name: "تأخیر بارگیری",
      en_name: "",
      definition: "",
      is_active: true,
    }));
  });
});
