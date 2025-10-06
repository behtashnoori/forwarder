import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { CheckCircle, ArrowLeft, Send, User, Phone, MapPin, Package, Calendar, FileText, ExternalLink } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface RequestConfirmationProps {
  formData: any;
  shippingType: "domestic" | "international";
  onBack: () => void;
  onSubmit: (gamificationCustomerId?: number) => void;
  isSubmitting: boolean;
}

const RequestConfirmation: React.FC<RequestConfirmationProps> = ({
  formData,
  shippingType,
  onBack,
  onSubmit,
  isSubmitting
}) => {
  const [showEmailRegistration, setShowEmailRegistration] = useState(false);
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [isRegistering, setIsRegistering] = useState(false);
  const [registeredCustomerId, setRegisteredCustomerId] = useState<number | null>(null);
  const { toast } = useToast();
  const navigate = useNavigate();

  const handleEmailRegistration = async () => {
    if (!email.trim()) {
      toast({
        title: "خطا",
        description: "لطفاً ایمیل خود را وارد کنید",
        variant: "destructive",
      });
      return;
    }

    setIsRegistering(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/customer/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: email.trim(),
          phone: formData.phoneNumber,
          first_name: firstName.trim() || null,
          last_name: lastName.trim() || null,
        }),
      });

      const data = await response.json();
      
      if (response.ok) {
        setRegisteredCustomerId(data.customer_id);
        toast({
          title: "ثبت‌نام موفق",
          description: "ایمیل تایید به آدرس شما ارسال شد. لطفاً ایمیل خود را تایید کنید تا بتوانید از امکانات ویژه استفاده کنید.",
          duration: 8000,
        });
      } else if (data.customer_id) {
        // Customer already exists
        setRegisteredCustomerId(data.customer_id);
        toast({
          title: "اطلاعات موجود",
          description: "این ایمیل قبلاً ثبت شده است. می‌توانید از امکانات ویژه استفاده کنید.",
          duration: 6000,
        });
      } else {
        toast({
          title: "خطا",
          description: data.message || "خطا در ثبت‌نام",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "خطا",
        description: "خطا در ارتباط با سرور",
        variant: "destructive",
      });
    } finally {
      setIsRegistering(false);
    }
  };

  const handleFinalSubmit = () => {
    onSubmit(registeredCustomerId || undefined);
  };

  const getLocationDisplay = () => {
    if (shippingType === "domestic") {
      return {
        origin: `${formData.originCityName}، ${formData.originCountyName}، ${formData.originProvinceName}`,
        destination: `${formData.destinationCityName}، ${formData.destinationCountyName}، ${formData.destinationProvinceName}`
      };
    } else {
      return {
        origin: `${formData.originCityInternationalName}، ${formData.originCountryName}`,
        destination: `${formData.destCityInternationalName}، ${formData.destCountryName}`
      };
    }
  };

  const locationDisplay = getLocationDisplay();

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

      {/* Email Registration for Gamification */}
      {!registeredCustomerId ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              امکانات ویژه برای مشتریان
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-blue-50 dark:bg-blue-950/20 p-4 rounded-lg">
              <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
                با ثبت ایمیل خود از امکانات ویژه استفاده کنید:
              </h4>
              <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
                <li>• ردیابی کامل گردش کار درخواست شما</li>
                <li>• مشاهده کارشناس مربوطه و اطلاعات تماس</li>
                <li>• دریافت امتیاز و ارتقای سطح مشتری</li>
                <li>• دسترسی به تاریخچه درخواست‌های قبلی</li>
                <li>• دریافت پیشنهادات ویژه و تخفیفات</li>
              </ul>
              <div className="mt-3 p-2 bg-blue-100 dark:bg-blue-900/30 rounded text-xs text-blue-700 dark:text-blue-300">
                💡 پس از ثبت‌نام، لینک تایید به ایمیل شما ارسال می‌شود. با کلیک روی آن، دسترسی کامل به پنل مشتری خواهید داشت.
              </div>
            </div>

            {!showEmailRegistration ? (
              <Button
                onClick={() => setShowEmailRegistration(true)}
                variant="outline"
                className="w-full"
              >
                ثبت ایمیل برای استفاده از امکانات ویژه
              </Button>
            ) : (
              <div className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <input
                    type="email"
                    placeholder="آدرس ایمیل"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <input
                    type="text"
                    placeholder="نام (اختیاری)"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <input
                  type="text"
                  placeholder="نام خانوادگی (اختیاری)"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <div className="flex gap-2">
                  <Button
                    onClick={handleEmailRegistration}
                    disabled={isRegistering}
                    className="flex-1"
                  >
                    {isRegistering ? "در حال ثبت..." : "ثبت ایمیل"}
                  </Button>
                  <Button
                    onClick={() => setShowEmailRegistration(false)}
                    variant="outline"
                  >
                    انصراف
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              امکانات ویژه فعال شد
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-green-50 dark:bg-green-950/20 p-4 rounded-lg">
              <h4 className="font-semibold text-green-900 dark:text-green-100 mb-2">
                تبریک! حالا می‌توانید از امکانات ویژه استفاده کنید:
              </h4>
              <ul className="text-sm text-green-800 dark:text-green-200 space-y-1">
                <li>• ردیابی کامل گردش کار درخواست شما</li>
                <li>• مشاهده کارشناس مربوطه و اطلاعات تماس</li>
                <li>• دریافت امتیاز و ارتقای سطح مشتری</li>
                <li>• دسترسی به تاریخچه درخواست‌های قبلی</li>
                <li>• دریافت پیشنهادات ویژه و تخفیفات</li>
              </ul>
            </div>
            <div className="space-y-2">
              <Button
                onClick={() => navigate(`/customer/${registeredCustomerId}`)}
                className="w-full"
                variant="outline"
              >
                <ExternalLink className="w-4 h-4 ml-2" />
                مشاهده پنل مشتری
              </Button>
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground text-center">
                  پس از تایید ایمیل، می‌توانید از طریق همین لینک به پنل خود دسترسی داشته باشید
                </p>
                <div className="bg-yellow-50 dark:bg-yellow-950/20 p-3 rounded-lg">
                  <p className="text-xs text-yellow-800 dark:text-yellow-200 text-center">
                    📧 لینک تایید به ایمیل شما ارسال شده است. لطفاً ایمیل خود را بررسی کنید.
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

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
