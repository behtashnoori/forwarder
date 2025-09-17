import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, MapPin, Send, CheckCircle2, Phone } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

// Mock data - در واقعیت از API یا دیتابیس خواهد آمد
const provinces = [
  { id: 1, name: "تهران" },
  { id: 2, name: "اصفهان" },
  { id: 3, name: "فارس" },
  { id: 4, name: "خراسان رضوی" },
  { id: 5, name: "آذربایجان شرقی" },
];

const counties = {
  1: [{ id: 11, name: "تهران" }, { id: 12, name: "شمیرانات" }, { id: 13, name: "ری" }],
  2: [{ id: 21, name: "اصفهان" }, { id: 22, name: "کاشان" }, { id: 23, name: "نجف‌آباد" }],
  3: [{ id: 31, name: "شیراز" }, { id: 32, name: "مرودشت" }, { id: 33, name: "فسا" }],
  4: [{ id: 41, name: "مشهد" }, { id: 42, name: "نیشابور" }, { id: 43, name: "سبزوار" }],
  5: [{ id: 51, name: "تبریز" }, { id: 52, name: "مراغه" }, { id: 53, name: "اهر" }],
};

const cities = {
  11: [{ id: 111, name: "تهران" }, { id: 112, name: "شهریار" }],
  12: [{ id: 121, name: "شمیران" }, { id: 122, name: "تجریش" }],
  13: [{ id: 131, name: "ری" }, { id: 132, name: "ورامین" }],
  21: [{ id: 211, name: "اصفهان" }, { id: 212, name: "فولادشهر" }],
  22: [{ id: 221, name: "کاشان" }, { id: 222, name: "آران و بیدگل" }],
  23: [{ id: 231, name: "نجف‌آباد" }, { id: 232, name: "تیران" }],
  31: [{ id: 311, name: "شیراز" }, { id: 312, name: "صدرا" }],
  32: [{ id: 321, name: "مرودشت" }, { id: 322, name: "درودزن" }],
  33: [{ id: 331, name: "فسا" }, { id: 332, name: "قیر" }],
  41: [{ id: 411, name: "مشهد" }, { id: 412, name: "طوس" }],
  42: [{ id: 421, name: "نیشابور" }, { id: 422, name: "فیروزه" }],
  43: [{ id: 431, name: "سبزوار" }, { id: 432, name: "جوین" }],
  51: [{ id: 511, name: "تبریز" }, { id: 512, name: "آذرشهر" }],
  52: [{ id: 521, name: "مراغه" }, { id: 522, name: "بناب" }],
  53: [{ id: 531, name: "اهر" }, { id: 532, name: "هریس" }],
};

interface LocationFormData {
  originProvince: string;
  originCounty: string;
  originCity: string;
  destinationProvince: string;
  destinationCounty: string;
  destinationCity: string;
  phoneNumber: string;
}

const LocationForm = () => {
  const { toast } = useToast();
  const [formData, setFormData] = useState<LocationFormData>({
    originProvince: "",
    originCounty: "",
    originCity: "",
    destinationProvince: "",
    destinationCounty: "",
    destinationCity: "",
    phoneNumber: "",
  });
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = () => {
    if (!formData.originProvince || !formData.originCounty || !formData.originCity ||
        !formData.destinationProvince || !formData.destinationCounty || !formData.destinationCity ||
        !formData.phoneNumber) {
      toast({
        title: "خطا",
        description: "لطفاً همه فیلدها را تکمیل کنید",
        variant: "destructive",
      });
      return;
    }

    // Phone number validation
    const phoneRegex = /^09\d{9}$/;
    if (!phoneRegex.test(formData.phoneNumber)) {
      toast({
        title: "خطا",
        description: "شماره تماس باید با 09 شروع شده و 11 رقم باشد",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitted(true);
    toast({
      title: "درخواست ثبت شد",
      description: "کارشناس ما ظرف ۲ ساعت با شما تماس خواهد گرفت",
    });
  };

  const resetForm = () => {
    setFormData({
      originProvince: "",
      originCounty: "",
      originCity: "",
      destinationProvince: "",
      destinationCounty: "",
      destinationCity: "",
      phoneNumber: "",
    });
    setIsSubmitted(false);
  };

  if (isSubmitted) {
    return (
      <Card className="w-full max-w-md bg-gradient-card shadow-lg border-0">
        <CardContent className="p-6 text-center">
          <div className="mb-4">
            <CheckCircle2 className="w-16 h-16 text-secondary mx-auto" />
          </div>
          <h3 className="text-xl font-bold text-foreground mb-2">درخواست شما ثبت شد!</h3>
          <p className="text-muted-foreground mb-6">
            کارشناس ما ظرف ۲ ساعت با شما تماس خواهد گرفت و جزئیات ارسال را هماهنگ خواهد کرد.
          </p>
          <Button onClick={resetForm} variant="outline" className="w-full">
            ثبت درخواست جدید
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md bg-gradient-card shadow-lg border-0">
      <CardHeader className="text-center pb-4">
        <CardTitle className="text-xl font-bold flex items-center justify-center gap-2">
          <MapPin className="w-5 h-5 text-primary" />
          انتخاب مبدا و مقصد
        </CardTitle>
        <p className="text-muted-foreground text-sm">
          برای ارسال مرسوله خود، مبدا و مقصد را انتخاب کنید
        </p>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Origin Section */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-primary">
            <div className="w-3 h-3 bg-primary rounded-full"></div>
            مبدا ارسال
          </div>
          
          <div className="space-y-3 pr-5">
            <Select
              value={formData.originProvince}
              onValueChange={(value) => {
                setFormData({
                  ...formData,
                  originProvince: value,
                  originCounty: "",
                  originCity: "",
                });
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="انتخاب استان" />
              </SelectTrigger>
              <SelectContent>
                {provinces.map((province) => (
                  <SelectItem key={province.id} value={province.id.toString()}>
                    {province.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={formData.originCounty}
              onValueChange={(value) => {
                setFormData({
                  ...formData,
                  originCounty: value,
                  originCity: "",
                });
              }}
              disabled={!formData.originProvince}
            >
              <SelectTrigger>
                <SelectValue placeholder="انتخاب شهرستان" />
              </SelectTrigger>
              <SelectContent>
                {formData.originProvince && counties[parseInt(formData.originProvince)]?.map((county) => (
                  <SelectItem key={county.id} value={county.id.toString()}>
                    {county.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={formData.originCity}
              onValueChange={(value) => {
                setFormData({
                  ...formData,
                  originCity: value,
                });
              }}
              disabled={!formData.originCounty}
            >
              <SelectTrigger>
                <SelectValue placeholder="انتخاب شهر" />
              </SelectTrigger>
              <SelectContent>
                {formData.originCounty && cities[parseInt(formData.originCounty)]?.map((city) => (
                  <SelectItem key={city.id} value={city.id.toString()}>
                    {city.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Arrow */}
        <div className="flex justify-center">
          <div className="p-2 bg-accent rounded-full">
            <ArrowLeft className="w-4 h-4 text-muted-foreground rotate-90" />
          </div>
        </div>

        {/* Destination Section */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-secondary">
            <div className="w-3 h-3 bg-secondary rounded-full"></div>
            مقصد ارسال
          </div>
          
          <div className="space-y-3 pr-5">
            <Select
              value={formData.destinationProvince}
              onValueChange={(value) => {
                setFormData({
                  ...formData,
                  destinationProvince: value,
                  destinationCounty: "",
                  destinationCity: "",
                });
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="انتخاب استان" />
              </SelectTrigger>
              <SelectContent>
                {provinces.map((province) => (
                  <SelectItem key={province.id} value={province.id.toString()}>
                    {province.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={formData.destinationCounty}
              onValueChange={(value) => {
                setFormData({
                  ...formData,
                  destinationCounty: value,
                  destinationCity: "",
                });
              }}
              disabled={!formData.destinationProvince}
            >
              <SelectTrigger>
                <SelectValue placeholder="انتخاب شهرستان" />
              </SelectTrigger>
              <SelectContent>
                {formData.destinationProvince && counties[parseInt(formData.destinationProvince)]?.map((county) => (
                  <SelectItem key={county.id} value={county.id.toString()}>
                    {county.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={formData.destinationCity}
              onValueChange={(value) => {
                setFormData({
                  ...formData,
                  destinationCity: value,
                });
              }}
              disabled={!formData.destinationCounty}
            >
              <SelectTrigger>
                <SelectValue placeholder="انتخاب شهر" />
              </SelectTrigger>
              <SelectContent>
                {formData.destinationCounty && cities[parseInt(formData.destinationCounty)]?.map((city) => (
                  <SelectItem key={city.id} value={city.id.toString()}>
                    {city.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Phone Number Section */}
        <div className="space-y-3">
          <Label htmlFor="phone" className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Phone className="w-4 h-4 text-primary" />
            شماره تماس
          </Label>
          <Input
            id="phone"
            type="tel"
            placeholder="09123456789"
            value={formData.phoneNumber}
            onChange={(e) => {
              // Only allow numbers and limit to 11 digits
              const value = e.target.value.replace(/\D/g, '').slice(0, 11);
              setFormData({
                ...formData,
                phoneNumber: value,
              });
            }}
            className="text-left"
            dir="ltr"
          />
          <p className="text-xs text-muted-foreground">
            شماره موبایل خود را وارد کنید تا کارشناس با شما تماس بگیرد
          </p>
        </div>

        {/* Submit Button */}
        <Button 
          onClick={handleSubmit} 
          className="w-full bg-gradient-primary hover:shadow-primary font-medium"
          size="lg"
        >
          <Send className="w-4 h-4 ml-2" />
          درخواست ارسال
        </Button>
      </CardContent>
    </Card>
  );
};

export default LocationForm;