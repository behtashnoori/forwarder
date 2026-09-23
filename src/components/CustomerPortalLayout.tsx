import type { ReactNode } from "react";
import { Link } from "react-router";
import Header from "@/components/Header";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n";

export default function CustomerPortalLayout({ children, privateNav = false }: { children: ReactNode; privateNav?: boolean }) {
  const { t } = useI18n();
  return <div className="min-h-screen bg-slate-50"><Header />
    {privateNav && <nav className="border-b bg-white" aria-label={t("customer.portalNavigation")}><div className="mx-auto flex max-w-6xl flex-wrap gap-2 px-4 py-3">
      <Button asChild variant="ghost" size="sm"><Link to="/customer/requests">{t("customer.requests")}</Link></Button>
      <Button asChild variant="ghost" size="sm"><Link to="/customer/profile">{t("customer.profile")}</Link></Button>
      <Button asChild variant="ghost" size="sm"><Link to="/customer/change-password">{t("customer.changePassword")}</Link></Button>
    </div></nav>}
    <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
  </div>;
}
