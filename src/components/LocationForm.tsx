import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, MapPin, Send, CheckCircle2, Phone, Truck } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import {
  City,
  County,
  Province,
  fetchCities,
  fetchCounties,
  fetchProvinces,
  submitShipmentRequest,
} from "@/lib/api";

interface LocationFormData {
  originProvince: string;
  originCounty: string;
  originCity: string;
  destinationProvince: string;
  destinationCounty: string;
  destinationCity: string;
  phoneNumber: string;
  transportMethod: string;
}

const LocationForm = () => {
  const { toast } = useToast();
  const [provinces, setProvinces] = useState<Province[]>([]);
  const [originCounties, setOriginCounties] = useState<County[]>([]);
  const [destinationCounties, setDestinationCounties] = useState<County[]>([]);
  const [originCities, setOriginCities] = useState<City[]>([]);
  const [destinationCities, setDestinationCities] = useState<City[]>([]);
  const [isLoadingProvinces, setIsLoadingProvinces] = useState(false);
  const [isLoadingOriginCounties, setIsLoadingOriginCounties] = useState(false);
  const [isLoadingDestinationCounties, setIsLoadingDestinationCounties] = useState(false);
  const [isLoadingOriginCities, setIsLoadingOriginCities] = useState(false);
  const [isLoadingDestinationCities, setIsLoadingDestinationCities] = useState(false);
  const [formData, setFormData] = useState<LocationFormData>({
    originProvince: "",
    originCounty: "",
    originCity: "",
    destinationProvince: "",
    destinationCounty: "",
    destinationCity: "",
    phoneNumber: "",
    transportMethod: "",
  });
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let active = true;

    const loadProvinces = async () => {
      setIsLoadingProvinces(true);
      try {
        const data = await fetchProvinces();
        if (active) {
          setProvinces(data);
        }
      } catch (error) {
        if (active) {
          toast({
            title: "خطا در دریافت استان‌ها",
            description: error instanceof Error ? error.message : "دریافت اطلاعات استان‌ها با خطا مواجه شد.",
            variant: "destructive",
          });
        }
      } finally {
        if (active) {
          setIsLoadingProvinces(false);
        }
      }
    };

    loadProvinces();

    return () => {
      active = false;
    };
  }, [toast]);

  useEffect(() => {
    let active = true;
    if (!formData.originProvince) {
      setOriginCounties([]);
      setOriginCities([]);
      setIsLoadingOriginCounties(false);
      return () => {
        active = false;
      };
    }

    const provinceId = Number(formData.originProvince);
    setIsLoadingOriginCounties(true);
    setOriginCounties([]);
    setOriginCities([]);

    const loadCounties = async () => {
      try {
        const data = await fetchCounties(provinceId);
        if (active) {
          setOriginCounties(data);
        }
      } catch (error) {
        if (active) {
          toast({
            title: "خطا در دریافت شهرستان‌های مبدا",
            description: error instanceof Error ? error.message : "دریافت شهرستان‌ها با خطا مواجه شد.",
            variant: "destructive",
          });
        }
      } finally {
        if (active) {
          setIsLoadingOriginCounties(false);
        }
      }
    };

    loadCounties();

    return () => {
      active = false;
    };
  }, [formData.originProvince, toast]);

  useEffect(() => {
    let active = true;
    if (!formData.destinationProvince) {
      setDestinationCounties([]);
      setDestinationCities([]);
      setIsLoadingDestinationCounties(false);
      return () => {
        active = false;
      };
    }

    const provinceId = Number(formData.destinationProvince);
    setIsLoadingDestinationCounties(true);
    setDestinationCounties([]);
    setDestinationCities([]);

    const loadCounties = async () => {
      try {
        const data = await fetchCounties(provinceId);
        if (active) {
          setDestinationCounties(data);
        }
      } catch (error) {
        if (active) {
          toast({
            title: "خطا در دریافت شهرستان‌های مقصد",
            description: error instanceof Error ? error.message : "دریافت شهرستان‌ها با خطا مواجه شد.",
            variant: "destructive",
          });
        }
      } finally {
        if (active) {
          setIsLoadingDestinationCounties(false);
        }
      }
    };

    loadCounties();

    return () => {
      active = false;
    };
  }, [formData.destinationProvince, toast]);

  useEffect(() => {
    let active = true;
    if (!formData.originCounty) {
      setOriginCities([]);
      setIsLoadingOriginCities(false);
      return () => {
        active = false;
      };
    }

    const countyId = Number(formData.originCounty);
    setIsLoadingOriginCities(true);
    setOriginCities([]);

    const loadCities = async () => {
      try {
        const data = await fetchCities(countyId);
        if (active) {
          setOriginCities(data);
        }
      } catch (error) {
        if (active) {
          toast({
            title: "خطا در دریافت شهرهای مبدا",
            description: error instanceof Error ? error.message : "دریافت شهرها با خطا مواجه شد.",
            variant: "destructive",
          });
        }
      } finally {
        if (active) {
          setIsLoadingOriginCities(false);
        }
      }
    };

    loadCities();

    return () => {
      active = false;
    };
  }, [formData.originCounty, toast]);

  useEffect(() => {
    let active = true;
    if (!formData.destinationCounty) {
      setDestinationCities([]);
      setIsLoadingDestinationCities(false);
      return () => {
        active = false;
      };
    }

    const countyId = Number(formData.destinationCounty);
    setIsLoadingDestinationCities(true);
    setDestinationCities([]);

    const loadCities = async () => {
      try {
        const data = await fetchCities(countyId);
        if (active) {
          setDestinationCities(data);
        }
      } catch (error) {
        if (active) {
          toast({
            title: "خطا در دریافت شهرهای مقصد",
            description: error instanceof Error ? error.message : "دریافت شهرها با خطا مواجه شد.",
            variant: "destructive",
          });
        }
      } finally {
        if (active) {
          setIsLoadingDestinationCities(false);
        }
      }
    };

    loadCities();

    return () => {
      active = false;
    };
  }, [formData.destinationCounty, toast]);

  const provinceOptions = useMemo(
    () => [...provinces].sort((a, b) => a.name.localeCompare(b.name)),
    [provinces],
  );
  const originCountyOptions = useMemo(
    () => [...originCounties].sort((a, b) => a.name.localeCompare(b.name)),
    [originCounties],
  );
  const destinationCountyOptions = useMemo(
    () => [...destinationCounties].sort((a, b) => a.name.localeCompare(b.name)),
    [destinationCounties],
  );
  const originCityOptions = useMemo(
    () => [...originCities].sort((a, b) => a.name.localeCompare(b.name)),
    [originCities],
  );
  const destinationCityOptions = useMemo(
    () => [...destinationCities].sort((a, b) => a.name.localeCompare(b.name)),
    [destinationCities],
  );

  const handleSubmit = async () => {
    if (!formData.originProvince || !formData.originCounty || !formData.originCity ||
        !formData.destinationProvince || !formData.destinationCounty || !formData.destinationCity ||
        !formData.phoneNumber || !formData.transportMethod) {
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

    setIsSubmitting(true);

    try {
      await submitShipmentRequest({
        origin_province_id: Number(formData.originProvince),
        origin_county_id: Number(formData.originCounty),
        origin_city_id: Number(formData.originCity),
        dest_province_id: Number(formData.destinationProvince),
        dest_county_id: Number(formData.destinationCounty),
        dest_city_id: Number(formData.destinationCity),
        contact_phone: formData.phoneNumber,
      });

      setIsSubmitted(true);
      toast({
        title: "درخواست ثبت شد",
        description: "کارشناس ما ظرف ۲ ساعت با شما تماس خواهد گرفت",
      });
    } catch (error) {
      toast({
        title: "ثبت درخواست ناموفق بود",
        description: error instanceof Error ? error.message : "خطایی در ثبت درخواست رخ داد.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
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
      transportMethod: "",
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
              disabled={isLoadingProvinces && provinceOptions.length === 0}
            >
              <SelectTrigger>
                <SelectValue placeholder={isLoadingProvinces ? "در حال بارگذاری..." : "انتخاب استان"} />
              </SelectTrigger>
              <SelectContent>
                {provinceOptions.map((province) => (
                  <SelectItem key={province.id} value={province.id.toString()}>
                    {province.name}
                  </SelectItem>
                ))}
                {provinceOptions.length === 0 && !isLoadingProvinces && (
                  <SelectItem value="no-origin-province" disabled>
                    استان موجود نیست
                  </SelectItem>
                )}
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
              disabled={!formData.originProvince || isLoadingOriginCounties}
            >
              <SelectTrigger>
                <SelectValue
                  placeholder={
                    !formData.originProvince
                      ? "ابتدا استان را انتخاب کنید"
                      : isLoadingOriginCounties
                        ? "در حال بارگذاری..."
                        : "انتخاب شهرستان"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {originCountyOptions.map((county) => (
                  <SelectItem key={county.id} value={county.id.toString()}>
                    {county.name}
                  </SelectItem>
                ))}
                {originCountyOptions.length === 0 && formData.originProvince && !isLoadingOriginCounties && (
                  <SelectItem value="no-origin-county" disabled>
                    شهرستانی یافت نشد
                  </SelectItem>
                )}
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
              disabled={!formData.originCounty || isLoadingOriginCities}
            >
              <SelectTrigger>
                <SelectValue
                  placeholder={
                    !formData.originCounty
                      ? "ابتدا شهرستان را انتخاب کنید"
                      : isLoadingOriginCities
                        ? "در حال بارگذاری..."
                        : "انتخاب شهر"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {originCityOptions.map((city) => (
                  <SelectItem key={city.id} value={city.id.toString()}>
                    {city.name}
                  </SelectItem>
                ))}
                {originCityOptions.length === 0 && formData.originCounty && !isLoadingOriginCities && (
                  <SelectItem value="no-origin-city" disabled>
                    شهری یافت نشد
                  </SelectItem>
                )}
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
              disabled={isLoadingProvinces && provinceOptions.length === 0}
            >
              <SelectTrigger>
                <SelectValue placeholder={isLoadingProvinces ? "در حال بارگذاری..." : "انتخاب استان"} />
              </SelectTrigger>
              <SelectContent>
                {provinceOptions.map((province) => (
                  <SelectItem key={province.id} value={province.id.toString()}>
                    {province.name}
                  </SelectItem>
                ))}
                {provinceOptions.length === 0 && !isLoadingProvinces && (
                  <SelectItem value="no-destination-province" disabled>
                    استان موجود نیست
                  </SelectItem>
                )}
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
              disabled={!formData.destinationProvince || isLoadingDestinationCounties}
            >
              <SelectTrigger>
                <SelectValue
                  placeholder={
                    !formData.destinationProvince
                      ? "ابتدا استان را انتخاب کنید"
                      : isLoadingDestinationCounties
                        ? "در حال بارگذاری..."
                        : "انتخاب شهرستان"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {destinationCountyOptions.map((county) => (
                  <SelectItem key={county.id} value={county.id.toString()}>
                    {county.name}
                  </SelectItem>
                ))}
                {destinationCountyOptions.length === 0 && formData.destinationProvince && !isLoadingDestinationCounties && (
                  <SelectItem value="no-destination-county" disabled>
                    شهرستانی یافت نشد
                  </SelectItem>
                )}
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
              disabled={!formData.destinationCounty || isLoadingDestinationCities}
            >
              <SelectTrigger>
                <SelectValue
                  placeholder={
                    !formData.destinationCounty
                      ? "ابتدا شهرستان را انتخاب کنید"
                      : isLoadingDestinationCities
                        ? "در حال بارگذاری..."
                        : "انتخاب شهر"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {destinationCityOptions.map((city) => (
                  <SelectItem key={city.id} value={city.id.toString()}>
                    {city.name}
                  </SelectItem>
                ))}
                {destinationCityOptions.length === 0 && formData.destinationCounty && !isLoadingDestinationCities && (
                  <SelectItem value="no-destination-city" disabled>
                    شهری یافت نشد
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Transport Method Section */}
        <div className="space-y-3">
          <Label htmlFor="transport" className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Truck className="w-4 h-4 text-primary" />
            روش حمل و نقل
          </Label>
          <Select
            value={formData.transportMethod}
            onValueChange={(value) => {
              setFormData({
                ...formData,
                transportMethod: value,
              });
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder="انتخاب روش حمل و نقل" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="road">جاده‌ای</SelectItem>
              <SelectItem value="rail">ریلی</SelectItem>
              <SelectItem value="sea">دریایی</SelectItem>
              <SelectItem value="combined">ترکیبی (جاده‌ای + ریلی)</SelectItem>
              <SelectItem value="road-sea">ترکیبی (جاده‌ای + دریایی)</SelectItem>
              <SelectItem value="rail-sea">ترکیبی (ریلی + دریایی)</SelectItem>
              <SelectItem value="multi-modal">چندوجهی (همه روش‌ها)</SelectItem>
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            کارشناس ما بهترین روش حمل را بر اساس انتخاب شما پیشنهاد خواهد داد
          </p>
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
          disabled={isSubmitting}
        >
          <Send className="w-4 h-4 ml-2" />
          {isSubmitting ? "در حال ارسال..." : "درخواست ارسال"}
        </Button>
      </CardContent>
    </Card>
  );
};

export default LocationForm;