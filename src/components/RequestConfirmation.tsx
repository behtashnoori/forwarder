import React, { useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ArrowLeft, Send, User, Phone, MapPin, Package, Calendar, FileText } from "lucide-react";

export interface LocationDisplayPayload {
  origin: string;
  destination: string;
}

interface RequestConfirmationFormData {
  phoneNumber: string;
  customerFirstName?: string;
  customerLastName?: string;
  originCityName?: string;
  originCountyName?: string;
  originProvinceName?: string;
  destinationCityName?: string;
  destinationCountyName?: string;
  destinationProvinceName?: string;
  originCityInternationalName?: string;
  originCountryName?: string;
  destCityInternationalName?: string;
  destCountryName?: string;
  transportMethodPreference?: string;
  domesticTransportMethodName?: string;
  internationalTransportMethodName?: string;
  cargoDescription?: string;
  cargoWeight?: string;
  cargoVolume?: string;
  cargoValue?: string;
  pickupDate?: string;
  deliveryDate?: string;
  specialInstructions?: string;
}

interface RequestConfirmationProps {
  formData: RequestConfirmationFormData;
  shippingType: "domestic" | "international";
  onBack: () => void;
  onSubmit: () => void;
  isSubmitting: boolean;
  /** Resolved origin/destination labels; when provided, used instead of formData name fields */
  locationDisplay?: LocationDisplayPayload;
}

const RequestConfirmation: React.FC<RequestConfirmationProps> = ({
  formData,
  shippingType,
  onBack,
  onSubmit,
  isSubmitting,
  locationDisplay: locationDisplayProp,
}) => {
  useEffect(() => {
    if (typeof window !== "undefined") {
      console.log("[RequestConfirmation] formData received:", formData);
    }
  }, [formData]);

  const handleFinalSubmit = () => {
    onSubmit();
  };

  const getLocationDisplayFallback = (): LocationDisplayPayload => {
    if (shippingType === "domestic") {
      return {
        origin: [formData.originCityName, formData.originCountyName, formData.originProvinceName].filter(Boolean).join("، ") || "—",
        destination: [formData.destinationCityName, formData.destinationCountyName, formData.destinationProvinceName].filter(Boolean).join("، ") || "—",
      };
    }
    return {
      origin: [formData.originCityInternationalName, formData.originCountryName].filter(Boolean).join("، ") || "—",
      destination: [formData.destCityInternationalName, formData.destCountryName].filter(Boolean).join("، ") || "—",
    };
  };

  const locationDisplay = locationDisplayProp ?? getLocationDisplayFallback();

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-foreground mb-2">
          تایید و ارسال درخواست
        </h2>
        <p className="text-muted-foreground">
          لطفاً اطلاعات زیر را بررسی کرده و درخواست خود را تایید کنید
        </p>
      </div>

      {/* Request Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            خلاصه درخواست
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Contact Information */}
          <div className="space-y-3">
            <h3 className="font-semibold text-lg flex items-center gap-2">
              <User className="w-5 h-5" />
              اطلاعات تماس
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center gap-2">
                <Phone className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm">شماره تماس:</span>
                <span className="font-medium">{formData.phoneNumber}</span>
              </div>
              {(formData.customerFirstName || formData.customerLastName) && (
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm">نام:</span>
                  <span className="font-medium">
                    {formData.customerFirstName} {formData.customerLastName}
                  </span>
                </div>
              )}
            </div>
          </div>

          <Separator />

          {/* Location Information */}
          <div className="space-y-3">
            <h3 className="font-semibold text-lg flex items-center gap-2">
              <MapPin className="w-5 h-5" />
              اطلاعات مبدا و مقصد
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">مبدا</Badge>
                </div>
                <p className="text-sm text-muted-foreground">{locationDisplay.origin}</p>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">مقصد</Badge>
                </div>
                <p className="text-sm text-muted-foreground">{locationDisplay.destination}</p>
              </div>
            </div>
          </div>

          <Separator />

          {/* Transport Method */}
          <div className="space-y-3">
            <h3 className="font-semibold text-lg flex items-center gap-2">
              <Package className="w-5 h-5" />
              روش حمل
            </h3>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-sm">نوع ارسال:</span>
                <Badge variant="secondary">
                  {shippingType === "domestic" ? "حمل داخلی" : "حمل بین‌المللی"}
                </Badge>
              </div>
              {formData.transportMethodPreference === "customer_choice" && (
                <div className="flex items-center gap-2">
                  <span className="text-sm">روش انتخابی:</span>
                  <span className="font-medium">
                    {shippingType === "domestic" 
                      ? formData.domesticTransportMethodName 
                      : formData.internationalTransportMethodName}
                  </span>
                </div>
              )}
              {formData.transportMethodPreference === "forwarder_suggestion" && (
                <div className="flex items-center gap-2">
                  <span className="text-sm">پیشنهاد فورواردر</span>
                </div>
              )}
            </div>
          </div>

          {/* Cargo Details */}
          {(formData.cargoDescription || formData.cargoWeight || formData.cargoVolume || formData.cargoValue) && (
            <>
              <Separator />
              <div className="space-y-3">
                <h3 className="font-semibold text-lg flex items-center gap-2">
                  <Package className="w-5 h-5" />
                  جزئیات مرسوله
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {formData.cargoDescription && (
                    <div>
                      <span className="text-sm text-muted-foreground">توضیحات:</span>
                      <p className="text-sm font-medium">{formData.cargoDescription}</p>
                    </div>
                  )}
                  {formData.cargoWeight && (
                    <div>
                      <span className="text-sm text-muted-foreground">وزن (کیلوگرم):</span>
                      <p className="text-sm font-medium">{formData.cargoWeight}</p>
                    </div>
                  )}
                  {formData.cargoVolume && (
                    <div>
                      <span className="text-sm text-muted-foreground">حجم (متر مکعب):</span>
                      <p className="text-sm font-medium">{formData.cargoVolume}</p>
                    </div>
                  )}
                  {formData.cargoValue && (
                    <div>
                      <span className="text-sm text-muted-foreground">ارزش (ریال):</span>
                      <p className="text-sm font-medium">{formData.cargoValue}</p>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}

          {/* Dates */}
          {(formData.pickupDate || formData.deliveryDate) && (
            <>
              <Separator />
              <div className="space-y-3">
                <h3 className="font-semibold text-lg flex items-center gap-2">
                  <Calendar className="w-5 h-5" />
                  تاریخ‌های مهم
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {formData.pickupDate && (
                    <div>
                      <span className="text-sm text-muted-foreground">تاریخ تحویل:</span>
                      <p className="text-sm font-medium">{formData.pickupDate}</p>
                    </div>
                  )}
                  {formData.deliveryDate && (
                    <div>
                      <span className="text-sm text-muted-foreground">تاریخ تحویل:</span>
                      <p className="text-sm font-medium">{formData.deliveryDate}</p>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}

          {/* Special Instructions */}
          {formData.specialInstructions && (
            <>
              <Separator />
              <div className="space-y-3">
                <h3 className="font-semibold text-lg">دستورالعمل‌های ویژه</h3>
                <p className="text-sm text-muted-foreground">{formData.specialInstructions}</p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-4">
        <Button
          onClick={onBack}
          variant="outline"
          className="flex-1"
          disabled={isSubmitting}
        >
          <ArrowLeft className="w-4 h-4 ml-2" />
          بازگشت و ویرایش
        </Button>
        <Button
          onClick={handleFinalSubmit}
          className="flex-1 bg-gradient-primary hover:shadow-primary"
          disabled={isSubmitting}
        >
          <Send className="w-4 h-4 ml-2" />
          {isSubmitting ? "در حال ارسال..." : "تایید و ارسال درخواست"}
        </Button>
      </div>
    </div>
  );
};

export default RequestConfirmation;
