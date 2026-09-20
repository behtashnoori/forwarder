import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import RequestCargoEditor from "@/components/RequestCargoEditor";
import {
  newRequestCargoDraft,
  validateRequestCargoDrafts,
} from "@/components/requestCargoDraft";

vi.mock("@/i18n", () => ({
  useI18n: () => ({ language: "en", t: (key: string) => key }),
}));

const options = {
  cargo_types: [{ public_id: "type-1", code: "GENERAL", fa_name: "عمومی", en_name: "General" }],
  uoms: [{ public_id: "uom-1", code: "KG", fa_name: "کیلوگرم", en_name: "Kilogram", symbol: "kg", measurement_dimension: "WEIGHT" as const }],
};

describe("RequestCargoEditor", () => {
  it("starts with an intentional zero-item state and adds a draft only on request", async () => {
    const onChange = vi.fn();
    render(<RequestCargoEditor items={[]} options={options} errors={{}} onChange={onChange} />);
    expect(screen.getByText("requestForm.noCargoItems")).toBeInTheDocument();
    expect(screen.queryByLabelText("requestForm.cargoDescription")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /requestForm.addCargoItem/ }));
    expect(onChange).toHaveBeenCalledWith([
      expect.objectContaining({ description: "", quantity: "", cargoTypePublicId: "", uomPublicId: "" }),
    ]);
  });

  it("validates only voluntarily-created items and preserves exact decimal strings", () => {
    expect(validateRequestCargoDrafts([])).toEqual({});
    const empty = newRequestCargoDraft();
    expect(validateRequestCargoDrafts([empty])).toHaveProperty("cargo_items[0]");
    expect(validateRequestCargoDrafts([{ ...empty, description: "Cargo" }])).toEqual({});
    expect(validateRequestCargoDrafts([{ ...empty, quantity: "3.250000", uomPublicId: "uom-1" }])).toEqual({});
    expect(validateRequestCargoDrafts([{ ...empty, quantity: "3.2500001", uomPublicId: "uom-1" }]))
      .toHaveProperty("cargo_items[0].quantity", "requestForm.cargoQuantityScale");
  });
});
