import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";
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
import { useI18n } from "@/i18n";
import { formatLocalDate } from "@/lib/localDate";

const showLatestQuoteCard: boolean = false;

type StatusInfo = {
  variant: "secondary" | "default" | "destructive";
  color: string;
};

const getStatusBadge = (status: string): StatusInfo => {
  const statusMap: Record<string, StatusInfo> = {
    new: { variant: "secondary", color: "bg-gray-100 text-gray-800" },
    assigned: { variant: "default", color: "bg-blue-100 text-blue-800" },
    in_progress: { variant: "default", color: "bg-yellow-100 text-yellow-800" },
    quoted: { variant: "default", color: "bg-purple-100 text-purple-800" },
    waiting_for_customer: { variant: "default", color: "bg-orange-100 text-orange-800" },
    won: { variant: "default", color: "bg-green-100 text-green-800" },
    lost: { variant: "destructive", color: "bg-red-100 text-red-800" },
    closed: { variant: "secondary", color: "bg-gray-100 text-gray-800" },
    cancelled: { variant: "destructive", color: "bg-red-100 text-red-800" },
  };
  return statusMap[status] || { variant: "secondary", color: "bg-gray-100 text-gray-800" };
};

const formatDate = (
  value?: string | null,
  options?: Intl.DateTimeFormatOptions,
  fallback = "—",
  locale = "fa-IR",
) => {
  if (!value) return fallback;
  return new Intl.DateTimeFormat(locale, options).format(new Date(value));
};

const getLocationDisplay = (
  location: PublicTrackingData["route"]["origin"],
  isInternational: boolean,
  fallback: string,
) => {
  if (!location) return "—";
  if (isInternational) {
    const parts = [location.city_international, location.country].filter(Boolean);
    return parts.length ? parts.join("، ") : fallback;
  }
  const parts = [location.city, location.county, location.province].filter(Boolean);
  return parts.length ? parts.join("، ") : fallback;
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
  const { locale, statusLabel, shippingTypeLabel, t } = useI18n();

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
          title: t("common.notRegistered"),
          description: t("publicTracking.notFoundDescription"),
          variant: "destructive",
        });
      } else {
        toast({
          title: t("common.notRegistered"),
          description: t("publicTracking.notFoundDescription"),
          variant: "destructive",
        });
      }
    } finally {
      setLoading(false);
    }
  }, [requestId, t, toast]);

  useEffect(() => {
    if (requestId) {
      fetchRequestData();
    }
  }, [fetchRequestData, requestId]);

  const statusInfo = requestData ? getStatusBadge(requestData.status) : null;
  const currentStatusLabel = requestData ? statusLabel(requestData.status) : "";
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
            <h1 className="text-xl font-bold text-foreground">{t("publicTracking.loadingTitle")}</h1>
            <p className="mt-2 text-sm leading-7 text-muted-foreground">
              {t("publicTracking.loadingDescription")}
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
            <h1 className="text-2xl font-bold text-foreground">{t("publicTracking.notFoundTitle")}</h1>
            <p className="mx-auto mt-3 max-w-sm text-sm leading-7 text-muted-foreground">
              {t("publicTracking.notFoundDescription")}
            </p>
            <div className="mt-7 grid gap-3 sm:grid-cols-2">
              <Button onClick={() => navigate("/")} className="w-full">
                <ArrowLeft className="h-4 w-4" />
                {t("common.backHome")}
              </Button>
              <Button onClick={() => navigate("/")} variant="outline" className="w-full">
                <Package className="h-4 w-4" />
                {t("common.createNewRequest")}
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
  const unitTracking = requestData.unit_tracking;

  return (
    <main className="min-h-screen bg-gradient-background">
      <div className="container mx-auto max-w-7xl px-4 py-6 md:py-10">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <Button onClick={() => navigate("/")} variant="outline" size="sm">
            <ArrowLeft className="h-4 w-4" />
            {t("common.back")}
          </Button>
          <Button onClick={() => navigate("/")} variant="ghost" size="sm">
            <Home className="h-4 w-4" />
            {t("common.home")}
          </Button>
        </div>

        <section className="mb-6 overflow-hidden rounded-lg border border-border/80 bg-card/95 shadow-sm">
          <div className="border-b border-border/70 bg-muted/25 p-5 md:p-7">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <Badge variant={statusInfo.variant} className={statusInfo.color}>
                    {statusLabel(requestData.status)}
                  </Badge>
                  <Badge variant="outline">
                    {shippingTypeLabel(requestData.shipping_type)}
                  </Badge>
                  {currentStatusLabel && (
                    <Badge variant="outline">{t("common.currentStatus")}: {currentStatusLabel}</Badge>
                  )}
                </div>
                <h1 className="break-words font-mono text-2xl font-bold tracking-normal text-foreground md:text-3xl">
                  {requestData.tracking_number}
                </h1>
                <p className="mt-2 max-w-2xl text-sm leading-7 text-muted-foreground">
                  {t("publicTracking.heroDescription")}
                </p>
              </div>
              <div className="grid gap-3 text-sm sm:grid-cols-2 lg:min-w-[360px]">
                <Field
                  label={t("common.createdAt")}
                  value={formatDate(requestData.created_at, {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  }, "—", locale)}
                />
                <Field
                  label={t("publicTracking.assignedAt")}
                  value={formatDate(requestData.assigned_at, {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  }, "—", locale)}
                />
              </div>
            </div>
          </div>

          <div className="grid gap-0 divide-y divide-border/70 md:grid-cols-3 md:divide-x md:divide-x-reverse md:divide-y-0">
            <div className="p-5">
              <p className="text-xs font-medium text-muted-foreground">{t("common.trackingNumber")}</p>
              <p className="mt-2 break-all font-mono text-lg font-bold text-foreground">{requestData.tracking_number}</p>
            </div>
            <div className="p-5">
              <p className="text-xs font-medium text-muted-foreground">{t("common.currentStatus")}</p>
              <div className="mt-2">
                <Badge variant={statusInfo.variant} className={statusInfo.color}>
                  {statusLabel(requestData.status)}
                </Badge>
              </div>
            </div>
            <div className="p-5">
              <p className="text-xs font-medium text-muted-foreground">{t("common.transportMethod")}</p>
              <p className="mt-2 text-sm font-semibold text-foreground">{transportLabel || "—"}</p>
            </div>
          </div>
        </section>

        {requestData.latest_quote && (
          <Section icon={DollarSign} title={t("customer.quoteTitle")} className="mb-6">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                label={t("common.amount")}
                value={`${requestData.latest_quote.amount?.toLocaleString(locale)} ${requestData.latest_quote.currency}`}
              />
              {requestData.latest_quote.valid_until && (
                <Field
                  label={t("customer.quoteValidUntil")}
                  value={formatLocalDate(requestData.latest_quote.valid_until, locale)}
                />
              )}
            </div>
            {requestData.latest_quote.note && (
              <p className="mt-4 border-t border-border/70 pt-3 text-sm text-muted-foreground">
                {requestData.latest_quote.note}
              </p>
            )}
            {requestData.latest_quote.customer_response === "accepted" && (
              <div className="mt-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm font-medium text-green-800">
                {t("customer.quoteAccepted")}
              </div>
            )}
            {requestData.latest_quote.customer_response === "declined" && (
              <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm font-medium text-red-800">
                {t("customer.quoteDeclined")}
              </div>
            )}
          </Section>
        )}

        {unitTracking && (
          <Section icon={Truck} title={t("multiTracking.customerTitle")} className="mb-6">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Field label={t("multiTracking.aggregateStatus")} value={t(`multiTracking.status.${unitTracking.aggregate_status}`)} />
              <Field label={t("multiTracking.unitCount")} value={unitTracking.summary.total_units.toLocaleString(locale)} />
              <Field label={t("multiTracking.deliveredCount")} value={unitTracking.summary.delivered.toLocaleString(locale)} />
              <Field label={t("multiTracking.latestUpdate")} value={formatDate(unitTracking.last_updated_at, { dateStyle: "medium", timeStyle: "short" }, "—", locale)} />
            </div>
            <div className="mt-5">
              <div className="mb-2 flex items-center justify-between text-sm font-medium">
                <span>{t("multiTracking.overallProgress")}</span>
                <span>{unitTracking.progress_percent.toLocaleString(locale)}%</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuenow={unitTracking.progress_percent} aria-valuemin={0} aria-valuemax={100}>
                <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${unitTracking.progress_percent}%` }} />
              </div>
            </div>
            {unitTracking.aggregate_status === "partially_delivered" && (
              <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm font-medium text-amber-900">
                {t("multiTracking.partialDelivery")}
              </div>
            )}
            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              {unitTracking.units.map((unit) => (
                <Card key={unit.unit_code} className="border-border/80 shadow-none">
                  <CardContent className="p-5">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-bold text-foreground">{unit.display_name || unit.unit_code}</p>
                        <p className="mt-1 font-mono text-xs text-muted-foreground">{unit.unit_code} · {unit.unit_type}</p>
                        {unit.vehicle_reference && <p className="mt-1 text-xs text-muted-foreground">{t("multiTracking.vehicleReference")}: {unit.vehicle_reference}</p>}
                      </div>
                      <Badge variant="outline">{t(`multiTracking.status.${unit.latest_status}`)}</Badge>
                    </div>
                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <Field label={t("multiTracking.latestLocation")} value={unit.latest_location || "—"} />
                      <Field label={t("multiTracking.latestUpdate")} value={formatDate(unit.latest_event_at, { dateStyle: "medium", timeStyle: "short" }, "—", locale)} />
                    </div>
                    <div className="mt-4">
                      <p className="mb-3 text-sm font-bold">{t("multiTracking.customerHistory")}</p>
                      {unit.timeline.length === 0 ? <p className="text-sm text-muted-foreground">{t("multiTracking.noUpdates")}</p> : (
                        <ol className="space-y-3 border-s border-border ps-4">
                          {unit.timeline.map((update, index) => (
                            <li key={`${update.event_at}-${index}`} className="text-sm">
                              <p className="font-semibold">{t(`multiTracking.status.${update.status}`)}</p>
                              <p className="text-muted-foreground">{[update.location, update.customer_note].filter(Boolean).join(" · ") || "—"}</p>
                              <time className="text-xs text-muted-foreground">{formatDate(update.event_at, { dateStyle: "medium", timeStyle: "short" }, "—", locale)}</time>
                            </li>
                          ))}
                        </ol>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </Section>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
          <div className="space-y-6">
            <Section icon={Package} title={t("publicTracking.requestInfo")}>
              <div className="grid gap-4 md:grid-cols-2">
                <Field label={t("common.createdAt")} value={formatDate(requestData.created_at, undefined, "—", locale)} />
                <Field
                  label={t("common.shippingType")}
                  value={<Badge variant="outline">{shippingTypeLabel(requestData.shipping_type)}</Badge>}
                />
              </div>
            </Section>

            <Section icon={Route} title={t("publicTracking.route")}>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-md border border-border/70 bg-background/70 p-4">
                  <div className="mb-3 flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">{t("common.origin")}</Badge>
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <p className="break-words text-sm font-semibold leading-7 text-foreground">
                    {getLocationDisplay(requestData.route?.origin, isInternational, t("common.notRegistered"))}
                  </p>
                </div>
                <div className="rounded-md border border-border/70 bg-background/70 p-4">
                  <div className="mb-3 flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">{t("common.destination")}</Badge>
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <p className="break-words text-sm font-semibold leading-7 text-foreground">
                    {getLocationDisplay(requestData.route?.destination, isInternational, t("common.notRegistered"))}
                  </p>
                </div>
              </div>
              {transportLabel && (
                <div className="mt-4 rounded-md border border-border/70 bg-muted/20 p-4">
                  <div className="flex items-center gap-2 text-sm">
                    <Truck className="h-4 w-4 text-muted-foreground" />
                    <span className="text-muted-foreground">{t("common.transportMethod")}:</span>
                    <span className="font-semibold text-foreground">{transportLabel}</span>
                  </div>
                </div>
              )}
            </Section>

            <Section icon={User} title={t("publicTracking.contactInfo")}>
              <div className="grid gap-4 md:grid-cols-2">
                <Field
                  label={t("common.phone")}
                  value={
                    <span className="inline-flex items-center gap-2">
                      <Phone className="h-4 w-4 text-muted-foreground" />
                      {requestData.contact_phone}
                    </span>
                  }
                />
                {(requestData.customer_first_name || requestData.customer_last_name) && (
                  <Field
                    label={t("common.customerName")}
                    value={`${requestData.customer_first_name || ""} ${requestData.customer_last_name || ""}`.trim()}
                  />
                )}
              </div>
            </Section>

            {hasCargo && (
              <Section icon={FileText} title={t("common.cargoDetails")}>
                <div className="space-y-4">
                  {requestData.cargo_description && (
                    <Field label={t("common.description")} value={requestData.cargo_description} />
                  )}
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {requestData.cargo_weight != null && (
                      <Field label={t("common.weightKg")} value={requestData.cargo_weight} />
                    )}
                    {requestData.cargo_volume != null && (
                      <Field label={t("common.volumeM3")} value={requestData.cargo_volume} />
                    )}
                    {requestData.cargo_value != null && (
                      <Field label={t("common.value")} value={requestData.cargo_value} />
                    )}
                    {requestData.pickup_date && (
                      <Field label={t("common.createdAt")} value={formatLocalDate(requestData.pickup_date, locale)} />
                    )}
                    {requestData.delivery_date && (
                      <Field label={t("common.createdAt")} value={formatLocalDate(requestData.delivery_date, locale)} />
                    )}
                  </div>
                  {requestData.special_instructions && (
                    <Field label={t("common.specialInstructions")} value={requestData.special_instructions} />
                  )}
                </div>
              </Section>
            )}
          </div>

          <aside className="space-y-6">
            {requestData.assigned_expert && (
              <Section icon={User} title={t("publicTracking.assignedExpert")}>
                <div className="space-y-4">
                  <Field label={t("common.expert")} value={requestData.assigned_expert.full_name} />
                  {requestData.assigned_at && (
                    <Field
                      label={t("publicTracking.assignedAt")}
                      value={formatDate(requestData.assigned_at, {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      }, "—", locale)}
                    />
                  )}
                  <Field
                    label={t("common.phone")}
                    value={
                      <a href={`tel:${requestData.assigned_expert.phone}`} className="hover:underline">
                        {requestData.assigned_expert.phone}
                      </a>
                    }
                  />
                  {requestData.assigned_expert.email && (
                    <Field label={t("common.email")} value={requestData.assigned_expert.email} />
                  )}
                </div>
              </Section>
            )}

            {showLatestQuoteCard && requestData.latest_quote && (
              <Section icon={DollarSign} title={t("customer.quoteTitle")}>
                <div className="space-y-4">
                  <Field
                    label={t("common.amount")}
                    value={`${requestData.latest_quote.amount?.toLocaleString(locale)} ${requestData.latest_quote.currency}`}
                  />
                  {requestData.latest_quote.valid_until && (
                    <Field
                      label={t("common.validUntil")}
                      value={formatLocalDate(requestData.latest_quote.valid_until, locale)}
                    />
                  )}
                  {requestData.latest_quote.note && (
                    <Field label={t("common.notes")} value={requestData.latest_quote.note} />
                  )}
                  <p className="text-xs leading-6 text-muted-foreground">
                    {formatDate(requestData.latest_quote.created_at, {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    }, "", locale)}
                    {requestData.latest_quote.created_by && ` — ${requestData.latest_quote.created_by}`}
                  </p>
                </div>
              </Section>
            )}

            {workflowSteps.length > 0 && (
              <Section icon={CheckCircle} title={t("publicTracking.workflow")}>
                {currentStatusLabel && (
                  <div className="mb-4 rounded-md bg-muted/30 px-3 py-2 text-xs font-medium text-muted-foreground">
                    {t("common.currentStatus")}: {currentStatusLabel}
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
                            ? formatDate(step.completed_at, undefined, "—", locale)
                            : t("common.pending")}
                          {step.meta?.warning === "closed_without_decision" && (
                            <span className="mt-1 block text-amber-600">
                              {t("publicTracking.closedWithoutDecision")}
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
                  {t("common.newRequest")}
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
