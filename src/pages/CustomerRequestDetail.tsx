import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  ArrowLeft,
  Calendar,
  CheckCircle,
  Clock,
  DollarSign,
  FileText,
  Mail,
  Package,
  Phone,
  RefreshCw,
  User,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import {
  CustomerWorkflowHttpError,
  fetchCustomerWorkflow,
  type CustomerWorkflowData,
} from "@/lib/api";

const CUSTOMER_PANEL_ID_KEY = "customer_panel_id";
const showLatestQuoteCard: boolean = false;

function formatDate(date: string | null | undefined): string {
  return date ? new Date(date).toLocaleDateString("fa-IR") : "در انتظار";
}

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

  const [requestDetail, setRequestDetail] = useState<CustomerWorkflowData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchRequestDetail = useCallback(async () => {
    try {
      const data = await fetchCustomerWorkflow(customer ?? "", requestId ?? "");
      setRequestDetail(data);
    } catch (error) {
      if (error instanceof CustomerWorkflowHttpError) {
        toast({
          title: "خطا",
          description: "اطلاعات درخواست یافت نشد",
          variant: "destructive",
        });
      } else {
        toast({
          title: "خطا",
          description: "خطا در دریافت اطلاعات",
          variant: "destructive",
        });
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [customer, requestId, toast]);

  useEffect(() => {
    if (requestId && customer) {
      fetchRequestDetail();
    } else if (requestId && !customer) {
      setLoading(false);
    }
  }, [requestId, customer, fetchRequestDetail]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchRequestDetail();
  };

  const getStatusBadge = (status: string) => {
    const statusMap = {
      new: { label: "جدید", variant: "secondary" as const, color: "bg-gray-100 text-gray-800" },
      assigned: { label: "اختصاص یافته", variant: "default" as const, color: "bg-blue-100 text-blue-800" },
      in_progress: { label: "در حال انجام", variant: "default" as const, color: "bg-yellow-100 text-yellow-800" },
      quoted: { label: "پیشنهاد ارائه شده", variant: "default" as const, color: "bg-purple-100 text-purple-800" },
      waiting_for_customer: { label: "منتظر پاسخ شما", variant: "default" as const, color: "bg-orange-100 text-orange-800" },
      won: { label: "پذیرفته شد", variant: "default" as const, color: "bg-green-100 text-green-800" },
      lost: { label: "پذیرفته نشد", variant: "destructive" as const, color: "bg-red-100 text-red-800" },
      closed: { label: "بسته شد", variant: "secondary" as const, color: "bg-gray-100 text-gray-800" },
      completed: { label: "تکمیل شده", variant: "default" as const, color: "bg-green-100 text-green-800" },
      cancelled: { label: "لغو شده", variant: "destructive" as const, color: "bg-red-100 text-red-800" },
    };
    return statusMap[status as keyof typeof statusMap] || {
      label: status,
      variant: "secondary" as const,
      color: "bg-gray-100 text-gray-800",
    };
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
      shipment_delivered: "تحویل به مقصد",
      in_progress: "در حال پیگیری",
      final_decision: "پذیرش / عدم پذیرش",
    };
    return stepMap[stepName as keyof typeof stepMap] || stepName;
  };

  const getCurrentStatusLabel = (status: string): string => {
    const map: Record<string, string> = {
      in_progress: "در حال پیگیری",
      quoted: "پیشنهاد ارائه شده",
      waiting_for_customer: "منتظر پاسخ شما",
      won: "پذیرفته شد",
      lost: "پذیرفته نشد",
      closed: "بسته شد",
    };
    return map[status] ?? "";
  };

  const backDestination = customer ? `/customer/${customer}` : "/";
  const workflowSteps = useMemo(() => {
    if (!requestDetail) {
      return [];
    }

    return (requestDetail.workflow_steps_simple ?? requestDetail.workflow_steps).filter((step) =>
      requestDetail.workflow_steps_simple ? true : step.name !== "quote_provided",
    );
  }, [requestDetail]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-background px-4 py-10">
        <div className="mx-auto flex min-h-[70vh] max-w-md items-center justify-center">
          <Card className="w-full border-border/70 bg-card/95 shadow-sm">
            <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
              <div className="rounded-full bg-primary/10 p-4">
                <RefreshCw className="h-7 w-7 animate-spin text-primary" />
              </div>
              <div className="space-y-1">
                <h2 className="text-lg font-semibold text-foreground">در حال بارگذاری جزئیات درخواست</h2>
                <p className="text-sm text-muted-foreground">وضعیت، مراحل و اطلاعات کارشناس دریافت می‌شود.</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (!requestDetail) {
    return (
      <div className="min-h-screen bg-gradient-background px-4 py-10">
        <div className="mx-auto flex min-h-[70vh] max-w-md items-center justify-center">
          <Card className="w-full border-border/70 bg-card/95 shadow-sm">
            <CardContent className="flex flex-col items-center gap-5 p-8 text-center">
              <div className="rounded-full bg-muted p-4">
                <FileText className="h-7 w-7 text-muted-foreground" />
              </div>
              <div className="space-y-1">
                <h2 className="text-lg font-semibold text-foreground">
                  {customer ? "اطلاعات درخواست یافت نشد" : "ورود به پنل مشتری لازم است"}
                </h2>
                <p className="text-sm leading-6 text-muted-foreground">
                  {customer
                    ? "برای مشاهده درخواست‌های دیگر می‌توانید به پنل مشتری برگردید."
                    : "لطفا از پنل مشتری وارد شوید یا ابتدا وارد پنل خود شوید."}
                </p>
              </div>
              <Button onClick={() => navigate(backDestination)} variant="outline">
                <ArrowLeft className="ml-2 h-4 w-4" />
                {customer ? "بازگشت به پنل مشتری" : "بازگشت به صفحه اصلی"}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const statusInfo = getStatusBadge(requestDetail.status);
  const currentStatusLabel = getCurrentStatusLabel(requestDetail.status);

  return (
    <div className="min-h-screen bg-gradient-background">
      <div className="container mx-auto max-w-7xl px-4 py-6 sm:py-8">
        <section className="mb-6 overflow-hidden rounded-2xl border border-border/70 bg-card/95 shadow-sm">
          <div className="flex flex-col gap-5 p-5 sm:p-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-center">
              <Button onClick={() => navigate(backDestination)} variant="outline" size="sm" className="w-fit">
                <ArrowLeft className="ml-2 h-4 w-4" />
                بازگشت
              </Button>
              <div className="min-w-0">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <Badge variant={statusInfo.variant} className={statusInfo.color}>
                    {statusInfo.label}
                  </Badge>
                  <Badge variant="outline" className="bg-background/70">
                    {requestDetail.shipping_type === "domestic" ? "حمل داخلی" : "حمل بین‌المللی"}
                  </Badge>
                </div>
                <h1 className="break-words text-2xl font-bold tracking-normal text-foreground sm:text-3xl">
                  جزئیات درخواست #{requestDetail.id}
                </h1>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                  نمای خلاصه از وضعیت فعلی، مراحل انجام کار و اطلاعات ارتباطی کارشناس مربوطه.
                </p>
              </div>
            </div>
            <Button onClick={handleRefresh} variant="outline" size="sm" disabled={refreshing} className="w-fit">
              <RefreshCw className={`ml-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
              به‌روزرسانی
            </Button>
          </div>

          <div className="grid border-t border-border/70 bg-muted/20 sm:grid-cols-3">
            <div className="border-b border-border/70 p-5 sm:border-b-0 sm:border-l">
              <p className="text-xs text-muted-foreground">تاریخ ثبت</p>
              <p className="mt-1 text-lg font-semibold text-foreground">{formatDate(requestDetail.created_at)}</p>
            </div>
            <div className="border-b border-border/70 p-5 sm:border-b-0 sm:border-l">
              <p className="text-xs text-muted-foreground">امتیاز کسب شده</p>
              <p className="mt-1 text-2xl font-bold text-primary">{requestDetail.total_points_earned}</p>
            </div>
            <div className="p-5">
              <p className="text-xs text-muted-foreground">پیشرفت مراحل</p>
              <p className="mt-1 text-2xl font-bold text-green-600">
                {requestDetail.completed_steps}/{requestDetail.total_steps}
              </p>
            </div>
          </div>
        </section>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <aside className="space-y-6 lg:col-span-4">
            <Card className="border-border/70 bg-card/95 shadow-sm">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <FileText className="h-5 w-5 text-primary" />
                  اطلاعات درخواست
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="space-y-3">
                  <div className="flex items-center gap-2 rounded-lg bg-background/60 p-3">
                    <Calendar className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">تاریخ ثبت:</span>
                    <span className="text-sm font-medium text-foreground">{formatDate(requestDetail.created_at)}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 rounded-lg bg-background/60 p-3">
                    <Package className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">نوع ارسال:</span>
                    <Badge variant="outline">
                      {requestDetail.shipping_type === "domestic" ? "داخلی" : "بین‌المللی"}
                    </Badge>
                  </div>
                </div>

                <Separator />

                <div className="rounded-xl border bg-muted/20 p-4 text-center">
                  <div className="text-2xl font-bold text-primary">{requestDetail.total_points_earned}</div>
                  <div className="mt-1 text-sm text-muted-foreground">امتیاز کسب شده</div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl border bg-background/60 p-4 text-center">
                    <div className="text-xl font-bold text-green-600">{requestDetail.completed_steps}</div>
                    <div className="mt-1 text-xs text-muted-foreground">تکمیل شده</div>
                  </div>
                  <div className="rounded-xl border bg-background/60 p-4 text-center">
                    <div className="text-xl font-bold text-muted-foreground">{requestDetail.total_steps}</div>
                    <div className="mt-1 text-xs text-muted-foreground">کل مراحل</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {requestDetail.assigned_expert && (
              <Card className="border-border/70 bg-card/95 shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <User className="h-5 w-5 text-primary" />
                    کارشناس مربوطه
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="flex items-center gap-3 rounded-xl border bg-muted/20 p-4">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary/10">
                      <User className="h-6 w-6 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="break-words font-semibold text-foreground">{requestDetail.assigned_expert.full_name}</h3>
                      <p className="text-sm text-muted-foreground">کارشناس فورواردر</p>
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-3">
                    <div className="flex min-w-0 items-center gap-2 rounded-lg bg-background/60 p-3">
                      <Phone className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span className="min-w-0 break-words text-sm">{requestDetail.assigned_expert.phone}</span>
                    </div>
                    <div className="flex min-w-0 items-center gap-2 rounded-lg bg-background/60 p-3">
                      <Mail className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span className="min-w-0 break-all text-sm">{requestDetail.assigned_expert.email}</span>
                    </div>
                  </div>

                  <div className="rounded-xl border border-blue-200/70 bg-blue-50 p-3 dark:border-blue-900/40 dark:bg-blue-950/20">
                    <p className="text-sm leading-6 text-blue-800 dark:text-blue-200">
                      کارشناس ما در اسرع وقت با شما تماس خواهد گرفت تا جزئیات ارسال را هماهنگ کند.
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </aside>

          <main className="space-y-6 lg:col-span-8">
            <Card className="border-border/70 bg-card/95 shadow-sm">
              <CardHeader>
                <CardTitle className="flex flex-wrap items-center gap-2 text-base">
                  <CheckCircle className="h-5 w-5 text-primary" />
                  پیشرفت کار
                  {currentStatusLabel && (
                    <span className="text-sm font-normal text-muted-foreground">— وضعیت فعلی: {currentStatusLabel}</span>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {workflowSteps.map((step, index) => (
                    <div key={index} className="relative flex gap-4 rounded-xl border border-border/70 bg-background/70 p-4">
                      <div
                        className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${
                          step.is_completed ? "bg-green-100 text-green-600" : "bg-muted text-muted-foreground"
                        }`}
                      >
                        {step.is_completed ? <CheckCircle className="h-4 w-4" /> : <Clock className="h-4 w-4" />}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                          <p className="break-words text-sm font-semibold text-foreground">
                            {requestDetail.workflow_steps_simple ? step.title : getStepTitle(step.name)}
                          </p>
                          {step.points_earned != null && step.points_earned > 0 && (
                            <Badge variant="outline" className="w-fit">
                              {step.points_earned} امتیاز
                            </Badge>
                          )}
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {step.is_completed && step.completed_at ? formatDate(step.completed_at) : "در انتظار"}
                        </p>
                        {step.meta?.warning === "closed_without_decision" && (
                          <p className="mt-2 text-sm text-amber-600">بسته شده بدون ثبت پذیرش/عدم پذیرش</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {showLatestQuoteCard && requestDetail.latest_quote && (
              <Card className="border-border/70 bg-card/95 shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <DollarSign className="h-5 w-5 text-primary" />
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
                      <Calendar className="h-4 w-4 shrink-0" />
                      <span>اعتبار تا: {formatDate(requestDetail.latest_quote.valid_until)}</span>
                    </div>
                  )}
                  {requestDetail.latest_quote.note && (
                    <p className="border-t pt-2 text-sm text-muted-foreground">{requestDetail.latest_quote.note}</p>
                  )}
                  <div className="pt-1 text-xs text-muted-foreground">
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
          </main>
        </div>
      </div>
    </div>
  );
};

export default CustomerRequestDetail;
