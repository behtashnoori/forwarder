import { fireEvent, render, screen } from "@testing-library/react";
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
    expect(screen.getByRole("option", { name: "ریال ایران (IRR)" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "دلار آمریکا (USD)" })).toBeInTheDocument();

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

it("keeps optional Quote expiry a date across Persian/Gregorian representations", async () => {
  render(<QuoteModal open onOpenChange={vi.fn()} requestId="12" onSuccess={vi.fn()}/>);
  expect(screen.getByLabelText("تاریخ اعتبار")).toHaveValue("");
  fireEvent.change(screen.getByLabelText("مبلغ (الزامی)"),{target:{value:"1500000"}});
  fireEvent.change(screen.getByLabelText("تاریخ اعتبار"),{target:{value:"2026-10-04"}});
  fireEvent.click(screen.getByRole("button",{name:/شمسی/}));
  fireEvent.click(screen.getByRole("button",{name:"میلادی"}));
  expect(screen.getByLabelText("تاریخ اعتبار")).toHaveValue("2026-10-04");
  fireEvent.click(screen.getByRole("button",{name:"شمسی"}));
  fireEvent.change(screen.getByLabelText("تاریخ اعتبار روز"),{target:{value:"13"}});
  expect(screen.getByLabelText("تاریخ اعتبار")).toHaveValue("2026-10-05");
  await userEvent.click(screen.getByRole("button",{name:"ارسال پیشنهاد"}));
  expect(api.submitQuote).toHaveBeenLastCalledWith("12",expect.objectContaining({valid_until:"2026-10-05"}));
});
