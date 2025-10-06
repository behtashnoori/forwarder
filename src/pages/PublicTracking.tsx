import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { 
  ArrowLeft, 
  User, 
  Phone, 
  Mail, 
  MapPin, 
  Package, 
  Calendar, 
  CheckCircle, 
  Clock, 
  AlertCircle,
  ExternalLink,
  Star
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface PublicTrackingData {
  id: number;
  tracking_number: string;
  status: string;
  created_at: string;
  shipping_type: string;
  contact_phone: string;
  customer_first_name?: string;
  customer_last_name?: string;
  route: {
    origin: {
      province?: string;
      county?: string;
      city?: string;
      country?: string;
      city_international?: string;
    };
    destination: {
      province?: string;
      county?: string;
      city?: string;
      country?: string;
      city_international?: string;
    };
  };
  assigned_expert?: {
    id: number;
    full_name: string;
    phone: string;
  };
}

const PublicTracking: React.FC = () => {
  const { requestId } = useParams<{ requestId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [requestData, setRequestData] = useState<PublicTrackingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (requestId) {
      fetchRequestData();
    }
  }, [requestId]);

  const fetchRequestData = async () => {
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/public/track/${requestId}`
      );
      
      if (response.ok) {
        const data = await response.json();
        setRequestData(data);
      } else if (response.status === 404) {
        setNotFound(true);
      } else {
        toast({
          title: "خطا",
          description: "خطا در دریافت اطلاعات درخواست",
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
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusMap = {
      new: { label: "جدید", variant: "secondary" as const, color: "bg-gray-100 text-gray-800" },
      assigned: { label: "اختصاص یافته", variant: "default" as const, color: "bg-blue-100 text-blue-800" },
      in_progress: { label: "در حال انجام", variant: "default" as const, color: "bg-yellow-100 text-yellow-800" },
      quoted: { label: "پیشنهاد ارائه شده", variant: "default" as const, color: "bg-purple-100 text-purple-800" },
      waiting_for_customer: { label: "در انتظار مشتری", variant: "default" as const, color: "bg-orange-100 text-orange-800" },
      won: { label: "تکمیل شده", variant: "default" as const, color: "bg-green-100 text-green-800" },
      lost: { label: "لغو شده", variant: "destructive" as const, color: "bg-red-100 text-red-800" },
      closed: { label: "بسته شده", variant: "secondary" as const, color: "bg-gray-100 text-gray-800" }
    };
    return statusMap[status as keyof typeof statusMap] || { label: status, variant: "secondary" as const, color: "bg-gray-100 text-gray-800" };
  };

  const getLocationDisplay = (location: any, isInternational: boolean) => {
    if (isInternational) {
      return `${location.city_international || 'نامشخص'}، ${location.country || 'نامشخص'}`;
    } else {
      return `${location.city || 'نامشخص'}، ${location.county || 'نامشخص'}، ${location.province || 'نامشخص'}`;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-background flex items-center justify-center">
        <div className="text-center">
          <Clock className="w-8 h-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">در حال بارگذاری...</p>
        </div>
      </div>
    );
  }

  if (notFound || !requestData) {
    return (
      <div className="min-h-screen bg-gradient-background flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-6">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-foreground mb-2">
            درخواست یافت نشد
          </h1>
          <p className="text-muted-foreground mb-6">
            شماره پیگیری وارد شده معتبر نیست یا درخواست وجود ندارد.
          </p>
          <div className="space-y-3">
            <Button onClick={() => navigate("/")} className="w-full">
              <ArrowLeft className="w-4 h-4 ml-2" />
              بازگشت به صفحه اصلی
            </Button>
            <Button 
              onClick={() => navigate("/")} 
              variant="outline" 
              className="w-full"
            >
              <Package className="w-4 h-4 ml-2" />
              ثبت درخواست جدید
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const statusInfo = getStatusBadge(requestData.status);
  const isInternational = requestData.shipping_type === "international";

  return (
    <div className="min-h-screen bg-gradient-background">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Button
              onClick={() => navigate("/")}
              variant="outline"
              size="sm"
            >
              <ArrowLeft className="w-4 h-4 ml-2" />
              بازگشت
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-foreground">
                پیگیری درخواست {requestData.tracking_number}
              </h1>
              <p className="text-muted-foreground">
                {isInternational ? "حمل بین‌المللی" : "حمل داخلی"}
              </p>
            </div>
          </div>
          <Badge variant={statusInfo.variant} className={statusInfo.color}>
            {statusInfo.label}
          </Badge>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Request Info */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Package className="w-5 h-5" />
                  اطلاعات درخواست
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">تاریخ ثبت:</span>
                    <span className="text-sm font-medium">
                      {new Date(requestData.created_at).toLocaleDateString("fa-IR")}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Package className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">نوع ارسال:</span>
                    <Badge variant="outline">
                      {isInternational ? "بین‌المللی" : "داخلی"}
                    </Badge>
                  </div>
                </div>

                <Separator />

                <div className="space-y-3">
                  <h3 className="font-semibold text-lg flex items-center gap-2">
                    <MapPin className="w-5 h-5" />
                    مسیر ارسال
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-xs">مبدا</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {getLocationDisplay(requestData.route.origin, isInternational)}
                      </p>
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-xs">مقصد</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {getLocationDisplay(requestData.route.destination, isInternational)}
                      </p>
                    </div>
                  </div>
                </div>

                <Separator />

                <div className="space-y-3">
                  <h3 className="font-semibold text-lg flex items-center gap-2">
                    <User className="w-5 h-5" />
                    اطلاعات تماس
                  </h3>
                  <div className="flex items-center gap-2">
                    <Phone className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">{requestData.contact_phone}</span>
                  </div>
                  {(requestData.customer_first_name || requestData.customer_last_name) && (
                    <div className="flex items-center gap-2">
                      <User className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm">
                        {requestData.customer_first_name} {requestData.customer_last_name}
                      </span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Registration Prompt */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Star className="w-5 h-5 text-yellow-500" />
                  امکانات ویژه
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-yellow-50 dark:bg-yellow-950/20 p-4 rounded-lg">
                  <h4 className="font-semibold text-yellow-900 dark:text-yellow-100 mb-2">
                    برای دسترسی کامل ثبت‌نام کنید:
                  </h4>
                  <ul className="text-sm text-yellow-800 dark:text-yellow-200 space-y-1">
                    <li>• ردیابی کامل مراحل کار</li>
                    <li>• مشاهده کارشناس مربوطه</li>
                    <li>• دریافت امتیاز و تخفیفات</li>
                    <li>• دسترسی به تاریخچه درخواست‌ها</li>
                    <li>• دریافت پیشنهادات ویژه</li>
                  </ul>
                </div>

                {requestData.assigned_expert && (
                  <div className="bg-blue-50 dark:bg-blue-950/20 p-4 rounded-lg">
                    <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
                      کارشناس مربوطه
                    </h4>
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <User className="w-4 h-4 text-blue-600" />
                        <span className="text-sm font-medium">
                          {requestData.assigned_expert.full_name}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Phone className="w-4 h-4 text-blue-600" />
                        <span className="text-sm">
                          {requestData.assigned_expert.phone}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <Button 
                    onClick={() => navigate("/")} 
                    className="w-full"
                  >
                    <User className="w-4 h-4 ml-2" />
                    ثبت‌نام و دسترسی کامل
                  </Button>
                  <Button 
                    onClick={() => navigate("/")} 
                    variant="outline" 
                    className="w-full"
                  >
                    <Package className="w-4 h-4 ml-2" />
                    درخواست جدید
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PublicTracking;
