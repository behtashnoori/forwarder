import { type ElementType, useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import {
  AlertCircle,
  BarChart3,
  Bell,
  Clock,
  FileSpreadsheet,
  Files,
  Gauge,
  LogOut,
  MapPin,
  Package,
  RefreshCw,
  Scale,
  Settings,
  ShieldCheck,
  Trophy,
  Truck,
  Users,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { AdminDashboardHttpError, fetchAdminDashboard, type AdminDashboardStats } from "@/lib/api";
import AdminReportsTab from "@/components/AdminReportsTab";
import ReferralRulesTab from "@/components/ReferralRulesTab";
import SiteSettingsTab from "@/components/SiteSettingsTab";
import TrackingLocationsAdminTab from "@/components/TrackingLocationsAdminTab";
import LocationsAdminTab from "@/components/LocationsAdminTab";
import DocumentDefinitionsTab from "@/components/DocumentDefinitionsTab";
import OrganizationDocumentPolicyTab from "@/components/OrganizationDocumentPolicyTab";
import MasterDataAdminTab from "@/components/MasterDataAdminTab";
import CargoCatalogAdminTab from "@/components/CargoCatalogAdminTab";
import LogisticsNetworkAdminTab from "@/components/LogisticsNetworkAdminTab";
import OperationalReasonsAdminTab from "@/components/OperationalReasonsAdminTab";
import UnassignedRequestsTab from "@/components/UnassignedRequestsTab";
import UserManagement from "./UserManagement";
import { useI18n } from "@/i18n";
import { logoutAndClearExpertSession } from "@/lib/authSession";
import ReleaseIdentity from "@/components/ReleaseIdentity";

type MetricCardProps = {
  label: string;
  value: number;
  helper: string;
  icon: ElementType;
  tone: string;
};

type DistributionTone = {
  dot: string;
  row: string;
  icon: string;
};

const formatNumber = (value: number, locale: string) => new Intl.NumberFormat(locale).format(value);

const MetricCard = ({ label, value, helper, icon: Icon, tone, locale }: MetricCardProps & { locale: string }) => (
  <Card className="h-full rounded-3xl border-slate-200 bg-white shadow-sm">
    <CardContent className="flex h-full items-start justify-between gap-4 p-5">
      <div className="min-w-0">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <p className="mt-3 text-3xl font-bold tracking-normal text-slate-950">{formatNumber(value, locale)}</p>
        <p className="mt-2 text-xs leading-5 text-slate-500">{helper}</p>
      </div>
      <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl ${tone}`}>
        <Icon className="h-6 w-6" />
      </div>
    </CardContent>
  </Card>
);

const EmptyDashboardState = ({ title, description }: { title: string; description: string }) => (
  <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
    <CardContent className="flex flex-col items-center gap-4 p-10 text-center">
      <div className="rounded-2xl bg-slate-100 p-4">
        <BarChart3 className="h-8 w-8 text-slate-400" />
      </div>
      <div className="space-y-1">
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <p className="max-w-xl text-sm leading-6 text-slate-500">
          {description}
        </p>
      </div>
    </CardContent>
  </Card>
);

const distributionTones: DistributionTone[] = [
  { dot: "bg-blue-500", row: "bg-blue-50 border-blue-100", icon: "bg-blue-100 text-blue-700" },
  { dot: "bg-emerald-500", row: "bg-emerald-50 border-emerald-100", icon: "bg-emerald-100 text-emerald-700" },
  { dot: "bg-violet-500", row: "bg-violet-50 border-violet-100", icon: "bg-violet-100 text-violet-700" },
  { dot: "bg-orange-500", row: "bg-orange-50 border-orange-100", icon: "bg-orange-100 text-orange-700" },
  { dot: "bg-rose-500", row: "bg-rose-50 border-rose-100", icon: "bg-rose-100 text-rose-700" },
];

const AdminPanel = () => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const { locale, statusLabel, t, tf, transportLabel } = useI18n();
  const [dashboardStats, setDashboardStats] = useState<AdminDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("dashboard");
  const isPlatformAdmin = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem("expert_user") || "{}").authority === "PLATFORM_ADMIN";
    } catch {
      return false;
    }
  }, []);
  const isOrganizationAdmin = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem("expert_user") || "{}").authority === "ORGANIZATION_ADMIN";
    } catch {
      return false;
    }
  }, []);

  const adminLabel = useMemo(() => {
    try {
      const storedUser = localStorage.getItem("expert_user");
      if (!storedUser) return t("common.systemAdmin");
      const user = JSON.parse(storedUser) as { full_name?: string; username?: string; role?: string };
      return user.full_name || user.username || t("common.systemAdmin");
    } catch (error) {
      return t("common.systemAdmin");
    }
  }, [t]);

  const handleLogout = async () => {
    const confirmed = await logoutAndClearExpertSession();
    if (!confirmed) {
      toast({ title: t("common.error"), description: t("admin.serverError"), variant: "destructive" });
    }
    navigate("/", { replace: true });
  };

  const loadDashboard = useCallback(async () => {
    const token = localStorage.getItem("expert_token");
    if (!token || token === "null") {
      toast({
        title: t("admin.loginAgain"),
        description: t("admin.loginAgainDescription"),
        variant: "destructive",
      });
      localStorage.removeItem("expert_user");
      localStorage.removeItem("expert_token");
      navigate("/", { replace: true });
      return;
    }

    try {
      setLoading(true);
      const data = await fetchAdminDashboard(token);
      setDashboardStats(data);
    } catch (error) {
      if (error instanceof AdminDashboardHttpError && error.status === 401) {
        toast({
          title: t("admin.sessionExpired"),
          description: t("admin.loginAgainDescription"),
          variant: "destructive",
        });
        localStorage.removeItem("expert_user");
        localStorage.removeItem("expert_token");
        navigate("/", { replace: true });
      } else if (error instanceof AdminDashboardHttpError) {
        toast({
          title: t("common.error"),
          description: t("admin.dashboardFetchError"),
          variant: "destructive",
        });
      } else {
        toast({
          title: t("common.error"),
          description: t("admin.serverError"),
          variant: "destructive",
        });
      }
    } finally {
      setLoading(false);
    }
  }, [navigate, t, toast]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const secondaryMetrics = dashboardStats
    ? [
        {
          label: t("admin.totalRequests"),
          value: dashboardStats.total_requests,
          icon: Package,
          tone: "bg-blue-50 text-blue-700",
        },
        {
          label: t("admin.last24h"),
          value: dashboardStats.last_24h_count,
          icon: Clock,
          tone: "bg-emerald-50 text-emerald-700",
        },
        {
          label: t("admin.last7Days"),
          value: dashboardStats.last_7_days_count,
          icon: Gauge,
          tone: "bg-violet-50 text-violet-700",
        },
        {
          label: t("status.unassigned"),
          value: dashboardStats.unassigned_count,
          icon: AlertCircle,
          tone: "bg-orange-50 text-orange-700",
        },
      ]
    : [];

  return (
    <div className="min-h-screen bg-[#FAFAFA]" dir="rtl">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
        <section className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-col gap-6 p-5 lg:flex-row lg:items-center lg:justify-between lg:p-7">
            <div className="flex min-w-0 items-start gap-4">
              <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-3xl bg-blue-600 text-white shadow-sm">
                <ShieldCheck className="h-8 w-8" />
              </div>
              <div className="min-w-0">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <Badge className="rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1 text-emerald-700 hover:bg-emerald-50">
                    {t("admin.badge")}
                  </Badge>
                </div>
                <h1 className="text-2xl font-bold tracking-normal text-slate-950 sm:text-3xl">{t("admin.title")}</h1>
                <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-500">
                  {t("admin.description")}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 lg:justify-end">
              <Button variant="outline" size="icon" className="h-10 w-10 rounded-full border-slate-200 bg-white">
                <Bell className="h-4 w-4 text-slate-600" />
              </Button>
              <div className="flex h-10 items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-4 text-sm font-medium text-slate-700">
                <Users className="h-4 w-4 text-blue-600" />
                {adminLabel}
              </div>
              <Button onClick={loadDashboard} disabled={loading} variant="outline" size="sm" className="h-10 rounded-full">
                <RefreshCw className={`ml-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                {t("common.refresh")}
              </Button>
              <Button onClick={handleLogout} variant="outline" size="sm" className="h-10 rounded-full text-red-600 hover:bg-red-50 hover:text-red-700">
                <LogOut className="ml-2 h-4 w-4" />
                {t("common.logout")}
              </Button>
            </div>
          </div>
        </section>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid h-auto w-full grid-cols-2 gap-1 rounded-[1.75rem] border border-slate-200 bg-white p-2 shadow-sm md:grid-cols-4 xl:grid-cols-9">
            <TabsTrigger
              value="dashboard"
              className="gap-2 rounded-2xl border-b-2 border-transparent py-3 data-[state=active]:border-blue-600 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-700 data-[state=active]:shadow-none"
            >
              <BarChart3 className="h-4 w-4" />
              {t("admin.dashboard")}
            </TabsTrigger>
            {isOrganizationAdmin && <TabsTrigger value="unassigned" className="gap-2 rounded-2xl py-3">
              <AlertCircle className="h-4 w-4" />درخواست‌های تخصیص‌نیافته
            </TabsTrigger>}
            <TabsTrigger
              value="reports"
              className="gap-2 rounded-2xl border-b-2 border-transparent py-3 data-[state=active]:border-blue-600 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-700 data-[state=active]:shadow-none"
            >
              <FileSpreadsheet className="h-4 w-4" />
              {t("admin.reports")}
            </TabsTrigger>
            <TabsTrigger
              value="users"
              className="gap-2 rounded-2xl border-b-2 border-transparent py-3 data-[state=active]:border-blue-600 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-700 data-[state=active]:shadow-none"
            >
              <Users className="h-4 w-4" />
              {t("admin.userManagement")}
            </TabsTrigger>
            <TabsTrigger
              value="referral-rules"
              className="gap-2 rounded-2xl border-b-2 border-transparent py-3 data-[state=active]:border-blue-600 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-700 data-[state=active]:shadow-none"
            >
              <Scale className="h-4 w-4" />
              {t("admin.referralRules")}
            </TabsTrigger>
            {isPlatformAdmin && <TabsTrigger
              value="site-settings"
              className="gap-2 rounded-2xl border-b-2 border-transparent py-3 data-[state=active]:border-blue-600 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-700 data-[state=active]:shadow-none"
            >
              <Settings className="h-4 w-4" />
              {t("admin.siteSettings")}
            </TabsTrigger>}
            {isPlatformAdmin && <TabsTrigger
              value="locations"
              className="gap-2 rounded-2xl border-b-2 border-transparent py-3 data-[state=active]:border-blue-600 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-700 data-[state=active]:shadow-none"
            >
              <MapPin className="h-4 w-4" />
              مبدا و مقصد
            </TabsTrigger>}
            {isPlatformAdmin && <TabsTrigger value="tracking-locations" className="gap-2 rounded-2xl py-3">نقاط ردیابی</TabsTrigger>}
            {isPlatformAdmin && <TabsTrigger value="documents" className="gap-2 rounded-2xl py-3"><Files className="h-4 w-4"/>مدیریت مستندات</TabsTrigger>}
            {isOrganizationAdmin && <TabsTrigger value="organization-documents" className="gap-2 rounded-2xl py-3"><Files className="h-4 w-4"/>الزامات مستندات سازمان</TabsTrigger>}
            {isPlatformAdmin && <TabsTrigger value="master-data" className="gap-2 rounded-2xl py-3"><Package className="h-4 w-4"/>داده‌های مرجع</TabsTrigger>}
            <TabsTrigger value="cargo-catalog" className="gap-2 rounded-2xl py-3"><Package className="h-4 w-4"/>کاتالوگ کالا</TabsTrigger>
            <TabsTrigger value="logistics-network" className="gap-2 rounded-2xl py-3"><MapPin className="h-4 w-4"/>شبکه لجستیکی</TabsTrigger>
            <TabsTrigger value="operational-reasons" className="gap-2 rounded-2xl py-3">دلایل عملیاتی</TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            {loading ? (
              <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                <CardContent className="flex min-h-[260px] flex-col items-center justify-center gap-4 p-8 text-center">
                  <div className="rounded-2xl bg-blue-50 p-4">
                    <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
                  </div>
                  <div className="space-y-1">
                    <h2 className="text-lg font-semibold text-slate-900">{t("admin.loadingTitle")}</h2>
                    <p className="text-sm leading-6 text-slate-500">
                      {t("admin.loadingDescription")}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ) : dashboardStats ? (
              <>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <MetricCard
                    label={t("admin.totalRequests")}
                    value={dashboardStats.total_requests}
                    helper={t("admin.totalRequestsHelper")}
                    icon={Package}
                    locale={locale}
                    tone="bg-blue-50 text-blue-700"
                  />
                  <MetricCard
                    label={t("admin.last24h")}
                    value={dashboardStats.last_24h_count}
                    helper={t("admin.last24hHelper")}
                    icon={Clock}
                    locale={locale}
                    tone="bg-emerald-50 text-emerald-700"
                  />
                  <MetricCard
                    label={t("admin.last7Days")}
                    value={dashboardStats.last_7_days_count}
                    helper={t("admin.last7DaysHelper")}
                    icon={Gauge}
                    locale={locale}
                    tone="bg-violet-50 text-violet-700"
                  />
                  <MetricCard
                    label={t("status.unassigned")}
                    value={dashboardStats.unassigned_count}
                    helper={t("admin.unassignedHelper")}
                    icon={AlertCircle}
                    locale={locale}
                    tone="bg-orange-50 text-orange-700"
                  />
                </div>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                  {secondaryMetrics.map((metric) => {
                    const Icon = metric.icon;
                    return (
                      <Card key={metric.label} className="rounded-3xl border-slate-200 bg-white shadow-sm">
                        <CardContent className="flex items-center justify-between gap-4 p-5">
                          <div>
                            <p className="text-sm text-slate-500">{metric.label}</p>
                            <p className="mt-2 text-2xl font-bold text-slate-950">{formatNumber(metric.value, locale)}</p>
                          </div>
                          <div className={`flex h-11 w-11 items-center justify-center rounded-2xl ${metric.tone}`}>
                            <Icon className="h-5 w-5" />
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>

                <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                  <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                    <CardHeader className="space-y-1 p-5 pb-3">
                      <CardTitle className="flex items-center gap-2 text-base text-slate-950">
                        <BarChart3 className="h-5 w-5 text-blue-600" />
                        {t("admin.statusDistribution")}
                      </CardTitle>
                      <p className="text-sm text-slate-500">{t("admin.statusDistributionDescription")}</p>
                    </CardHeader>
                    <CardContent className="space-y-3 p-5 pt-2">
                      {Object.entries(dashboardStats.requests_per_status).map(([status, count], index) => {
                        const tone = distributionTones[index % distributionTones.length];
                        return (
                          <div key={status} className={`flex items-center justify-between gap-3 rounded-2xl border p-4 ${tone.row}`}>
                            <div className="flex min-w-0 items-center gap-3">
                              <span className={`h-3 w-3 shrink-0 rounded-full ${tone.dot}`} />
                              <span className="min-w-0 break-words text-sm font-medium text-slate-800">{status === "closed" ? t("status.closedOperational") : statusLabel(status)}</span>
                            </div>
                            <Badge variant="outline" className="shrink-0 rounded-full bg-white px-3 py-1">
                              {formatNumber(count, locale)}
                            </Badge>
                          </div>
                        );
                      })}
                    </CardContent>
                  </Card>

                  <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                    <CardHeader className="space-y-1 p-5 pb-3">
                      <CardTitle className="flex items-center gap-2 text-base text-slate-950">
                        <Truck className="h-5 w-5 text-blue-600" />
                        {t("admin.transportDistribution")}
                      </CardTitle>
                      <p className="text-sm text-slate-500">{t("admin.transportDistributionDescription")}</p>
                    </CardHeader>
                    <CardContent className="space-y-3 p-5 pt-2">
                      {Object.entries(dashboardStats.requests_per_transport_method).map(([method, count], index) => {
                        const tone = distributionTones[index % distributionTones.length];
                        return (
                          <div key={method} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-100 bg-slate-50 p-4">
                            <div className="flex min-w-0 items-center gap-3">
                              <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl ${tone.icon}`}>
                                <Truck className="h-5 w-5" />
                              </span>
                              <span className="min-w-0 break-words text-sm font-medium text-slate-800">
                                {transportLabel(method)}
                              </span>
                            </div>
                            <Badge variant="outline" className="shrink-0 rounded-full bg-white px-3 py-1">
                              {formatNumber(count, locale)}
                            </Badge>
                          </div>
                        );
                      })}
                    </CardContent>
                  </Card>
                </div>

                {dashboardStats.top_provinces.length > 0 && (
                  <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                    <CardHeader className="space-y-1 p-5 pb-3">
                      <CardTitle className="flex items-center gap-2 text-base text-slate-950">
                        <Trophy className="h-5 w-5 text-amber-500" />
                        {t("admin.topProvinces")}
                      </CardTitle>
                      <p className="text-sm text-slate-500">{t("admin.topProvincesDescription")}</p>
                    </CardHeader>
                    <CardContent className="p-5 pt-2">
                      <div className="grid gap-3">
                        {dashboardStats.top_provinces.map((province, index) => (
                          <div
                            key={`${province.province}-${index}`}
                            className="flex flex-col gap-3 rounded-2xl border border-slate-100 bg-slate-50 p-4 sm:flex-row sm:items-center sm:justify-between"
                          >
                            <div className="flex min-w-0 items-center gap-3">
                              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white">
                                {formatNumber(index + 1, locale)}
                              </span>
                              <span className="min-w-0 break-words font-medium text-slate-900">{province.province}</span>
                            </div>
                            <Badge variant="outline" className="w-fit rounded-full bg-white px-3 py-1">
                              {tf("admin.provinceRequestCount", { count: formatNumber(province.count, locale) })}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </>
            ) : (
              <EmptyDashboardState title={t("common.noDataTitle")} description={t("common.noDataDescription")} />
            )}
          </TabsContent>

          <TabsContent value="reports" className="space-y-4">
            <AdminReportsTab />
          </TabsContent>

          {isOrganizationAdmin && <TabsContent value="unassigned" className="space-y-4"><UnassignedRequestsTab /></TabsContent>}

          <TabsContent value="users" className="space-y-4">
            <UserManagement />
          </TabsContent>

          <TabsContent value="referral-rules" className="space-y-4">
            <ReferralRulesTab />
          </TabsContent>

          {isPlatformAdmin && <TabsContent value="site-settings" className="space-y-4">
            <SiteSettingsTab />
          </TabsContent>}
          {isPlatformAdmin && <TabsContent value="locations" className="space-y-4"><LocationsAdminTab /></TabsContent>}
          {isPlatformAdmin && <TabsContent value="tracking-locations" className="space-y-4"><TrackingLocationsAdminTab /></TabsContent>}
          {isPlatformAdmin && <TabsContent value="documents" className="space-y-4"><DocumentDefinitionsTab /></TabsContent>}
          {isOrganizationAdmin && <TabsContent value="organization-documents" className="space-y-4"><OrganizationDocumentPolicyTab /></TabsContent>}
          {isPlatformAdmin && <TabsContent value="master-data" className="space-y-4"><MasterDataAdminTab /></TabsContent>}
          <TabsContent value="cargo-catalog" className="space-y-4"><CargoCatalogAdminTab /></TabsContent>
          <TabsContent value="logistics-network" className="space-y-4"><LogisticsNetworkAdminTab isPlatformAdmin={isPlatformAdmin} /></TabsContent>
          <TabsContent value="operational-reasons" className="space-y-4"><OperationalReasonsAdminTab /></TabsContent>
        </Tabs>
        <footer className="rounded-2xl border border-slate-200 bg-white p-4"><ReleaseIdentity details /></footer>
      </div>
    </div>
  );
};

export default AdminPanel;
