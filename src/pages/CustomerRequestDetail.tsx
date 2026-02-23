import React, { useState, useEffect } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
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
  FileText,
  RefreshCw,
  DollarSign
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { env } from "@/lib/env";

interface WorkflowStep {
  name: string;
  order: number;
  title: string;
  points: number;
  is_completed: boolean;
  completed_at: string | null;
  points_earned: number;
}

interface RequestDetail {
  id: number;
  shipping_type: string;
  status: string;
  created_at: string;
  assigned_expert: {
    id: number;
    full_name: string;
    phone: string;
    email: string;
  } | null;
  workflow_steps: WorkflowStep[];
  total_points_earned: number;
  completed_steps: number;
  total_steps: number;
  latest_quote?: {
    id: number;
    amount: number;
    currency: string;
    note?: string | null;
    valid_until?: string | null;
    created_at: string;
    created_by?: string | null;
  } | null;
}

const CUSTOMER_PANEL_ID_KEY = "customer_panel_id";

const CustomerRequestDetail: React.FC = () => {
  const { requestId } = useParams<{ requestId: string }>();
  const [searchParams] = useSearchParams();
  const customerFromQuery = searchParams.get("customer");
  const customer =
    customerFromQuery ??
    (typeof localStorage !== "undefined" ? localStorage.getItem(CUSTOMER_PANEL_ID_KEY) : null) ??
    undefined;
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [requestDetail, setRequestDetail] = useState<RequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchRequestDetail = async () => {
    try {
      const response = await fetch(
        `${env.API_URL}/api/customer/workflow/${customer}?request_id=${requestId}`
      );
      
      if (response.ok) {
        const data = await response.json();
        setRequestDetail(data);
      } else {
        toast({
          title: "خطا",
          description: "اطلاعات درخواست یافت نشد",
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
    if (requestId && customer) {
      fetchRequestDetail();
    } else if (requestId && !customer) {
      setLoading(false);
    }
  }, [requestId, customer]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchRequestDetail();
  };

  const getStatusBadge = (status: string) => {
    const statusMap = {
      new: { label: "جدید", variant: "secondary" as const, color: "bg-gray-100 text-gray-800" },
      assigned: { label: "اختصاص یافته", variant: "default" as const, color: "bg-blue-100 text-blue-800" },
      in_progress: { label: "در حال انجام", variant: "default" as const, color: "bg-yellow-100 text-yellow-800" },
      completed: { label: "تکمیل شده", variant: "default" as const, color: "bg-green-100 text-green-800" },
      cancelled: { label: "لغو شده", variant: "destructive" as const, color: "bg-red-100 text-red-800" }
    };
    return statusMap[status as keyof typeof statusMap] || { label: status, variant: "secondary" as const, color: "bg-gray-100 text-gray-800" };
  };

  const getStepTitle = (stepName: string) => {
    const stepMap = {
      email_verified: "تایید ایمیل",
      request_submitted: "ارسال درخواست",
      expert_assigned: "اختصاص کارشناس",
      expert_contacted: "تماس کارشناس",
      quote_provided: "ارائه پیشنهاد",
      contract_signed: "امضای قرارداد",
      shipment_picked_up: "تحویل مرسوله",
      shipment_delivered: "تحویل به مقصد"
    };
    return stepMap[stepName as keyof typeof stepMap] || stepName;
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

  if (!requestDetail) {
    return (
      <div className="min-h-screen bg-gradient-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">
            {customer
              ? "اطلاعات درخواست یافت نشد"
              : "لطفاً از پنل مشتری وارد شوید یا ابتدا وارد پنل خود شوید."}
          </p>
          <Button
            onClick={() => navigate(customer ? `/customer/${customer}` : "/")}
            variant="outline"
          >
            <ArrowLeft className="w-4 h-4 ml-2" />
            {customer ? "بازگشت به پنل مشتری" : "بازگشت به صفحه اصلی"}
          </Button>
        </div>
      </div>
    );
  }

  const statusInfo = getStatusBadge(requestDetail.status);

  return (
    <div className="min-h-screen bg-gradient-background">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Button
              onClick={() => navigate(customer ? `/customer/${customer}` : "/")}
              variant="outline"
              size="sm"
            >
              <ArrowLeft className="w-4 h-4 ml-2" />
              بازگشت
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-foreground">
                جزئیات درخواست #{requestDetail.id}
              </h1>
              <p className="text-muted-foreground">
                {requestDetail.shipping_type === "domestic" ? "حمل داخلی" : "حمل بین‌المللی"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Badge variant={statusInfo.variant} className={statusInfo.color}>
              {statusInfo.label}
            </Badge>
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
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Request Info */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  اطلاعات درخواست
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">تاریخ ثبت:</span>
                    <span className="text-sm font-medium">
                      {new Date(requestDetail.created_at).toLocaleDateString("fa-IR")}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Package className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">نوع ارسال:</span>
                    <Badge variant="outline">
                      {requestDetail.shipping_type === "domestic" ? "داخلی" : "بین‌المللی"}
                    </Badge>
                  </div>
                </div>

                <Separator />

                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">
                    {requestDetail.total_points_earned}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    امتیاز کسب شده
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center">
                    <div className="text-xl font-bold text-green-600">
                      {requestDetail.completed_steps}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      تکمیل شده
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-xl font-bold text-muted-foreground">
                      {requestDetail.total_steps}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      کل مراحل
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Assigned Expert */}
          {requestDetail.assigned_expert && (
            <div className="lg:col-span-1">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <User className="w-5 h-5" />
                    کارشناس مربوطه
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
                      <User className="w-6 h-6 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-semibold">{requestDetail.assigned_expert.full_name}</h3>
                      <p className="text-sm text-muted-foreground">کارشناس فورواردر</p>
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Phone className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm">{requestDetail.assigned_expert.phone}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Mail className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm">{requestDetail.assigned_expert.email}</span>
                    </div>
                  </div>

                  <div className="bg-blue-50 dark:bg-blue-950/20 p-3 rounded-lg">
                    <p className="text-sm text-blue-800 dark:text-blue-200">
                      کارشناس ما در اسرع وقت با شما تماس خواهد گرفت تا جزئیات ارسال را هماهنگ کند.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Workflow Progress */}
          <div className="lg:col-span-1 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5" />
                  پیشرفت کار
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {requestDetail.workflow_steps.map((step, index) => (
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
                          {getStepTitle(step.name)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {step.is_completed && step.completed_at
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

            {requestDetail.latest_quote && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <DollarSign className="w-5 h-5" />
                    پیشنهاد (قیمت)
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-sm text-muted-foreground">مبلغ</span>
                    <span className="text-lg font-bold text-foreground">
                      {requestDetail.latest_quote.amount?.toLocaleString("fa-IR")} {requestDetail.latest_quote.currency}
                    </span>
                  </div>
                  {requestDetail.latest_quote.valid_until && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="w-4 h-4 shrink-0" />
                      <span>اعتبار تا: {new Date(requestDetail.latest_quote.valid_until).toLocaleDateString("fa-IR")}</span>
                    </div>
                  )}
                  {requestDetail.latest_quote.note && (
                    <p className="text-sm text-muted-foreground border-t pt-2">{requestDetail.latest_quote.note}</p>
                  )}
                  <div className="text-xs text-muted-foreground pt-1">
                    {requestDetail.latest_quote.created_at &&
                      new Date(requestDetail.latest_quote.created_at).toLocaleDateString("fa-IR", {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    {requestDetail.latest_quote.created_by && ` — ${requestDetail.latest_quote.created_by}`}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CustomerRequestDetail;
