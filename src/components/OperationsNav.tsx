import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router";
import { Plus } from "lucide-react";
import { getOperationalContext } from "@/lib/api";
import { currentActorCanManageTenantCustomers } from "@/lib/customerMaintenanceAccess";
import { useI18n } from "@/i18n";
import ReleaseIdentity from "@/components/ReleaseIdentity";

const NavItem = ({ to, active, children }: { to: string; active: boolean; children: ReactNode }) => (
  <Link
    to={to}
    aria-current={active ? "page" : undefined}
    className="navigation-item app-nav__item inline-flex min-h-10 items-center rounded-lg px-3 text-sm"
  >
    {children}
  </Link>
);

export default function OperationsNav() {
  const { t } = useI18n();
  const { pathname } = useLocation();
  const [permissions, setPermissions] = useState<string[]>([]);
  const [contextLoaded, setContextLoaded] = useState(false);
  useEffect(() => {
    getOperationalContext()
      .then(r => setPermissions(r.data.permissions))
      .catch(() => setPermissions([]))
      .finally(() => setContextLoaded(true));
  }, []);
  const canCreate = permissions.some(p => ["operational_shipment.create_direct", "operational_shipment.create_from_quote", "operational_shipment.create"].includes(p));
  const canReadOperations = permissions.includes("operational_shipment.read");
  const canReadWorkQueue = permissions.includes("oip.read");
  const canReadDashboards = permissions.includes("personal_dashboard.read");
  const canManageCustomers = currentActorCanManageTenantCustomers();
  const canReadRequests = canReadOperations || permissions.includes("request.read") || (() => {
    try {
      const actor = JSON.parse(localStorage.getItem("expert_user") || "{}");
      return actor.authority === "EXPERT"
        || (!actor.authority && ["expert", "business_expert"].includes(actor.role));
    } catch {
      return false;
    }
  })();
  if (!contextLoaded) return null;
  const isNewOperation = pathname === "/operations/shipments/new";
  return <nav aria-label={t("operations.navLabel")} className="navigation-surface app-nav flex flex-wrap items-center gap-1.5 rounded-xl border p-1.5 shadow-sm">
    {canReadOperations && <NavItem to="/operations" active={pathname === "/operations"}>فضای کار امروز</NavItem>}
    {canReadRequests && <NavItem to="/expert" active={pathname === "/expert" || pathname.startsWith("/expert/requests/")}>درخواست‌ها و قیمت‌ها</NavItem>}
    {canReadOperations && <NavItem to="/operations/shipments" active={!isNewOperation && pathname.startsWith("/operations/shipments")}>{t("operations.shipmentsTitle")}</NavItem>}
    {canReadOperations && <NavItem to="/operations/control-tower" active={pathname.startsWith("/operations/control-tower")}>برج کنترل عملیات</NavItem>}
    {canReadDashboards && <NavItem to="/dashboards" active={pathname.startsWith("/dashboards")}>داشبوردهای من</NavItem>}
    {canReadWorkQueue && <NavItem to="/operations/work-queue" active={pathname.startsWith("/operations/work-queue")}>{t("operations.workQueue")}</NavItem>}
    {canManageCustomers && <NavItem to="/customers" active={pathname.startsWith("/customers")}>مشتریان</NavItem>}
    {canCreate && <Link className="navigation-item inline-flex min-h-10 items-center gap-2 rounded-lg border border-[hsl(var(--nav-border))] px-3 text-sm" to="/operations/shipments/new"><Plus />{t("operations.newOperation")}</Link>}
    <div className="ms-auto shrink-0 px-2"><ReleaseIdentity /></div>
  </nav>;
}
