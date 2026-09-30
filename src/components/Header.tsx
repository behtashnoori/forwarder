import { Button } from "@/components/ui/button";
import { Globe2, Menu, UserRound, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router";
import ExpertLogin from "./ExpertLogin";
import { useI18n } from "@/i18n";
import { fetchCustomerSession } from "@/lib/customerPortalApi";

const Header = () => {
  const { pathname } = useLocation();
  const { t, toggleLanguage } = useI18n();
  const [open, setOpen] = useState(false);
  const [customerAuthenticated, setCustomerAuthenticated] = useState(false);
  useEffect(() => {
    let active = true;
    fetchCustomerSession()
      .then((session) => { if (active) setCustomerAuthenticated(session.authenticated); })
      .catch(() => { if (active) setCustomerAuthenticated(false); });
    return () => { active = false; };
  }, [pathname]);
  const href = (anchor: string) => pathname === "/" ? anchor : `/${anchor}`;
  const customerEntryHref = customerAuthenticated ? "/customer/requests" : "/customer";
  const customerEntryLabel = customerAuthenticated ? t("customer.portalAuthenticatedEntry") : t("customer.portalEntry");
  const links = [["#capabilities", "nav.capabilities"], ["#solutions", "nav.solutions"], ["#about", "nav.about"], ["#contact", "nav.contact"]] as const;
  return <header className="site-header sticky top-0 z-50 border-b border-slate-200/80 bg-white/90 backdrop-blur-xl"><div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 py-2.5 sm:px-6 lg:px-8"><Link to="/" className="flex items-center gap-2.5 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"><span className="h-9 w-9 overflow-hidden rounded-lg border border-slate-200 bg-white"><img src="/brand-icon.png" alt="" className="h-full w-full scale-[1.35] object-cover" /></span><span className="text-base font-semibold tracking-tight">{t("brand.name")}</span></Link><nav className="hidden items-center gap-0.5 lg:flex" aria-label={t("nav.primary")}>
    {links.map(([anchor, key]) => <a key={anchor} href={href(anchor)} className="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">{t(key)}</a>)}
    <Button asChild variant="ghost" size="sm"><Link to={customerEntryHref}><UserRound className="h-4 w-4" />{customerEntryLabel}</Link></Button><Button variant="ghost" size="sm" onClick={toggleLanguage} aria-label={t("app.language.switchLabel")}><Globe2 className="h-4 w-4" />{t("app.language.toggle")}</Button><ExpertLogin triggerClassName="border-primary bg-primary text-white hover:bg-primary/90 hover:text-white" />
  </nav><Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="mobile-nav" aria-label={t("nav.menu")}>{open ? <X /> : <Menu />}</Button></div>
  {open && <nav id="mobile-nav" className="border-t border-slate-200 bg-white px-4 py-4 lg:hidden" aria-label={t("nav.primary")}><div className="mx-auto flex max-w-7xl flex-col gap-1">{links.map(([anchor, key]) => <a key={anchor} href={href(anchor)} onClick={() => setOpen(false)} className="rounded-lg px-3 py-3 text-sm text-slate-700">{t(key)}</a>)}<Button asChild variant="ghost" className="justify-start"><Link to={customerEntryHref} onClick={() => setOpen(false)}><UserRound className="h-4 w-4" />{customerEntryLabel}</Link></Button><Button variant="ghost" className="justify-start" onClick={() => { toggleLanguage(); setOpen(false); }}><Globe2 className="h-4 w-4" />{t("app.language.toggle")}</Button><ExpertLogin triggerClassName="mt-2 w-full bg-primary text-white hover:bg-primary/90 hover:text-white" /></div></nav>}
  </header>;
};
export default Header;
