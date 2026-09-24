import { useEffect, useState } from "react";
import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import { getOperationalContext } from "@/lib/api";
import { currentActorCanManageTenantCustomers } from "@/lib/customerMaintenanceAccess";
import { useI18n } from "@/i18n";
import ReleaseIdentity from "@/components/ReleaseIdentity";

export default function OperationsNav() {
  const { t } = useI18n();
  const [permissions, setPermissions] = useState<string[]>([]);
  useEffect(() => { getOperationalContext().then(r => setPermissions(r.data.permissions)).catch(() => setPermissions([])); }, []);
  const canCreate = permissions.some(p => ["operational_shipment.create_direct", "operational_shipment.create_from_quote", "operational_shipment.create"].includes(p));
  const canReadOperations = permissions.includes("operational_shipment.read");
  const canReadWorkQueue = permissions.includes("oip.read");
  const canReadDashboards = permissions.includes("personal_dashboard.read");
  const canManageCustomers = currentActorCanManageTenantCustomers();
  if (!permissions.length) return null;
  return <nav aria-label={t("operations.navLabel")} className="flex flex-wrap items-center gap-2 rounded-xl border bg-white p-2">
    {canReadOperations && <Button asChild variant="ghost"><Link to="/operations">فضای کار امروز</Link></Button>}
    {canReadOperations && <Button asChild variant="ghost"><Link to="/operations/shipments">{t("operations.shipmentsTitle")}</Link></Button>}
    {canReadOperations && <Button asChild variant="ghost"><Link to="/operations/control-tower">برج کنترل عملیات</Link></Button>}
    {canReadWorkQueue && <Button asChild variant="ghost"><Link to="/operations/work-queue">{t("operations.workQueue")}</Link></Button>}
    {canReadDashboards && <Button asChild variant="ghost"><Link to="/dashboards">داشبوردهای من</Link></Button>}
    {canManageCustomers && <Button asChild variant="ghost"><Link to="/customers">مشتریان</Link></Button>}
    {canCreate && <Button asChild><Link to="/operations/shipments/new">{t("operations.newOperation")}</Link></Button>}
    <div className="ms-auto shrink-0 px-2"><ReleaseIdentity /></div>
  </nav>;
}
