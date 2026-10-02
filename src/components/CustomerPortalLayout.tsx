import type { ReactNode } from "react";
import { Link, useLocation } from "react-router";
import Header from "@/components/Header";
import { useI18n } from "@/i18n";

export default function CustomerPortalLayout({ children, privateNav = false }: { children: ReactNode; privateNav?: boolean }) {
  const { t } = useI18n();
  const { pathname } = useLocation();
  const item = (to: string, label: string) => <Link
    to={to}
    aria-current={pathname === to || pathname.startsWith(`${to}/`) ? "page" : undefined}
    className="navigation-item inline-flex min-h-9 items-center rounded-lg px-3 py-2 text-sm font-medium"
  >{label}</Link>;
  return <div className="min-h-screen bg-slate-50"><Header />
    {privateNav && <nav className="navigation-surface border-b" aria-label={t("customer.portalNavigation")}><div className="mx-auto flex max-w-6xl flex-wrap gap-2 px-4 py-3">
      {item("/customer/requests", t("customer.requests"))}
      {item("/customer/shipments", t("customer.shipments"))}
      {item("/customer/documents", t("customer.documents"))}
      {item("/customer/profile", t("customer.profile"))}
      {item("/customer/change-password", t("customer.changePassword"))}
    </div></nav>}
    <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
  </div>;
}
