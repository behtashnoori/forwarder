import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n";

export type RequestShippingType = "domestic" | "international";

export default function RequestTypeChooser({
  onSelect,
}: {
  onSelect: (shippingType: RequestShippingType) => void;
}) {
  const { t } = useI18n();

  return (
    <div className="grid min-w-0 gap-3 sm:grid-cols-2">
      <Button className="min-h-12 min-w-0 whitespace-normal" onClick={() => onSelect("domestic")}>
        {t("shipping.domestic.title")}
      </Button>
      <Button className="min-h-12 min-w-0 whitespace-normal" variant="outline" onClick={() => onSelect("international")}>
        {t("shipping.international.title")}
      </Button>
    </div>
  );
}
