import { useEffect, useState } from "react";
import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import { getOperationalContext } from "@/lib/api";
import { useI18n } from "@/i18n";

export default function OperationsNav() {
  const { t, language } = useI18n();
  const [permissions, setPermissions] = useState<string[]>([]);
  useEffect(() => { getOperationalContext().then(r => setPermissions(r.data.permissions)).catch(() => setPermissions([])); }, []);
  const canCreate = permissions.some(p => ["operational_shipment.create_direct", "operational_shipment.create_from_quote", "operational_shipment.create"].includes(p));
  if (!permissions.length) return null;
  return <nav aria-label="Operations" className="flex flex-wrap gap-2 rounded-xl border bg-white p-2">
    <Button asChild variant="ghost"><Link to="/operations/shipments">{t("operations.shipmentsTitle")}</Link></Button>
    <Button asChild variant="ghost"><Link to="/operations/work-queue">{t("operations.workQueue")}</Link></Button>
    {canCreate && <Button asChild><Link to="/operations/shipments/new">{language === "fa" ? "عملیات جدید" : "New Operation"}</Link></Button>}
  </nav>;
}
