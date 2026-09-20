import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QuoteModal } from "@/components/QuoteModal";
import * as api from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, submitQuote: vi.fn() };
});

describe("QuoteModal supported currencies", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.submitQuote).mockResolvedValue({
      ok: true,
      quote: { id: 1, amount: 1234567, currency: "EUR", created_at: "2026-09-20T00:00:00" },
      request: { id: 12, status: "waiting_for_customer" },
    });
  });

  it("offers EUR and submits its canonical code through the existing quote path", async () => {
    const user = userEvent.setup();
    const onSuccess = vi.fn();
    render(
      <QuoteModal
        open
        onOpenChange={vi.fn()}
        requestId="12"
        onSuccess={onSuccess}
      />,
    );

    const currency = screen.getByLabelText("ارز");
    expect(Array.from(currency.querySelectorAll("option")).map((item) => item.value)).toEqual([
      "IRR",
      "USD",
      "EUR",
    ]);
    expect(screen.getByRole("option", { name: "یورو (EUR)" })).toBeInTheDocument();

    await user.type(screen.getByLabelText("مبلغ (الزامی)"), "1234567");
    await user.selectOptions(currency, "EUR");
    await user.click(screen.getByRole("button", { name: "ارسال پیشنهاد" }));

    expect(api.submitQuote).toHaveBeenCalledWith(
      "12",
      expect.objectContaining({ amount: 1234567, currency: "EUR" }),
    );
    expect(onSuccess).toHaveBeenCalledTimes(1);
  });
});
