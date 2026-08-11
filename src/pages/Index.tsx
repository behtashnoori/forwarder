import { useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, Check, FileText, Search, ShieldCheck, Truck } from "lucide-react";
import Header from "@/components/Header";
import LocationForm from "@/components/LocationForm";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useI18n } from "@/i18n";
import { useNavigate } from "react-router";

export const trackingRouteFor = (code: string) => {
  const normalized = code.trim();
  const encoded = encodeURIComponent(normalized);
  return /^(?:SR(?:-|\d)|\d+$)/i.test(normalized) ? `/customer/track/${encoded}` : `/project/track/${encoded}`;
};

const journey = ["request", "pricing", "operations", "documents", "tracking"] as const;
const values = ["coverage", "insight", "experience", "security", "support"] as const;

const Index = () => {
  const [shippingType, setShippingType] = useState<"domestic" | "international" | null>(null);
  const [trackingNumber, setTrackingNumber] = useState("");
  const [trackingError, setTrackingError] = useState("");
  const [requestPickerOpen, setRequestPickerOpen] = useState(false);
  const navigate = useNavigate();
  const { direction, language, t } = useI18n();

  useEffect(() => { document.title = t("landing.metaTitle"); }, [language, t]);

  const submitTracking = (event: FormEvent) => {
    event.preventDefault();
    const code = trackingNumber.trim();
    if (!code) { setTrackingError(t("command.trackingRequired")); return; }
    setTrackingError("");
    navigate(trackingRouteFor(code));
  };

  if (shippingType) return <div className="min-h-screen bg-slate-50"><Header /><main className="mx-auto flex max-w-5xl justify-center px-4 py-6"><LocationForm shippingType={shippingType} onBack={() => setShippingType(null)} /></main></div>;

  return (
    <div id="command-center-root" className="min-h-screen overflow-x-hidden bg-slate-50 text-slate-950">
      <Header />
      <main>
        <section className="relative overflow-hidden border-b border-slate-200 bg-white">
          <div className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(circle_at_72%_0%,rgba(37,99,235,0.08),transparent_58%)]" />
          <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-[1.08fr_.92fr] lg:px-8 lg:py-28">
            <div className={direction === "rtl" ? "text-right" : "text-left"}>
              <div className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50/70 px-3 py-1.5 text-xs font-semibold text-blue-800"><ShieldCheck className="h-4 w-4" aria-hidden="true" />{t("command.eyebrow")}</div>
              <h1 className="mt-6 max-w-3xl text-4xl font-extrabold leading-[1.2] tracking-tight sm:text-5xl lg:text-6xl">{t("command.title")}</h1>
              <p className="mt-6 max-w-2xl text-base leading-8 text-slate-600 sm:text-lg">{t("command.description")}</p>
              <Button size="lg" className="mt-8 min-h-12 px-6 shadow-sm" onClick={() => setRequestPickerOpen(true)}><Truck className="h-5 w-5" aria-hidden="true" />{t("command.newRequest")}<ArrowLeft className={`h-4 w-4 ${direction === "ltr" ? "rotate-180" : ""}`} aria-hidden="true" /></Button>
            </div>

            <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-[0_24px_70px_-38px_rgba(15,23,42,.35)] sm:p-8" aria-labelledby="tracking-title">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-primary"><Search className="h-5 w-5" aria-hidden="true" /></div>
              <h2 id="tracking-title" className="mt-5 text-2xl font-bold">{t("command.trackingTitle")}</h2>
              <p className="mt-3 text-sm leading-7 text-slate-600">{t("command.trackingDescription")}</p>
              <form className="mt-6" onSubmit={submitTracking} noValidate>
                <Label htmlFor="command-tracking">{t("command.trackingLabel")}</Label>
                <Input id="command-tracking" value={trackingNumber} onChange={(e) => { setTrackingNumber(e.target.value); if (trackingError) setTrackingError(""); }} placeholder={t("command.trackingPlaceholder")} className="mt-2 h-12 font-mono" dir="ltr" aria-invalid={Boolean(trackingError)} aria-describedby="tracking-help tracking-error" />
                <p id="tracking-help" className="mt-2 text-xs text-slate-500" dir="ltr">{t("command.trackingHelp")}</p>
                <p id="tracking-error" role="alert" className="mt-2 min-h-5 text-sm font-medium text-destructive">{trackingError}</p>
                <Button type="submit" className="mt-1 h-12 w-full"><Search className="h-4 w-4" aria-hidden="true" />{t("command.track")}</Button>
              </form>
            </section>
          </div>
        </section>

        <section id="capabilities" className="scroll-mt-24 bg-white py-16 sm:py-20" aria-labelledby="journey-title">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <p className="text-sm font-semibold text-primary">{t("journey.eyebrow")}</p>
            <h2 id="journey-title" className="mt-2 text-3xl font-bold tracking-tight">{t("journey.title")}</h2>
            <ol className="mt-10 grid gap-3 md:grid-cols-5">
              {journey.map((step, index) => <li key={step} className="relative rounded-2xl border border-slate-200 bg-slate-50/60 p-5"><span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">{index + 1}</span><h3 className="mt-4 font-bold">{t(`journey.${step}.title`)}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{t(`journey.${step}.description`)}</p></li>)}
            </ol>
          </div>
        </section>

        <section id="solutions" className="scroll-mt-24 border-y border-slate-200 bg-slate-50 py-16 sm:py-20" aria-labelledby="value-title">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <h2 id="value-title" className="text-3xl font-bold tracking-tight">{t("valueStrip.title")}</h2>
            <div className="mt-10 grid gap-x-8 gap-y-8 sm:grid-cols-2 lg:grid-cols-5">
              {values.map((item) => <div key={item} className="border-s-2 border-blue-100 ps-4"><Check className="h-5 w-5 text-primary" aria-hidden="true" /><h3 className="mt-3 font-bold">{t(`valueStrip.${item}.title`)}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{t(`valueStrip.${item}.description`)}</p></div>)}
            </div>
          </div>
        </section>

        <section id="about" className="scroll-mt-24 bg-white py-16 sm:py-20"><div className="mx-auto max-w-4xl px-4 text-center sm:px-6"><FileText className="mx-auto h-7 w-7 text-primary" aria-hidden="true" /><h2 className="mt-4 text-3xl font-bold">{t("brand.name")}</h2><p className="mt-3 text-lg text-slate-600">{t("landing.brandDescriptor")}</p><p className="mt-6 text-sm text-slate-500">{t("landing.companyAttribution")}</p></div></section>
      </main>

      <footer id="contact" className="scroll-mt-24 border-t border-slate-200 bg-slate-950 text-slate-300"><div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-10 sm:px-6 md:flex-row md:items-end md:justify-between lg:px-8"><div><p className="text-xl font-bold text-white">{t("brand.name")}</p><p className="mt-2 text-sm">{t("landing.brandDescriptor")}</p><p className="mt-4 text-xs text-slate-500">{t("landing.companyAttribution")}</p></div><a className="rounded-sm text-sm hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400" href="mailto:info@forwarding.ir">info@forwarding.ir</a></div></footer>

      <Dialog open={requestPickerOpen} onOpenChange={setRequestPickerOpen}><DialogContent className="sm:max-w-lg"><DialogHeader><DialogTitle>{t("command.requestTypeTitle")}</DialogTitle><DialogDescription>{t("command.requestTypeDescription")}</DialogDescription></DialogHeader><div className="grid gap-3 sm:grid-cols-2"><Button className="min-h-12" onClick={() => setShippingType("domestic")}>{t("shipping.domestic.title")}</Button><Button className="min-h-12" variant="outline" onClick={() => setShippingType("international")}>{t("shipping.international.title")}</Button></div></DialogContent></Dialog>
    </div>
  );
};

export default Index;
