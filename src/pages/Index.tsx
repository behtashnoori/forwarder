import { useState } from "react";
import Header from "@/components/Header";
import Hero from "@/components/Hero";
import LocationForm from "@/components/LocationForm";
import Footer from "@/components/Footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Search, Package, User, ExternalLink } from "lucide-react";
import { useNavigate } from "react-router-dom";

const Index = () => {
  const [shippingType, setShippingType] = useState<"domestic" | "international" | null>(null);
  const [activeTab, setActiveTab] = useState("request");
  const [trackingNumber, setTrackingNumber] = useState("");
  const navigate = useNavigate();

  const handleShippingTypeSelect = (type: "domestic" | "international") => {
    setShippingType(type);
  };

  const handleBackToSelection = () => {
    setShippingType(null);
  };

  const handleTrackRequest = () => {
    if (!trackingNumber.trim()) {
      return;
    }
    
    // Extract ID from tracking number (SR000001 -> 1)
    const id = trackingNumber.replace('SR', '');
    const numericId = parseInt(id, 10);
    
    if (isNaN(numericId)) {
      return;
    }
    
    // Navigate to public tracking page
    navigate(`/customer/track/${numericId}`);
  };

  return (
    <div className="min-h-screen bg-gradient-background">
      <Header />
      <Hero />
      
      {/* Main Section */}
      <section className="py-16 px-4">
        <div className="container mx-auto max-w-4xl">
          <div className="text-center mb-8">
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-4">
              خدمات فورواردر
            </h2>
            <p className="text-muted-foreground text-base md:text-lg">
              درخواست ارسال مرسوله یا پیگیری درخواست‌های قبلی
            </p>
          </div>
          
          <div className="flex justify-center">
            {!shippingType ? (
              <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full max-w-2xl">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="request" className="flex items-center gap-2">
                    <Package className="w-4 h-4" />
                    درخواست ارسال
                  </TabsTrigger>
                  <TabsTrigger value="track" className="flex items-center gap-2">
                    <Search className="w-4 h-4" />
                    پیگیری درخواست
                  </TabsTrigger>
                </TabsList>
                
                <TabsContent value="request" className="mt-6">
                  <div className="text-center mb-6">
                    <h3 className="text-xl font-semibold text-foreground mb-2">
                      نوع ارسال خود را انتخاب کنید
                    </h3>
                  </div>
                  <ShippingTypeSelector onSelect={handleShippingTypeSelect} />
                </TabsContent>
                
                <TabsContent value="track" className="mt-6">
                  <TrackingSection 
                    trackingNumber={trackingNumber}
                    setTrackingNumber={setTrackingNumber}
                    onTrack={handleTrackRequest}
                    onSwitchToRequest={() => setActiveTab('request')}
                  />
                </TabsContent>
              </Tabs>
            ) : (
              <LocationForm 
                shippingType={shippingType} 
                onBack={handleBackToSelection}
              />
            )}
          </div>
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
  onSwitchToRequest
}: { 
  trackingNumber: string;
  setTrackingNumber: (value: string) => void;
  onTrack: () => void;
  onSwitchToRequest: () => void;
}) => {
  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="w-5 h-5" />
          پیگیری درخواست
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="trackingNumber" className="text-sm font-medium">
            شماره پیگیری
          </label>
          <Input
            id="trackingNumber"
            placeholder="مثال: SR000001"
            value={trackingNumber}
            onChange={(e) => setTrackingNumber(e.target.value)}
            className="text-center"
          />
        </div>
        
        <Button 
          onClick={onTrack}
          className="w-full"
          disabled={!trackingNumber.trim()}
        >
          <Search className="w-4 h-4 ml-2" />
          پیگیری درخواست
        </Button>
        
        <div className="bg-blue-50 dark:bg-blue-950/20 p-4 rounded-lg">
          <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
            برای پیگیری کامل نیاز به ثبت‌نام دارید:
          </h4>
          <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
            <li>• مشاهده جزئیات کامل درخواست</li>
            <li>• ردیابی مراحل کار</li>
            <li>• ارتباط با کارشناس مربوطه</li>
            <li>• دریافت امتیاز و تخفیفات</li>
          </ul>
        </div>
        
        <div className="text-center">
          <p className="text-sm text-muted-foreground mb-2">
            شماره پیگیری خود را ندارید؟
          </p>
          <Button 
            variant="outline" 
            size="sm"
            onClick={onSwitchToRequest}
          >
            <User className="w-4 h-4 ml-2" />
            ثبت درخواست جدید
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

const ShippingTypeSelector = ({ onSelect }: { onSelect: (type: "domestic" | "international") => void }) => {
  return (
    <div className="w-full max-w-md space-y-6">
      {/* Domestic Shipping Option */}
      <div 
        onClick={() => onSelect("domestic")}
        className="bg-gradient-card shadow-lg border-0 rounded-lg p-6 cursor-pointer hover:shadow-xl transition-all duration-200 hover:scale-105"
      >
        <div className="text-center">
          <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <h3 className="text-xl font-bold text-foreground mb-2">حمل داخلی</h3>
          <p className="text-muted-foreground text-sm mb-4">
            ارسال مرسوله در داخل کشور
          </p>
          <div className="text-xs text-muted-foreground">
            مبدا و مقصد در استان‌های ایران
          </div>
        </div>
      </div>

      {/* International Shipping Option */}
      <div 
        onClick={() => onSelect("international")}
        className="bg-gradient-card shadow-lg border-0 rounded-lg p-6 cursor-pointer hover:shadow-xl transition-all duration-200 hover:scale-105"
      >
        <div className="text-center">
          <div className="w-16 h-16 bg-secondary/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-xl font-bold text-foreground mb-2">حمل بین‌المللی</h3>
          <p className="text-muted-foreground text-sm mb-4">
            ارسال مرسوله به خارج از کشور
          </p>
          <div className="text-xs text-muted-foreground">
            مبدا یا مقصد در کشورهای دیگر
          </div>
        </div>
      </div>
    </div>
  );
};

export default Index;
