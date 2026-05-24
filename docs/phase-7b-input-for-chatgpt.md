# Phase 7B Input for ChatGPT

## 1. Current Git Context

- Current branch: `forwarder-14050229-ver-7`
- Latest commit hash: `cbce756`
- Working tree clean: `No`

### `git branch --show-current`

```text
forwarder-14050229-ver-7
```

### `git rev-parse --short HEAD`

```text
cbce756
```

### `git status --short`

```text
 M backend/routes/admin_panel.py
 M backend/routes/customer_gamification.py
 M backend/routes/user_management.py
 M backend/services/assignment_service.py
 M backend/tests/test_expert_assignment_referral_contract.py
 M backend/tests/test_user_management_contract.py
 M src/lib/api.ts
 M src/pages/AdminPanel.tsx
 M src/pages/CustomerDashboard.tsx
 M src/pages/CustomerRequestDetail.tsx
 M src/pages/PublicTracking.tsx
 M src/pages/VerifyEmail.tsx
?? backend/services/admin_dashboard_service.py
?? backend/services/admin_report_service.py
?? backend/services/admin_shipment_request_service.py
?? backend/services/assignment_statistics_service.py
?? backend/services/customer_gamification_service.py
?? backend/services/user_delete_service.py
?? backend/services/user_service.py
?? backend/tests/test_admin_panel_read_contract.py
?? backend/tests/test_customer_gamification_contract.py
?? docs/openapi/
?? docs/phase-5aa-customer-gamification-final-closure-review.md
?? docs/phase-5e-assignment-statistics-service-extraction.md
?? docs/phase-5f-user-crud-service-extraction.md
?? docs/phase-5g-user-delete-cleanup-service-extraction.md
?? docs/phase-5h-manual-assignment-behavior-decision.md
?? docs/phase-5i-manual-assignment-fix.md
?? docs/phase-5j-user-management-final-review.md
?? docs/phase-5k-customer-gamification-characterization.md
?? docs/phase-5l-customer-gamification-service-extraction.md
?? docs/phase-5m-admin-panel-read-report-characterization.md
?? docs/phase-5n-admin-assignment-summary-fix.md
?? docs/phase-5o-admin-dashboard-service-extraction.md
?? docs/phase-5p-admin-assignment-summary-service-extraction.md
?? docs/phase-5q-admin-shipment-request-read-service-extraction.md
?? docs/phase-5r-admin-panel-final-review.md
?? docs/phase-5s-customer-gamification-follow-up-review.md
?? docs/phase-5t-customer-profile-read-service-extraction.md
?? docs/phase-5u-customer-workflow-read-service-extraction.md
?? docs/phase-5v-customer-gamification-final-review.md
?? docs/phase-5w-customer-write-flow-characterization.md
?? docs/phase-5x-customer-registration-service-extraction.md
?? docs/phase-5y-customer-email-verification-service-extraction.md
?? docs/phase-5z-customer-complete-step-service-extraction.md
?? docs/phase-6a-repository-layer-readiness-review.md
?? docs/phase-6b-openapi-documentation.md
?? docs/phase-6c-frontend-api-client-refactor-inventory.md
?? docs/phase-6d-public-tracking-api-client-refactor.md
?? docs/phase-6e-customer-profile-api-client-refactor.md
?? docs/phase-6f-customer-workflow-api-client-refactor.md
?? docs/phase-6g-customer-email-verification-api-client-refactor.md
?? docs/phase-6h-customer-registration-api-client-refactor.md
?? docs/phase-6i-customer-complete-step-api-client-refactor.md
?? docs/phase-6j-admin-dashboard-api-client-refactor.md
?? docs/phase-6k-admin-assignment-summary-api-client-refactor.md
?? docs/phase-6l-admin-shipment-request-api-client-refactor.md
?? docs/phase-6m-expert-console-api-client-inventory.md
?? docs/phase-6n-expert-dashboard-kpis-openapi-client-alignment.md
?? docs/phase-6o-expert-experts-list-openapi-client-alignment.md
?? docs/phase-6p-expert-status-update-openapi-client-alignment.md
?? docs/phase-6q-expert-mark-read-openapi-client-alignment.md
?? docs/phase-6r-expert-login-api-client-refactor-decision.md
?? docs/phase-6s-frontend-api-openapi-final-alignment-review.md
?? docs/phase-6t-final-quality-warning-review.md
?? docs/phase-6u-final-stabilization-closure-report.md
?? docs/phase-7a-frontend-ui-lovable-style-audit-and-plan.md
?? docs/phase-7b-input-for-chatgpt.md
```

### Uncommitted files

The working tree is not clean. The uncommitted files are exactly the entries shown in `git status --short` above.

## 2. Exact Current PublicTracking.tsx

Full current content of `src/pages/PublicTracking.tsx`:

```tsx
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
  MapPin,
  Package,
  Calendar,
  CheckCircle,
  Clock,
  AlertCircle,
  Truck,
  FileText,
  DollarSign,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import {
  fetchPublicTracking,
  PublicTrackingHttpError,
  PublicTrackingNotFoundError,
  type PublicTrackingData,
} from "@/lib/api";

const showLatestQuoteCard: boolean = false;

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
  };

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { label: string; variant: "secondary" | "default" | "destructive"; color: string }> = {
      new: { label: "جدید", variant: "secondary", color: "bg-gray-100 text-gray-800" },
      assigned: { label: "اختصاص یافته", variant: "default", color: "bg-blue-100 text-blue-800" },
      in_progress: { label: "در حال انجام", variant: "default", color: "bg-yellow-100 text-yellow-800" },
      quoted: { label: "پیشنهاد ارائه شده", variant: "default", color: "bg-purple-100 text-purple-800" },
      waiting_for_customer: { label: "در انتظار مشتری", variant: "default", color: "bg-orange-100 text-orange-800" },
      won: { label: "تکمیل شده", variant: "default", color: "bg-green-100 text-green-800" },
      lost: { label: "لغو شده", variant: "destructive", color: "bg-red-100 text-red-800" },
      closed: { label: "بسته شده", variant: "secondary", color: "bg-gray-100 text-gray-800" },
      cancelled: { label: "لغو شده", variant: "destructive", color: "bg-red-100 text-red-800" },
    };
    return statusMap[status] || { label: status, variant: "secondary" as const, color: "bg-gray-100 text-gray-800" };
  };

  /** Optional "وضعیت فعلی" label for timeline section (plan-specified map). */
  const getCurrentStatusLabel = (status: string): string => {
    const map: Record<string, string> = {
      in_progress: "در حال پیگیری",
      waiting_for_customer: "منتظر پاسخ شما",
      won: "پذیرفته شد",
      lost: "پذیرفته نشد",
      closed: "بسته شد",
    };
    return map[status] ?? "";
  };

  const getLocationDisplay = (location: PublicTrackingData["route"]["origin"], isInternational: boolean) => {
    if (!location) return "—";
    if (isInternational) {
      const parts = [location.city_international, location.country].filter(Boolean);
      return parts.length ? parts.join("، ") : "ثبت نشده";
    }
    const parts = [location.city, location.county, location.province].filter(Boolean);
    return parts.length ? parts.join("، ") : "ثبت نشده";
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
          <h1 className="text-2xl font-bold text-foreground mb-2">درخواست یافت نشد</h1>
          <p className="text-muted-foreground mb-6">
            شماره پیگیری وارد شده معتبر نیست یا درخواست وجود ندارد.
          </p>
          <div className="space-y-3">
            <Button onClick={() => navigate("/")} className="w-full">
              <ArrowLeft className="w-4 h-4 ml-2" />
              بازگشت به صفحه اصلی
            </Button>
            <Button onClick={() => navigate("/")} variant="outline" className="w-full">
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
    <div className="min-h-screen bg-gradient-background">
      <div className="container mx-auto px-4 py-8">
        {/* Back button */}
        <div className="mb-6">
          <Button onClick={() => navigate("/")} variant="outline" size="sm">
            <ArrowLeft className="w-4 h-4 ml-2" />
            بازگشت
          </Button>
        </div>

        {/* Summary box */}
        <Card className="mb-8 bg-muted/30">
          <CardContent className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-muted-foreground mb-1">شماره رهگیری</p>
                <p className="text-xl font-mono font-bold text-foreground">{requestData.tracking_number}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">وضعیت فعلی</p>
                <Badge variant={statusInfo.variant} className={statusInfo.color}>
                  {statusInfo.label}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">تاریخ ثبت درخواست</p>
                <p className="text-sm font-medium">
                  {requestData.created_at
                    ? new Date(requestData.created_at).toLocaleDateString("fa-IR", {
                        year: "numeric",
                        month: "long",
                        day: "numeric",
                      })
                    : "—"}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">تاریخ اختصاص کارشناس</p>
                <p className="text-sm font-medium">
                  {requestData.assigned_at
                    ? new Date(requestData.assigned_at).toLocaleDateString("fa-IR", {
                        year: "numeric",
                        month: "long",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : "—"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main: Request info, route, transport, cargo */}
          <div className="lg:col-span-2 space-y-6">
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
                    <Badge variant="outline">{isInternational ? "بین‌المللی" : "داخلی"}</Badge>
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
                      <Badge variant="outline" className="text-xs">مبدا</Badge>
                      <p className="text-sm text-muted-foreground">
                        {getLocationDisplay(requestData.route?.origin, isInternational)}
                      </p>
                    </div>
                    <div className="space-y-2">
                      <Badge variant="outline" className="text-xs">مقصد</Badge>
                      <p className="text-sm text-muted-foreground">
                        {getLocationDisplay(requestData.route?.destination, isInternational)}
                      </p>
                    </div>
                  </div>
                </div>

                {transportLabel && (
                  <>
                    <Separator />
                    <div className="space-y-2">
                      <h3 className="font-semibold flex items-center gap-2">
                        <Truck className="w-4 h-4" />
                        روش حمل
                      </h3>
                      <p className="text-sm text-muted-foreground">{transportLabel}</p>
                    </div>
                  </>
                )}

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

            {hasCargo && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    جزئیات مرسوله
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {requestData.cargo_description && (
                    <div>
                      <span className="text-sm text-muted-foreground">توضیحات: </span>
                      <span className="text-sm">{requestData.cargo_description}</span>
                    </div>
                  )}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {requestData.cargo_weight != null && (
                      <div>
                        <span className="text-sm text-muted-foreground">وزن (کیلوگرم): </span>
                        <span className="text-sm font-medium">{requestData.cargo_weight}</span>
                      </div>
                    )}
                    {requestData.cargo_volume != null && (
                      <div>
                        <span className="text-sm text-muted-foreground">حجم (م³): </span>
                        <span className="text-sm font-medium">{requestData.cargo_volume}</span>
                      </div>
                    )}
                    {requestData.cargo_value != null && (
                      <div>
                        <span className="text-sm text-muted-foreground">ارزش: </span>
                        <span className="text-sm font-medium">{requestData.cargo_value}</span>
                      </div>
                    )}
                  </div>
                  {requestData.special_instructions && (
                    <div>
                      <span className="text-sm text-muted-foreground">دستورالعمل‌های ویژه: </span>
                      <p className="text-sm mt-1">{requestData.special_instructions}</p>
                    </div>
                  )}
                  {(requestData.pickup_date || requestData.delivery_date) && (
                    <div className="flex gap-4 text-sm">
                      {requestData.pickup_date && (
                        <span>
                          <span className="text-muted-foreground">تاریخ تحویل مبدا: </span>
                          {new Date(requestData.pickup_date).toLocaleDateString("fa-IR")}
                        </span>
                      )}
                      {requestData.delivery_date && (
                        <span>
                          <span className="text-muted-foreground">تاریخ تحویل مقصد: </span>
                          {new Date(requestData.delivery_date).toLocaleDateString("fa-IR")}
                        </span>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sidebar: Expert + Timeline + Actions */}
          <div className="space-y-6">
            {requestData.assigned_expert && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <User className="w-5 h-5" />
                    کارشناس مربوطه
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4 text-muted-foreground" />
                    <span className="font-medium">{requestData.assigned_expert.full_name}</span>
                  </div>
                  {requestData.assigned_at && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="w-4 h-4 shrink-0" />
                      <span>
                        تاریخ اختصاص:{" "}
                        {new Date(requestData.assigned_at).toLocaleDateString("fa-IR", {
                          year: "numeric",
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <Phone className="w-4 h-4 text-muted-foreground" />
                    <a href={`tel:${requestData.assigned_expert.phone}`} className="text-sm hover:underline">
                      {requestData.assigned_expert.phone}
                    </a>
                  </div>
                  {requestData.assigned_expert.email && (
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">ایمیل:</span>
                      <span className="text-sm">{requestData.assigned_expert.email}</span>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {showLatestQuoteCard && requestData.latest_quote && (
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
                      {requestData.latest_quote.amount?.toLocaleString("fa-IR")} {requestData.latest_quote.currency}
                    </span>
                  </div>
                  {requestData.latest_quote.valid_until && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="w-4 h-4 shrink-0" />
                      <span>اعتبار تا: {new Date(requestData.latest_quote.valid_until).toLocaleDateString("fa-IR")}</span>
                    </div>
                  )}
                  {requestData.latest_quote.note && (
                    <p className="text-sm text-muted-foreground border-t pt-2">{requestData.latest_quote.note}</p>
                  )}
                  <div className="text-xs text-muted-foreground pt-1">
                    {requestData.latest_quote.created_at &&
                      new Date(requestData.latest_quote.created_at).toLocaleDateString("fa-IR", {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    {requestData.latest_quote.created_by && ` — ${requestData.latest_quote.created_by}`}
                  </div>
                </CardContent>
              </Card>
            )}

            {(() => {
              const steps = requestData.workflow_steps_simple ?? requestData.workflow_steps ?? [];
              const currentStatusLabel = getCurrentStatusLabel(requestData.status);
              if (steps.length === 0) return null;
              return (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5" />
                      مراحل گردش کار
                      {currentStatusLabel && (
                        <span className="text-sm font-normal text-muted-foreground mr-2">— وضعیت فعلی: {currentStatusLabel}</span>
                      )}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {steps
                        .filter((step) => requestData.workflow_steps_simple ? true : step.name !== "quote_provided")
                        .map((step, index) => (
                        <div key={index} className="flex items-center gap-3">
                          <div
                            className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                              step.is_completed ? "bg-green-100 text-green-600" : "bg-gray-100 text-gray-400"
                            }`}
                          >
                            {step.is_completed ? <CheckCircle className="w-4 h-4" /> : <Clock className="w-4 h-4" />}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium">{step.title}</p>
                            <p className="text-xs text-muted-foreground">
                              {step.is_completed && step.completed_at
                                ? new Date(step.completed_at).toLocaleDateString("fa-IR")
                                : "در انتظار"}
                              {step.meta?.warning === "closed_without_decision" && (
                                <span className="block text-amber-600 mt-0.5">بسته شده بدون ثبت پذیرش/عدم پذیرش</span>
                              )}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              );
            })()}

            <div className="space-y-2">
              <Button onClick={() => navigate("/")} variant="outline" className="w-full">
                <Package className="w-4 h-4 ml-2" />
                درخواست جدید
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PublicTracking;

```
