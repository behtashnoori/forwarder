import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { ArrowLeft, Search, ShieldCheck, Truck } from "lucide-react";
import Header from "@/components/Header";
import LocationForm from "@/components/LocationForm";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useI18n } from "@/i18n";

export const trackingRouteFor = (code: string) => {
  const normalized = code.trim();
  const encoded = encodeURIComponent(normalized);
  return /^(?:SR(?:-|\d)|\d+$)/i.test(normalized)
    ? `/customer/track/${encoded}`
    : `/project/track/${encoded}`;
};

const Index = () => {
  const [shippingType, setShippingType] = useState<"domestic" | "international" | null>(null);
  const [trackingNumber, setTrackingNumber] = useState("");
  const [trackingError, setTrackingError] = useState("");
  const [requestPickerOpen, setRequestPickerOpen] = useState(false);
  const navigate = useNavigate();
  const { direction, language, t } = useI18n();

  useEffect(() => {
    document.title = language === "fa"
      ? "فورواردر | ثبت درخواست و رهگیری عملیات حمل"
      : "Forwarder — Shipment Request and Tracking Portal";
  }, [language]);

  const submitTracking = (event: FormEvent) => {
    event.preventDefault();
    const code = trackingNumber.trim();
    if (!code) {
      setTrackingError(t("command.trackingRequired"));
      return;
    }
    setTrackingError("");
    navigate(trackingRouteFor(code));
  };

  if (shippingType) {
    return <div className="min-h-screen bg-slate-50"><Header /><main className="mx-auto flex max-w-5xl justify-center px-4 py-6"><LocationForm shippingType={shippingType} onBack={() => setShippingType(null)} /></main></div>;
  }

  return (
    <div id="command-center-root" className="flex min-h-screen flex-col overflow-x-hidden bg-[radial-gradient(circle_at_top_right,_rgba(13,79,163,0.10),_transparent_32%),#f8fafc] lg:h-screen lg:min-h-0 lg:overflow-hidden">
      <Header />
      <main className="mx-auto flex w-full max-w-6xl flex-1 items-center px-4 py-6 sm:px-6 lg:py-8">
        <div className="grid w-full items-center gap-7 lg:grid-cols-[1fr_0.9fr] lg:gap-12">
          <section className={direction === "rtl" ? "text-right" : "text-left"} aria-labelledby="command-title">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary/15 bg-white/80 px-3 py-1.5 text-xs font-semibold text-primary shadow-sm"><ShieldCheck className="h-4 w-4" aria-hidden="true" />{t("command.eyebrow")}</div>
            <h1 id="command-title" className="max-w-2xl text-3xl font-extrabold leading-tight tracking-tight text-slate-950 sm:text-4xl lg:text-5xl">{t("command.title")}</h1>
            <p className="mt-4 max-w-xl text-base leading-7 text-slate-600 sm:text-lg">{t("command.description")}</p>
            <div className="mt-7 flex flex-col gap-3 sm:flex-row">
              <Button size="lg" className="min-h-12 px-6" onClick={() => setRequestPickerOpen(true)}><Truck className="h-5 w-5" aria-hidden="true" />{t("command.newRequest")}<ArrowLeft className={`h-4 w-4 ${direction === "ltr" ? "rotate-180" : ""}`} aria-hidden="true" /></Button>
            </div>
            <p className="mt-3 text-sm text-slate-500">{t("command.requestHint")}</p>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-xl shadow-slate-200/50 sm:p-7" aria-labelledby="tracking-title">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary"><Search className="h-5 w-5" aria-hidden="true" /></div>
            <h2 id="tracking-title" className="mt-4 text-xl font-bold text-slate-950 sm:text-2xl">{t("command.trackingTitle")}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">{t("command.trackingDescription")}</p>
            <form className="mt-5" onSubmit={submitTracking} noValidate>
              <Label htmlFor="command-tracking">{t("command.trackingLabel")}</Label>
              <div className="mt-2 flex flex-col gap-3 sm:flex-row">
                <Input id="command-tracking" value={trackingNumber} onChange={(event) => { setTrackingNumber(event.target.value); if (trackingError) setTrackingError(""); }} placeholder={t("command.trackingPlaceholder")} className="h-12 min-w-0 flex-1 font-mono" dir="ltr" aria-invalid={Boolean(trackingError)} aria-describedby="tracking-help tracking-error" />
                <Button type="submit" className="h-12 shrink-0 px-6"><Search className="h-4 w-4" aria-hidden="true" />{t("command.track")}</Button>
              </div>
              <p id="tracking-help" className="mt-2 text-xs leading-5 text-slate-500">{t("command.trackingHelp")}</p>
              <p id="tracking-error" role="alert" className="mt-2 min-h-5 text-sm font-medium text-destructive">{trackingError}</p>
            </form>
          </section>
        </div>
      </main>
      <Dialog open={requestPickerOpen} onOpenChange={setRequestPickerOpen}><DialogContent className="sm:max-w-lg"><DialogHeader><DialogTitle>{t("command.requestTypeTitle")}</DialogTitle><DialogDescription>{t("command.requestTypeDescription")}</DialogDescription></DialogHeader><div className="grid gap-3 sm:grid-cols-2"><Button className="min-h-12" onClick={() => setShippingType("domestic")}>{t("shipping.domestic.title")}</Button><Button className="min-h-12" variant="outline" onClick={() => setShippingType("international")}>{t("shipping.international.title")}</Button></div></DialogContent></Dialog>
      <footer className="border-t border-slate-200/80 bg-white/70"><nav className="mx-auto flex min-h-14 max-w-6xl flex-wrap items-center justify-center gap-x-6 gap-y-2 px-4 py-3 text-sm text-slate-600" aria-label={t("command.secondaryNav")}><Link className="rounded-sm hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary" to="/about">{t("nav.about")}</Link><Link className="rounded-sm hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary" to="/contact">{t("nav.contact")}</Link><span className="text-slate-400">© {new Date().getFullYear()} {t("brand.name")}</span></nav></footer>
    </div>
  );
};

export default Index;
