export interface RequestCargoDraft {
  key: string;
  description: string;
  cargoTypePublicId: string;
  quantity: string;
  uomPublicId: string;
}

export const newRequestCargoDraft = (): RequestCargoDraft => ({
  key: crypto.randomUUID(),
  description: "",
  cargoTypePublicId: "",
  quantity: "",
  uomPublicId: "",
});

export const validateRequestCargoDrafts = (
  items: RequestCargoDraft[],
): Record<string, string> => {
  const errors: Record<string, string> = {};
  items.forEach((item, index) => {
    const base = `cargo_items[${index}]`;
    const description = item.description.trim();
    const quantity = item.quantity.trim();
    const hasQuantity = Boolean(quantity);
    const hasUom = Boolean(item.uomPublicId);

    if (description.length > 2000) {
      errors[`${base}.description`] = "requestForm.cargoDescriptionTooLong";
    }
    if (hasQuantity !== hasUom) {
      errors[hasQuantity ? `${base}.uom_public_id` : `${base}.quantity`] =
        "requestForm.cargoQuantityUnitPair";
    }
    if (hasQuantity) {
      const match = /^(?:0|[1-9][0-9]*)(?:\.([0-9]+))?$/.exec(quantity);
      if (!match) {
        errors[`${base}.quantity`] = "requestForm.cargoQuantityFormat";
      } else if ((match[1] || "").length > 6) {
        errors[`${base}.quantity`] = "requestForm.cargoQuantityScale";
      } else if (quantity.replace(".", "").length > 18 || quantity.split(".")[0].length > 12) {
        errors[`${base}.quantity`] = "requestForm.cargoQuantityPrecision";
      } else if (/^0(?:\.0+)?$/.test(quantity)) {
        errors[`${base}.quantity`] = "requestForm.cargoQuantityPositive";
      }
    }
    if (!description && !item.cargoTypePublicId && !(hasQuantity && hasUom)) {
      errors[base] = "requestForm.cargoItemEmpty";
    }
  });
  return errors;
};
