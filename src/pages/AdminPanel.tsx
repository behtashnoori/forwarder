import { type ElementType, useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertCircle,
  BarChart3,
  Clock,
  Package,
  RefreshCw,
  Scale,
  Settings,
  TrendingUp,
  Users,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { AdminDashboardHttpError, fetchAdminDashboard, type AdminDashboardStats } from "@/lib/api";
import UserManagement from "./UserManagement";
import ReferralRulesTab from "@/components/ReferralRulesTab";
import SiteSettingsTab from "@/components/SiteSettingsTab";
import PageNav from "@/components/PageNav";

type MetricCardProps = {
  label: string;
  value: number;
  helper: string;
  icon: ElementType;
  tone: string;
};

const MetricCard = ({ label, value, helper, icon: Icon, tone }: MetricCardProps) => (
  <Card className="overflow-hidden border-border/70 bg-card/95 shadow-sm">
    <CardContent className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="mt-2 text-3xl font-bold tracking-normal text-foreground">{value}</p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">{helper}</p>
        </div>
        <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${tone}`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </CardContent>
  </Card>
);

const EmptyDashboardState = () => (
  <Card className="border-border/70 bg-card/95 shadow-sm">
    <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
      <div className="rounded-full bg-muted p-4">
        <BarChart3 className="h-8 w-8 text-muted-foreground" />
      </div>
      <div className="space-y-1">
        <h2 className="text-lg font-semibold text-foreground">داده‌ای یافت نشد</h2>
        <p className="text-sm leading-6 text-muted-foreground">
          پس از ثبت درخواست‌ها، آمار مدیریتی در این بخش نمایش داده می‌شود.
        </p>
      </div>
    </CardContent>
  </Card>
);

const AdminPanel = () => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [dashboardStats, setDashboardStats] = useState<AdminDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("dashboard");

  const loadDashboard = useCallback(async () => {
    const token = localStorage.getItem("expert_token");
    if (!token || token === "null") {
      toast({
        title: "ورود مجدد",
        description: "لطفاً دوباره وارد شوید",
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
          title: "نشست منقضی شده",
          description: "لطفاً دوباره وارد شوید",
          variant: "destructive",
        });
        localStorage.removeItem("expert_user");
        localStorage.removeItem("expert_token");
        navigate("/", { replace: true });
      } else if (error instanceof AdminDashboardHttpError) {
        toast({
          title: "خطا",
          description: "خطا در دریافت آمار داشبورد",
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
  }, [navigate, toast]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      new: "جدید",
      pending: "در انتظار",
      assigned: "ارجاع شده",
      in_progress: "در حال انجام",
      won: "پذیرش مشتری",
      lost: "عدم پذیرش مشتری",
      cancelled: "لغو شده",
      waiting_for_customer: "در انتظار مشتری",
    };
    return labels[status] || status;
  };

  const getTransportMethodLabel = (method: string) => {
    const labels: Record<string, string> = {
      road: "جاده‌ای",
      rail: "ریلی",
      air: "هوایی",
      sea: "دریایی",
      unknown: "نامشخص",
    };
    return labels[method] || method;
  };

  return (
    <div className="min-h-screen bg-gradient-background">
      <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
        <section className="overflow-hidden rounded-2xl border border-border/70 bg-card/95 shadow-sm">
          <div className="flex flex-col gap-5 p-5 sm:p-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-center">
              <PageNav backTo="/" showLogout />
              <div className="min-w-0">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className="bg-background/70">
                    پنل مدیریت
                  </Badge>
                  <Badge variant="secondary" className="gap-1">
                    <BarChart3 className="h-3.5 w-3.5" />
                    داشبورد عملیاتی
                  </Badge>
                </div>
                <h1 className="break-words text-2xl font-bold tracking-normal text-foreground sm:text-3xl">
                  پنل مدیریت
                </h1>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                  نمای مدیریتی برای پایش درخواست‌ها، وضعیت ارجاع و توزیع روش‌های حمل.
                </p>
              </div>
            </div>
            <Button onClick={loadDashboard} disabled={loading} variant="outline" size="sm" className="w-fit">
              <RefreshCw className={`ml-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              به‌روزرسانی
            </Button>
          </div>
        </section>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid h-auto w-full grid-cols-2 gap-2 rounded-2xl border border-border/70 bg-card/80 p-2 shadow-sm lg:grid-cols-4">
            <TabsTrigger value="dashboard" className="gap-2">
              <BarChart3 className="h-4 w-4" />
              داشبورد
            </TabsTrigger>
            <TabsTrigger value="users" className="gap-2">
              <Users className="h-4 w-4" />
              مدیریت کاربران
            </TabsTrigger>
            <TabsTrigger value="referral-rules" className="gap-2">
              <Scale className="h-4 w-4" />
              قوانین ارجاع
            </TabsTrigger>
            <TabsTrigger value="site-settings" className="gap-2">
              <Settings className="h-4 w-4" />
              تنظیمات سایت
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            {loading ? (
              <Card className="border-border/70 bg-card/95 shadow-sm">
                <CardContent className="flex min-h-[260px] flex-col items-center justify-center gap-4 p-8 text-center">
                  <div className="rounded-full bg-primary/10 p-4">
                    <RefreshCw className="h-8 w-8 animate-spin text-primary" />
                  </div>
                  <div className="space-y-1">
                    <h2 className="text-lg font-semibold text-foreground">در حال بارگذاری داشبورد</h2>
                    <p className="text-sm leading-6 text-muted-foreground">
                      آمار درخواست‌ها و توزیع وضعیت‌ها دریافت می‌شود.
                    </p>
                  </div>
                </CardContent>
              </Card>
            ) : dashboardStats ? (
              <>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <MetricCard
                    label="کل درخواست‌ها"
                    value={dashboardStats.total_requests}
                    helper="تمام درخواست‌های ثبت شده"
                    icon={Package}
                    tone="bg-blue-100 text-blue-700"
                  />
                  <MetricCard
                    label="۲۴ ساعت اخیر"
                    value={dashboardStats.last_24h_count}
                    helper="درخواست‌های جدید امروز"
                    icon={Clock}
                    tone="bg-green-100 text-green-700"
                  />
                  <MetricCard
                    label="۷ روز اخیر"
                    value={dashboardStats.last_7_days_count}
                    helper="روند کوتاه‌مدت درخواست‌ها"
                    icon={TrendingUp}
                    tone="bg-purple-100 text-purple-700"
                  />
                  <MetricCard
                    label="ارجاع نشده"
                    value={dashboardStats.unassigned_count}
                    helper="نیازمند بررسی یا ارجاع"
                    icon={AlertCircle}
                    tone="bg-orange-100 text-orange-700"
                  />
                </div>

                <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                  <Card className="border-border/70 bg-card/95 shadow-sm">
                    <CardHeader className="space-y-1">
                      <CardTitle className="flex items-center gap-2 text-base">
                        <BarChart3 className="h-5 w-5 text-primary" />
                        توزیع بر اساس وضعیت
                      </CardTitle>
                      <p className="text-sm text-muted-foreground">نمای فشرده از وضعیت فعلی درخواست‌ها.</p>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        {Object.entries(dashboardStats.requests_per_status).map(([status, count]) => (
                          <div key={status} className="rounded-xl border border-border/70 bg-background/70 p-4">
                            <div className="flex items-center justify-between gap-3">
                              <p className="min-w-0 break-words text-sm text-muted-foreground">{getStatusLabel(status)}</p>
                              <Badge variant="outline" className="shrink-0">
                                {count}
                              </Badge>
                            </div>
                            <p className="mt-2 text-2xl font-bold text-foreground">{count}</p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  <Card className="border-border/70 bg-card/95 shadow-sm">
                    <CardHeader className="space-y-1">
                      <CardTitle className="flex items-center gap-2 text-base">
                        <Package className="h-5 w-5 text-primary" />
                        توزیع بر اساس روش حمل
                      </CardTitle>
                      <p className="text-sm text-muted-foreground">روش‌های حمل انتخاب شده در درخواست‌ها.</p>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        {Object.entries(dashboardStats.requests_per_transport_method).map(([method, count]) => (
                          <div key={method} className="rounded-xl border border-border/70 bg-background/70 p-4">
                            <div className="flex items-center justify-between gap-3">
                              <p className="min-w-0 break-words text-sm text-muted-foreground">
                                {getTransportMethodLabel(method)}
                              </p>
                              <Badge variant="outline" className="shrink-0">
                                {count}
                              </Badge>
                            </div>
                            <p className="mt-2 text-2xl font-bold text-foreground">{count}</p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {dashboardStats.top_provinces.length > 0 && (
                  <Card className="border-border/70 bg-card/95 shadow-sm">
                    <CardHeader className="space-y-1">
                      <CardTitle className="flex items-center gap-2 text-base">
                        <TrendingUp className="h-5 w-5 text-primary" />
                        استان‌های برتر
                      </CardTitle>
                      <p className="text-sm text-muted-foreground">استان‌هایی با بیشترین تعداد درخواست ثبت شده.</p>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {dashboardStats.top_provinces.map((province, index) => (
                          <div
                            key={index}
                            className="flex flex-col gap-3 rounded-xl border border-border/70 bg-background/70 p-4 sm:flex-row sm:items-center sm:justify-between"
                          >
                            <div className="flex min-w-0 items-center gap-3">
                              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">
                                {index + 1}
                              </span>
                              <span className="min-w-0 break-words font-medium text-foreground">{province.province}</span>
                            </div>
                            <Badge variant="outline" className="w-fit">
                              {province.count} درخواست
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </>
            ) : (
              <EmptyDashboardState />
            )}
          </TabsContent>

          <TabsContent value="users" className="space-y-4">
            <UserManagement />
          </TabsContent>

          <TabsContent value="referral-rules" className="space-y-4">
            <ReferralRulesTab />
          </TabsContent>
          <TabsContent value="site-settings" className="space-y-4">
            <SiteSettingsTab />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default AdminPanel;
