import { useState } from "react";
import Header from "@/components/Header";
import LocationForm from "@/components/LocationForm";
import Footer from "@/components/Footer";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowLeft, Globe2, MapPin, Search, Truck } from "lucide-react";
import { useNavigate } from "react-router-dom";

const Index = () => {
  const [shippingType, setShippingType] = useState<"domestic" | "international" | null>(null);
  const [trackingNumber, setTrackingNumber] = useState("");
  const navigate = useNavigate();

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

      <section className="px-4 py-16 md:py-20">
        <div className="container mx-auto max-w-5xl">
          {!shippingType ? (
            <div className="space-y-10">
              <div className="mx-auto max-w-2xl text-center">
                <h1 className="text-3xl font-bold tracking-normal text-[#1F2937] md:text-4xl">
                  خدمات فوروارد
                </h1>
                <p className="mt-4 text-base leading-7 text-[#6B7280] md:text-lg">
                  نوع ارسال خود را انتخاب کنید
                </p>
              </div>

              <ShippingTypeSelector onSelect={handleShippingTypeSelect} />

              <TrackingSection
                trackingNumber={trackingNumber}
                setTrackingNumber={setTrackingNumber}
                onTrack={handleTrackRequest}
              />
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
}: {
  trackingNumber: string;
  setTrackingNumber: (value: string) => void;
  onTrack: () => void;
}) => {
  return (
    <Card className="mx-auto w-full max-w-2xl border-border/70 bg-white shadow-sm">
      <CardContent className="p-5 sm:p-6">
        <div className="mb-4 flex flex-col gap-2 text-center sm:flex-row sm:items-center sm:justify-between sm:text-right">
          <div>
            <h2 className="flex items-center justify-center gap-2 text-base font-semibold text-[#1F2937] sm:justify-start">
              <Search className="h-5 w-5 text-primary" />
              پیگیری درخواست
            </h2>
            <p className="mt-1 text-sm text-[#6B7280]">شماره پیگیری خود را وارد کنید.</p>
          </div>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          <Input
            id="trackingNumber"
            aria-label="شماره پیگیری"
            placeholder="مثال: SR-XXXXXX یا SR000001"
            value={trackingNumber}
            onChange={(e) => setTrackingNumber(e.target.value)}
            className="h-11 min-w-0 flex-1 bg-white text-center sm:text-right"
          />
          <Button onClick={onTrack} className="h-11 shrink-0 px-6" disabled={!trackingNumber.trim()}>
            <Search className="h-4 w-4" />
            جستجو
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

const ShippingTypeSelector = ({ onSelect }: { onSelect: (type: "domestic" | "international") => void }) => {
  const options = [
    {
      type: "domestic" as const,
      title: "حمل داخلی",
      description: "ارسال مرسوله در مسیرهای داخل کشور با ثبت سریع درخواست.",
      detail: "مناسب برای مبدا و مقصد در استان‌های ایران",
      icon: MapPin,
    },
    {
      type: "international" as const,
      title: "حمل بین‌المللی",
      description: "ثبت درخواست ارسال بین ایران و کشورهای دیگر.",
      detail: "مناسب برای مسیرهای واردات، صادرات و حمل خارجی",
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
              <Truck className="h-4 w-4" />
              درخواست ارسال
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

export default Index;
