import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  ArrowLeft,
  Award,
  CheckCircle,
  Clock,
  Mail,
  Package,
  Phone,
  RefreshCw,
  Star,
  Trophy,
  TrendingUp,
  User,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import {
  CustomerProfileHttpError,
  fetchCustomerProfile,
  type CustomerProfileData,
} from "@/lib/api";
import { useI18n } from "@/i18n";

function formatDate(date: string | null | undefined, locale: string, fallback: string): string {
  return date ? new Date(date).toLocaleDateString(locale) : fallback;
}

const CustomerDashboard: React.FC = () => {
  const { customerId } = useParams<{ customerId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { locale, shippingTypeLabel, statusLabel, stepLabel, t } = useI18n();

  const [data, setData] = useState<CustomerProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchCustomerData = useCallback(async () => {
    try {
      const customerData = await fetchCustomerProfile(customerId ?? "");
      setData(customerData);
      if (customerId) {
        try {
          localStorage.setItem("customer_panel_id", customerId);
        } catch {
          // ignore storage errors
        }
      }
    } catch (error) {
      if (error instanceof CustomerProfileHttpError) {
        toast({
          title: t("customer.notFoundTitle"),
          description: t("customer.notFoundDescription"),
          variant: "destructive",
        });
      } else {
        toast({
          title: t("customer.notFoundTitle"),
          description: t("customer.notFoundDescription"),
          variant: "destructive",
        });
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [customerId, t, toast]);

  useEffect(() => {
    if (customerId) {
      fetchCustomerData();
    }
  }, [customerId, fetchCustomerData]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchCustomerData();
  };

  const getLevelInfo = (level: string) => {
    const levels = {
      bronze: { name: locale === "fa-IR" ? "برنز" : "Bronze", color: "bg-amber-500", icon: Award },
      silver: { name: locale === "fa-IR" ? "نقره" : "Silver", color: "bg-gray-400", icon: Star },
      gold: { name: locale === "fa-IR" ? "طلا" : "Gold", color: "bg-yellow-500", icon: Trophy },
      platinum: { name: locale === "fa-IR" ? "پلاتین" : "Platinum", color: "bg-purple-500", icon: TrendingUp },
    };
    return levels[level as keyof typeof levels] || levels.bronze;
  };

  const getStatusBadge = (status: string) => {
    const statusMap = {
      new: { variant: "secondary" as const },
      assigned: { variant: "default" as const },
      in_progress: { variant: "default" as const },
      quoted: { variant: "default" as const },
      waiting_for_customer: { variant: "default" as const },
      won: { variant: "default" as const },
      lost: { variant: "destructive" as const },
      closed: { variant: "secondary" as const },
      completed: { variant: "default" as const },
      cancelled: { variant: "destructive" as const },
    };
    return statusMap[status as keyof typeof statusMap] || { variant: "secondary" as const };
  };

  const customerName = useMemo(() => {
    if (!data) {
      return "";
    }
    return `${data.customer.first_name} ${data.customer.last_name}`.trim();
  }, [data]);

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
                <h2 className="text-lg font-semibold text-foreground">{t("customer.loadingTitle")}</h2>
                <p className="text-sm text-muted-foreground">{t("customer.loadingDescription")}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gradient-background px-4 py-10">
        <div className="mx-auto flex min-h-[70vh] max-w-md items-center justify-center">
          <Card className="w-full border-border/70 bg-card/95 shadow-sm">
            <CardContent className="flex flex-col items-center gap-5 p-8 text-center">
              <div className="rounded-full bg-muted p-4">
                <User className="h-7 w-7 text-muted-foreground" />
              </div>
              <div className="space-y-1">
                <h2 className="text-lg font-semibold text-foreground">{t("customer.notFoundTitle")}</h2>
                <p className="text-sm text-muted-foreground">{t("customer.notFoundDescription")}</p>
              </div>
              <Button onClick={() => navigate("/")} variant="outline">
                <ArrowLeft className="ml-2 h-4 w-4" />
                {t("common.backHome")}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const levelInfo = getLevelInfo(data.customer.customer_level);
  const LevelIcon = levelInfo.icon;

  return (
    <div className="min-h-screen bg-gradient-background">
      <div className="container mx-auto max-w-7xl px-4 py-6 sm:py-8">
        <section className="mb-6 overflow-hidden rounded-2xl border border-border/70 bg-card/95 shadow-sm">
          <div className="flex flex-col gap-5 p-5 sm:p-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-center">
              <Button onClick={() => navigate("/")} variant="outline" size="sm" className="w-fit">
                <ArrowLeft className="ml-2 h-4 w-4" />
                {t("common.back")}
              </Button>
              <div className="min-w-0">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className="bg-background/70">
                    {t("customer.panel")}
                  </Badge>
                  {data.customer.is_email_verified && (
                    <Badge variant="secondary" className="gap-1">
                      <CheckCircle className="h-3.5 w-3.5" />
                      {t("customer.emailVerified")}
                    </Badge>
                  )}
                </div>
                <h1 className="break-words text-2xl font-bold tracking-normal text-foreground sm:text-3xl">
                  {t("customer.welcome")} {customerName}
                </h1>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                  {t("customer.dashboardDescription")}
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
              <p className="text-xs text-muted-foreground">{t("customer.currentPoints")}</p>
              <p className="mt-1 text-2xl font-bold text-primary">{data.customer.loyalty_points}</p>
            </div>
            <div className="border-b border-border/70 p-5 sm:border-b-0 sm:border-l">
              <p className="text-xs text-muted-foreground">{t("customer.totalRequests")}</p>
              <p className="mt-1 text-2xl font-bold text-foreground">{data.customer.total_requests}</p>
            </div>
            <div className="p-5">
              <p className="text-xs text-muted-foreground">{t("customer.completedRequests")}</p>
              <p className="mt-1 text-2xl font-bold text-green-600">{data.customer.completed_requests}</p>
            </div>
          </div>
        </section>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <aside className="space-y-6 lg:col-span-4">
            <Card className="border-border/70 bg-card/95 shadow-sm">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <User className="h-5 w-5 text-primary" />
                  {t("customer.profile")}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="flex items-center gap-3 rounded-xl border bg-muted/20 p-4">
                  <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full ${levelInfo.color}`}>
                    <LevelIcon className="h-6 w-6 text-white" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-foreground">{levelInfo.name}</h3>
                    <p className="text-sm text-muted-foreground">{data.customer.loyalty_points} {t("common.points")}</p>
                  </div>
                </div>

                <Separator />

                <div className="space-y-3">
                  <div className="flex min-w-0 items-center gap-2 rounded-lg bg-background/60 p-3">
                    <Mail className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 break-all text-sm">{data.customer.email}</span>
                    {data.customer.is_email_verified && <CheckCircle className="h-4 w-4 shrink-0 text-green-500" />}
                  </div>
                  <div className="flex min-w-0 items-center gap-2 rounded-lg bg-background/60 p-3">
                    <Phone className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 break-words text-sm">{data.customer.phone}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border/70 bg-card/95 shadow-sm">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Clock className="h-5 w-5 text-primary" />
                  {t("customer.recentActivity")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {data.recent_steps.length === 0 ? (
                  <div className="rounded-xl border border-dashed bg-muted/20 p-6 text-center">
                    <Clock className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
                    <p className="text-sm font-medium text-foreground">{t("customer.noActivityTitle")}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{t("customer.noActivityDescription")}</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {data.recent_steps.map((step, index) => (
                      <div key={index} className="flex gap-3">
                        <div
                          className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                            step.is_completed ? "bg-green-100 text-green-600" : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {step.is_completed ? <CheckCircle className="h-4 w-4" /> : <Clock className="h-4 w-4" />}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-foreground">{stepLabel(step.step_name)}</p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {formatDate(step.completed_at, locale, t("common.pending"))}
                            {step.points_earned > 0 && <span className="mr-2">• {step.points_earned} {t("common.points")}</span>}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </aside>

          <main className="lg:col-span-8">
            <Card className="border-border/70 bg-card/95 shadow-sm">
              <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Package className="h-5 w-5 text-primary" />
                  {t("customer.recentRequests")}
                </CardTitle>
                <Badge variant="outline" className="w-fit">
                  {data.recent_requests.length} {t("common.requests")}
                </Badge>
              </CardHeader>
              <CardContent>
                {data.recent_requests.length === 0 ? (
                  <div className="rounded-xl border border-dashed bg-muted/20 p-8 text-center">
                    <Package className="mx-auto mb-4 h-10 w-10 text-muted-foreground" />
                    <p className="font-medium text-foreground">{t("customer.noRequestsTitle")}</p>
                    <p className="mt-2 text-sm text-muted-foreground">{t("customer.noRequestsDescription")}</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {data.recent_requests.map((request) => {
                      const statusInfo = getStatusBadge(request.status);
                      return (
                        <div
                          key={request.id}
                          className="rounded-xl border border-border/70 bg-background/70 p-4 transition-colors hover:bg-muted/40"
                        >
                          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                            <div className="min-w-0 space-y-2">
                              <div className="flex flex-wrap items-center gap-2">
                                <Badge variant={statusInfo.variant}>{statusLabel(request.status)}</Badge>
                                <Badge variant="outline">
                                  {shippingTypeLabel(request.shipping_type)}
                                </Badge>
                                <span className="text-xs text-muted-foreground">{formatDate(request.created_at, locale, t("common.pending"))}</span>
                              </div>
                              <p className="break-words font-semibold text-foreground">{t("common.request")} #{request.id}</p>
                              {request.assigned_expert && (
                                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
                                  <span className="flex min-w-0 items-center gap-1">
                                    <User className="h-4 w-4 shrink-0" />
                                    <span className="break-words">{t("common.expert")}: {request.assigned_expert.full_name}</span>
                                  </span>
                                  <span className="flex min-w-0 items-center gap-1">
                                    <Phone className="h-4 w-4 shrink-0" />
                                    <span className="break-words">{request.assigned_expert.phone}</span>
                                  </span>
                                </div>
                              )}
                            </div>
                            <Button
                              variant="outline"
                              size="sm"
                              className="w-full sm:w-auto"
                              onClick={() => navigate(`/request/${request.id}?customer=${customerId}`)}
                            >
                              {t("customer.viewDetails")}
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </main>
        </div>
      </div>
    </div>
  );
};

export default CustomerDashboard;
