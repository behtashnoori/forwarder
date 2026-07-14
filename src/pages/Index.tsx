import { useEffect, useState } from "react";
import Header from "@/components/Header";
import LocationForm from "@/components/LocationForm";
import Footer from "@/components/Footer";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ArrowLeft,
  Check,
  ClipboardCheck,
  Clock3,
  Database,
  Eye,
  FileText,
  Globe2,
  MapPin,
  MapPinned,
  PackageCheck,
  PhoneCall,
  Search,
  Sparkles,
  Truck,
  UserRoundCheck,
  FileSignature,
} from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { useI18n } from "@/i18n";

const Index = () => {
  const [shippingType, setShippingType] = useState<"domestic" | "international" | null>(null);
  const [trackingNumber, setTrackingNumber] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const { direction, t } = useI18n();

  useEffect(() => {
    const sectionId = location.hash === "#about" || location.hash === "#contact"
      ? location.hash.slice(1)
      : "";

    if (!sectionId) {
      return;
    }

    setShippingType(null);

    const scrollTimer = window.setTimeout(() => {
      document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);

    return () => window.clearTimeout(scrollTimer);
  }, [location.hash]);

  const handleShippingTypeSelect = (type: "domestic" | "international") => {
    setShippingType(type);
  };

  const handleBackToSelection = () => {
    setShippingType(null);
  };

  const handleTrackRequest = () => {
    const code = trackingNumber.trim();
    if (!code) return;
    navigate(`/customer/track/${encodeURIComponent(code)}`);
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA]">
      <Header />

      <section className="px-4 py-8 md:py-12">
        <div className="container mx-auto max-w-5xl">
          {!shippingType ? (
            <div className="space-y-14 md:space-y-20">
              <Hero direction={direction} />

              <WorkflowSection />

              <ValueSection />

              <section id="services" className="scroll-mt-24 space-y-7">
                <div className="text-center">
                  <p className="text-sm font-semibold text-primary">{t("services.eyebrow")}</p>
                  <h2 className="mt-2 text-2xl font-bold text-[#1F2937] md:text-3xl">{t("services.title")}</h2>
                </div>
                <ShippingTypeSelector onSelect={handleShippingTypeSelect} />
              </section>

              <div id="tracking" className="scroll-mt-24">
                <TrackingSection
                  trackingNumber={trackingNumber}
                  setTrackingNumber={setTrackingNumber}
                  onTrack={handleTrackRequest}
                  direction={direction}
                />
              </div>

              <section id="contact" className="scroll-mt-24 rounded-2xl border border-border/70 bg-white p-5 text-center shadow-sm md:p-6">
                <h2 className="text-lg font-bold text-[#1F2937]">{t("contact.title")}</h2>
                <p className="mx-auto mt-2 max-w-2xl text-sm leading-7 text-[#6B7280]">
                  {t("contact.description")}
                </p>
              </section>
            </div>
          ) : (
            <div className="flex justify-center">
              <LocationForm shippingType={shippingType} onBack={handleBackToSelection} />
            </div>
          )}
        </div>
      </section>

      <Footer />
    </div>
  );
};

const Hero = ({ direction }: { direction: "rtl" | "ltr" }) => {
  const { t } = useI18n();
  const arrowClass = direction === "rtl" ? "" : "rotate-180";

  return (
    <section id="about" className="scroll-mt-24 overflow-hidden rounded-3xl border border-primary/10 bg-white px-5 py-9 shadow-sm md:px-10 md:py-12">
      <div className="grid items-center gap-10 lg:grid-cols-[1.15fr_0.85fr] lg:gap-14">
        <div className={direction === "rtl" ? "text-right" : "text-left"}>
          <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary">
            <Sparkles className="h-4 w-4" />
            {t("hero.newEyebrow")}
          </div>
          <h1 className="mt-5 text-3xl font-bold leading-[1.35] text-[#172033] md:text-5xl md:leading-[1.25]">
            {t("hero.newTitle")}
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-8 text-[#667085] md:text-lg">
            {t("hero.newDescription")}
          </p>
          <div className="mt-7 flex flex-col gap-3 sm:flex-row">
            <Button size="lg" className="h-12 px-6" asChild>
              <a href="#services">
                <Truck className="h-4 w-4" />
                {t("hero.primaryCta")}
                <ArrowLeft className={`h-4 w-4 ${arrowClass}`} />
              </a>
            </Button>
            <Button size="lg" variant="outline" className="h-12 px-6" asChild>
              <a href="#tracking">
                <Search className="h-4 w-4" />
                {t("hero.secondaryCta")}
              </a>
            </Button>
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-md">
          <div className="absolute -inset-4 rounded-[2rem] bg-primary/5 blur-2xl" />
          <div className="relative rounded-2xl border border-border/70 bg-[#FCFCFD] p-5 shadow-md md:p-6">
            <div className="flex items-start justify-between gap-4 border-b border-border/70 pb-4">
              <div>
                <p className="text-xs text-muted-foreground">{t("hero.sampleLabel")}</p>
                <p className="mt-1 font-bold text-[#1F2937]" dir="ltr">SR-10234</p>
              </div>
              <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
                {t("hero.sampleStatus")}
              </span>
            </div>
            <div className="mt-5 space-y-0">
              {["hero.statusRegistered", "hero.statusAssigned", "hero.statusContacted", "hero.statusQuoted"].map((key, index) => (
                <div key={key} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <div className={`flex h-7 w-7 items-center justify-center rounded-full ${index < 2 ? "bg-primary text-white" : "border-2 border-border bg-white text-muted-foreground"}`}>
                      {index < 2 ? <Check className="h-4 w-4" /> : <Clock3 className="h-3.5 w-3.5" />}
                    </div>
                    {index < 3 && <div className={`h-8 w-px ${index < 1 ? "bg-primary/25" : "bg-border"}`} />}
                  </div>
                  <div className="pt-1 text-sm font-medium text-[#344054]">{t(key)}</div>
                </div>
              ))}
              <div className="mt-1 flex items-center gap-3 text-xs font-semibold text-primary">
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10">+3</div>
                <span>{t("hero.moreSteps")}</span>
              </div>
            </div>
            <div className="mt-5 flex items-center gap-2 rounded-xl bg-primary/5 p-3 text-xs leading-6 text-primary">
              <Eye className="h-4 w-4 shrink-0" />
              {t("hero.sampleHint")}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

const WorkflowSection = () => {
  const { t } = useI18n();
  const desktopPlacements = ["", "", "", "", "lg:col-start-2", "lg:col-start-4", "lg:col-start-6"];
  const steps = [
    { icon: FileText, title: "workflow.step1.title", description: "workflow.step1.description" },
    { icon: UserRoundCheck, title: "workflow.step2.title", description: "workflow.step2.description" },
    { icon: PhoneCall, title: "workflow.step3.title", description: "workflow.step3.description" },
    { icon: ClipboardCheck, title: "workflow.step4.title", description: "workflow.step4.description" },
    { icon: FileSignature, title: "workflow.step5.title", description: "workflow.step5.description" },
    { icon: PackageCheck, title: "workflow.step6.title", description: "workflow.step6.description" },
    { icon: MapPinned, title: "workflow.step7.title", description: "workflow.step7.description" },
  ];

  return (
    <section aria-labelledby="workflow-title">
      <div className="text-center">
        <p className="text-sm font-semibold text-primary">{t("workflow.eyebrow")}</p>
        <h2 id="workflow-title" className="mt-2 text-2xl font-bold text-[#1F2937] md:text-3xl">{t("workflow.title")}</h2>
        <p className="mx-auto mt-3 max-w-2xl text-sm leading-7 text-[#667085]">{t("workflow.description")}</p>
      </div>
      <div className="relative mt-9 grid gap-4 md:grid-cols-2 md:gap-5 lg:grid-cols-8">
        {steps.map(({ icon: Icon, title, description }, index) => (
          <div key={title} className={`relative h-full rounded-2xl border border-border/60 bg-white p-5 shadow-sm lg:col-span-2 ${desktopPlacements[index]}`}>
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Icon className="h-6 w-6" />
              </div>
              <div>
                <span className="text-xs font-bold text-primary">{t("workflow.stepLabel")} {index + 1}</span>
                <h3 className="mt-1 font-bold text-[#1F2937]">{t(title)}</h3>
              </div>
            </div>
            <p className="mt-3 text-sm leading-7 text-[#667085]">{t(description)}</p>
          </div>
        ))}
      </div>
    </section>
  );
};

const ValueSection = () => {
  const { t } = useI18n();
  const values = [
    { icon: Sparkles, title: "value.fast.title", description: "value.fast.description" },
    { icon: UserRoundCheck, title: "value.expert.title", description: "value.expert.description" },
    { icon: Eye, title: "value.clear.title", description: "value.clear.description" },
    { icon: Database, title: "value.focused.title", description: "value.focused.description" },
  ];

  return (
    <section className="rounded-3xl bg-[#172033] px-5 py-8 text-white md:px-8 md:py-10" aria-labelledby="value-title">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-end">
        <div>
          <p className="text-sm font-semibold text-blue-300">{t("value.eyebrow")}</p>
          <h2 id="value-title" className="mt-2 text-2xl font-bold md:text-3xl">{t("value.title")}</h2>
        </div>
        <p className="max-w-lg text-sm leading-7 text-slate-300">{t("value.description")}</p>
      </div>
      <div className="mt-8 grid gap-x-8 gap-y-6 sm:grid-cols-2 lg:grid-cols-4">
        {values.map(({ icon: Icon, title, description }) => (
          <div key={title} className="flex gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/10 text-blue-300">
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold">{t(title)}</h3>
              <p className="mt-1 text-xs leading-6 text-slate-300">{t(description)}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

const TrackingSection = ({
  trackingNumber,
  setTrackingNumber,
  onTrack,
  direction,
}: {
  trackingNumber: string;
  setTrackingNumber: (value: string) => void;
  onTrack: () => void;
  direction: "rtl" | "ltr";
}) => {
  const { t } = useI18n();
  const responsiveTextAlign = direction === "rtl" ? "sm:text-right" : "sm:text-left";

  return (
    <Card className="mx-auto w-full max-w-2xl border-border/70 bg-white shadow-sm">
      <CardContent className="p-5 sm:p-6">
        <div className={`mb-4 flex flex-col gap-2 text-center sm:flex-row sm:items-center sm:justify-between ${responsiveTextAlign}`}>
          <div>
            <h2 className="flex items-center justify-center gap-2 text-base font-semibold text-[#1F2937] sm:justify-start">
              <Search className="h-5 w-5 text-primary" />
              {t("tracking.title")}
            </h2>
            <p className="mt-1 text-sm leading-6 text-[#6B7280]">
              {t("tracking.description")}
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          <Input
            id="trackingNumber"
            aria-label={t("tracking.ariaLabel")}
            placeholder={t("tracking.placeholder")}
            value={trackingNumber}
            onChange={(e) => setTrackingNumber(e.target.value)}
            className={`h-11 min-w-0 flex-1 bg-white text-center ${responsiveTextAlign}`}
          />
          <Button onClick={onTrack} className="h-11 shrink-0 px-6" disabled={!trackingNumber.trim()}>
            <Search className="h-4 w-4" />
            {t("tracking.search")}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

const ShippingTypeSelector = ({ onSelect }: { onSelect: (type: "domestic" | "international") => void }) => {
  const { direction, t } = useI18n();
  const options = [
    {
      type: "domestic" as const,
      title: t("shipping.domestic.title"),
      description: t("shipping.domestic.description"),
      detail: t("shipping.domestic.detail"),
      icon: MapPin,
    },
    {
      type: "international" as const,
      title: t("shipping.international.title"),
      description: t("shipping.international.description"),
      detail: t("shipping.international.detail"),
      icon: Globe2,
    },
  ];

  return (
    <div className="mx-auto grid w-full max-w-[800px] grid-cols-1 gap-6 md:grid-cols-2">
      {options.map(({ type, title, description, detail, icon: Icon }) => (
        <Card key={type} className="h-full border-border/70 bg-white shadow-sm transition hover:shadow-md">
          <CardContent className="flex h-full flex-col items-center p-8 text-center">
            <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <Icon className="h-7 w-7" />
            </div>
            <h2 className="text-xl font-bold text-[#1F2937]">{title}</h2>
            <p className="mt-3 min-h-[48px] text-sm leading-6 text-[#6B7280]">{description}</p>
            <p className="mt-3 text-xs leading-5 text-[#6B7280]">{detail}</p>
            <Button className="mt-6 w-full" onClick={() => onSelect(type)}>
              {direction === "ltr" && <ArrowLeft className="h-4 w-4 rotate-180" />}
              <Truck className="h-4 w-4" />
              {t("shipping.submit")}
              {direction === "rtl" && <ArrowLeft className="h-4 w-4" />}
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

export default Index;
