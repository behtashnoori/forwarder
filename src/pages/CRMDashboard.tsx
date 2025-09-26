import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  Users, 
  TrendingUp, 
  Activity, 
  Plus,
  Search,
  Filter,
  Eye,
  Edit,
  Phone,
  Mail,
  Calendar,
  DollarSign,
  Target,
  BarChart3,
  RefreshCw,
  UserPlus,
  Briefcase,
  Clock
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { 
  fetchCRMDashboardKPIs,
  fetchCustomers,
  fetchOpportunities,
  fetchActivities,
  type CRMDashboardKPIs,
  type Customer,
  type Opportunity,
  type Activity as ActivityType
} from "@/lib/api";

const CRMDashboard = () => {
  const { toast } = useToast();
  const [kpis, setKpis] = useState<CRMDashboardKPIs | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [activities, setActivities] = useState<ActivityType[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("customers");
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [kpisData, customersData, opportunitiesData, activitiesData] = await Promise.all([
        fetchCRMDashboardKPIs(),
        fetchCustomers({ page: 1, per_page: 10 }),
        fetchOpportunities({ page: 1, per_page: 10 }),
        fetchActivities({ page: 1, per_page: 10 })
      ]);

      setKpis(kpisData);
      setCustomers(customersData.customers);
      setOpportunities(opportunitiesData.opportunities);
      setActivities(activitiesData.activities);
    } catch (error) {
      toast({
        title: "خطا",
        description: "خطا در بارگذاری داده‌های داشبورد",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const getCustomerTypeColor = (type: string) => {
    switch (type) {
      case "customer": return "bg-green-100 text-green-800";
      case "prospect": return "bg-blue-100 text-blue-800";
      case "partner": return "bg-purple-100 text-purple-800";
      case "vendor": return "bg-orange-100 text-orange-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  const getCustomerTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      customer: "مشتری",
      prospect: "پیشنهاد",
      partner: "شریک",
      vendor: "فروشنده"
    };
    return labels[type] || type;
  };

  const getOpportunityStageColor = (stage: string) => {
    switch (stage) {
      case "lead": return "bg-blue-100 text-blue-800";
      case "qualified": return "bg-yellow-100 text-yellow-800";
      case "proposal": return "bg-purple-100 text-purple-800";
      case "negotiation": return "bg-orange-100 text-orange-800";
      case "closed_won": return "bg-green-100 text-green-800";
      case "closed_lost": return "bg-red-100 text-red-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  const getOpportunityStageLabel = (stage: string) => {
    const labels: Record<string, string> = {
      lead: "سرنخ",
      qualified: "تایید شده",
      proposal: "پیشنهاد",
      negotiation: "مذاکره",
      closed_won: "برنده",
      closed_lost: "باخته"
    };
    return labels[stage] || stage;
  };

  const getActivityTypeColor = (type: string) => {
    switch (type) {
      case "call": return "bg-blue-100 text-blue-800";
      case "email": return "bg-green-100 text-green-800";
      case "meeting": return "bg-purple-100 text-purple-800";
      case "task": return "bg-orange-100 text-orange-800";
      case "note": return "bg-gray-100 text-gray-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  const getActivityTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      call: "تماس",
      email: "ایمیل",
      meeting: "جلسه",
      task: "وظیفه",
      note: "یادداشت"
    };
    return labels[type] || type;
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('fa-IR').format(value) + " ریال";
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">داشبورد CRM</h1>
            <p className="text-gray-600 mt-1">مدیریت مشتریان، فروش و فعالیت‌ها</p>
          </div>
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="sm"
              onClick={loadDashboardData}
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 ml-2 ${loading ? "animate-spin" : ""}`} />
              به‌روزرسانی
            </Button>
            <Button size="sm">
              <UserPlus className="w-4 h-4 ml-2" />
              مشتری جدید
            </Button>
          </div>
        </div>

        {/* KPI Cards */}
        {kpis && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">کل مشتریان</p>
                    <p className="text-3xl font-bold text-blue-600">{kpis.customers.total}</p>
                    <p className="text-xs text-green-600 mt-1">
                      +{kpis.customers.new_this_month} این ماه
                    </p>
                  </div>
                  <div className="p-3 bg-blue-100 rounded-lg">
                    <Users className="w-8 h-8 text-blue-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">فرصت‌های باز</p>
                    <p className="text-3xl font-bold text-purple-600">{kpis.opportunities.open}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {kpis.opportunities.won} برنده شده
                    </p>
                  </div>
                  <div className="p-3 bg-purple-100 rounded-lg">
                    <Target className="w-8 h-8 text-purple-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">ارزش پipeline</p>
                    <p className="text-3xl font-bold text-green-600">
                      {formatCurrency(kpis.opportunities.pipeline_value)}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {kpis.opportunities.total} فرصت کل
                    </p>
                  </div>
                  <div className="p-3 bg-green-100 rounded-lg">
                    <DollarSign className="w-8 h-8 text-green-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">فعالیت‌های تکمیل شده</p>
                    <p className="text-3xl font-bold text-orange-600">{kpis.activities.completed}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      از {kpis.activities.total} کل
                    </p>
                  </div>
                  <div className="p-3 bg-orange-100 rounded-lg">
                    <Activity className="w-8 h-8 text-orange-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Recent Activities Summary */}
        {kpis?.recent_activities && kpis.recent_activities.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-5 h-5" />
                فعالیت‌های اخیر
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {kpis.recent_activities.map((activity) => (
                  <div key={activity.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-blue-100 rounded-lg">
                        <Activity className="w-4 h-4 text-blue-600" />
                      </div>
                      <div>
                        <p className="font-medium">{activity.subject}</p>
                        <p className="text-sm text-gray-600">
                          {activity.customer_name} • {activity.expert_name}
                        </p>
                      </div>
                    </div>
                    <div className="text-sm text-gray-500">
                      {new Date(activity.created_at).toLocaleDateString("fa-IR")}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Main Content Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="customers">
              <Users className="w-4 h-4 ml-2" />
              مشتریان
            </TabsTrigger>
            <TabsTrigger value="opportunities">
              <Target className="w-4 h-4 ml-2" />
              فرصت‌های فروش
            </TabsTrigger>
            <TabsTrigger value="activities">
              <Activity className="w-4 h-4 ml-2" />
              فعالیت‌ها
            </TabsTrigger>
          </TabsList>

          <TabsContent value="customers" className="space-y-4">
            {/* Customers Filters */}
            <Card>
              <CardContent className="p-4">
                <div className="flex flex-col md:flex-row gap-4">
                  <div className="flex-1">
                    <div className="relative">
                      <Search className="absolute right-3 top-3 w-4 h-4 text-gray-400" />
                      <Input
                        placeholder="جستجو در مشتریان..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="pr-10"
                      />
                    </div>
                  </div>
                  <Select>
                    <SelectTrigger className="w-full md:w-48">
                      <SelectValue placeholder="نوع مشتری" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">همه انواع</SelectItem>
                      <SelectItem value="customer">مشتری</SelectItem>
                      <SelectItem value="prospect">پیشنهاد</SelectItem>
                      <SelectItem value="partner">شریک</SelectItem>
                      <SelectItem value="vendor">فروشنده</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            {/* Customers List */}
            {loading ? (
              <div className="flex justify-center py-8">
                <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
              </div>
            ) : customers.length === 0 ? (
              <Card>
                <CardContent className="p-8 text-center">
                  <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">مشتری یافت نشد</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {customers.map((customer) => (
                  <Card key={customer.id}>
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 space-y-3">
                          <div className="flex items-center gap-3">
                            <h3 className="font-semibold text-lg">{customer.name}</h3>
                            <Badge className={getCustomerTypeColor(customer.customer_type)}>
                              {getCustomerTypeLabel(customer.customer_type)}
                            </Badge>
                            {customer.company_name && (
                              <span className="text-sm text-gray-600">{customer.company_name}</span>
                            )}
                          </div>
                          
                          <div className="flex items-center gap-4 text-sm text-gray-600">
                            {customer.email && (
                              <div className="flex items-center gap-1">
                                <Mail className="w-4 h-4" />
                                {customer.email}
                              </div>
                            )}
                            {customer.phone && (
                              <div className="flex items-center gap-1">
                                <Phone className="w-4 h-4" />
                                {customer.phone}
                              </div>
                            )}
                            {customer.industry && (
                              <div className="flex items-center gap-1">
                                <Briefcase className="w-4 h-4" />
                                {customer.industry}
                              </div>
                            )}
                          </div>

                          <div className="flex items-center gap-4 text-xs text-gray-500">
                            <span>
                              {customer.total_opportunities} فرصت فروش
                            </span>
                            <span>•</span>
                            <span>
                              {customer.total_activities} فعالیت
                            </span>
                            {customer.last_contact_at && (
                              <>
                                <span>•</span>
                                <span>
                                  آخرین تماس: {new Date(customer.last_contact_at).toLocaleDateString("fa-IR")}
                                </span>
                              </>
                            )}
                          </div>
                        </div>

                        <div className="flex gap-2">
                          <Button size="sm" variant="outline">
                            <Eye className="w-4 h-4 ml-2" />
                            مشاهده
                          </Button>
                          <Button size="sm" variant="outline">
                            <Edit className="w-4 h-4 ml-2" />
                            ویرایش
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="opportunities" className="space-y-4">
            {/* Opportunities List */}
            {loading ? (
              <div className="flex justify-center py-8">
                <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
              </div>
            ) : opportunities.length === 0 ? (
              <Card>
                <CardContent className="p-8 text-center">
                  <Target className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">فرصت فروش یافت نشد</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {opportunities.map((opportunity) => (
                  <Card key={opportunity.id}>
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 space-y-3">
                          <div className="flex items-center gap-3">
                            <h3 className="font-semibold text-lg">{opportunity.title}</h3>
                            <Badge className={getOpportunityStageColor(opportunity.stage)}>
                              {getOpportunityStageLabel(opportunity.stage)}
                            </Badge>
                            {opportunity.value && (
                              <span className="text-sm font-medium text-green-600">
                                {formatCurrency(opportunity.value)}
                              </span>
                            )}
                          </div>
                          
                          {opportunity.customer && (
                            <div className="text-sm text-gray-600">
                              <span className="font-medium">مشتری:</span> {opportunity.customer.name}
                              {opportunity.customer.company_name && (
                                <span> ({opportunity.customer.company_name})</span>
                              )}
                            </div>
                          )}

                          <div className="flex items-center gap-4 text-sm text-gray-500">
                            <span>
                              احتمال: {opportunity.probability}%
                            </span>
                            {opportunity.expected_close_date && (
                              <>
                                <span>•</span>
                                <span>
                                  تاریخ بسته شدن: {new Date(opportunity.expected_close_date).toLocaleDateString("fa-IR")}
                                </span>
                              </>
                            )}
                            {opportunity.assigned_to && (
                              <>
                                <span>•</span>
                                <span>
                                  مسئول: {opportunity.assigned_to.name}
                                </span>
                              </>
                            )}
                          </div>
                        </div>

                        <div className="flex gap-2">
                          <Button size="sm" variant="outline">
                            <Eye className="w-4 h-4 ml-2" />
                            مشاهده
                          </Button>
                          <Button size="sm" variant="outline">
                            <Edit className="w-4 h-4 ml-2" />
                            ویرایش
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="activities" className="space-y-4">
            {/* Activities List */}
            {loading ? (
              <div className="flex justify-center py-8">
                <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
              </div>
            ) : activities.length === 0 ? (
              <Card>
                <CardContent className="p-8 text-center">
                  <Activity className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">فعالیت یافت نشد</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {activities.map((activity) => (
                  <Card key={activity.id}>
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 space-y-3">
                          <div className="flex items-center gap-3">
                            <h3 className="font-semibold text-lg">{activity.subject}</h3>
                            <Badge className={getActivityTypeColor(activity.type)}>
                              {getActivityTypeLabel(activity.type)}
                            </Badge>
                            <Badge variant="outline">
                              {activity.priority}
                            </Badge>
                          </div>
                          
                          {activity.description && (
                            <p className="text-sm text-gray-600">{activity.description}</p>
                          )}

                          <div className="flex items-center gap-4 text-sm text-gray-500">
                            {activity.customer && (
                              <span>
                                مشتری: {activity.customer.name}
                              </span>
                            )}
                            {activity.expert && (
                              <>
                                <span>•</span>
                                <span>
                                  کارشناس: {activity.expert.name}
                                </span>
                              </>
                            )}
                            {activity.due_date && (
                              <>
                                <span>•</span>
                                <span>
                                  موعد: {new Date(activity.due_date).toLocaleDateString("fa-IR")}
                                </span>
                              </>
                            )}
                          </div>
                        </div>

                        <div className="flex gap-2">
                          <Button size="sm" variant="outline">
                            <Eye className="w-4 h-4 ml-2" />
                            مشاهده
                          </Button>
                          <Button size="sm" variant="outline">
                            <Edit className="w-4 h-4 ml-2" />
                            ویرایش
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default CRMDashboard;
