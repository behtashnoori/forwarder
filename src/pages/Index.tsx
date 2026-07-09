import { useEffect, useState } from "react";
import Header from "@/components/Header";
import LocationForm from "@/components/LocationForm";
import Footer from "@/components/Footer";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowLeft, Globe2, MapPin, Search, Truck } from "lucide-react";
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
            <div className="space-y-7">
              <div id="about" className="scroll-mt-24 mx-auto max-w-3xl text-center">
                <h1 className="text-3xl font-bold tracking-normal text-[#1F2937] md:text-4xl">
                  {t("home.title")}
                </h1>
                <p className="mt-4 text-base leading-7 text-[#6B7280] md:text-lg">
                  {t("home.description")}
                </p>
              </div>

              <ShippingTypeSelector onSelect={handleShippingTypeSelect} />

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
