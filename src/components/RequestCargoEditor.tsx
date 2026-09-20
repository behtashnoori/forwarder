import { ArrowDown, ArrowUp, Package, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { RequestCargoOptions } from "@/lib/api";
import { useI18n } from "@/i18n";
import { newRequestCargoDraft, type RequestCargoDraft } from "./requestCargoDraft";

interface RequestCargoEditorProps {
  items: RequestCargoDraft[];
  options: RequestCargoOptions;
  optionsError?: string | null;
  errors: Record<string, string>;
  onChange: (items: RequestCargoDraft[]) => void;
}

const RequestCargoEditor = ({
  errors,
  items,
  onChange,
  options,
  optionsError,
}: RequestCargoEditorProps) => {
  const { language, t } = useI18n();
  const errorText = (value: string) =>
    value.startsWith("requestForm.")
      ? t(value as Parameters<typeof t>[0])
      : value;
  const update = (index: number, patch: Partial<RequestCargoDraft>) =>
    onChange(items.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  const move = (index: number, offset: -1 | 1) => {
    const next = [...items];
    const target = index + offset;
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };

  return (
    <section aria-labelledby="request-cargo-heading" className="space-y-4 rounded-lg border bg-muted/20 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 id="request-cargo-heading" className="flex items-center gap-2 text-sm font-semibold">
            <Package className="h-4 w-4 text-primary" />
            {t("requestForm.cargoItemsTitle")}
          </h3>
          <p className="mt-1 text-xs leading-6 text-muted-foreground">{t("requestForm.cargoItemsOptionalHelp")}</p>
        </div>
        <Button type="button" variant="outline" onClick={() => onChange([...items, newRequestCargoDraft()])}>
          <Plus className="ml-2 h-4 w-4" />
          {t("requestForm.addCargoItem")}
        </Button>
      </div>

      {optionsError && <p className="text-xs text-amber-700" role="status">{optionsError}</p>}
      {items.length === 0 && (
        <p className="rounded-lg border border-dashed p-4 text-center text-sm text-muted-foreground">
          {t("requestForm.noCargoItems")}
        </p>
      )}

      {items.map((item, index) => {
        const base = `cargo_items[${index}]`;
        return (
          <article key={item.key} className="space-y-4 rounded-lg border bg-background p-4" aria-label={`${t("requestForm.cargoItem")} ${index + 1}`}>
            <div className="flex items-center justify-between gap-2">
              <strong className="text-sm">{t("requestForm.cargoItem")} {index + 1}</strong>
              <div className="flex gap-1">
                <Button type="button" variant="ghost" size="icon" disabled={index === 0} aria-label={t("requestForm.moveCargoUp")} onClick={() => move(index, -1)}><ArrowUp className="h-4 w-4" /></Button>
                <Button type="button" variant="ghost" size="icon" disabled={index === items.length - 1} aria-label={t("requestForm.moveCargoDown")} onClick={() => move(index, 1)}><ArrowDown className="h-4 w-4" /></Button>
                <Button type="button" variant="ghost" size="icon" aria-label={t("requestForm.removeCargoItem")} onClick={() => onChange(items.filter((_, itemIndex) => itemIndex !== index))}><Trash2 className="h-4 w-4" /></Button>
              </div>
            </div>

            {errors[base] && <p className="text-sm text-destructive" role="alert">{errorText(errors[base])}</p>}
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor={`cargo-description-${item.key}`}>{t("requestForm.cargoDescription")}</Label>
                <Input id={`cargo-description-${item.key}`} value={item.description} maxLength={2000} onChange={(event) => update(index, { description: event.target.value })} />
                {errors[`${base}.description`] && <p className="text-xs text-destructive" role="alert">{errorText(errors[`${base}.description`])}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor={`cargo-type-${item.key}`}>{t("requestForm.cargoType")}</Label>
                <select id={`cargo-type-${item.key}`} className="h-10 w-full rounded-md border bg-background px-3 text-sm" value={item.cargoTypePublicId} onChange={(event) => update(index, { cargoTypePublicId: event.target.value })}>
                  <option value="">{t("requestForm.cargoTypeNone")}</option>
                  {options.cargo_types.map((option) => <option key={option.public_id} value={option.public_id}>{language === "fa" ? option.fa_name : option.en_name}</option>)}
                </select>
                {errors[`${base}.cargo_type_public_id`] && <p className="text-xs text-destructive" role="alert">{errors[`${base}.cargo_type_public_id`]}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor={`cargo-quantity-${item.key}`}>{t("requestForm.cargoQuantity")}</Label>
                <Input id={`cargo-quantity-${item.key}`} inputMode="decimal" dir="ltr" value={item.quantity} placeholder="12.500000" onChange={(event) => update(index, { quantity: event.target.value })} />
                {errors[`${base}.quantity`] && <p className="text-xs text-destructive" role="alert">{errorText(errors[`${base}.quantity`])}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor={`cargo-uom-${item.key}`}>{t("requestForm.cargoUnit")}</Label>
                <select id={`cargo-uom-${item.key}`} className="h-10 w-full rounded-md border bg-background px-3 text-sm" value={item.uomPublicId} onChange={(event) => update(index, { uomPublicId: event.target.value })}>
                  <option value="">{t("requestForm.cargoUnitNone")}</option>
                  {options.uoms.map((option) => <option key={option.public_id} value={option.public_id}>{language === "fa" ? option.fa_name : option.en_name} ({option.symbol})</option>)}
                </select>
                {errors[`${base}.uom_public_id`] && <p className="text-xs text-destructive" role="alert">{errorText(errors[`${base}.uom_public_id`])}</p>}
              </div>
            </div>
          </article>
        );
      })}
    </section>
  );
};

export default RequestCargoEditor;
