import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import {
  fetchPublicTracking,
  PublicTrackingHttpError,
  PublicTrackingNotFoundError,
  type PublicTrackingData,
} from "@/lib/api";
import {
  AlertCircle,
  ArrowLeft,
  Calendar,
  CheckCircle,
  Clock,
  DollarSign,
  FileText,
  Home,
  MapPin,
  Package,
  Phone,
  Route,
  Truck,
  User,
} from "lucide-react";

const showLatestQuoteCard: boolean = false;

type StatusInfo = {
  label: string;
  variant: "secondary" | "default" | "destructive";
  color: string;
};

const getStatusBadge = (status: string): StatusInfo => {
  const statusMap: Record<string, StatusInfo> = {
    new: { label: "ثبت شده", variant: "secondary", color: "bg-gray-100 text-gray-800" },
    assigned: { label: "در انتظار بررسی", variant: "default", color: "bg-blue-100 text-blue-800" },
    in_progress: { label: "در حال پیگیری", variant: "default", color: "bg-yellow-100 text-yellow-800" },
    quoted: { label: "پیشنهاد ارائه شده", variant: "default", color: "bg-purple-100 text-purple-800" },
    waiting_for_customer: { label: "در انتظار مشتری", variant: "default", color: "bg-orange-100 text-orange-800" },
    won: { label: "تکمیل شده", variant: "default", color: "bg-green-100 text-green-800" },
    lost: { label: "لغو شده", variant: "destructive", color: "bg-red-100 text-red-800" },
    closed: { label: "بسته شده", variant: "secondary", color: "bg-gray-100 text-gray-800" },
    cancelled: { label: "لغو شده", variant: "destructive", color: "bg-red-100 text-red-800" },
  };
  return statusMap[status] || { label: status, variant: "secondary", color: "bg-gray-100 text-gray-800" };
};

const getCurrentStatusLabel = (status: string): string => {
  const map: Record<string, string> = {
    assigned: "در انتظار بررسی",
    in_progress: "در حال پیگیری",
    waiting_for_customer: "منتظر پاسخ شما",
    won: "پذیرفته شد",
    lost: "پذیرفته نشد",
    closed: "بسته شد",
  };
  return map[status] ?? "";
};

const formatDate = (
  value?: string | null,
  options?: Intl.DateTimeFormatOptions,
  fallback = "—",
) => {
  if (!value) return fallback;
  return new Date(value).toLocaleDateString("fa-IR", options);
};

const getLocationDisplay = (
  location: PublicTrackingData["route"]["origin"],
  isInternational: boolean,
) => {
  if (!location) return "—";
  if (isInternational) {
    const parts = [location.city_international, location.country].filter(Boolean);
    return parts.length ? parts.join("، ") : "ثبت نشده";
  }
  const parts = [location.city, location.county, location.province].filter(Boolean);
  return parts.length ? parts.join("، ") : "ثبت نشده";
};

const Section = ({
  icon: Icon,
  title,
  children,
  className = "",
}: {
  icon: React.ElementType;
  title: string;
  children: React.ReactNode;
  className?: string;
}) => (
  <Card className={`overflow-hidden border-border/80 bg-card/95 shadow-sm ${className}`}>
    <CardContent className="p-0">
      <div className="flex items-center gap-3 border-b border-border/70 bg-muted/25 px-5 py-4">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
          <Icon className="h-5 w-5" />
        </span>
        <h2 className="text-base font-bold text-foreground">{title}</h2>
      </div>
      <div className="p-5">{children}</div>
    </CardContent>
  </Card>
);

const Field = ({
  label,
  value,
  className = "",
}: {
  label: string;
  value: React.ReactNode;
  className?: string;
}) => (
  <div className={`rounded-md border border-border/70 bg-background/70 p-4 ${className}`}>
    <p className="mb-1 text-xs font-medium text-muted-foreground">{label}</p>
    <div className="break-words text-sm font-semibold leading-7 text-foreground">{value}</div>
  </div>
);

const PublicTracking: React.FC = () => {
  const { requestId } = useParams<{ requestId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [requestData, setRequestData] = useState<PublicTrackingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  const fetchRequestData = useCallback(async () => {
    if (!requestId) return;
    try {
      const data = await fetchPublicTracking(requestId);
      setRequestData(data);
    } catch (error) {
      if (error instanceof PublicTrackingNotFoundError) {
        setNotFound(true);
      } else if (error instanceof PublicTrackingHttpError) {
        toast({
          title: "خطا",
          description: "خطا در دریافت اطلاعات درخواست",
          variant: "destructive",
        });
      } else {
        toast({
          title: "خطا",
          description: "خطا در ارتباط با سرور",
          variant: "destructive",
        });
      }
    } finally {
      setLoading(false);
    }
  }, [requestId, toast]);

  useEffect(() => {
    if (requestId) {
      fetchRequestData();
    }
  }, [fetchRequestData, requestId]);

  const statusInfo = requestData ? getStatusBadge(requestData.status) : null;
  const currentStatusLabel = requestData ? getCurrentStatusLabel(requestData.status) : "";
  const isInternational = requestData?.shipping_type === "international";
  const workflowSteps = useMemo(() => {
    if (!requestData) return [];
    const steps = requestData.workflow_steps_simple ?? requestData.workflow_steps ?? [];
    return steps.filter((step) => (requestData.workflow_steps_simple ? true : step.name !== "quote_provided"));
  }, [requestData]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gradient-background px-4">
        <Card className="w-full max-w-md border-border/80 bg-card/95 shadow-md">
          <CardContent className="p-8 text-center">
            <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Clock className="h-7 w-7 animate-spin" />
            </div>
            <h1 className="text-xl font-bold text-foreground">در حال بارگذاری وضعیت درخواست</h1>
            <p className="mt-2 text-sm leading-7 text-muted-foreground">
              لطفا چند لحظه صبر کنید تا اطلاعات رهگیری نمایش داده شود.
            </p>
          </CardContent>
        </Card>
      </main>
    );
  }

  if (notFound || !requestData || !statusInfo) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gradient-background px-4 py-10">
        <Card className="w-full max-w-lg border-border/80 bg-card/95 shadow-md">
          <CardContent className="p-8 text-center">
            <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10 text-destructive">
              <AlertCircle className="h-8 w-8" />
            </div>
            <h1 className="text-2xl font-bold text-foreground">درخواست یافت نشد</h1>
            <p className="mx-auto mt-3 max-w-sm text-sm leading-7 text-muted-foreground">
              کد پیگیری واردشده پیدا نشد. لطفاً کد را بررسی کنید و دوباره وارد کنید.
            </p>
            <div className="mt-7 grid gap-3 sm:grid-cols-2">
              <Button onClick={() => navigate("/")} className="w-full">
                <ArrowLeft className="h-4 w-4" />
                بازگشت به صفحه اصلی
              </Button>
              <Button onClick={() => navigate("/")} variant="outline" className="w-full">
                <Package className="h-4 w-4" />
                ثبت درخواست جدید
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
    );
  }

  const hasCargo =
    requestData.cargo_description ||
    requestData.cargo_weight != null ||
    requestData.cargo_volume != null ||
    requestData.cargo_value != null ||
    requestData.special_instructions ||
    requestData.pickup_date ||
    requestData.delivery_date;

  const transportLabel =
    requestData.domestic_transport_method ||
    requestData.international_transport_method ||
    requestData.transport_method ||
    null;

  return (
    <main className="min-h-screen bg-gradient-background">
      <div className="container mx-auto max-w-7xl px-4 py-6 md:py-10">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <Button onClick={() => navigate("/")} variant="outline" size="sm">
            <ArrowLeft className="h-4 w-4" />
            بازگشت
          </Button>
          <Button onClick={() => navigate("/")} variant="ghost" size="sm">
            <Home className="h-4 w-4" />
            صفحه اصلی
          </Button>
        </div>

        <section className="mb-6 overflow-hidden rounded-lg border border-border/80 bg-card/95 shadow-sm">
          <div className="border-b border-border/70 bg-muted/25 p-5 md:p-7">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <Badge variant={statusInfo.variant} className={statusInfo.color}>
                    {statusInfo.label}
                  </Badge>
                  <Badge variant="outline">
                    {isInternational ? "بین‌المللی" : "داخلی"}
                  </Badge>
                  {currentStatusLabel && (
                    <Badge variant="outline">وضعیت فعلی: {currentStatusLabel}</Badge>
                  )}
                </div>
                <h1 className="break-words font-mono text-2xl font-bold tracking-normal text-foreground md:text-3xl">
                  {requestData.tracking_number}
                </h1>
                <p className="mt-2 max-w-2xl text-sm leading-7 text-muted-foreground">
                  آخرین وضعیت ثبت‌شده برای درخواست شما در این صفحه نمایش داده می‌شود. برای اطلاع از وضعیت جدیدتر، همین کد پیگیری را دوباره در بخش پیگیری درخواست وارد کنید.
                </p>
              </div>
              <div className="grid gap-3 text-sm sm:grid-cols-2 lg:min-w-[360px]">
                <Field
                  label="تاریخ ثبت درخواست"
                  value={formatDate(requestData.created_at, {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                />
                <Field
                  label="تاریخ اختصاص کارشناس"
                  value={formatDate(requestData.assigned_at, {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                />
              </div>
            </div>
          </div>

          <div className="grid gap-0 divide-y divide-border/70 md:grid-cols-3 md:divide-x md:divide-x-reverse md:divide-y-0">
            <div className="p-5">
              <p className="text-xs font-medium text-muted-foreground">شماره رهگیری</p>
              <p className="mt-2 break-all font-mono text-lg font-bold text-foreground">{requestData.tracking_number}</p>
            </div>
            <div className="p-5">
              <p className="text-xs font-medium text-muted-foreground">وضعیت فعلی</p>
              <div className="mt-2">
                <Badge variant={statusInfo.variant} className={statusInfo.color}>
                  {statusInfo.label}
                </Badge>
              </div>
            </div>
            <div className="p-5">
              <p className="text-xs font-medium text-muted-foreground">روش حمل</p>
              <p className="mt-2 text-sm font-semibold text-foreground">{transportLabel || "—"}</p>
            </div>
          </div>
        </section>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
          <div className="space-y-6">
            <Section icon={Package} title="اطلاعات درخواست">
              <div className="grid gap-4 md:grid-cols-2">
                <Field label="تاریخ ثبت" value={formatDate(requestData.created_at)} />
                <Field
                  label="نوع ارسال"
                  value={<Badge variant="outline">{isInternational ? "بین‌المللی" : "داخلی"}</Badge>}
                />
              </div>
            </Section>

            <Section icon={Route} title="مسیر ارسال">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-md border border-border/70 bg-background/70 p-4">
                  <div className="mb-3 flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">مبدا</Badge>
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <p className="break-words text-sm font-semibold leading-7 text-foreground">
                    {getLocationDisplay(requestData.route?.origin, isInternational)}
                  </p>
                </div>
                <div className="rounded-md border border-border/70 bg-background/70 p-4">
                  <div className="mb-3 flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">مقصد</Badge>
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <p className="break-words text-sm font-semibold leading-7 text-foreground">
                    {getLocationDisplay(requestData.route?.destination, isInternational)}
                  </p>
                </div>
              </div>
              {transportLabel && (
                <div className="mt-4 rounded-md border border-border/70 bg-muted/20 p-4">
                  <div className="flex items-center gap-2 text-sm">
                    <Truck className="h-4 w-4 text-muted-foreground" />
                    <span className="text-muted-foreground">روش حمل:</span>
                    <span className="font-semibold text-foreground">{transportLabel}</span>
                  </div>
                </div>
              )}
            </Section>

            <Section icon={User} title="اطلاعات تماس">
              <div className="grid gap-4 md:grid-cols-2">
                <Field
                  label="شماره تماس"
                  value={
                    <span className="inline-flex items-center gap-2">
                      <Phone className="h-4 w-4 text-muted-foreground" />
                      {requestData.contact_phone}
                    </span>
                  }
                />
                {(requestData.customer_first_name || requestData.customer_last_name) && (
                  <Field
                    label="نام مشتری"
                    value={`${requestData.customer_first_name || ""} ${requestData.customer_last_name || ""}`.trim()}
                  />
                )}
              </div>
            </Section>

            {hasCargo && (
              <Section icon={FileText} title="جزئیات مرسوله">
                <div className="space-y-4">
                  {requestData.cargo_description && (
                    <Field label="توضیحات" value={requestData.cargo_description} />
                  )}
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {requestData.cargo_weight != null && (
                      <Field label="وزن (کیلوگرم)" value={requestData.cargo_weight} />
                    )}
                    {requestData.cargo_volume != null && (
                      <Field label="حجم (م³)" value={requestData.cargo_volume} />
                    )}
                    {requestData.cargo_value != null && (
                      <Field label="ارزش" value={requestData.cargo_value} />
                    )}
                    {requestData.pickup_date && (
                      <Field label="تاریخ تحویل مبدا" value={formatDate(requestData.pickup_date)} />
                    )}
                    {requestData.delivery_date && (
                      <Field label="تاریخ تحویل مقصد" value={formatDate(requestData.delivery_date)} />
                    )}
                  </div>
                  {requestData.special_instructions && (
                    <Field label="دستورالعمل‌های ویژه" value={requestData.special_instructions} />
                  )}
                </div>
              </Section>
            )}
          </div>

          <aside className="space-y-6">
            {requestData.assigned_expert && (
              <Section icon={User} title="کارشناس مربوطه">
                <div className="space-y-4">
                  <Field label="نام کارشناس" value={requestData.assigned_expert.full_name} />
                  {requestData.assigned_at && (
                    <Field
                      label="تاریخ اختصاص"
                      value={formatDate(requestData.assigned_at, {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    />
                  )}
                  <Field
                    label="شماره تماس"
                    value={
                      <a href={`tel:${requestData.assigned_expert.phone}`} className="hover:underline">
                        {requestData.assigned_expert.phone}
                      </a>
                    }
                  />
                  {requestData.assigned_expert.email && (
                    <Field label="ایمیل" value={requestData.assigned_expert.email} />
                  )}
                </div>
              </Section>
            )}

            {showLatestQuoteCard && requestData.latest_quote && (
              <Section icon={DollarSign} title="پیشنهاد (قیمت)">
                <div className="space-y-4">
                  <Field
                    label="مبلغ"
                    value={`${requestData.latest_quote.amount?.toLocaleString("fa-IR")} ${requestData.latest_quote.currency}`}
                  />
                  {requestData.latest_quote.valid_until && (
                    <Field
                      label="اعتبار تا"
                      value={formatDate(requestData.latest_quote.valid_until)}
                    />
                  )}
                  {requestData.latest_quote.note && (
                    <Field label="یادداشت" value={requestData.latest_quote.note} />
                  )}
                  <p className="text-xs leading-6 text-muted-foreground">
                    {formatDate(requestData.latest_quote.created_at, {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    }, "")}
                    {requestData.latest_quote.created_by && ` — ${requestData.latest_quote.created_by}`}
                  </p>
                </div>
              </Section>
            )}

            {workflowSteps.length > 0 && (
              <Section icon={CheckCircle} title="مراحل گردش کار">
                {currentStatusLabel && (
                  <div className="mb-4 rounded-md bg-muted/30 px-3 py-2 text-xs font-medium text-muted-foreground">
                    وضعیت فعلی: {currentStatusLabel}
                  </div>
                )}
                <div className="space-y-4">
                  {workflowSteps.map((step, index) => (
                    <div key={index} className="flex gap-3">
                      <div
                        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border ${
                          step.is_completed
                            ? "border-green-200 bg-green-100 text-green-700"
                            : "border-border bg-muted text-muted-foreground"
                        }`}
                      >
                        {step.is_completed ? <CheckCircle className="h-4 w-4" /> : <Clock className="h-4 w-4" />}
                      </div>
                      <div className="min-w-0 flex-1 pb-3">
                        <p className="break-words text-sm font-semibold leading-7 text-foreground">{step.title}</p>
                        <p className="text-xs leading-6 text-muted-foreground">
                          {step.is_completed && step.completed_at
                            ? formatDate(step.completed_at)
                            : "در انتظار"}
                          {step.meta?.warning === "closed_without_decision" && (
                            <span className="mt-1 block text-amber-600">
                              بسته شده بدون ثبت پذیرش/عدم پذیرش
                            </span>
                          )}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            <Card className="border-border/80 bg-card/95 shadow-sm">
              <CardContent className="p-5">
                <Button onClick={() => navigate("/")} variant="outline" className="w-full">
                  <Package className="h-4 w-4" />
                  درخواست جدید
                </Button>
              </CardContent>
            </Card>
          </aside>
        </div>
      </div>
    </main>
  );
};

export default PublicTracking;
