import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, MapPin, Send, CheckCircle2, Phone, Truck, Package, Calendar, Weight, DollarSign, FileText, ChevronDown, ChevronUp, ChevronLeft, ChevronRight, User, Copy } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import RequestConfirmation from "./RequestConfirmation";
import {
  City,
  County,
  Province,
  Country,
  InternationalCity,
  IranPort,
  BorderCustoms,
  RecommendedPort,
  TransportMethod,
  TransportMethodOptions,
  ShipmentRequestPayload,
  fetchCities,
  fetchCounties,
  fetchProvinces,
  fetchCountries,
  fetchInternationalCities,
  fetchIranPorts,
  fetchBorderCustoms,
  fetchRecommendedPorts,
  fetchTransportMethodOptions,
  submitShipmentRequest,
  buildIranDestinationPayload,
  isInternationalRouteComplete,
} from "@/lib/api";
import { useI18n } from "@/i18n";

interface LocationFormData {
  // Domestic shipping fields
  originProvince: string;
  originCounty: string;
  originCity: string;
  destinationProvince: string;
  destinationCounty: string;
  destinationCity: string;
  // International shipping fields
  originCountry: string;
  originCityInternational: string;
  originAddressInternational: string;
  destCountry: string;
  destCityInternational: string;
  destAddressInternational: string;
  // Iran destination point (for international shipping to Iran)
  // iranDestType selects how the in-Iran destination is named: port | customs | city
  iranDestType: "port" | "customs" | "city";
  iranEntryPort: string;        // port mode selection (iran_port id)
  iranDestCustomsOffice: string; // customs mode selection (customs_office id)
  iranDestCounty: string;        // city mode: county in the destination province
  iranDestCity: string;          // city mode: final delivery city (city id)
  iranEntryProvince: string;     // destination province: derived (port/customs) or chosen (city)
  // Common fields
  phoneNumber: string;
  // Customer details (optional)
  customerFirstName: string;
  customerLastName: string;
  transportMethod: string;  // Legacy field
  internationalTransportMethod: string;
  domesticTransportMethod: string;
  transportMethodPreference: string;
  // Cargo details (optional)
  cargoDescription: string;
  cargoWeight: string;
  cargoVolume: string;
  cargoValue: string;
  specialInstructions: string;
  pickupDate: string;
  deliveryDate: string;
}

interface LocationFormProps {
  shippingType: "domestic" | "international";
  onBack?: () => void;
}

const helperTextClass = "text-xs leading-6 text-muted-foreground";

const getTransportLabel = (method: TransportMethod, language: "fa" | "en") =>
  language === "fa" ? method.name_fa || method.name : method.name || method.name_fa;
const getTransportDescription = (method: TransportMethod, fallback: string) => method.description || fallback;
const RequiredAsterisk = () => <span className="text-red-600" aria-hidden="true">*</span>;

interface JalaliDate {
  year: number;
  month: number;
  day: number;
}

interface JalaliDateInputProps {
  id: string;
  label: string;
  selectLabel: string;
  nextMonthLabel: string;
  previousMonthLabel: string;
  clearLabel: string;
  value: string;
  onChange: (value: string) => void;
}

const jalaliMonthNames = [
  "فروردین",
  "اردیبهشت",
  "خرداد",
  "تیر",
  "مرداد",
  "شهریور",
  "مهر",
  "آبان",
  "آذر",
  "دی",
  "بهمن",
  "اسفند",
];

const jalaliWeekDays = ["ش", "ی", "د", "س", "چ", "پ", "ج"];
const padDatePart = (value: number) => String(value).padStart(2, "0");
const div = (a: number, b: number) => Math.trunc(a / b);

const formatGregorianDate = ({ year, month, day }: JalaliDate) =>
  `${year}-${padDatePart(month)}-${padDatePart(day)}`;

const formatJalaliDate = ({ year, month, day }: JalaliDate) =>
  `${year}/${padDatePart(month)}/${padDatePart(day)}`;

const parseGregorianDate = (value: string) => {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);

  if (!match) {
    return null;
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);

  if (!year || month < 1 || month > 12 || day < 1 || day > 31) {
    return null;
  }

  return { year, month, day };
};

const gregorianToJalali = (gy: number, gm: number, gd: number): JalaliDate => {
  const gDayMonth = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
  let jy;

  if (gy > 1600) {
    jy = 979;
    gy -= 1600;
  } else {
    jy = 0;
    gy -= 621;
  }

  const gy2 = gm > 2 ? gy + 1 : gy;
  let days =
    365 * gy +
    div(gy2 + 3, 4) -
    div(gy2 + 99, 100) +
    div(gy2 + 399, 400) -
    80 +
    gd +
    gDayMonth[gm - 1];

  jy += 33 * div(days, 12053);
  days %= 12053;
  jy += 4 * div(days, 1461);
  days %= 1461;

  if (days > 365) {
    jy += div(days - 1, 365);
    days = (days - 1) % 365;
  }

  const jm = days < 186 ? 1 + div(days, 31) : 7 + div(days - 186, 30);
  const jd = 1 + (days < 186 ? days % 31 : (days - 186) % 30);

  return { year: jy, month: jm, day: jd };
};

const jalaliToGregorian = (jy: number, jm: number, jd: number): JalaliDate => {
  jy += 1595;
  let days =
    -355668 +
    365 * jy +
    div(jy, 33) * 8 +
    div((jy % 33) + 3, 4) +
    jd +
    (jm < 7 ? (jm - 1) * 31 : (jm - 7) * 30 + 186);

  let gy = 400 * div(days, 146097);
  days %= 146097;

  if (days > 36524) {
    gy += 100 * div(--days, 36524);
    days %= 36524;

    if (days >= 365) {
      days++;
    }
  }

  gy += 4 * div(days, 1461);
  days %= 1461;

  if (days > 365) {
    gy += div(days - 1, 365);
    days = (days - 1) % 365;
  }

  let gd = days + 1;
  const leap = (gy % 4 === 0 && gy % 100 !== 0) || gy % 400 === 0;
  const gregorianMonthLengths = [0, 31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  let gm = 0;

  for (gm = 1; gm <= 12 && gd > gregorianMonthLengths[gm]; gm++) {
    gd -= gregorianMonthLengths[gm];
  }

  return { year: gy, month: gm, day: gd };
};

const getTodayJalali = () => {
  const today = new Date();
  return gregorianToJalali(today.getFullYear(), today.getMonth() + 1, today.getDate());
};

const getJalaliMonthLength = (year: number, month: number) => {
  if (month <= 6) {
    return 31;
  }

  if (month <= 11) {
    return 30;
  }

  const start = jalaliToGregorian(year, 1, 1);
  const nextStart = jalaliToGregorian(year + 1, 1, 1);
  const startTime = Date.UTC(start.year, start.month - 1, start.day);
  const nextStartTime = Date.UTC(nextStart.year, nextStart.month - 1, nextStart.day);

  return (nextStartTime - startTime) / 86400000 === 366 ? 30 : 29;
};

const getJalaliFromGregorianValue = (value: string) => {
  const parsedValue = parseGregorianDate(value);

  if (!parsedValue) {
    return null;
  }

  return gregorianToJalali(parsedValue.year, parsedValue.month, parsedValue.day);
};

const JalaliDateInput = ({
  clearLabel,
  id,
  label,
  nextMonthLabel,
  onChange,
  previousMonthLabel,
  selectLabel,
  value,
}: JalaliDateInputProps) => {
  const [open, setOpen] = useState(false);
  const selectedDate = getJalaliFromGregorianValue(value);
  const initialViewDate = selectedDate ?? getTodayJalali();
  const [viewMonth, setViewMonth] = useState({ year: initialViewDate.year, month: initialViewDate.month });
  const monthLength = getJalaliMonthLength(viewMonth.year, viewMonth.month);
  const firstDayGregorian = jalaliToGregorian(viewMonth.year, viewMonth.month, 1);
  const firstDayDate = new Date(firstDayGregorian.year, firstDayGregorian.month - 1, firstDayGregorian.day);
  const firstDayOffset = (firstDayDate.getDay() + 1) % 7;

  useEffect(() => {
    if (!open) {
      return;
    }

    const nextViewDate = getJalaliFromGregorianValue(value) ?? getTodayJalali();
    setViewMonth({ year: nextViewDate.year, month: nextViewDate.month });
  }, [open, value]);

  const changeMonth = (direction: -1 | 1) => {
    setViewMonth((current) => {
      const nextMonth = current.month + direction;

      if (nextMonth < 1) {
        return { year: current.year - 1, month: 12 };
      }

      if (nextMonth > 12) {
        return { year: current.year + 1, month: 1 };
      }

      return { ...current, month: nextMonth };
    });
  };

  const handleSelectDay = (day: number) => {
    const gregorianDate = jalaliToGregorian(viewMonth.year, viewMonth.month, day);
    onChange(formatGregorianDate(gregorianDate));
    setOpen(false);
  };

  return (
    <div className="space-y-2">
      <Label htmlFor={id} className="flex items-center gap-2 text-sm font-medium">
        <Calendar className="w-4 h-4 text-muted-foreground" />
        {label}
      </Label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            id={id}
            type="button"
            variant="outline"
            className="h-10 w-full justify-between text-right font-normal"
            dir="rtl"
          >
            <span className={selectedDate ? "text-foreground" : "text-muted-foreground"}>
              {selectedDate ? formatJalaliDate(selectedDate) : selectLabel}
            </span>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-72 p-3 text-right" align="end" dir="rtl">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Button type="button" variant="ghost" size="icon" onClick={() => changeMonth(1)} aria-label={nextMonthLabel}>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <div className="text-sm font-medium">
                {jalaliMonthNames[viewMonth.month - 1]} {viewMonth.year}
              </div>
              <Button type="button" variant="ghost" size="icon" onClick={() => changeMonth(-1)} aria-label={previousMonthLabel}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
            </div>

            <div className="grid grid-cols-7 gap-1 text-center text-xs text-muted-foreground">
              {jalaliWeekDays.map((dayName) => (
                <div key={dayName} className="h-7 leading-7">
                  {dayName}
                </div>
              ))}
            </div>

            <div className="grid grid-cols-7 gap-1">
              {Array.from({ length: firstDayOffset }).map((_, index) => (
                <div key={`empty-${index}`} className="h-8" />
              ))}
              {Array.from({ length: monthLength }).map((_, index) => {
                const day = index + 1;
                const isSelected =
                  selectedDate?.year === viewMonth.year &&
                  selectedDate.month === viewMonth.month &&
                  selectedDate.day === day;

                return (
                  <Button
                    key={day}
                    type="button"
                    variant={isSelected ? "default" : "ghost"}
                    size="icon"
                    className="h-8 w-8 text-sm"
                    onClick={() => handleSelectDay(day)}
                  >
                    {day}
                  </Button>
                );
              })}
            </div>

            {value && (
              <Button type="button" variant="ghost" size="sm" className="w-full" onClick={() => onChange("")}>
                {clearLabel}
              </Button>
            )}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
};

const LocationForm = ({ shippingType, onBack }: LocationFormProps) => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const { language, t, tf } = useI18n();
  const [provinces, setProvinces] = useState<Province[]>([]);
  const [originCounties, setOriginCounties] = useState<County[]>([]);
  const [destinationCounties, setDestinationCounties] = useState<County[]>([]);
  const [originCities, setOriginCities] = useState<City[]>([]);
  const [destinationCities, setDestinationCities] = useState<City[]>([]);
  const [countries, setCountries] = useState<Country[]>([]);
  const [originInternationalCities, setOriginInternationalCities] = useState<InternationalCity[]>([]);
  const [destinationInternationalCities, setDestinationInternationalCities] = useState<InternationalCity[]>([]);
  const [iranPorts, setIranPorts] = useState<IranPort[]>([]);
  const [borderCustoms, setBorderCustoms] = useState<BorderCustoms[]>([]);
  const [iranDestCounties, setIranDestCounties] = useState<County[]>([]);
  const [iranDestCities, setIranDestCities] = useState<City[]>([]);
  const [recommendedPorts, setRecommendedPorts] = useState<RecommendedPort[]>([]);
  const [transportMethodOptions, setTransportMethodOptions] = useState<TransportMethodOptions | null>(null);
  const [isLoadingProvinces, setIsLoadingProvinces] = useState(false);
  const [isLoadingOriginCounties, setIsLoadingOriginCounties] = useState(false);
  const [isLoadingDestinationCounties, setIsLoadingDestinationCounties] = useState(false);
  const [isLoadingOriginCities, setIsLoadingOriginCities] = useState(false);
  const [isLoadingDestinationCities, setIsLoadingDestinationCities] = useState(false);
  const [isLoadingCountries, setIsLoadingCountries] = useState(false);
  const [isLoadingOriginInternationalCities, setIsLoadingOriginInternationalCities] = useState(false);
  const [isLoadingDestinationInternationalCities, setIsLoadingDestinationInternationalCities] = useState(false);
  const [isLoadingIranPorts, setIsLoadingIranPorts] = useState(false);
  const [isLoadingBorderCustoms, setIsLoadingBorderCustoms] = useState(false);
  const [isLoadingIranDestCounties, setIsLoadingIranDestCounties] = useState(false);
  const [isLoadingIranDestCities, setIsLoadingIranDestCities] = useState(false);
  const [isLoadingRecommendedPorts, setIsLoadingRecommendedPorts] = useState(false);
  const [formData, setFormData] = useState<LocationFormData>({
    // Domestic shipping fields
    originProvince: "",
    originCounty: "",
    originCity: "",
    destinationProvince: "",
    destinationCounty: "",
    destinationCity: "",
    // International shipping fields
    originCountry: "",
    originCityInternational: "",
    originAddressInternational: "",
    destCountry: "",
    destCityInternational: "",
    destAddressInternational: "",
    // Iran destination point fields (default to final delivery city)
    iranDestType: "city",
    iranEntryPort: "",
    iranDestCustomsOffice: "",
    iranDestCounty: "",
    iranDestCity: "",
    iranEntryProvince: "",
    // Common fields
    phoneNumber: "",
    customerFirstName: "",
    customerLastName: "",
    transportMethod: "",  // Legacy field
    internationalTransportMethod: "",
    domesticTransportMethod: "",
    transportMethodPreference: "customer_choice",
    cargoDescription: "",
    cargoWeight: "",
    cargoVolume: "",
    cargoValue: "",
    specialInstructions: "",
    pickupDate: "",
    deliveryDate: "",
  });
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showCargoDetails, setShowCargoDetails] = useState(false);
  const [showOriginLocationDetails, setShowOriginLocationDetails] = useState(false);
  const [showDestinationLocationDetails, setShowDestinationLocationDetails] = useState(false);
  const [submittedTrackingCode, setSubmittedTrackingCode] = useState<string | null>(null);

  // Fetch transport method options on component mount
  useEffect(() => {
    const fetchTransportOptions = async () => {
      try {
        const options = await fetchTransportMethodOptions();
        setTransportMethodOptions(options);
      } catch (error) {
        console.error("Error fetching transport method options:", error);
        toast({
          title: t("common.error"),
          description: t("requestForm.loadBaseError"),
          variant: "destructive",
        });
      }
    };

    fetchTransportOptions();
  }, [t, toast]);

  // Legacy transport method options (fallback)
  const transportMethods = [
    { value: "road", label: "حمل زمینی (جاده‌ای)" },
    { value: "air", label: "حمل هوایی" },
    { value: "sea", label: "حمل دریایی" },
    { value: "rail", label: "حمل ریلی" },
  ];

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
          console.error("Error fetching provinces:", error);
          toast({
          title: t("common.error"),
          description: t("requestForm.loadBaseError"),
            variant: "destructive",
          });
        }
      } finally {
        if (active) {
          setIsLoadingProvinces(false);
        }
      }
    };

    const loadCountries = async () => {
      setIsLoadingCountries(true);
      try {
        const data = await fetchCountries();
        if (active) {
          setCountries(data);
        }
      } catch (error) {
        if (active) {
          toast({
            title: t("requestForm.loadCountriesErrorTitle"),
            description: error instanceof Error ? error.message : t("requestForm.loadCountriesError"),
            variant: "destructive",
          });
        }
      } finally {
        if (active) {
          setIsLoadingCountries(false);
        }
      }
    };

    const loadIranPorts = async () => {
      setIsLoadingIranPorts(true);
      try {
        const data = await fetchIranPorts();
        if (active) {
          setIranPorts(data);
        }
      } catch (error) {
        if (active) {
          toast({
            title: t("requestForm.loadIranPortsErrorTitle"),
            description: error instanceof Error ? error.message : t("requestForm.loadIranPortsError"),
            variant: "destructive",
          });
        }
      } finally {
        if (active) {
          setIsLoadingIranPorts(false);
        }
      }
    };

    const loadBorderCustoms = async () => {
      setIsLoadingBorderCustoms(true);
      try {
        const data = await fetchBorderCustoms();
        if (active) {
          setBorderCustoms(data);
        }
      } catch (error) {
        if (active) {
          console.error("Error fetching border customs:", error);
        }
      } finally {
        if (active) {
          setIsLoadingBorderCustoms(false);
        }
      }
    };

    if (shippingType === "domestic") {
      loadProvinces();
    } else {
      loadCountries();
      loadProvinces(); // Needed for the Iran destination province/city cascade
      loadIranPorts(); // Load Iran ports for international shipping
      loadBorderCustoms(); // Load border customs offices for Iran destination
    }

    return () => {
      active = false;
    };
  }, [t, toast, shippingType]);

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
            title: t("requestForm.loadOriginCountiesErrorTitle"),
            description: error instanceof Error ? error.message : t("requestForm.loadCountiesError"),
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
  }, [formData.originProvince, t, toast]);

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
            title: t("requestForm.loadDestinationCountiesErrorTitle"),
            description: error instanceof Error ? error.message : t("requestForm.loadCountiesError"),
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
  }, [formData.destinationProvince, t, toast]);

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
            title: t("requestForm.loadOriginCitiesErrorTitle"),
            description: error instanceof Error ? error.message : t("requestForm.loadCitiesError"),
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
  }, [formData.originCounty, t, toast]);

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
            title: t("requestForm.loadDestinationCitiesErrorTitle"),
            description: error instanceof Error ? error.message : t("requestForm.loadCitiesError"),
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
  }, [formData.destinationCounty, t, toast]);

  // Load international cities for origin country
  useEffect(() => {
    let active = true;
    if (!formData.originCountry) {
      setOriginInternationalCities([]);
      setIsLoadingOriginInternationalCities(false);
      return () => {
        active = false;
      };
    }

    const countryId = Number(formData.originCountry);
    setIsLoadingOriginInternationalCities(true);
    setOriginInternationalCities([]);

    const loadCities = async () => {
      try {
        const data = await fetchInternationalCities(countryId);
        if (active) {
          setOriginInternationalCities(data);
        }
      } catch (error) {
        if (active) {
          toast({
            title: t("requestForm.loadOriginCitiesErrorTitle"),
            description: error instanceof Error ? error.message : t("requestForm.loadCitiesError"),
            variant: "destructive",
          });
        }
      } finally {
        if (active) {
          setIsLoadingOriginInternationalCities(false);
        }
      }
    };

    loadCities();

    return () => {
      active = false;
    };
  }, [formData.originCountry, t, toast]);

  // Load international cities for destination country
  useEffect(() => {
    let active = true;
    const selectedCountry = countries.find(
      (country) => country.id.toString() === formData.destCountry,
    );
    if (!formData.destCountry || selectedCountry?.code === "IR") {
      setDestinationInternationalCities([]);
      setIsLoadingDestinationInternationalCities(false);
      return () => {
        active = false;
      };
    }

    const countryId = Number(formData.destCountry);
    setIsLoadingDestinationInternationalCities(true);
    setDestinationInternationalCities([]);

    const loadCities = async () => {
      try {
        const data = await fetchInternationalCities(countryId);
        if (active) {
          setDestinationInternationalCities(data);
        }
      } catch (error) {
        if (active) {
          toast({
            title: t("requestForm.loadDestinationCitiesErrorTitle"),
            description: error instanceof Error ? error.message : t("requestForm.loadCitiesError"),
            variant: "destructive",
          });
        }
      } finally {
        if (active) {
          setIsLoadingDestinationInternationalCities(false);
        }
      }
    };

    loadCities();

    return () => {
      active = false;
    };
  }, [countries, formData.destCountry, t, toast]);

  // Derive the destination province from the selected port (port mode).
  useEffect(() => {
    if (formData.iranDestType !== "port" || !formData.iranEntryPort) {
      return;
    }
    const selectedPort = iranPorts.find(port => port.id.toString() === formData.iranEntryPort);
    if (selectedPort) {
      setFormData(prev => ({ ...prev, iranEntryProvince: selectedPort.province_id.toString() }));
    }
  }, [formData.iranDestType, formData.iranEntryPort, iranPorts]);

  // Derive the destination province from the selected border customs (customs mode).
  useEffect(() => {
    if (formData.iranDestType !== "customs" || !formData.iranDestCustomsOffice) {
      return;
    }
    const selectedCustoms = borderCustoms.find(c => c.id.toString() === formData.iranDestCustomsOffice);
    if (selectedCustoms?.province_id) {
      setFormData(prev => ({ ...prev, iranEntryProvince: selectedCustoms.province_id!.toString() }));
    }
  }, [formData.iranDestType, formData.iranDestCustomsOffice, borderCustoms]);

  // Load a "suggested entry port" hint for whatever destination province is active.
  useEffect(() => {
    let active = true;
    if (!formData.iranEntryProvince) {
      setRecommendedPorts([]);
      setIsLoadingRecommendedPorts(false);
      return () => {
        active = false;
      };
    }

    const provinceId = Number(formData.iranEntryProvince);
    setIsLoadingRecommendedPorts(true);

    const loadRecommendedPorts = async () => {
      try {
        const data = await fetchRecommendedPorts(provinceId);
        if (active) {
          setRecommendedPorts(data);
        }
      } catch (error) {
        if (active) {
          console.error("Error fetching recommended ports:", error);
        }
      } finally {
        if (active) {
          setIsLoadingRecommendedPorts(false);
        }
      }
    };

    loadRecommendedPorts();

    return () => {
      active = false;
    };
  }, [formData.iranEntryProvince]);

  // City mode: load counties for the chosen destination province.
  useEffect(() => {
    let active = true;
    if (formData.iranDestType !== "city" || !formData.iranEntryProvince) {
      setIranDestCounties([]);
      setIsLoadingIranDestCounties(false);
      return () => {
        active = false;
      };
    }

    const provinceId = Number(formData.iranEntryProvince);
    setIsLoadingIranDestCounties(true);
    setIranDestCounties([]);

    const loadCounties = async () => {
      try {
        const data = await fetchCounties(provinceId);
        if (active) {
          setIranDestCounties(data);
        }
      } catch (error) {
        if (active) {
          console.error("Error fetching Iran destination counties:", error);
        }
      } finally {
        if (active) {
          setIsLoadingIranDestCounties(false);
        }
      }
    };

    loadCounties();

    return () => {
      active = false;
    };
  }, [formData.iranDestType, formData.iranEntryProvince]);

  // City mode: load cities for the chosen destination county.
  useEffect(() => {
    let active = true;
    if (formData.iranDestType !== "city" || !formData.iranDestCounty) {
      setIranDestCities([]);
      setIsLoadingIranDestCities(false);
      return () => {
        active = false;
      };
    }

    const countyId = Number(formData.iranDestCounty);
    setIsLoadingIranDestCities(true);
    setIranDestCities([]);

    const loadCities = async () => {
      try {
        const data = await fetchCities(countyId);
        if (active) {
          setIranDestCities(data);
        }
      } catch (error) {
        if (active) {
          console.error("Error fetching Iran destination cities:", error);
        }
      } finally {
        if (active) {
          setIsLoadingIranDestCities(false);
        }
      }
    };

    loadCities();

    return () => {
      active = false;
    };
  }, [formData.iranDestType, formData.iranDestCounty]);

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
  const countryOptions = useMemo(
    () => [...countries].sort((a, b) => a.name.localeCompare(b.name)),
    [countries],
  );
  const isIranDestination = useMemo(
    () => countries.find((country) => country.id.toString() === formData.destCountry)?.code === "IR",
    [countries, formData.destCountry],
  );
  const originInternationalCityOptions = useMemo(
    () => [...originInternationalCities].sort((a, b) => a.name.localeCompare(b.name)),
    [originInternationalCities],
  );
  const destinationInternationalCityOptions = useMemo(
    () => [...destinationInternationalCities].sort((a, b) => a.name.localeCompare(b.name)),
    [destinationInternationalCities],
  );

  /** Resolved origin/destination labels for confirmation page (avoids undefined when formData only has IDs). */
  const confirmationLocationDisplay = useMemo(() => {
    if (shippingType === "domestic") {
      const oProv = provinceOptions.find((p) => p.id.toString() === formData.originProvince);
      const oCounty = originCountyOptions.find((c) => c.id.toString() === formData.originCounty);
      const oCity = originCityOptions.find((c) => c.id.toString() === formData.originCity);
      const dProv = provinceOptions.find((p) => p.id.toString() === formData.destinationProvince);
      const dCounty = destinationCountyOptions.find((c) => c.id.toString() === formData.destinationCounty);
      const dCity = destinationCityOptions.find((c) => c.id.toString() === formData.destinationCity);
      return {
        origin: [oCity?.name, oCounty?.name, oProv?.name].filter(Boolean).join("، ") || "—",
        destination: [dCity?.name, dCounty?.name, dProv?.name].filter(Boolean).join("، ") || "—",
      };
    }
    const oCountry = countryOptions.find((c) => c.id.toString() === formData.originCountry);
    const oCity = originInternationalCityOptions.find((c) => c.id.toString() === formData.originCityInternational);
    const dCountry = countryOptions.find((c) => c.id.toString() === formData.destCountry);
    const dCity = destinationInternationalCityOptions.find((c) => c.id.toString() === formData.destCityInternational);

    // When shipping to Iran, spell out the chosen in-Iran destination point.
    let iranDestLabel = "";
    if (dCountry?.code === "IR") {
      const provinceName = provinceOptions.find((p) => p.id.toString() === formData.iranEntryProvince)?.name;
      if (formData.iranDestType === "port") {
        iranDestLabel = iranPorts.find((p) => p.id.toString() === formData.iranEntryPort)?.name_fa || "";
      } else if (formData.iranDestType === "customs") {
        iranDestLabel = borderCustoms.find((c) => c.id.toString() === formData.iranDestCustomsOffice)?.name_fa || "";
      } else if (formData.iranDestType === "city") {
        const cityName = iranDestCities.find((c) => c.id.toString() === formData.iranDestCity)?.name;
        const countyName = iranDestCounties.find((c) => c.id.toString() === formData.iranDestCounty)?.name;
        iranDestLabel = [cityName, countyName, provinceName].filter(Boolean).join("، ");
      }
    }

    return {
      origin: [oCity?.name, oCountry?.name].filter(Boolean).join("، ") || "—",
      destination:
        [dCity?.name, dCountry?.name].filter(Boolean).join("، ")
          + (iranDestLabel ? ` ← ${iranDestLabel}` : "")
        || "—",
    };
  }, [
    shippingType,
    formData.originProvince,
    formData.originCounty,
    formData.originCity,
    formData.destinationProvince,
    formData.destinationCounty,
    formData.destinationCity,
    formData.originCountry,
    formData.originCityInternational,
    formData.destCountry,
    formData.destCityInternational,
    formData.iranDestType,
    formData.iranEntryPort,
    formData.iranDestCustomsOffice,
    formData.iranDestCounty,
    formData.iranDestCity,
    formData.iranEntryProvince,
    provinceOptions,
    originCountyOptions,
    destinationCountyOptions,
    originCityOptions,
    destinationCityOptions,
    countryOptions,
    originInternationalCityOptions,
    destinationInternationalCityOptions,
    iranPorts,
    borderCustoms,
    iranDestCounties,
    iranDestCities,
  ]);

  // Attach the structured Iran destination point to an international payload when
  // the destination country is Iran. Shared by the preview and final submit paths.
  const applyIranDestinationToPayload = (payload: ShipmentRequestPayload) => {
    const selectedProvince = provinces.find(p => p.id.toString() === formData.iranEntryProvince);
    const selectedPort = iranPorts.find(p => p.id.toString() === formData.iranEntryPort);
    Object.assign(payload, buildIranDestinationPayload({
      type: formData.iranDestType,
      provinceId: formData.iranEntryProvince,
      provinceName: selectedProvince?.name,
      portId: formData.iranEntryPort,
      portName: selectedPort?.name_fa,
      customsOfficeId: formData.iranDestCustomsOffice,
      cityId: formData.iranDestCity,
    }));
  };

  const handleSubmit = async () => {
    // Validate required fields based on shipping type
    let isValid = true;
    let errorMessage = t("requestForm.validation.phoneRequired");

    if (!formData.phoneNumber) {
      isValid = false;
      errorMessage = t("requestForm.validation.phoneRequired");
    } else if (formData.transportMethodPreference === "customer_choice") {
      // If customer wants to choose, validate that they've selected methods
      if (shippingType === "international" && !formData.internationalTransportMethod) {
        isValid = false;
        errorMessage = t("requestForm.validation.internationalMethodRequired");
      } else if (shippingType === "domestic" && !formData.domesticTransportMethod) {
        isValid = false;
        errorMessage = t("requestForm.validation.domesticMethodRequired");
      }
    }
    
    if (isValid && shippingType === "domestic") {
      if (!formData.originProvince || !formData.destinationProvince) {
        isValid = false;
        errorMessage = t("requestForm.validation.domesticRouteRequired");
      }
    } else if (shippingType === "international") {
      if (!isInternationalRouteComplete({
        originCountry: formData.originCountry,
        originCity: formData.originCityInternational,
        destinationCountry: formData.destCountry,
        destinationCity: formData.destCityInternational,
        isIranDestination,
      })) {
        isValid = false;
        errorMessage = t("requestForm.validation.internationalRouteRequired");
      }
      
    }

    if (!isValid) {
      toast({
        title: t("common.error"),
        description: errorMessage,
        variant: "destructive",
      });
      return;
    }

    // Phone number validation
    const phoneRegex = /^09\d{9}$/;
    if (!phoneRegex.test(formData.phoneNumber)) {
      toast({
        title: t("common.error"),
        description: t("requestForm.validation.phoneInvalid"),
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);

    try {
      const payload: ShipmentRequestPayload = {
        shipping_type: shippingType,
        contact_phone: formData.phoneNumber,
        transport_method: formData.transportMethod,  // Legacy field
        international_transport_method: formData.internationalTransportMethod,
        domestic_transport_method: formData.domesticTransportMethod,
        transport_method_preference: formData.transportMethodPreference,
      };

      // Add location data based on shipping type
      if (shippingType === "domestic") {
        payload.origin_province_id = Number(formData.originProvince);
        payload.origin_county_id = formData.originCounty ? Number(formData.originCounty) : null;
        payload.origin_city_id = formData.originCity ? Number(formData.originCity) : null;
        payload.dest_province_id = Number(formData.destinationProvince);
        payload.dest_county_id = formData.destinationCounty ? Number(formData.destinationCounty) : null;
        payload.dest_city_id = formData.destinationCity ? Number(formData.destinationCity) : null;
      } else {
        // Get country names from selected IDs
        const originCountry = countries.find(c => c.id.toString() === formData.originCountry);
        const destCountry = countries.find(c => c.id.toString() === formData.destCountry);
        const originCity = originInternationalCities.find(c => c.id.toString() === formData.originCityInternational);
        const destCity = destinationInternationalCities.find(c => c.id.toString() === formData.destCityInternational);
        
        payload.origin_country = originCountry?.name || "";
        payload.origin_city_international = originCity?.name || "";
        payload.origin_address_international = formData.originAddressInternational;
        payload.dest_country = destCountry?.name || "";
        if (destCountry?.code !== "IR") {
          payload.dest_city_international = destCity?.name || "";
        }
        payload.dest_address_international = formData.destAddressInternational;
        
        // Add the structured Iran destination point if destination is Iran
        if (destCountry?.code === "IR") {
          applyIranDestinationToPayload(payload);
        }
      }

      // Add customer details if provided
      if (formData.customerFirstName.trim()) {
        payload.customer_first_name = formData.customerFirstName.trim();
      }
      if (formData.customerLastName.trim()) {
        payload.customer_last_name = formData.customerLastName.trim();
      }

      // Add cargo details if provided
      if (formData.cargoDescription.trim()) {
        payload.cargo_description = formData.cargoDescription.trim();
      }
      if (formData.cargoWeight.trim()) {
        payload.cargo_weight = parseFloat(formData.cargoWeight);
      }
      if (formData.cargoVolume.trim()) {
        payload.cargo_volume = parseFloat(formData.cargoVolume);
      }
      if (formData.cargoValue.trim()) {
        payload.cargo_value = parseFloat(formData.cargoValue);
      }
      if (formData.specialInstructions.trim()) {
        payload.special_instructions = formData.specialInstructions.trim();
      }
      if (formData.pickupDate) {
        payload.pickup_date = formData.pickupDate;
      }
      if (formData.deliveryDate) {
        payload.delivery_date = formData.deliveryDate;
      }

      // Show confirmation page instead of submitting directly
      setShowConfirmation(true);
    } catch (error) {
      toast({
        title: t("requestForm.submitErrorTitle"),
        description: error instanceof Error ? error.message : t("requestForm.submitError"),
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFinalSubmit = async () => {
    setIsSubmitting(true);

    try {
      const payload: ShipmentRequestPayload = {
        shipping_type: shippingType,
        contact_phone: formData.phoneNumber,
        transport_method: formData.transportMethod,  // Legacy field
        international_transport_method: formData.internationalTransportMethod,
        domestic_transport_method: formData.domesticTransportMethod,
        transport_method_preference: formData.transportMethodPreference,
      };

      // Add location data based on shipping type
      if (shippingType === "domestic") {
        payload.origin_province_id = Number(formData.originProvince);
        payload.origin_county_id = formData.originCounty ? Number(formData.originCounty) : null;
        payload.origin_city_id = formData.originCity ? Number(formData.originCity) : null;
        payload.dest_province_id = Number(formData.destinationProvince);
        payload.dest_county_id = formData.destinationCounty ? Number(formData.destinationCounty) : null;
        payload.dest_city_id = formData.destinationCity ? Number(formData.destinationCity) : null;
      } else {
        // Get country names from selected IDs
        const originCountry = countries.find(c => c.id.toString() === formData.originCountry);
        const destCountry = countries.find(c => c.id.toString() === formData.destCountry);
        const originCity = originInternationalCities.find(c => c.id.toString() === formData.originCityInternational);
        const destCity = destinationInternationalCities.find(c => c.id.toString() === formData.destCityInternational);
        
        payload.origin_country = originCountry?.name || "";
        payload.origin_city_international = originCity?.name || "";
        payload.origin_address_international = formData.originAddressInternational;
        payload.dest_country = destCountry?.name || "";
        if (destCountry?.code !== "IR") {
          payload.dest_city_international = destCity?.name || "";
        }
        payload.dest_address_international = formData.destAddressInternational;
        
        // Add the structured Iran destination point if destination is Iran
        if (destCountry?.code === "IR") {
          applyIranDestinationToPayload(payload);
        }
      }

      // Add customer details if provided
      if (formData.customerFirstName.trim()) {
        payload.customer_first_name = formData.customerFirstName.trim();
      }
      if (formData.customerLastName.trim()) {
        payload.customer_last_name = formData.customerLastName.trim();
      }

      // Add cargo details if provided
      if (formData.cargoDescription.trim()) {
        payload.cargo_description = formData.cargoDescription.trim();
      }
      if (formData.cargoWeight.trim()) {
        payload.cargo_weight = parseFloat(formData.cargoWeight);
      }
      if (formData.cargoVolume.trim()) {
        payload.cargo_volume = parseFloat(formData.cargoVolume);
      }
      if (formData.cargoValue.trim()) {
        payload.cargo_value = parseFloat(formData.cargoValue);
      }
      if (formData.specialInstructions.trim()) {
        payload.special_instructions = formData.specialInstructions.trim();
      }
      if (formData.pickupDate) {
        payload.pickup_date = formData.pickupDate;
      }
      if (formData.deliveryDate) {
        payload.delivery_date = formData.deliveryDate;
      }

      const response = await submitShipmentRequest(payload);
      const trackingCode = response.tracking_code || `SR${response.id.toString().padStart(6, "0")}`;
      setSubmittedTrackingCode(trackingCode);
      setIsSubmitted(true);
      setShowConfirmation(false);
      toast({
        title: t("requestForm.submitSuccessTitle"),
        description: tf("requestForm.submitSuccessDescription", { trackingCode }),
      });
    } catch (error) {
      toast({
        title: t("requestForm.submitErrorTitle"),
        description: error instanceof Error ? error.message : t("requestForm.submitError"),
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setFormData({
      // Domestic shipping fields
      originProvince: "",
      originCounty: "",
      originCity: "",
      destinationProvince: "",
      destinationCounty: "",
      destinationCity: "",
      // International shipping fields
      originCountry: "",
      originCityInternational: "",
      originAddressInternational: "",
      destCountry: "",
      destCityInternational: "",
      destAddressInternational: "",
      // Iran destination point fields
      iranDestType: "city",
      iranEntryPort: "",
      iranDestCustomsOffice: "",
      iranDestCounty: "",
      iranDestCity: "",
      iranEntryProvince: "",
      // Common fields
      phoneNumber: "",
      customerFirstName: "",
      customerLastName: "",
      transportMethod: "",  // Legacy field
      internationalTransportMethod: "",
      domesticTransportMethod: "",
      transportMethodPreference: "customer_choice",
      cargoDescription: "",
      cargoWeight: "",
      cargoVolume: "",
      cargoValue: "",
      specialInstructions: "",
      pickupDate: "",
      deliveryDate: "",
    });
    setIsSubmitted(false);
    setShowCargoDetails(false);
    setShowOriginLocationDetails(false);
    setShowDestinationLocationDetails(false);
    setSubmittedTrackingCode(null);
    // Reset international cities arrays
    setOriginInternationalCities([]);
    setDestinationInternationalCities([]);
  };

  const returnToLanding = () => {
    setIsSubmitted(false);
    setSubmittedTrackingCode(null);
    onBack();
  };

  const handleCopyTrackingCode = async () => {
    if (!submittedTrackingCode) return;

    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error("Clipboard is not available");
      }
      await navigator.clipboard.writeText(submittedTrackingCode);
      toast({
        title: t("requestForm.copySuccessTitle"),
        description: t("requestForm.copySuccessDescription"),
      });
    } catch {
      toast({
        title: t("requestForm.copyErrorTitle"),
        description: t("requestForm.copyErrorDescription"),
        variant: "destructive",
      });
    }
  };

  if (isSubmitted) {
    return (
      <Card className="w-full max-w-md bg-gradient-card shadow-lg border-0">
        <CardContent className="p-6 text-center">
          <div className="mb-4">
            <CheckCircle2 className="w-16 h-16 text-secondary mx-auto" />
          </div>
          <h3 className="text-xl font-bold text-foreground mb-2">{t("requestFlow.confirmAndSend")}</h3>
          {submittedTrackingCode && (
            <div className="mb-4 p-4 bg-muted/50 rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">{t("common.trackingNumber")}</p>
              <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
                <p className="break-all text-xl font-mono font-bold text-foreground">{submittedTrackingCode}</p>
                <Button type="button" variant="outline" size="sm" onClick={handleCopyTrackingCode}>
                  <Copy className="h-4 w-4" />
                  {t("requestForm.copyCode")}
                </Button>
              </div>
            </div>
          )}
          <p className="text-muted-foreground mb-6 leading-7">{t("requestForm.successHelp")}</p>
          <div className="space-y-2">
            <Button
              onClick={() => submittedTrackingCode && navigate(`/customer/track/${submittedTrackingCode}`)}
              className="w-full bg-gradient-primary hover:shadow-primary"
              disabled={!submittedTrackingCode}
            >
              {t("tracking.title")}
            </Button>
            <Button onClick={resetForm} variant="outline" className="w-full">
              {t("common.createNewRequest")}
            </Button>
            <Button onClick={returnToLanding} variant="ghost" className="w-full">
              {t("common.home")}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (showConfirmation) {
    return (
      <RequestConfirmation
        formData={formData}
        shippingType={shippingType}
        onBack={() => setShowConfirmation(false)}
        onSubmit={handleFinalSubmit}
        isSubmitting={isSubmitting}
        locationDisplay={confirmationLocationDisplay}
      />
    );
  }

  return (
    <Card className="w-full max-w-md bg-gradient-card shadow-lg border-0">
      <CardHeader className="text-center pb-4">
        <div className="flex items-center justify-between mb-4">
          {onBack && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onBack}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              {t("common.back")}
            </Button>
          )}
          <div className="flex-1"></div>
        </div>
        <CardTitle className="text-xl font-bold flex items-center justify-center gap-2">
          <MapPin className="w-5 h-5 text-primary" />
          {shippingType === "domestic" ? t("requestForm.domesticRouteTitle") : t("requestForm.internationalRouteTitle")}
        </CardTitle>
        <p className="text-muted-foreground text-sm">
          {shippingType === "domestic" 
            ? t("requestForm.domesticRouteDescription")
            : t("requestForm.internationalRouteDescription")
          }
        </p>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {shippingType === "domestic" ? (
          <>
            {/* Domestic Origin Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-primary">
                <div className="w-3 h-3 bg-primary rounded-full"></div>
                {t("requestForm.originSection")}
              </div>
              
              <div className="space-y-3 pr-5">
                <Label className="flex items-center gap-1 text-sm font-medium">
                  {t("requestForm.originProvince")}
                  <RequiredAsterisk />
                </Label>
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
                    <SelectValue placeholder={isLoadingProvinces ? t("requestForm.loading") : t("requestForm.selectProvince")} />
                  </SelectTrigger>
                  <SelectContent>
                    {provinceOptions.map((province) => (
                      <SelectItem key={province.id} value={province.id.toString()}>
                        {province.name}
                      </SelectItem>
                    ))}
                    {provinceOptions.length === 0 && !isLoadingProvinces && (
                      <SelectItem value="no-origin-province" disabled>
                        {t("requestForm.noProvince")}
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>

                {formData.originProvince && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowOriginLocationDetails((value) => !value)}
                    className="h-auto px-0 text-xs font-medium text-primary hover:bg-transparent hover:text-primary/80"
                  >
                    {showOriginLocationDetails ? t("requestForm.hideOptionalDetails") : t("requestForm.showOriginDetails")}
                  </Button>
                )}

                {showOriginLocationDetails && (
                  <div className="space-y-3 rounded-lg border bg-muted/20 p-3">
                    <p className={helperTextClass}>{t("requestForm.provinceEnough")}</p>
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
                              ? t("requestForm.selectProvinceFirst")
                              : isLoadingOriginCounties
                                ? t("requestForm.loading")
                                : t("requestForm.selectCountyOptional")
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
                            {t("requestForm.noCounty")}
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
                              ? t("requestForm.selectCountyFirst")
                              : isLoadingOriginCities
                                ? t("requestForm.loading")
                                : t("requestForm.selectCityOptional")
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
                            {t("requestForm.noCity")}
                          </SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
            </div>

            {/* Arrow */}
            <div className="flex justify-center">
              <div className="p-2 bg-accent rounded-full">
                <ArrowLeft className="w-4 h-4 text-muted-foreground rotate-90" />
              </div>
            </div>

            {/* Domestic Destination Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-secondary">
                <div className="w-3 h-3 bg-secondary rounded-full"></div>
                {t("requestForm.destinationSection")}
              </div>
              
              <div className="space-y-3 pr-5">
                <Label className="flex items-center gap-1 text-sm font-medium">
                  {t("requestForm.destinationProvince")}
                  <RequiredAsterisk />
                </Label>
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
                    <SelectValue placeholder={isLoadingProvinces ? t("requestForm.loading") : t("requestForm.selectProvince")} />
                  </SelectTrigger>
                  <SelectContent>
                    {provinceOptions.map((province) => (
                      <SelectItem key={province.id} value={province.id.toString()}>
                        {province.name}
                      </SelectItem>
                    ))}
                    {provinceOptions.length === 0 && !isLoadingProvinces && (
                      <SelectItem value="no-destination-province" disabled>
                        {t("requestForm.noProvince")}
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>

                {formData.destinationProvince && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowDestinationLocationDetails((value) => !value)}
                    className="h-auto px-0 text-xs font-medium text-primary hover:bg-transparent hover:text-primary/80"
                  >
                    {showDestinationLocationDetails ? t("requestForm.hideOptionalDetails") : t("requestForm.showDestinationDetails")}
                  </Button>
                )}

                {showDestinationLocationDetails && (
                  <div className="space-y-3 rounded-lg border bg-muted/20 p-3">
                    <p className={helperTextClass}>{t("requestForm.provinceEnough")}</p>
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
                              ? t("requestForm.selectProvinceFirst")
                              : isLoadingDestinationCounties
                                ? t("requestForm.loading")
                                : t("requestForm.selectCountyOptional")
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
                            {t("requestForm.noCounty")}
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
                              ? t("requestForm.selectCountyFirst")
                              : isLoadingDestinationCities
                                ? t("requestForm.loading")
                                : t("requestForm.selectCityOptional")
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
                            {t("requestForm.noCity")}
                          </SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          <>
            {/* International Origin Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-primary">
                <div className="w-3 h-3 bg-primary rounded-full"></div>
                {t("requestForm.originInternationalSection")}
              </div>
              
              <div className="space-y-3 pr-5">
                <Label className="flex items-center gap-1 text-sm font-medium">
                  {t("requestForm.originCountry")}
                  <RequiredAsterisk />
                </Label>
                <Select
                  value={formData.originCountry}
                  onValueChange={(value) => {
                    setFormData({
                      ...formData,
                      originCountry: value,
                      originCityInternational: "",
                    });
                  }}
                  disabled={isLoadingCountries && countryOptions.length === 0}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={isLoadingCountries ? t("requestForm.loading") : t("requestForm.selectOriginCountry")} />
                  </SelectTrigger>
                  <SelectContent>
                    {countryOptions.map((country) => (
                      <SelectItem key={country.id} value={country.id.toString()}>
                        {country.name}
                      </SelectItem>
                    ))}
                    {countryOptions.length === 0 && !isLoadingCountries && (
                      <SelectItem value="no-origin-country" disabled>
                        {t("requestForm.noCountry")}
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>

                <Label className="flex items-center gap-1 text-sm font-medium">
                  {t("requestForm.originCityPort")}
                  <RequiredAsterisk />
                </Label>
                <Select
                  value={formData.originCityInternational}
                  onValueChange={(value) => {
                    setFormData({
                      ...formData,
                      originCityInternational: value,
                    });
                  }}
                  disabled={!formData.originCountry || isLoadingOriginInternationalCities}
                >
                  <SelectTrigger>
                    <SelectValue
                      placeholder={
                        !formData.originCountry
                          ? t("requestForm.selectCountryFirst")
                          : isLoadingOriginInternationalCities
                            ? t("requestForm.loading")
                            : t("requestForm.selectOriginCityPort")
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {originInternationalCityOptions.map((city) => (
                      <SelectItem key={city.id} value={city.id.toString()}>
                        {city.name} {city.is_major_port && "🏭"} {city.is_major_airport && "✈️"}
                      </SelectItem>
                    ))}
                    {originInternationalCityOptions.length === 0 && formData.originCountry && !isLoadingOriginInternationalCities && (
                      <SelectItem value="no-origin-city" disabled>
                        {t("requestForm.noCity")}
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>

                <div className="space-y-2">
                  <Label htmlFor="originAddressInternational" className="flex items-center gap-2 text-sm font-medium">
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    {t("requestForm.originAddressOptional")}
                  </Label>
                  <Input
                    id="originAddressInternational"
                    placeholder={t("requestForm.originAddressPlaceholder")}
                    value={formData.originAddressInternational}
                    onChange={(e) => {
                      setFormData({
                        ...formData,
                        originAddressInternational: e.target.value,
                      });
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Arrow */}
            <div className="flex justify-center">
              <div className="p-2 bg-accent rounded-full">
                <ArrowLeft className="w-4 h-4 text-muted-foreground rotate-90" />
              </div>
            </div>

            {/* International Destination Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-secondary">
                <div className="w-3 h-3 bg-secondary rounded-full"></div>
                {t("requestForm.destinationInternationalSection")}
              </div>
              
              <div className="space-y-3 pr-5">
                <Label className="flex items-center gap-1 text-sm font-medium">
                  {t("requestForm.destinationCountry")}
                  <RequiredAsterisk />
                </Label>
                <Select
                  value={formData.destCountry}
                  onValueChange={(value) => {
                    setFormData({
                      ...formData,
                      destCountry: value,
                      destCityInternational: "",
                      iranDestType: "city",
                      iranEntryPort: "",
                      iranDestCustomsOffice: "",
                      iranDestCounty: "",
                      iranDestCity: "",
                      iranEntryProvince: "",
                    });
                  }}
                  disabled={isLoadingCountries && countryOptions.length === 0}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={isLoadingCountries ? t("requestForm.loading") : t("requestForm.selectDestinationCountry")} />
                  </SelectTrigger>
                  <SelectContent>
                    {countryOptions.map((country) => (
                      <SelectItem key={country.id} value={country.id.toString()}>
                        {country.name}
                      </SelectItem>
                    ))}
                    {countryOptions.length === 0 && !isLoadingCountries && (
                      <SelectItem value="no-dest-country" disabled>
                        {t("requestForm.noCountry")}
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>

                {!isIranDestination && (
                  <>
                    <Label className="flex items-center gap-1 text-sm font-medium">
                      {t("requestForm.destinationCityPort")}
                      <RequiredAsterisk />
                    </Label>
                    <Select
                      value={formData.destCityInternational}
                      onValueChange={(value) => {
                        setFormData({
                          ...formData,
                          destCityInternational: value,
                        });
                      }}
                      disabled={!formData.destCountry || isLoadingDestinationInternationalCities}
                    >
                      <SelectTrigger>
                        <SelectValue
                          placeholder={
                            !formData.destCountry
                              ? t("requestForm.selectCountryFirst")
                              : isLoadingDestinationInternationalCities
                                ? t("requestForm.loading")
                                : t("requestForm.selectDestinationCityPort")
                          }
                        />
                      </SelectTrigger>
                      <SelectContent>
                        {destinationInternationalCityOptions.map((city) => (
                          <SelectItem key={city.id} value={city.id.toString()}>
                            {city.name} {city.is_major_port && "🏭"} {city.is_major_airport && "✈️"}
                          </SelectItem>
                        ))}
                        {destinationInternationalCityOptions.length === 0 && formData.destCountry && !isLoadingDestinationInternationalCities && (
                          <SelectItem value="no-dest-city" disabled>
                            {t("requestForm.noCity")}
                          </SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                  </>
                )}

                <div className="space-y-2">
                  <Label htmlFor="destAddressInternational" className="flex items-center gap-2 text-sm font-medium">
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    {t("requestForm.destinationAddressOptional")}
                  </Label>
                  <Input
                    id="destAddressInternational"
                    placeholder={t("requestForm.destinationAddressPlaceholder")}
                    value={formData.destAddressInternational}
                    onChange={(e) => {
                      setFormData({
                        ...formData,
                        destAddressInternational: e.target.value,
                      });
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Iran Destination Section - Only show if destination is Iran */}
            {isIranDestination && (
              <>
                {/* Arrow */}
                <div className="flex justify-center">
                  <div className="p-2 bg-accent rounded-full">
                    <ArrowLeft className="w-4 h-4 text-muted-foreground rotate-90" />
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-sm font-semibold text-primary">
                    <div className="w-3 h-3 bg-primary rounded-full"></div>
                    {t("requestForm.iranDestStepTitle")}
                  </div>

                  <div className="space-y-3 pr-5">
                    {/* Destination point type: port / customs / city */}
                    <Label className="flex items-center gap-1 text-sm font-medium">
                      {t("requestForm.iranDestTypeLabel")}
                    </Label>
                    <div className="grid grid-cols-3 gap-2">
                      {([
                        { type: "city" as const, icon: "🏙️", label: t("requestForm.iranDestTypeCity") },
                        { type: "port" as const, icon: "🚢", label: t("requestForm.iranDestTypePort") },
                        { type: "customs" as const, icon: "🛃", label: t("requestForm.iranDestTypeCustoms") },
                      ]).map(({ type, icon, label }) => (
                        <Button
                          key={type}
                          type="button"
                          variant={formData.iranDestType === type ? "default" : "outline"}
                          onClick={() => {
                            setFormData({
                              ...formData,
                              iranDestType: type,
                              // Reset every mode-specific selection when the type changes.
                              iranEntryPort: "",
                              iranDestCustomsOffice: "",
                              iranDestCounty: "",
                              iranDestCity: "",
                              iranEntryProvince: "",
                            });
                          }}
                          className="h-auto flex-col gap-1 py-2 text-xs"
                        >
                          <span className="text-base leading-none">{icon}</span>
                          <span>{label}</span>
                        </Button>
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {t("requestForm.iranDestTypeHint")}
                    </p>

                    {/* PORT MODE */}
                    {formData.iranDestType === "port" && (
                      <>
                        <Label className="flex items-center gap-1 text-sm font-medium">
                          {t("requestForm.entryPort")}
                        </Label>
                        <Select
                          value={formData.iranEntryPort}
                          onValueChange={(value) => {
                            setFormData({ ...formData, iranEntryPort: value, iranEntryProvince: "" });
                          }}
                          disabled={isLoadingIranPorts && iranPorts.length === 0}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder={isLoadingIranPorts ? t("requestForm.loading") : t("requestForm.selectEntryPort")} />
                          </SelectTrigger>
                          <SelectContent>
                            {iranPorts.map((port) => (
                              <SelectItem key={port.id} value={port.id.toString()}>
                                {port.name_fa} ({port.port_type === "sea" ? t("requestForm.portSea") : port.port_type === "air" ? t("requestForm.portAir") : t("requestForm.portLand")})
                                {port.is_major_port && " ⭐"}
                              </SelectItem>
                            ))}
                            {iranPorts.length === 0 && !isLoadingIranPorts && (
                              <SelectItem value="no-port" disabled>
                                {t("requestForm.noPort")}
                              </SelectItem>
                            )}
                          </SelectContent>
                        </Select>

                        {formData.iranEntryPort && (
                          <div className="p-3 bg-accent rounded-md">
                            {(() => {
                              const selectedPort = iranPorts.find(p => p.id.toString() === formData.iranEntryPort);
                              return selectedPort ? (
                                <div className="space-y-1 text-sm">
                                  <div className="font-medium">{selectedPort.name_fa}</div>
                                  {selectedPort.description && (
                                    <div className="text-muted-foreground text-xs">{selectedPort.description}</div>
                                  )}
                                  <div className="text-muted-foreground text-xs">
                                    {t("requestForm.portType")}: {selectedPort.port_type === "sea" ? t("requestForm.portSea") : selectedPort.port_type === "air" ? t("requestForm.portAir") : t("requestForm.portLand")}
                                  </div>
                                </div>
                              ) : null;
                            })()}
                          </div>
                        )}
                      </>
                    )}

                    {/* CUSTOMS MODE */}
                    {formData.iranDestType === "customs" && (
                      <>
                        <Label className="flex items-center gap-1 text-sm font-medium">
                          {t("requestForm.borderCustoms")}
                        </Label>
                        <Select
                          value={formData.iranDestCustomsOffice}
                          onValueChange={(value) => {
                            setFormData({ ...formData, iranDestCustomsOffice: value, iranEntryProvince: "" });
                          }}
                          disabled={isLoadingBorderCustoms && borderCustoms.length === 0}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder={isLoadingBorderCustoms ? t("requestForm.loading") : t("requestForm.selectBorderCustoms")} />
                          </SelectTrigger>
                          <SelectContent>
                            {borderCustoms.map((office) => (
                              <SelectItem key={office.id} value={office.id.toString()}>
                                {office.name_fa}
                                {office.customs_type === "rail" ? ` (${t("requestForm.customsRail")})` : ` (${t("requestForm.customsRoad")})`}
                              </SelectItem>
                            ))}
                            {borderCustoms.length === 0 && !isLoadingBorderCustoms && (
                              <SelectItem value="no-customs" disabled>
                                {t("requestForm.noBorderCustoms")}
                              </SelectItem>
                            )}
                          </SelectContent>
                        </Select>

                        {formData.iranDestCustomsOffice && (
                          <div className="p-3 bg-accent rounded-md">
                            {(() => {
                              const office = borderCustoms.find(c => c.id.toString() === formData.iranDestCustomsOffice);
                              return office ? (
                                <div className="space-y-1 text-sm">
                                  <div className="font-medium">{office.name_fa}</div>
                                  {office.description && (
                                    <div className="text-muted-foreground text-xs">{office.description}</div>
                                  )}
                                </div>
                              ) : null;
                            })()}
                          </div>
                        )}
                      </>
                    )}

                    {/* CITY MODE */}
                    {formData.iranDestType === "city" && (
                      <>
                        <Label className="flex items-center gap-1 text-sm font-medium">
                          {t("requestForm.entryProvince")}
                        </Label>
                        <Select
                          value={formData.iranEntryProvince}
                          onValueChange={(value) => {
                            setFormData({ ...formData, iranEntryProvince: value, iranDestCounty: "", iranDestCity: "" });
                          }}
                          disabled={isLoadingProvinces && provinceOptions.length === 0}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder={isLoadingProvinces ? t("requestForm.loading") : t("requestForm.selectEntryProvince")} />
                          </SelectTrigger>
                          <SelectContent>
                            {provinceOptions.map((province) => (
                              <SelectItem key={province.id} value={province.id.toString()}>
                                {province.name}
                              </SelectItem>
                            ))}
                            {provinceOptions.length === 0 && !isLoadingProvinces && (
                              <SelectItem value="no-province" disabled>
                                {t("requestForm.noProvince")}
                              </SelectItem>
                            )}
                          </SelectContent>
                        </Select>

                        <Label className="flex items-center gap-1 text-sm font-medium">
                          {t("requestForm.destinationCounty")}
                        </Label>
                        <Select
                          value={formData.iranDestCounty}
                          onValueChange={(value) => {
                            setFormData({ ...formData, iranDestCounty: value, iranDestCity: "" });
                          }}
                          disabled={!formData.iranEntryProvince || isLoadingIranDestCounties}
                        >
                          <SelectTrigger>
                            <SelectValue
                              placeholder={
                                !formData.iranEntryProvince
                                  ? t("requestForm.selectProvinceFirst")
                                  : isLoadingIranDestCounties
                                    ? t("requestForm.loading")
                                    : t("requestForm.selectCounty")
                              }
                            />
                          </SelectTrigger>
                          <SelectContent>
                            {iranDestCounties.map((county) => (
                              <SelectItem key={county.id} value={county.id.toString()}>
                                {county.name}
                              </SelectItem>
                            ))}
                            {iranDestCounties.length === 0 && formData.iranEntryProvince && !isLoadingIranDestCounties && (
                              <SelectItem value="no-county" disabled>
                                {t("requestForm.noCounty")}
                              </SelectItem>
                            )}
                          </SelectContent>
                        </Select>

                        <Label className="flex items-center gap-1 text-sm font-medium">
                          {t("requestForm.destinationCity")}
                        </Label>
                        <Select
                          value={formData.iranDestCity}
                          onValueChange={(value) => {
                            setFormData({ ...formData, iranDestCity: value });
                          }}
                          disabled={!formData.iranDestCounty || isLoadingIranDestCities}
                        >
                          <SelectTrigger>
                            <SelectValue
                              placeholder={
                                !formData.iranDestCounty
                                  ? t("requestForm.selectCountyFirst")
                                  : isLoadingIranDestCities
                                    ? t("requestForm.loading")
                                    : t("requestForm.selectCity")
                              }
                            />
                          </SelectTrigger>
                          <SelectContent>
                            {iranDestCities.map((city) => (
                              <SelectItem key={city.id} value={city.id.toString()}>
                                {city.name}
                              </SelectItem>
                            ))}
                            {iranDestCities.length === 0 && formData.iranDestCounty && !isLoadingIranDestCities && (
                              <SelectItem value="no-city" disabled>
                                {t("requestForm.noCity")}
                              </SelectItem>
                            )}
                          </SelectContent>
                        </Select>
                      </>
                    )}

                    {/* Derived province notice for port / customs modes */}
                    {formData.iranDestType !== "city" && formData.iranEntryProvince && (
                      <div className="text-xs text-muted-foreground">
                        {t("requestForm.derivedProvince")}:{" "}
                        <span className="font-medium text-foreground">
                          {provinces.find(p => p.id.toString() === formData.iranEntryProvince)?.name}
                        </span>
                      </div>
                    )}

                    {/* Suggested entry port hint (city mode) */}
                    {formData.iranDestType === "city" && formData.iranEntryProvince && recommendedPorts.length > 0 && (
                      <div className="space-y-2">
                        <Label className="text-sm font-medium text-muted-foreground">
                          {t("requestForm.suggestedEntryPorts")}
                        </Label>
                        <div className="space-y-1">
                          {recommendedPorts.slice(0, 3).map((port, index) => (
                            <div key={port.port_id} className="flex items-center justify-between p-2 bg-accent rounded-md text-sm">
                              <span className="flex items-center gap-2">
                                {index === 0 && "🥇"} {index === 1 && "🥈"} {index === 2 && "🥉"}
                                {port.port_name_fa} ({port.port_type === "sea" ? t("requestForm.portSea") : port.port_type === "air" ? t("requestForm.portAir") : t("requestForm.portLand")})
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {port.estimated_days} {t("requestForm.dayUnit")}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
          </>
        )}

        {/* Customer Details Section */}
        <div className="space-y-3">
          <Label className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <User className="w-4 h-4 text-primary" />
                {t("requestForm.customerInfoOptional")}
          </Label>
          
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="customerFirstName" className="flex items-center gap-2 text-sm font-medium">
                <User className="w-4 h-4 text-muted-foreground" />
                {t("requestForm.firstName")}
              </Label>
              <Input
                id="customerFirstName"
                placeholder={t("requestForm.firstNamePlaceholder")}
                value={formData.customerFirstName}
                onChange={(e) => {
                  setFormData({
                    ...formData,
                    customerFirstName: e.target.value,
                  });
                }}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="customerLastName" className="flex items-center gap-2 text-sm font-medium">
                <User className="w-4 h-4 text-muted-foreground" />
                {t("requestForm.lastName")}
              </Label>
              <Input
                id="customerLastName"
                placeholder={t("requestForm.lastNamePlaceholder")}
                value={formData.customerLastName}
                onChange={(e) => {
                  setFormData({
                    ...formData,
                    customerLastName: e.target.value,
                  });
                }}
              />
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            {t("requestForm.customerInfoHelp")}
          </p>
        </div>

        {/* Phone Number Section */}
        <div className="space-y-3">
          <Label htmlFor="phone" className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Phone className="w-4 h-4 text-primary" />
            {t("common.phone")}
            <RequiredAsterisk />
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
            {t("requestForm.phoneHelp")}
          </p>
        </div>

        {/* Transport Method Section */}
        <div className="space-y-4">
          <Label className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Truck className="w-4 h-4 text-primary" />
            {t("common.transportMethod")}
          </Label>
          
          {/* Transport Method Preference */}
          <div className="space-y-2">
            <Label className="text-sm text-muted-foreground">{t("requestForm.transportPreference")}</Label>
            <Select
              value={formData.transportMethodPreference}
              onValueChange={(value) => {
                setFormData({
                  ...formData,
                  transportMethodPreference: value,
                  internationalTransportMethod: "",
                  domesticTransportMethod: "",
                });
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder={t("requestForm.transportPreferencePlaceholder")} />
              </SelectTrigger>
              <SelectContent>
                {transportMethodOptions?.preference_options.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    <div className="space-y-1 text-right">
                      <div className="font-medium">{option.label}</div>
                      <div className="text-xs text-muted-foreground">{option.description}</div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Customer Choice Transport Methods */}
          {formData.transportMethodPreference === "customer_choice" && (
            <div className="space-y-3 p-4 border rounded-lg bg-muted/30">
              <p className={helperTextClass}>
                {t("requestForm.transportChoiceHelp")}
              </p>
              {shippingType === "international" && (
                <div className="space-y-2">
                  <Label className="flex items-center gap-1 text-sm font-medium">
                    {t("requestForm.internationalMethod")}
                    <RequiredAsterisk />
                  </Label>
                  <Select
                    value={formData.internationalTransportMethod}
                    onValueChange={(value) => {
                      setFormData({
                        ...formData,
                        internationalTransportMethod: value,
                      });
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={t("requestForm.selectInternationalMethod")} />
                    </SelectTrigger>
                    <SelectContent>
                      {transportMethodOptions?.international_methods.map((method) => (
                        <SelectItem key={method.id} value={method.name}>
                          <div className="space-y-1 text-right">
                            <div className="font-medium">{getTransportLabel(method, language)}</div>
                            {method.description && (
                              <div className="text-xs text-muted-foreground">{getTransportDescription(method, t("requestForm.internationalMethodFallback"))}</div>
                            )}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
              
              {shippingType === "domestic" && (
                <div className="space-y-2">
                  <Label className="flex items-center gap-1 text-sm font-medium">
                    {t("requestForm.domesticMethod")}
                    <RequiredAsterisk />
                  </Label>
                  <Select
                    value={formData.domesticTransportMethod}
                    onValueChange={(value) => {
                      setFormData({
                        ...formData,
                        domesticTransportMethod: value,
                      });
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={t("requestForm.selectDomesticMethod")} />
                    </SelectTrigger>
                    <SelectContent>
                      {transportMethodOptions?.domestic_methods.map((method) => (
                        <SelectItem key={method.id} value={method.name}>
                          <div className="space-y-1 text-right">
                            <div className="font-medium">{getTransportLabel(method, language)}</div>
                            {method.description && (
                              <div className="text-xs text-muted-foreground">{getTransportDescription(method, t("requestForm.domesticMethodFallback"))}</div>
                            )}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
          )}

          {/* Forwarder Suggestion Message */}
          {formData.transportMethodPreference === "forwarder_suggestion" && (
            <div className="p-4 border rounded-lg bg-blue-50 border-blue-200">
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-5 h-5 text-blue-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-blue-900">
                    {t("requestForm.forwarderSuggestionSelected")}
                  </p>
                  <p className="text-xs text-blue-700 mt-1">
                    {t("requestForm.forwarderSuggestionHelp")}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Cargo Details Toggle Button */}
        <div className="space-y-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => setShowCargoDetails(!showCargoDetails)}
            className="w-full flex items-center justify-between"
          >
            <div className="flex items-center gap-2">
              <Package className="w-4 h-4 text-primary" />
              <span>{t("requestForm.cargoOptional")}</span>
            </div>
            {showCargoDetails ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
          <p className={helperTextClass}>
            {t("requestForm.cargoHelp")}
          </p>
          <p className={helperTextClass}>
            {t("requestForm.cargoOptionalHelp")}
          </p>
        </div>

        {/* Cargo Details Form */}
        {showCargoDetails && (
          <div className="space-y-4 p-4 bg-muted/30 rounded-lg border">
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground mb-3">
              <Package className="w-4 h-4 text-primary" />
              {t("requestForm.cargoDetails")}
            </div>

            {/* Cargo Description */}
            <div className="space-y-2">
              <Label htmlFor="cargoDescription" className="flex items-center gap-2 text-sm font-medium">
                <FileText className="w-4 h-4 text-muted-foreground" />
                {t("requestForm.cargoDescription")}
              </Label>
              <Input
                id="cargoDescription"
                placeholder={t("requestForm.cargoDescriptionPlaceholder")}
                value={formData.cargoDescription}
                onChange={(e) => {
                  setFormData({
                    ...formData,
                    cargoDescription: e.target.value,
                  });
                }}
              />
            </div>

            {/* Weight and Volume Row */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="cargoWeight" className="flex items-center gap-2 text-sm font-medium">
                  <Weight className="w-4 h-4 text-muted-foreground" />
                  {t("common.weightKg")}
                </Label>
                <Input
                  id="cargoWeight"
                  type="number"
                  placeholder="0"
                  value={formData.cargoWeight}
                  onChange={(e) => {
                    setFormData({
                      ...formData,
                      cargoWeight: e.target.value,
                    });
                  }}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="cargoVolume" className="flex items-center gap-2 text-sm font-medium">
                  <Package className="w-4 h-4 text-muted-foreground" />
                  {t("common.volumeM3")}
                </Label>
                <Input
                  id="cargoVolume"
                  type="number"
                  step="0.01"
                  placeholder="0"
                  value={formData.cargoVolume}
                  onChange={(e) => {
                    setFormData({
                      ...formData,
                      cargoVolume: e.target.value,
                    });
                  }}
                />
              </div>
            </div>

            {/* Cargo Value */}
            <div className="space-y-2">
              <Label htmlFor="cargoValue" className="flex items-center gap-2 text-sm font-medium">
                <DollarSign className="w-4 h-4 text-muted-foreground" />
                {t("requestForm.cargoValueToman")}
              </Label>
              <Input
                id="cargoValue"
                type="number"
                placeholder="0"
                value={formData.cargoValue}
                onChange={(e) => {
                  setFormData({
                    ...formData,
                    cargoValue: e.target.value,
                  });
                }}
              />
            </div>

            {/* Special Instructions */}
            <div className="space-y-2">
              <Label htmlFor="specialInstructions" className="flex items-center gap-2 text-sm font-medium">
                <FileText className="w-4 h-4 text-muted-foreground" />
                {t("requestForm.specialInstructions")}
              </Label>
              <Input
                id="specialInstructions"
                placeholder={t("requestForm.specialInstructionsPlaceholder")}
                value={formData.specialInstructions}
                onChange={(e) => {
                  setFormData({
                    ...formData,
                    specialInstructions: e.target.value,
                  });
                }}
              />
            </div>

            {/* Dates Row */}
            <div className="grid grid-cols-2 gap-3">
              {shippingType === "domestic" && (
                <>
                  <JalaliDateInput
                    id="pickupDate"
                    label={t("requestForm.pickupDate")}
                    selectLabel={t("requestForm.selectJalaliDate")}
                    nextMonthLabel={t("requestForm.nextMonth")}
                    previousMonthLabel={t("requestForm.previousMonth")}
                    clearLabel={t("requestForm.clearDate")}
                    value={formData.pickupDate}
                    onChange={(pickupDate) => {
                      setFormData({
                        ...formData,
                        pickupDate,
                      });
                    }}
                  />
                  <JalaliDateInput
                    id="deliveryDate"
                    label={t("requestForm.deliveryDate")}
                    selectLabel={t("requestForm.selectJalaliDate")}
                    nextMonthLabel={t("requestForm.nextMonth")}
                    previousMonthLabel={t("requestForm.previousMonth")}
                    clearLabel={t("requestForm.clearDate")}
                    value={formData.deliveryDate}
                    onChange={(deliveryDate) => {
                      setFormData({
                        ...formData,
                        deliveryDate,
                      });
                    }}
                  />
                </>
              )}
              {shippingType !== "domestic" && (
                <div className="space-y-2">
                <Label htmlFor="pickupDate" className="flex items-center gap-2 text-sm font-medium">
                  <Calendar className="w-4 h-4 text-muted-foreground" />
                  {t("requestForm.pickupDate")}
                </Label>
                <Input
                  id="pickupDate"
                  type="date"
                  value={formData.pickupDate}
                  onChange={(e) => {
                    setFormData({
                      ...formData,
                      pickupDate: e.target.value,
                    });
                  }}
                />
                </div>
              )}
              {shippingType !== "domestic" && (
                <div className="space-y-2">
                <Label htmlFor="deliveryDate" className="flex items-center gap-2 text-sm font-medium">
                  <Calendar className="w-4 h-4 text-muted-foreground" />
                  {t("requestForm.deliveryDate")}
                </Label>
                <Input
                  id="deliveryDate"
                  type="date"
                  value={formData.deliveryDate}
                  onChange={(e) => {
                    setFormData({
                      ...formData,
                      deliveryDate: e.target.value,
                    });
                  }}
                />
                </div>
              )}
            </div>
            {shippingType === "domestic" && (
              <p className={helperTextClass}>
                {t("requestForm.domesticDateHelp")}
              </p>
            )}
            <p className={shippingType === "domestic" ? "hidden" : helperTextClass}>
              {t("requestForm.browserDateHelp")}
            </p>
          </div>
        )}

        {/* Submit Button */}
        <Button
          onClick={handleSubmit}
          className="w-full bg-gradient-primary hover:shadow-primary font-medium"
          size="lg"
          disabled={isSubmitting}
        >
          <Send className="w-4 h-4 ml-2" />
          {isSubmitting ? t("requestFlow.sending") : t("shipping.submit")}
        </Button>
      </CardContent>
    </Card>
  );
};

export default LocationForm;
