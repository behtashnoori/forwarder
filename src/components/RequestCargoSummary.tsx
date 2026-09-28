import { Package } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RequestCargoItem } from "@/lib/api";
import { formatQuantity } from "@/lib/formatQuantity";
import { meaningfulCargoDescription } from "@/lib/cargoPresentation";
import { useI18n } from "@/i18n";

interface RequestCargoSummaryProps {
  items: RequestCargoItem[];
  className?: string;
}

const RequestCargoSummary = ({ items, className = "" }: RequestCargoSummaryProps) => {
  const { language, locale, t } = useI18n();
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Package className="h-5 w-5 text-primary" />
          {t("requestForm.cargoItemsTitle")}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">{t("requestForm.noCargoItems")}</p>
        ) : (
          <ol className="space-y-3">
            {items.map((item) => {
              const typeName = item.cargo_type
                ? language === "fa" ? item.cargo_type.fa_name : item.cargo_type.en_name
                : null;
              const description = meaningfulCargoDescription(item.description);
              const positionLabel = formatQuantity(item.position, locale);
              const primaryLabel = description || typeName || (language === "fa" ? `قلم کالا ${positionLabel}` : `Cargo item ${positionLabel}`);
              const unitLabel = item.uom
                ? language === "fa" ? item.uom.fa_name : item.uom.en_name
                : null;
              return (
                <li key={item.public_id} className="rounded-xl border bg-muted/20 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <strong>{positionLabel}. {primaryLabel}</strong>
                    {item.quantity !== null && item.quantity !== undefined && unitLabel && (
                      <span dir="rtl" className="font-medium"><bdi>{formatQuantity(item.quantity, locale)}</bdi> {unitLabel}</span>
                    )}
                  </div>
                  {description && typeName && description !== typeName && <p className="mt-1 text-sm text-muted-foreground">{typeName}</p>}
                </li>
              );
            })}
          </ol>
        )}
      </CardContent>
    </Card>
  );
};

export default RequestCargoSummary;
