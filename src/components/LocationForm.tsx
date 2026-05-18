import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, MapPin, Send, CheckCircle2, Phone, Truck, Package, Calendar, Weight, DollarSign, FileText, ChevronDown, ChevronUp, User } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import RequestConfirmation from "./RequestConfirmation";
import {
  City,
  County,
  Province,
  Country,
  InternationalCity,
  IranPort,
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
  fetchRecommendedPorts,
  fetchTransportMethodOptions,
  submitShipmentRequest,
} from "@/lib/api";

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
  // Iran entry point fields (for international shipping to Iran)
  iranEntryPort: string;
  iranEntryProvince: string;
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

const LocationForm = ({ shippingType, onBack }: LocationFormProps) => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [provinces, setProvinces] = useState<Province[]>([]);
  const [originCounties, setOriginCounties] = useState<County[]>([]);
  const [destinationCounties, setDestinationCounties] = useState<County[]>([]);
  const [originCities, setOriginCities] = useState<City[]>([]);
  const [destinationCities, setDestinationCities] = useState<City[]>([]);
  const [countries, setCountries] = useState<Country[]>([]);
  const [originInternationalCities, setOriginInternationalCities] = useState<InternationalCity[]>([]);
  const [destinationInternationalCities, setDestinationInternationalCities] = useState<InternationalCity[]>([]);
  const [iranPorts, setIranPorts] = useState<IranPort[]>([]);
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
    // Iran entry point fields
    iranEntryPort: "",
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
          title: "خطا",
          description: "خطا در دریافت اطلاعات پایه (استان‌ها/روش‌های حمل). لطفاً بک‌اند را بررسی کنید.",
          variant: "destructive",
        });
      }
    };

    fetchTransportOptions();
  }, [toast]);

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
            title: "خطا",
            description: "خطا در دریافت اطلاعات پایه (استان‌ها/روش‌های حمل). لطفاً بک‌اند را بررسی کنید.",
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
            title: "خطا در دریافت کشورها",
            description: error instanceof Error ? error.message : "دریافت اطلاعات کشورها با خطا مواجه شد.",
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
            title: "خطا در دریافت بنادر ایران",
            description: error instanceof Error ? error.message : "دریافت اطلاعات بنادر با خطا مواجه شد.",
            variant: "destructive",
          });
        }
      } finally {
        if (active) {
          setIsLoadingIranPorts(false);
        }
      }
    };

    if (shippingType === "domestic") {
      loadProvinces();
    } else {
      loadCountries();
      loadIranPorts(); // Load Iran ports for international shipping
    }

    return () => {
      active = false;
    };
  }, [toast, shippingType]);

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
            title: "خطا در دریافت شهرهای مبدا",
            description: error instanceof Error ? error.message : "دریافت شهرها با خطا مواجه شد.",
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
  }, [formData.originCountry, toast]);

  // Load international cities for destination country
  useEffect(() => {
    let active = true;
    if (!formData.destCountry) {
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
            title: "خطا در دریافت شهرهای مقصد",
            description: error instanceof Error ? error.message : "دریافت شهرها با خطا مواجه شد.",
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
  }, [formData.destCountry, toast]);

  // Load recommended ports when Iran entry port is selected
  useEffect(() => {
    let active = true;
    if (!formData.iranEntryPort) {
      setRecommendedPorts([]);
      setIsLoadingRecommendedPorts(false);
      return () => {
        active = false;
      };
    }

    const portId = Number(formData.iranEntryPort);
    setIsLoadingRecommendedPorts(true);
    setRecommendedPorts([]);

    const loadRecommendedPorts = async () => {
      try {
        // Get the selected port to find its province
        const selectedPort = iranPorts.find(port => port.id === portId);
        if (selectedPort && active) {
          const data = await fetchRecommendedPorts(selectedPort.province_id);
          if (active) {
            setRecommendedPorts(data);
            // Auto-select the province if not already selected
            if (!formData.iranEntryProvince) {
              setFormData(prev => ({
                ...prev,
                iranEntryProvince: selectedPort.province_id.toString()
              }));
            }
          }
        }
      } catch (error) {
        if (active) {
          toast({
            title: "خطا در دریافت بنادر پیشنهادی",
            description: error instanceof Error ? error.message : "دریافت بنادر پیشنهادی با خطا مواجه شد.",
            variant: "destructive",
          });
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
  }, [formData.iranEntryPort, iranPorts, formData.iranEntryProvince, toast]);

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
    return {
      origin: [oCity?.name, oCountry?.name].filter(Boolean).join("، ") || "—",
      destination: [dCity?.name, dCountry?.name].filter(Boolean).join("، ") || "—",
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
    provinceOptions,
    originCountyOptions,
    destinationCountyOptions,
    originCityOptions,
    destinationCityOptions,
    countryOptions,
    originInternationalCityOptions,
    destinationInternationalCityOptions,
  ]);

  const handleSubmit = async () => {
    // Validate required fields based on shipping type
    let isValid = true;
    let errorMessage = "";

    if (!formData.phoneNumber) {
      isValid = false;
      errorMessage = "لطفاً شماره تماس را وارد کنید";
    } else if (formData.transportMethodPreference === "customer_choice") {
      // If customer wants to choose, validate that they've selected methods
      if (shippingType === "international" && !formData.internationalTransportMethod) {
        isValid = false;
        errorMessage = "لطفاً روش حمل بین‌المللی را انتخاب کنید";
      } else if (shippingType === "domestic" && !formData.domesticTransportMethod) {
        isValid = false;
        errorMessage = "لطفاً روش حمل داخلی را انتخاب کنید";
      }
    }
    
    if (isValid && shippingType === "domestic") {
      if (!formData.originProvince || !formData.originCounty || !formData.originCity ||
          !formData.destinationProvince || !formData.destinationCounty || !formData.destinationCity) {
        isValid = false;
        errorMessage = "لطفاً همه فیلدهای مبدا و مقصد را انتخاب کنید";
      }
    } else if (shippingType === "international") {
      if (!formData.originCountry || !formData.originCityInternational ||
          !formData.destCountry || !formData.destCityInternational) {
        isValid = false;
        errorMessage = "لطفاً کشور و شهر/بندر مبدا و مقصد را انتخاب کنید";
      }
      
      // Check if destination is Iran and validate Iran entry point
      const destCountry = countries.find(c => c.id.toString() === formData.destCountry);
      if (destCountry?.name === "ایران") {
        if (!formData.iranEntryPort || !formData.iranEntryProvince) {
          isValid = false;
          errorMessage = "برای ارسال به ایران، لطفاً بندر و استان ورود را انتخاب کنید";
        }
      }
    }

    if (!isValid) {
      toast({
        title: "خطا",
        description: errorMessage,
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
        payload.origin_county_id = Number(formData.originCounty);
        payload.origin_city_id = Number(formData.originCity);
        payload.dest_province_id = Number(formData.destinationProvince);
        payload.dest_county_id = Number(formData.destinationCounty);
        payload.dest_city_id = Number(formData.destinationCity);
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
        payload.dest_city_international = destCity?.name || "";
        payload.dest_address_international = formData.destAddressInternational;
        
        // Add Iran entry point data if destination is Iran
        if (destCountry?.name === "ایران") {
          const selectedPort = iranPorts.find(p => p.id.toString() === formData.iranEntryPort);
          const selectedProvince = provinces.find(p => p.id.toString() === formData.iranEntryProvince);
          
          payload.iran_entry_port = selectedPort?.name_fa || "";
          payload.iran_entry_province = selectedProvince?.name || "";
          payload.iran_entry_port_id = Number(formData.iranEntryPort);
          payload.iran_entry_province_id = Number(formData.iranEntryProvince);
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
        title: "ثبت درخواست ناموفق بود",
        description: error instanceof Error ? error.message : "خطایی در ثبت درخواست رخ داد.",
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
        payload.origin_county_id = Number(formData.originCounty);
        payload.origin_city_id = Number(formData.originCity);
        payload.dest_province_id = Number(formData.destinationProvince);
        payload.dest_county_id = Number(formData.destinationCounty);
        payload.dest_city_id = Number(formData.destinationCity);
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
        payload.dest_city_international = destCity?.name || "";
        payload.dest_address_international = formData.destAddressInternational;
        
        // Add Iran entry point data if destination is Iran
        if (destCountry?.name === "ایران") {
          const selectedPort = iranPorts.find(p => p.id.toString() === formData.iranEntryPort);
          const selectedProvince = provinces.find(p => p.id.toString() === formData.iranEntryProvince);
          
          payload.iran_entry_port = selectedPort?.name_fa || "";
          payload.iran_entry_province = selectedProvince?.name || "";
          payload.iran_entry_port_id = Number(formData.iranEntryPort);
          payload.iran_entry_province_id = Number(formData.iranEntryProvince);
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
        title: "درخواست ثبت شد",
        description: `شماره پیگیری شما: ${trackingCode}. کارشناس ما ظرف ۲ ساعت با شما تماس خواهد گرفت.`,
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
    setSubmittedTrackingCode(null);
    // Reset international cities arrays
    setOriginInternationalCities([]);
    setDestinationInternationalCities([]);
  };

  if (isSubmitted) {
    return (
      <Card className="w-full max-w-md bg-gradient-card shadow-lg border-0">
        <CardContent className="p-6 text-center">
          <div className="mb-4">
            <CheckCircle2 className="w-16 h-16 text-secondary mx-auto" />
          </div>
          <h3 className="text-xl font-bold text-foreground mb-2">درخواست شما ثبت شد!</h3>
          {submittedTrackingCode && (
            <div className="mb-4 p-4 bg-muted/50 rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">شماره پیگیری</p>
              <p className="text-xl font-mono font-bold text-foreground">{submittedTrackingCode}</p>
            </div>
          )}
          <p className="text-muted-foreground mb-6">
            کارشناس ما ظرف ۲ ساعت با شما تماس خواهد گرفت و جزئیات ارسال را هماهنگ خواهد کرد.
          </p>
          <div className="space-y-2">
            <Button
              onClick={() => submittedTrackingCode && navigate(`/customer/track/${submittedTrackingCode}`)}
              className="w-full bg-gradient-primary hover:shadow-primary"
              disabled={!submittedTrackingCode}
            >
              پیگیری درخواست
            </Button>
            <Button onClick={resetForm} variant="outline" className="w-full">
              ثبت درخواست جدید
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
              بازگشت
            </Button>
          )}
          <div className="flex-1"></div>
        </div>
        <CardTitle className="text-xl font-bold flex items-center justify-center gap-2">
          <MapPin className="w-5 h-5 text-primary" />
          {shippingType === "domestic" ? "انتخاب مبدا و مقصد داخلی" : "انتخاب مبدا و مقصد بین‌المللی"}
        </CardTitle>
        <p className="text-muted-foreground text-sm">
          {shippingType === "domestic" 
            ? "برای ارسال مرسوله خود، مبدا و مقصد را انتخاب کنید"
            : "برای ارسال بین‌المللی، کشور و شهر مبدا و مقصد را وارد کنید"
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

            {/* Domestic Destination Section */}
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
          </>
        ) : (
          <>
            {/* International Origin Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-primary">
                <div className="w-3 h-3 bg-primary rounded-full"></div>
                مبدا ارسال (بین‌المللی)
              </div>
              
              <div className="space-y-3 pr-5">
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
                    <SelectValue placeholder={isLoadingCountries ? "در حال بارگذاری..." : "انتخاب کشور مبدا"} />
                  </SelectTrigger>
                  <SelectContent>
                    {countryOptions.map((country) => (
                      <SelectItem key={country.id} value={country.id.toString()}>
                        {country.name}
                      </SelectItem>
                    ))}
                    {countryOptions.length === 0 && !isLoadingCountries && (
                      <SelectItem value="no-origin-country" disabled>
                        کشوری موجود نیست
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>

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
                          ? "ابتدا کشور را انتخاب کنید"
                          : isLoadingOriginInternationalCities
                            ? "در حال بارگذاری..."
                            : "انتخاب شهر/بندر مبدا"
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
                        شهری یافت نشد
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>

                <div className="space-y-2">
                  <Label htmlFor="originAddressInternational" className="flex items-center gap-2 text-sm font-medium">
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    آدرس مبدا (اختیاری)
                  </Label>
                  <Input
                    id="originAddressInternational"
                    placeholder="آدرس کامل مبدا را وارد کنید"
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
                مقصد ارسال (بین‌المللی)
              </div>
              
              <div className="space-y-3 pr-5">
                <Select
                  value={formData.destCountry}
                  onValueChange={(value) => {
                    setFormData({
                      ...formData,
                      destCountry: value,
                      destCityInternational: "",
                    });
                  }}
                  disabled={isLoadingCountries && countryOptions.length === 0}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={isLoadingCountries ? "در حال بارگذاری..." : "انتخاب کشور مقصد"} />
                  </SelectTrigger>
                  <SelectContent>
                    {countryOptions.map((country) => (
                      <SelectItem key={country.id} value={country.id.toString()}>
                        {country.name}
                      </SelectItem>
                    ))}
                    {countryOptions.length === 0 && !isLoadingCountries && (
                      <SelectItem value="no-dest-country" disabled>
                        کشوری موجود نیست
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>

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
                          ? "ابتدا کشور را انتخاب کنید"
                          : isLoadingDestinationInternationalCities
                            ? "در حال بارگذاری..."
                            : "انتخاب شهر/بندر مقصد"
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
                        شهری یافت نشد
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>

                <div className="space-y-2">
                  <Label htmlFor="destAddressInternational" className="flex items-center gap-2 text-sm font-medium">
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    آدرس مقصد (اختیاری)
                  </Label>
                  <Input
                    id="destAddressInternational"
                    placeholder="آدرس کامل مقصد را وارد کنید"
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

            {/* Iran Entry Point Section - Only show if destination is Iran */}
            {formData.destCountry && countries.find(c => c.id.toString() === formData.destCountry)?.name === "ایران" && (
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
                    مرحله ۳: تعیین نقطه ورود به ایران
                  </div>
                  
                  <div className="space-y-3 pr-5">
                    <Select
                      value={formData.iranEntryPort}
                      onValueChange={(value) => {
                        setFormData({
                          ...formData,
                          iranEntryPort: value,
                          iranEntryProvince: "", // Reset province when port changes
                        });
                      }}
                      disabled={isLoadingIranPorts && iranPorts.length === 0}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={isLoadingIranPorts ? "در حال بارگذاری..." : "انتخاب بندر ورود"} />
                      </SelectTrigger>
                      <SelectContent>
                        {iranPorts.map((port) => (
                          <SelectItem key={port.id} value={port.id.toString()}>
                            {port.name_fa} ({port.port_type === "sea" ? "دریایی" : port.port_type === "air" ? "هوایی" : "زمینی"})
                            {port.is_major_port && " ⭐"}
                          </SelectItem>
                        ))}
                        {iranPorts.length === 0 && !isLoadingIranPorts && (
                          <SelectItem value="no-port" disabled>
                            بندری موجود نیست
                          </SelectItem>
                        )}
                      </SelectContent>
                    </Select>

                    {/* Show recommended ports when a port is selected */}
                    {formData.iranEntryPort && recommendedPorts.length > 0 && (
                      <div className="space-y-2">
                        <Label className="text-sm font-medium text-muted-foreground">
                          بنادر پیشنهادی برای این استان:
                        </Label>
                        <div className="space-y-1">
                          {recommendedPorts.slice(0, 3).map((port, index) => (
                            <div key={port.port_id} className="flex items-center justify-between p-2 bg-accent rounded-md text-sm">
                              <span className="flex items-center gap-2">
                                {index === 0 && "🥇"} {index === 1 && "🥈"} {index === 2 && "🥉"}
                                {port.port_name_fa} ({port.port_type === "sea" ? "دریایی" : port.port_type === "air" ? "هوایی" : "زمینی"})
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {port.estimated_days} روز
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <Select
                      value={formData.iranEntryProvince}
                      onValueChange={(value) => {
                        setFormData({
                          ...formData,
                          iranEntryProvince: value,
                        });
                      }}
                      disabled={!formData.iranEntryPort || isLoadingRecommendedPorts}
                    >
                      <SelectTrigger>
                        <SelectValue
                          placeholder={
                            !formData.iranEntryPort
                              ? "ابتدا بندر را انتخاب کنید"
                              : isLoadingRecommendedPorts
                                ? "در حال بارگذاری..."
                                : "انتخاب استان ورود"
                          }
                        />
                      </SelectTrigger>
                      <SelectContent>
                        {provinceOptions.map((province) => (
                          <SelectItem key={province.id} value={province.id.toString()}>
                            {province.name}
                          </SelectItem>
                        ))}
                        {provinceOptions.length === 0 && !isLoadingProvinces && (
                          <SelectItem value="no-province" disabled>
                            استانی موجود نیست
                          </SelectItem>
                        )}
                      </SelectContent>
                    </Select>

                    {/* Show port information */}
                    {formData.iranEntryPort && (
                      <div className="p-3 bg-accent rounded-md">
                        <div className="text-sm">
                          {(() => {
                            const selectedPort = iranPorts.find(p => p.id.toString() === formData.iranEntryPort);
                            return selectedPort ? (
                              <div className="space-y-1">
                                <div className="font-medium">{selectedPort.name_fa}</div>
                                <div className="text-muted-foreground text-xs">
                                  {selectedPort.description}
                                </div>
                                <div className="text-muted-foreground text-xs">
                                  نوع: {selectedPort.port_type === "sea" ? "بندر دریایی" : selectedPort.port_type === "air" ? "فرودگاه" : "بندر زمینی"}
                                </div>
                              </div>
                            ) : null;
                          })()}
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
            اطلاعات مشتری (اختیاری)
          </Label>
          
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="customerFirstName" className="flex items-center gap-2 text-sm font-medium">
                <User className="w-4 h-4 text-muted-foreground" />
                نام
              </Label>
              <Input
                id="customerFirstName"
                placeholder="نام خود را وارد کنید"
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
                نام خانوادگی
              </Label>
              <Input
                id="customerLastName"
                placeholder="نام خانوادگی خود را وارد کنید"
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
            برای خدمات بهتر، نام خود را وارد کنید (اختیاری)
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

        {/* Transport Method Section */}
        <div className="space-y-4">
          <Label className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Truck className="w-4 h-4 text-primary" />
            روش حمل
          </Label>
          
          {/* Transport Method Preference */}
          <div className="space-y-2">
            <Label className="text-sm text-muted-foreground">نحوه انتخاب روش حمل</Label>
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
                <SelectValue placeholder="انتخاب نحوه تعیین روش حمل" />
              </SelectTrigger>
              <SelectContent>
                {transportMethodOptions?.preference_options.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    <div>
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
              {shippingType === "international" && (
                <div className="space-y-2">
                  <Label className="text-sm font-medium">روش حمل بین‌المللی</Label>
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
                      <SelectValue placeholder="انتخاب روش حمل بین‌المللی" />
                    </SelectTrigger>
                    <SelectContent>
                      {transportMethodOptions?.international_methods.map((method) => (
                        <SelectItem key={method.id} value={method.name}>
                          <div>
                            <div className="font-medium">{method.name_fa}</div>
                            {method.description && (
                              <div className="text-xs text-muted-foreground">{method.description}</div>
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
                  <Label className="text-sm font-medium">روش حمل داخلی</Label>
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
                      <SelectValue placeholder="انتخاب روش حمل داخلی" />
                    </SelectTrigger>
                    <SelectContent>
                      {transportMethodOptions?.domestic_methods.map((method) => (
                        <SelectItem key={method.id} value={method.name}>
                          <div>
                            <div className="font-medium">{method.name_fa}</div>
                            {method.description && (
                              <div className="text-xs text-muted-foreground">{method.description}</div>
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
                    پیشنهاد فورواردر انتخاب شده
                  </p>
                  <p className="text-xs text-blue-700 mt-1">
                    کارشناسان ما بر اساس مشخصات کالا و مسیر، بهترین روش حمل را به شما پیشنهاد خواهند داد.
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
              <span>مشخصات کالا (اختیاری)</span>
            </div>
            {showCargoDetails ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
          <p className="text-xs text-muted-foreground">
            برای اطلاعات دقیق‌تر در مورد کالای خود، مشخصات را وارد کنید
          </p>
        </div>

        {/* Cargo Details Form */}
        {showCargoDetails && (
          <div className="space-y-4 p-4 bg-muted/30 rounded-lg border">
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground mb-3">
              <Package className="w-4 h-4 text-primary" />
              جزئیات کالا
            </div>

            {/* Cargo Description */}
            <div className="space-y-2">
              <Label htmlFor="cargoDescription" className="flex items-center gap-2 text-sm font-medium">
                <FileText className="w-4 h-4 text-muted-foreground" />
                توضیحات کالا
              </Label>
              <Input
                id="cargoDescription"
                placeholder="مثال: لوازم الکترونیکی، پوشاک، مواد غذایی..."
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
                  وزن (کیلوگرم)
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
                  حجم (متر مکعب)
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
                ارزش کالا (تومان)
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
                دستورالعمل‌های خاص
              </Label>
              <Input
                id="specialInstructions"
                placeholder="مثال: مراقبت ویژه، دمای خاص، و..."
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
              <div className="space-y-2">
                <Label htmlFor="pickupDate" className="flex items-center gap-2 text-sm font-medium">
                  <Calendar className="w-4 h-4 text-muted-foreground" />
                  تاریخ تحویل
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
              <div className="space-y-2">
                <Label htmlFor="deliveryDate" className="flex items-center gap-2 text-sm font-medium">
                  <Calendar className="w-4 h-4 text-muted-foreground" />
                  تاریخ تحویل
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
            </div>
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
          {isSubmitting ? "در حال ارسال..." : "درخواست ارسال"}
        </Button>
      </CardContent>
    </Card>
  );
};

export default LocationForm;