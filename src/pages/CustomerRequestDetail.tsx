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
import { useI18n } from "@/i18n";

const CUSTOMER_PANEL_ID_KEY = "customer_panel_id";
const showLatestQuoteCard: boolean = false;

function formatDate(date: string | null | undefined, locale: string, fallback: string): string {
  return date ? new Date(date).toLocaleDateString(locale) : fallback;
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
  const { locale, shippingTypeLabel, statusLabel, stepLabel, t } = useI18n();

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
          title: t("customer.requestNotFoundTitle"),
          description: t("customer.requestNotFoundDescription"),
          variant: "destructive",
        });
      } else {
        toast({
          title: t("customer.requestNotFoundTitle"),
          description: t("customer.requestNotFoundDescription"),
          variant: "destructive",
        });
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [customer, requestId, t, toast]);

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
      new: { variant: "secondary" as const, color: "bg-gray-100 text-gray-800" },
      assigned: { variant: "default" as const, color: "bg-blue-100 text-blue-800" },
      in_progress: { variant: "default" as const, color: "bg-yellow-100 text-yellow-800" },
      quoted: { variant: "default" as const, color: "bg-purple-100 text-purple-800" },
      waiting_for_customer: { variant: "default" as const, color: "bg-orange-100 text-orange-800" },
      won: { variant: "default" as const, color: "bg-green-100 text-green-800" },
      lost: { variant: "destructive" as const, color: "bg-red-100 text-red-800" },
      closed: { variant: "secondary" as const, color: "bg-gray-100 text-gray-800" },
      completed: { variant: "default" as const, color: "bg-green-100 text-green-800" },
      cancelled: { variant: "destructive" as const, color: "bg-red-100 text-red-800" },
    };
    return statusMap[status as keyof typeof statusMap] || {
      variant: "secondary" as const,
      color: "bg-gray-100 text-gray-800",
    };
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
                <h2 className="text-lg font-semibold text-foreground">{t("customer.requestDetailsLoadingTitle")}</h2>
                <p className="text-sm text-muted-foreground">{t("customer.requestDetailsLoadingDescription")}</p>
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
                  {customer ? t("customer.requestNotFoundTitle") : t("customer.loginRequiredTitle")}
                </h2>
                <p className="text-sm leading-6 text-muted-foreground">
                  {customer
                    ? t("customer.requestNotFoundDescription")
                    : t("customer.loginRequiredDescription")}
                </p>
              </div>
              <Button onClick={() => navigate(backDestination)} variant="outline">
                <ArrowLeft className="ml-2 h-4 w-4" />
                {customer ? t("customer.backToPanel") : t("common.backHome")}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const statusInfo = getStatusBadge(requestDetail.status);
  const currentStatusLabel = statusLabel(requestDetail.status);

  return (
    <div className="min-h-screen bg-gradient-background">
      <div className="container mx-auto max-w-7xl px-4 py-6 sm:py-8">
        <section className="mb-6 overflow-hidden rounded-2xl border border-border/70 bg-card/95 shadow-sm">
          <div className="flex flex-col gap-5 p-5 sm:p-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-center">
              <Button onClick={() => navigate(backDestination)} variant="outline" size="sm" className="w-fit">
                <ArrowLeft className="ml-2 h-4 w-4" />
                {t("common.back")}
              </Button>
              <div className="min-w-0">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <Badge variant={statusInfo.variant} className={statusInfo.color}>
                    {statusLabel(requestDetail.status)}
                  </Badge>
                  <Badge variant="outline" className="bg-background/70">
                    {shippingTypeLabel(requestDetail.shipping_type, { full: true })}
                  </Badge>
                </div>
                <h1 className="break-words text-2xl font-bold tracking-normal text-foreground sm:text-3xl">
                  {t("customer.requestDetails")} #{requestDetail.id}
                </h1>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                  {t("customer.requestDetailsDescription")}
                </p>
              </div>
            </div>
            <Button onClick={handleRefresh} variant="outline" size="sm" disabled={refreshing} className="w-fit">
              <RefreshCw className={`ml-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
              {t("common.refresh")}
            </Button>
          </div>

          <div className="grid border-t border-border/70 bg-muted/20 sm:grid-cols-3">
            <div className="border-b border-border/70 p-5 sm:border-b-0 sm:border-l">
              <p className="text-xs text-muted-foreground">{t("common.createdAt")}</p>
              <p className="mt-1 text-lg font-semibold text-foreground">{formatDate(requestDetail.created_at, locale, t("common.pending"))}</p>
            </div>
            <div className="border-b border-border/70 p-5 sm:border-b-0 sm:border-l">
              <p className="text-xs text-muted-foreground">{t("customer.pointsEarned")}</p>
              <p className="mt-1 text-2xl font-bold text-primary">{requestDetail.total_points_earned}</p>
            </div>
            <div className="p-5">
              <p className="text-xs text-muted-foreground">{t("customer.progress")}</p>
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
                  {t("publicTracking.requestInfo")}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="space-y-3">
                  <div className="flex items-center gap-2 rounded-lg bg-background/60 p-3">
                    <Calendar className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">{t("common.createdAt")}:</span>
                    <span className="text-sm font-medium text-foreground">{formatDate(requestDetail.created_at, locale, t("common.pending"))}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 rounded-lg bg-background/60 p-3">
                    <Package className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">{t("common.shippingType")}:</span>
                    <Badge variant="outline">
                      {shippingTypeLabel(requestDetail.shipping_type)}
                    </Badge>
                  </div>
                </div>

                <Separator />

                <div className="rounded-xl border bg-muted/20 p-4 text-center">
                  <div className="text-2xl font-bold text-primary">{requestDetail.total_points_earned}</div>
                  <div className="mt-1 text-sm text-muted-foreground">{t("customer.pointsEarned")}</div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl border bg-background/60 p-4 text-center">
                    <div className="text-xl font-bold text-green-600">{requestDetail.completed_steps}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{t("customer.completed")}</div>
                  </div>
                  <div className="rounded-xl border bg-background/60 p-4 text-center">
                    <div className="text-xl font-bold text-muted-foreground">{requestDetail.total_steps}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{t("customer.totalSteps")}</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {requestDetail.assigned_expert && (
              <Card className="border-border/70 bg-card/95 shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <User className="h-5 w-5 text-primary" />
                    {t("publicTracking.assignedExpert")}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="flex items-center gap-3 rounded-xl border bg-muted/20 p-4">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary/10">
                      <User className="h-6 w-6 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="break-words font-semibold text-foreground">{requestDetail.assigned_expert.full_name}</h3>
                      <p className="text-sm text-muted-foreground">{t("customer.forwarderExpert")}</p>
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
                      {t("customer.expertWillCall")}
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
                  {t("customer.workProgress")}
                  {currentStatusLabel && (
                    <span className="text-sm font-normal text-muted-foreground">— {t("common.currentStatus")}: {currentStatusLabel}</span>
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
                            {requestDetail.workflow_steps_simple ? step.title : stepLabel(step.name)}
                          </p>
                          {step.points_earned != null && step.points_earned > 0 && (
                            <Badge variant="outline" className="w-fit">
                              {step.points_earned} {t("common.points")}
                            </Badge>
                          )}
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {step.is_completed && step.completed_at ? formatDate(step.completed_at, locale, t("common.pending")) : t("common.pending")}
                        </p>
                        {step.meta?.warning === "closed_without_decision" && (
                          <p className="mt-2 text-sm text-amber-600">{t("publicTracking.closedWithoutDecision")}</p>
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
                    {t("customer.quoteTitle")}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-sm text-muted-foreground">{t("common.amount")}</span>
                    <span className="text-lg font-bold text-foreground">
                      {requestDetail.latest_quote.amount?.toLocaleString(locale)} {requestDetail.latest_quote.currency}
                    </span>
                  </div>
                  {requestDetail.latest_quote.valid_until && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="h-4 w-4 shrink-0" />
                      <span>{formatDate(requestDetail.latest_quote.valid_until, locale, t("common.pending"))}</span>
                    </div>
                  )}
                  {requestDetail.latest_quote.note && (
                    <p className="border-t pt-2 text-sm text-muted-foreground">{requestDetail.latest_quote.note}</p>
                  )}
                  <div className="pt-1 text-xs text-muted-foreground">
                    {requestDetail.latest_quote.created_at &&
                      new Date(requestDetail.latest_quote.created_at).toLocaleDateString(locale, {
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
