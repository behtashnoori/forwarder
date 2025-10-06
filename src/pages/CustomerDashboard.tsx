import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { 
  User, 
  Phone, 
  Mail, 
  MapPin, 
  Package, 
  Calendar, 
  CheckCircle, 
  Clock, 
  Star,
  Trophy,
  Award,
  TrendingUp,
  ArrowLeft,
  RefreshCw
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface CustomerProfile {
  id: number;
  email: string;
  phone: string;
  first_name: string;
  last_name: string;
  is_email_verified: boolean;
  total_requests: number;
  completed_requests: number;
  loyalty_points: number;
  customer_level: string;
  created_at: string;
}

interface WorkflowStep {
  step_name: string;
  step_order: number;
  is_completed: boolean;
  completed_at: string | null;
  points_earned: number;
  created_at: string;
}

interface RecentRequest {
  id: number;
  shipping_type: string;
  status: string;
  created_at: string;
  assigned_expert: {
    id: number;
    full_name: string;
    phone: string;
  } | null;
}

interface CustomerDashboardData {
  customer: CustomerProfile;
  recent_steps: WorkflowStep[];
  recent_requests: RecentRequest[];
}

const CustomerDashboard: React.FC = () => {
  const { customerId } = useParams<{ customerId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [data, setData] = useState<CustomerDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchCustomerData = async () => {
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/customer/profile/${customerId}`
      );
      
      if (response.ok) {
        const customerData = await response.json();
        setData(customerData);
      } else {
        toast({
          title: "خطا",
          description: "اطلاعات مشتری یافت نشد",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "خطا",
        description: "خطا در دریافت اطلاعات",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (customerId) {
      fetchCustomerData();
    }
  }, [customerId]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchCustomerData();
  };

  const getLevelInfo = (level: string) => {
    const levels = {
      bronze: { name: "برنز", color: "bg-amber-500", icon: Award },
      silver: { name: "نقره", color: "bg-gray-400", icon: Star },
      gold: { name: "طلا", color: "bg-yellow-500", icon: Trophy },
      platinum: { name: "پلاتین", color: "bg-purple-500", icon: TrendingUp }
    };
    return levels[level as keyof typeof levels] || levels.bronze;
  };

  const getStatusBadge = (status: string) => {
    const statusMap = {
      new: { label: "جدید", variant: "secondary" as const },
      assigned: { label: "اختصاص یافته", variant: "default" as const },
      in_progress: { label: "در حال انجام", variant: "default" as const },
      completed: { label: "تکمیل شده", variant: "default" as const },
      cancelled: { label: "لغو شده", variant: "destructive" as const }
    };
    return statusMap[status as keyof typeof statusMap] || { label: status, variant: "secondary" as const };
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-background flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">در حال بارگذاری...</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gradient-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">اطلاعات مشتری یافت نشد</p>
          <Button onClick={() => navigate("/")} variant="outline">
            <ArrowLeft className="w-4 h-4 ml-2" />
            بازگشت به صفحه اصلی
          </Button>
        </div>
      </div>
    );
  }

  const levelInfo = getLevelInfo(data.customer.customer_level);
  const LevelIcon = levelInfo.icon;

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
                پنل مشتری
              </h1>
              <p className="text-muted-foreground">
                خوش آمدید {data.customer.first_name} {data.customer.last_name}
              </p>
            </div>
          </div>
          <Button
            onClick={handleRefresh}
            variant="outline"
            size="sm"
            disabled={refreshing}
          >
            <RefreshCw className={`w-4 h-4 ml-2 ${refreshing ? 'animate-spin' : ''}`} />
            به‌روزرسانی
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Customer Profile */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="w-5 h-5" />
                  پروفایل مشتری
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className={`w-12 h-12 rounded-full ${levelInfo.color} flex items-center justify-center`}>
                    <LevelIcon className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold">{levelInfo.name}</h3>
                    <p className="text-sm text-muted-foreground">
                      {data.customer.loyalty_points} امتیاز
                    </p>
                  </div>
                </div>

                <Separator />

                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Mail className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">{data.customer.email}</span>
                    {data.customer.is_email_verified && (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Phone className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">{data.customer.phone}</span>
                  </div>
                </div>

                <Separator />

                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-primary">
                      {data.customer.total_requests}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      کل درخواست‌ها
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {data.customer.completed_requests}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      تکمیل شده
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Recent Requests */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Package className="w-5 h-5" />
                  درخواست‌های اخیر
                </CardTitle>
              </CardHeader>
              <CardContent>
                {data.recent_requests.length === 0 ? (
                  <div className="text-center py-8">
                    <Package className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground">هنوز درخواستی ثبت نکرده‌اید</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {data.recent_requests.map((request) => {
                      const statusInfo = getStatusBadge(request.status);
                      return (
                        <div
                          key={request.id}
                          className="border rounded-lg p-4 hover:bg-muted/50 transition-colors"
                        >
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <Badge variant={statusInfo.variant}>
                                {statusInfo.label}
                              </Badge>
                              <Badge variant="outline">
                                {request.shipping_type === "domestic" ? "داخلی" : "بین‌المللی"}
                              </Badge>
                            </div>
                            <span className="text-sm text-muted-foreground">
                              {new Date(request.created_at).toLocaleDateString("fa-IR")}
                            </span>
                          </div>

                          <div className="flex items-center justify-between">
                            <div>
                              <p className="font-medium">درخواست #{request.id}</p>
                              {request.assigned_expert && (
                                <div className="flex items-center gap-2 mt-1">
                                  <User className="w-4 h-4 text-muted-foreground" />
                                  <span className="text-sm text-muted-foreground">
                                    کارشناس: {request.assigned_expert.full_name}
                                  </span>
                                  <Phone className="w-4 h-4 text-muted-foreground" />
                                  <span className="text-sm text-muted-foreground">
                                    {request.assigned_expert.phone}
                                  </span>
                                </div>
                              )}
                            </div>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => navigate(`/request/${request.id}?customer=${customerId}`)}
                            >
                              مشاهده جزئیات
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Recent Activity */}
        {data.recent_steps.length > 0 && (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-5 h-5" />
                فعالیت‌های اخیر
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {data.recent_steps.map((step, index) => (
                  <div key={index} className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      step.is_completed ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-400'
                    }`}>
                      {step.is_completed ? (
                        <CheckCircle className="w-4 h-4" />
                      ) : (
                        <Clock className="w-4 h-4" />
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">
                        {step.step_name === "email_verified" && "تایید ایمیل"}
                        {step.step_name === "request_submitted" && "ارسال درخواست"}
                        {step.step_name === "expert_assigned" && "اختصاص کارشناس"}
                        {step.step_name === "expert_contacted" && "تماس کارشناس"}
                        {step.step_name === "quote_provided" && "ارائه پیشنهاد"}
                        {step.step_name === "contract_signed" && "امضای قرارداد"}
                        {step.step_name === "shipment_picked_up" && "تحویل مرسوله"}
                        {step.step_name === "shipment_delivered" && "تحویل به مقصد"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {step.completed_at 
                          ? new Date(step.completed_at).toLocaleDateString("fa-IR")
                          : "در انتظار"
                        }
                        {step.points_earned > 0 && (
                          <span className="mr-2">• {step.points_earned} امتیاز</span>
                        )}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default CustomerDashboard;
