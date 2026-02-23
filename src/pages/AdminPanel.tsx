import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { RefreshCw, BarChart3, Users, Package, Clock, AlertCircle, TrendingUp, Scale, Settings } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { env } from "@/lib/env";
import UserManagement from "./UserManagement";
import ReferralRulesTab from "@/components/ReferralRulesTab";
import SiteSettingsTab from "@/components/SiteSettingsTab";
import PageNav from "@/components/PageNav";

interface DashboardStats {
  total_requests: number;
  requests_per_transport_method: Record<string, number>;
  requests_per_status: Record<string, number>;
  last_7_days_count: number;
  last_24h_count: number;
  unassigned_count: number;
  top_provinces: Array<{ province: string; count: number }>;
}

const AdminPanel = () => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("dashboard");

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    const token = localStorage.getItem('expert_token');
    if (!token || token === 'null') {
      toast({
        title: "ورود مجدد",
        description: "لطفاً دوباره وارد شوید",
        variant: "destructive"
      });
      localStorage.removeItem('expert_user');
      localStorage.removeItem('expert_token');
      navigate('/', { replace: true });
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`${env.API_URL}/api/admin/dashboard`, {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setDashboardStats(data);
      } else if (response.status === 401) {
        toast({
          title: "نشست منقضی شده",
          description: "لطفاً دوباره وارد شوید",
          variant: "destructive"
        });
        localStorage.removeItem('expert_user');
        localStorage.removeItem('expert_token');
        navigate('/', { replace: true });
      } else {
        toast({
          title: "خطا",
          description: "خطا در دریافت آمار داشبورد",
          variant: "destructive"
        });
      }
    } catch (error) {
      toast({
        title: "خطا",
        description: "خطا در ارتباط با سرور",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      new: "جدید",
      pending: "در انتظار",
      assigned: "ارجاع شده",
      in_progress: "در حال انجام",
      won: "پذیرش مشتری",
      lost: "عدم پذیرش مشتری",
      cancelled: "لغو شده",
      waiting_for_customer: "در انتظار مشتری"
    };
    return labels[status] || status;
  };

  const getTransportMethodLabel = (method: string) => {
    const labels: Record<string, string> = {
      road: "جاده‌ای",
      rail: "ریلی",
      air: "هوایی",
      sea: "دریایی",
      unknown: "نامشخص"
    };
    return labels[method] || method;
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4 flex-wrap">
            <PageNav backTo="/" showLogout />
            <div>
              <h1 className="text-3xl font-bold text-gray-900">پنل مدیریت</h1>
              <p className="text-gray-600 mt-1">داشبورد و مدیریت کاربران</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={loadDashboard}
              disabled={loading}
              className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Main Content Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="dashboard">
              <BarChart3 className="w-4 h-4 ml-2" />
              داشبورد
            </TabsTrigger>
            <TabsTrigger value="users">
              <Users className="w-4 h-4 ml-2" />
              مدیریت کاربران
            </TabsTrigger>
            <TabsTrigger value="referral-rules">
              <Scale className="w-4 h-4 ml-2" />
              قوانین ارجاع
            </TabsTrigger>
            <TabsTrigger value="site-settings">
              <Settings className="w-4 h-4 ml-2" />
              تنظیمات سایت
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            {loading ? (
              <div className="flex justify-center py-12">
                <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
              </div>
            ) : dashboardStats ? (
              <>
                {/* Statistics Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                  <Card>
                    <CardContent className="p-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm text-gray-600">کل درخواست‌ها</p>
                          <p className="text-3xl font-bold text-blue-600">{dashboardStats.total_requests}</p>
                        </div>
                        <div className="p-3 bg-blue-100 rounded-lg">
                          <Package className="w-8 h-8 text-blue-600" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardContent className="p-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm text-gray-600">۲۴ ساعت اخیر</p>
                          <p className="text-3xl font-bold text-green-600">{dashboardStats.last_24h_count}</p>
                        </div>
                        <div className="p-3 bg-green-100 rounded-lg">
                          <Clock className="w-8 h-8 text-green-600" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardContent className="p-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm text-gray-600">۷ روز اخیر</p>
                          <p className="text-3xl font-bold text-purple-600">{dashboardStats.last_7_days_count}</p>
                        </div>
                        <div className="p-3 bg-purple-100 rounded-lg">
                          <TrendingUp className="w-8 h-8 text-purple-600" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardContent className="p-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm text-gray-600">ارجاع نشده</p>
                          <p className="text-3xl font-bold text-orange-600">{dashboardStats.unassigned_count}</p>
                        </div>
                        <div className="p-3 bg-orange-100 rounded-lg">
                          <AlertCircle className="w-8 h-8 text-orange-600" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Status Distribution */}
                <Card>
                  <CardHeader>
                    <CardTitle>توزیع بر اساس وضعیت</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {Object.entries(dashboardStats.requests_per_status).map(([status, count]) => (
                        <div key={status} className="p-4 bg-gray-50 rounded-lg">
                          <p className="text-sm text-gray-600">{getStatusLabel(status)}</p>
                          <p className="text-2xl font-bold">{count}</p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Transport Method Distribution */}
                <Card>
                  <CardHeader>
                    <CardTitle>توزیع بر اساس روش حمل</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {Object.entries(dashboardStats.requests_per_transport_method).map(([method, count]) => (
                        <div key={method} className="p-4 bg-gray-50 rounded-lg">
                          <p className="text-sm text-gray-600">{getTransportMethodLabel(method)}</p>
                          <p className="text-2xl font-bold">{count}</p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Top Provinces */}
                {dashboardStats.top_provinces.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle>استان‌های برتر</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {dashboardStats.top_provinces.map((province, index) => (
                          <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <span className="font-medium">{province.province}</span>
                            <span className="text-lg font-bold">{province.count}</span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </>
            ) : (
              <Card>
                <CardContent className="p-8 text-center">
                  <p className="text-gray-600">داده‌ای یافت نشد</p>
                </CardContent>
              </Card>
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
