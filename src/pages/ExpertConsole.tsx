import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertCircle,
  BarChart3,
  CalendarDays,
  CheckCircle,
  Clock,
  Eye,
  Filter,
  MapPin,
  MessageSquare,
  Package,
  Plus,
  RefreshCw,
  Search,
  Truck,
  User,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import PageNav from "@/components/PageNav";
import { useToast } from "@/hooks/use-toast";
import {
  assignRequest,
  changeRequestStatus,
  fetchExpertRequests,
  fetchExperts,
  fetchKPIs,
  type ExpertRequest,
  type ExpertUser,
  type KPIs,
} from "@/lib/api";

type ShipmentRequest = ExpertRequest & {
  international_transport_method?: string;
  domestic_transport_method?: string;
  transport_method_preference?: string;
};
type KPI = KPIs;

const expertId = 1;

const statusItems = [
  { value: "all", label: "همه" },
  { value: "new", label: "جدید" },
  { value: "assigned", label: "ارجاع شده" },
  { value: "in_progress", label: "در حال بررسی" },
  { value: "waiting_for_customer", label: "منتظر مشتری" },
  { value: "closed", label: "تکمیل شده" },
];

const statusFilterItems = [
  { value: "all", label: "همه وضعیت‌ها" },
  { value: "new", label: "جدید" },
  { value: "assigned", label: "ارجاع شده" },
  { value: "in_progress", label: "در حال بررسی" },
  { value: "quoted", label: "پیشنهاد ارسال شده" },
  { value: "waiting_for_customer", label: "منتظر مشتری" },
  { value: "won", label: "پذیرش مشتری" },
  { value: "lost", label: "عدم پذیرش مشتری" },
  { value: "closed", label: "مختومه" },
];

const priorityItems = [
  { value: "all", label: "همه اولویت‌ها" },
  { value: "urgent", label: "فوری" },
  { value: "high", label: "بالا" },
  { value: "normal", label: "عادی" },
  { value: "low", label: "پایین" },
];

const slaFilterItems = [
  { value: "all", label: "همه مهلت‌ها" },
  { value: "due_soon", label: "نزدیک به مهلت" },
  { value: "overdue", label: "گذشته از مهلت" },
] as const;

type SlaFilter = (typeof slaFilterItems)[number]["value"];

const ExpertConsole = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [requests, setRequests] = useState<ShipmentRequest[]>([]);
  const [kpis, setKpis] = useState<KPI | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("new");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [slaFilter, setSlaFilter] = useState<SlaFilter>("all");
  const [currentExpert, setCurrentExpert] = useState<ExpertUser | null>(null);

  const loadRequests = useCallback(async () => {
    try {
      setLoading(true);

      const params: NonNullable<Parameters<typeof fetchExpertRequests>[0]> = {
        page: 1,
        per_page: 50,
        sort_by: "created_at",
        sort_order: "desc",
      };

      if (activeTab !== "all" && activeTab !== "closed") {
        params.status = activeTab;
      } else if (activeTab === "closed") {
        params.status = "won,lost,closed";
      }

      if (searchTerm) {
        params.search = searchTerm;
      }
      if (priorityFilter && priorityFilter !== "all") {
        params.priority = priorityFilter;
      }
      if (statusFilter && statusFilter !== "all" && activeTab === "all") {
        params.status = statusFilter;
      }

      const data = await fetchExpertRequests(params);
      setRequests(data.requests || []);
    } catch (error) {
      toast({
        title: "خطا",
        description: "خطا در دریافت درخواست‌ها",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [activeTab, priorityFilter, searchTerm, statusFilter, toast]);

  const loadKPIs = useCallback(async () => {
    try {
      const data = await fetchKPIs(expertId);
      setKpis(data);
    } catch (error) {
      console.error("Error loading KPIs:", error);
    }
  }, []);

  const loadCurrentExpert = useCallback(async () => {
    try {
      const storedExpert = localStorage.getItem("expert_user");
      if (storedExpert) {
        const expert = JSON.parse(storedExpert);
        setCurrentExpert(expert);
        return;
      }

      const expertsResponse = await fetchExperts();
      const experts = Array.isArray(expertsResponse) ? expertsResponse : expertsResponse.experts;
      const expert = experts.find((item) => item.id === expertId) || experts[0];
      setCurrentExpert(expert);
    } catch (error) {
      console.error("Error loading current expert:", error);
    }
  }, []);

  useEffect(() => {
    loadRequests();
    loadKPIs();
    loadCurrentExpert();
  }, [loadCurrentExpert, loadKPIs, loadRequests]);

  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        loadRequests();
        loadKPIs();
      }
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => document.removeEventListener("visibilitychange", onVisibilityChange);
  }, [loadKPIs, loadRequests]);

  const handleAssignToMe = async (requestId: number) => {
    try {
      await assignRequest(requestId, expertId);

      toast({
        title: "موفق",
        description: "درخواست به شما ارجاع داده شد",
      });

      loadRequests();
      loadKPIs();
    } catch (error) {
      toast({
        title: "خطا",
        description: "خطا در ارجاع درخواست",
        variant: "destructive",
      });
    }
  };

  const handleStatusChange = async (requestId: number, newStatus: string) => {
    try {
      await changeRequestStatus(requestId, newStatus, `تغییر وضعیت به ${newStatus}`);

      toast({
        title: "موفق",
        description: "وضعیت درخواست به‌روزرسانی شد",
      });

      loadKPIs();

      if (newStatus === "in_progress") {
        setActiveTab("in_progress");
      } else if (newStatus === "waiting_for_customer") {
        setActiveTab("waiting_for_customer");
      } else if (newStatus === "closed" || newStatus === "won" || newStatus === "lost") {
        setActiveTab("all");
      }
    } catch (error) {
      toast({
        title: "خطا",
        description: "خطا در تغییر وضعیت",
        variant: "destructive",
      });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "new":
        return "border-blue-200 bg-blue-50 text-blue-700";
      case "assigned":
        return "border-amber-200 bg-amber-50 text-amber-700";
      case "in_progress":
        return "border-violet-200 bg-violet-50 text-violet-700";
      case "quoted":
        return "border-indigo-200 bg-indigo-50 text-indigo-700";
      case "waiting_for_customer":
        return "border-orange-200 bg-orange-50 text-orange-700";
      case "won":
        return "border-emerald-200 bg-emerald-50 text-emerald-700";
      case "lost":
        return "border-rose-200 bg-rose-50 text-rose-700";
      case "closed":
        return "border-slate-200 bg-slate-100 text-slate-700";
      default:
        return "border-slate-200 bg-slate-100 text-slate-700";
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "urgent":
        return "border-red-200 bg-red-50 text-red-700";
      case "high":
        return "border-orange-200 bg-orange-50 text-orange-700";
      case "normal":
        return "border-blue-200 bg-blue-50 text-blue-700";
      case "low":
        return "border-slate-200 bg-slate-100 text-slate-700";
      default:
        return "border-slate-200 bg-slate-100 text-slate-700";
    }
  };

  const getSLAStatusColor = (slaStatus?: string | null) => {
    switch (slaStatus) {
      case "overdue":
        return "text-red-600";
      case "due_soon":
        return "text-amber-600";
      case "on_time":
        return "text-emerald-600";
      default:
        return "text-slate-500";
    }
  };

  const getSlaLabel = (slaStatus?: string | null, slaDueAt?: string | null) => {
    if (!slaDueAt) return "مهلت ثبت نشده";

    const labels: Record<string, string> = {
      overdue: "گذشته از مهلت",
      due_soon: "نزدیک به مهلت",
      on_time: "در محدوده مجاز",
    };

    return labels[slaStatus || "on_time"] || "در محدوده مجاز";
  };

  const getSlaBadgeClass = (slaStatus?: string | null, slaDueAt?: string | null) => {
    if (!slaDueAt) return "border-slate-200 bg-slate-50 text-slate-500";

    switch (slaStatus) {
      case "overdue":
        return "border-red-200 bg-red-50 text-red-700";
      case "due_soon":
        return "border-amber-200 bg-amber-50 text-amber-700";
      case "on_time":
        return "border-emerald-200 bg-emerald-50 text-emerald-700";
      default:
        return "border-emerald-200 bg-emerald-50 text-emerald-700";
    }
  };

  const formatRemainingSlaTime = (slaDueAt?: string | null) => {
    if (!slaDueAt) return null;

    const dueAt = new Date(slaDueAt);
    const dueAtTime = dueAt.getTime();

    if (Number.isNaN(dueAtTime)) return null;

    const remainingMinutes = Math.ceil((dueAtTime - Date.now()) / 60000);

    if (remainingMinutes <= 0) return "از مهلت گذشته";
    if (remainingMinutes < 60) return `زمان باقی‌مانده: ${remainingMinutes} دقیقه`;

    return `زمان باقی‌مانده: ${Math.ceil(remainingMinutes / 60)} ساعت`;
  };

  const formatSlaDueAt = (slaDueAt?: string | null) => {
    if (!slaDueAt) return "مهلت ثبت نشده";

    const dueAt = new Date(slaDueAt);
    if (Number.isNaN(dueAt.getTime())) return "مهلت نامعتبر";

    return dueAt.toLocaleString("fa-IR");
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      new: "جدید",
      assigned: "ارجاع شده",
      in_progress: "در حال بررسی",
      quoted: "پیشنهاد ارسال شده",
      waiting_for_customer: "منتظر مشتری",
      won: "پذیرش مشتری",
      lost: "عدم پذیرش مشتری",
      closed: "مختومه",
    };
    return labels[status] || status;
  };

  const getPriorityLabel = (priority: string) => {
    const labels: Record<string, string> = {
      urgent: "فوری",
      high: "بالا",
      normal: "عادی",
      low: "پایین",
    };
    return labels[priority] || priority;
  };

  const totalKpiCount = useMemo(() => {
    if (!kpis) return 0;
    return kpis.counts.new + kpis.counts.in_progress + kpis.counts.waiting_for_customer + kpis.counts.closed_today;
  }, [kpis]);

  const visibleRequests = useMemo(() => {
    if (slaFilter === "all") return requests;
    return requests.filter((request) => request.sla_status === slaFilter);
  }, [requests, slaFilter]);

  const clearFilters = () => {
    setSearchTerm("");
    setStatusFilter("");
    setPriorityFilter("");
    setSlaFilter("all");
  };

  const formatRoute = (request: ShipmentRequest) => {
    const origin = [request.route.origin.city, request.route.origin.county, request.route.origin.province].filter(Boolean).join("، ");
    const destination = [request.route.destination.city, request.route.destination.county, request.route.destination.province].filter(Boolean).join("، ");
    return {
      origin: origin || "مبدا نامشخص",
      destination: destination || "مقصد نامشخص",
    };
  };

  const formatTransport = (request: ShipmentRequest) => {
    if (request.international_transport_method) return `بین‌المللی: ${request.international_transport_method}`;
    if (request.domestic_transport_method) return `داخلی: ${request.domestic_transport_method}`;
    if (request.transport_method) return request.transport_method;
    return "روش حمل ثبت نشده";
  };

  const metricCards = kpis
    ? [
        {
          label: "درخواست‌های جدید",
          value: kpis.counts.new,
          icon: Plus,
          tone: "text-blue-700 bg-blue-50 border-blue-100",
        },
        {
          label: "در حال بررسی",
          value: kpis.counts.in_progress,
          icon: Clock,
          tone: "text-violet-700 bg-violet-50 border-violet-100",
        },
        {
          label: "منتظر مشتری",
          value: kpis.counts.waiting_for_customer,
          icon: MessageSquare,
          tone: "text-orange-700 bg-orange-50 border-orange-100",
        },
        {
          label: "مختومه امروز",
          value: kpis.counts.closed_today,
          icon: CheckCircle,
          tone: "text-emerald-700 bg-emerald-50 border-emerald-100",
        },
      ]
    : [];

  return (
    <div className="min-h-screen bg-slate-50" dir="rtl">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
        <section className="overflow-hidden rounded-3xl border border-blue-100 bg-white shadow-sm">
          <div className="flex flex-col gap-5 p-5 lg:flex-row lg:items-center lg:justify-between lg:p-7">
            <div className="flex min-w-0 flex-col gap-4">
              <PageNav backTo="/" showLogout className="flex-wrap" />
              <div className="flex items-start gap-4">
                <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-sm">
                  <BarChart3 className="h-7 w-7" />
                </div>
                <div className="min-w-0">
                  <h1 className="text-2xl font-bold text-slate-950 sm:text-3xl">کنسول کارشناس</h1>
                  <p className="mt-2 text-sm leading-6 text-slate-500 sm:text-base">مدیریت حرفه‌ای درخواست‌های حمل و نقل</p>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-3 sm:items-end">
              <div className="flex flex-wrap items-center gap-2">
                <div className="flex h-9 items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-4 text-sm font-medium text-blue-700">
                  <BarChart3 className="h-4 w-4" />
                  داشبورد درخواست‌ها
                </div>
                <Button variant="outline" size="sm" onClick={loadRequests} disabled={loading} className="rounded-full">
                  <RefreshCw className={`ml-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                  به‌روزرسانی
                </Button>
                <div className="flex h-9 items-center gap-2 rounded-full border border-slate-200 bg-white px-4 text-sm text-slate-700">
                  <User className="h-4 w-4 text-slate-500" />
                  {currentExpert ? currentExpert.full_name : "کارشناس"}
                </div>
              </div>
            </div>
          </div>
        </section>

        {kpis && (
          <section className="grid gap-4 lg:grid-cols-[1.25fr_0.75fr]">
            <Card className="rounded-3xl border-blue-100 bg-white shadow-sm">
              <CardContent className="p-5 sm:p-6">
                <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <p className="text-sm font-medium text-blue-700">خلاصه وضعیت درخواست‌ها</p>
                    <h2 className="mt-1 text-xl font-bold text-slate-950">نمای عملیاتی امروز</h2>
                  </div>
                  <div className="rounded-2xl bg-slate-50 px-4 py-3 text-right">
                    <p className="text-xs text-slate-500">کل درخواست‌های قابل مشاهده</p>
                    <p className="text-2xl font-bold text-slate-950">{totalKpiCount}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  {metricCards.map((metric) => {
                    const Icon = metric.icon;
                    return (
                      <div key={metric.label} className={`rounded-2xl border p-4 ${metric.tone}`}>
                        <div className="mb-4 flex items-center justify-between gap-3">
                          <span className="text-xs font-medium">{metric.label}</span>
                          <Icon className="h-5 w-5" />
                        </div>
                        <p className="text-2xl font-bold">{metric.value}</p>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
              <CardContent className="flex h-full flex-col justify-between gap-4 p-5 sm:p-6">
                <div>
                  <p className="text-sm font-medium text-slate-500">پایش SLA</p>
                  <h2 className="mt-1 text-xl font-bold text-slate-950">مهلت پاسخ‌گویی</h2>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-2xl border border-red-100 bg-red-50 p-4 text-red-700">
                    <AlertCircle className="mb-3 h-5 w-5" />
                    <p className="text-2xl font-bold">{kpis.sla.overdue}</p>
                    <p className="mt-1 text-xs">گذشته از مهلت</p>
                  </div>
                  <div className="rounded-2xl border border-amber-100 bg-amber-50 p-4 text-amber-700">
                    <Clock className="mb-3 h-5 w-5" />
                    <p className="text-2xl font-bold">{kpis.sla.due_soon}</p>
                    <p className="mt-1 text-xs">نزدیک به مهلت</p>
                  </div>
                </div>
                {kpis.sla.overdue === 0 && kpis.sla.due_soon === 0 && (
                  <div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm font-medium leading-6 text-emerald-700">
                    همه درخواست‌ها در محدوده مجاز پاسخ‌گویی هستند.
                  </div>
                )}
              </CardContent>
            </Card>
          </section>
        )}

        {(kpis?.sla.overdue || 0) > 0 && (
          <Card className="rounded-2xl border-red-200 bg-red-50 shadow-sm">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />
                <div>
                  <p className="font-medium text-red-800">{kpis?.sla.overdue} درخواست از مهلت SLA گذشته است</p>
                  <p className="mt-1 text-sm text-red-600">لطفاً درخواست‌های عقب‌افتاده را اولویت دهید.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
          <CardContent className="space-y-4 p-4 sm:p-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
              <Filter className="h-4 w-4 text-blue-600" />
              جستجو و فیلتر درخواست‌ها
            </div>
            <div className="grid gap-3 lg:grid-cols-[1fr_12rem_12rem_auto]">
              <div className="relative min-w-0">
                <Search className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  placeholder="جستجو در کد، مشتری یا مسیر..."
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  className="h-11 rounded-2xl border-slate-200 bg-slate-50 pr-10"
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="h-11 rounded-2xl border-slate-200 bg-slate-50">
                  <SelectValue placeholder="وضعیت" />
                </SelectTrigger>
                <SelectContent>
                  {statusFilterItems.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={priorityFilter} onValueChange={setPriorityFilter}>
                <SelectTrigger className="h-11 rounded-2xl border-slate-200 bg-slate-50">
                  <SelectValue placeholder="اولویت" />
                </SelectTrigger>
                <SelectContent>
                  {priorityItems.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button variant="outline" onClick={clearFilters} className="h-11 rounded-2xl">
                پاک کردن فیلترها
              </Button>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-slate-500">فیلتر SLA:</span>
              {slaFilterItems.map((item) => (
                <Button
                  key={item.value}
                  type="button"
                  variant={slaFilter === item.value ? "default" : "outline"}
                  size="sm"
                  onClick={() => setSlaFilter(item.value)}
                  className={`rounded-full ${
                    slaFilter === item.value ? "bg-blue-600 text-white hover:bg-blue-700" : "border-slate-200 bg-white text-slate-600"
                  }`}
                >
                  {item.label}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList className="flex h-auto w-full flex-wrap justify-start gap-2 rounded-3xl border border-slate-200 bg-white p-2 shadow-sm">
            {statusItems.map((item) => (
              <TabsTrigger
                key={item.value}
                value={item.value}
                className="rounded-2xl px-4 py-2 text-sm text-slate-600 data-[state=active]:bg-blue-600 data-[state=active]:text-white data-[state=active]:shadow-sm"
              >
                {item.label}
                {item.value === "new" && Boolean(kpis?.counts.new) && (
                  <Badge variant="secondary" className="mr-2 bg-white/20 text-current">
                    {kpis?.counts.new}
                  </Badge>
                )}
                {item.value === "in_progress" && Boolean(kpis?.counts.in_progress) && (
                  <Badge variant="secondary" className="mr-2 bg-white/20 text-current">
                    {kpis?.counts.in_progress}
                  </Badge>
                )}
                {item.value === "waiting_for_customer" && Boolean(kpis?.counts.waiting_for_customer) && (
                  <Badge variant="secondary" className="mr-2 bg-white/20 text-current">
                    {kpis?.counts.waiting_for_customer}
                  </Badge>
                )}
                {item.value === "closed" && Boolean(kpis?.counts.closed_today) && (
                  <Badge variant="secondary" className="mr-2 bg-white/20 text-current">
                    {kpis?.counts.closed_today}
                  </Badge>
                )}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value={activeTab} className="space-y-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-950">درخواست‌های حمل</h2>
                <p className="mt-1 text-sm text-slate-500">نمایش {visibleRequests.length} درخواست در فهرست فعلی</p>
              </div>
              <div className="rounded-full border border-slate-200 bg-white px-4 py-2 text-xs text-slate-500 shadow-sm">
                مرتب‌سازی: جدیدترین درخواست‌ها
              </div>
            </div>

            {loading ? (
              <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                <CardContent className="flex justify-center py-12">
                  <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
                </CardContent>
              </Card>
            ) : visibleRequests.length === 0 ? (
              <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                <CardContent className="p-10 text-center">
                  <Package className="mx-auto mb-4 h-12 w-12 text-slate-300" />
                  <p className="font-medium text-slate-700">درخواستی یافت نشد</p>
                  <p className="mt-1 text-sm text-slate-500">فیلترها را تغییر دهید یا فهرست را به‌روزرسانی کنید.</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {visibleRequests.map((request) => {
                  const route = formatRoute(request);
                  const remainingSlaTime = formatRemainingSlaTime(request.sla_due_at);
                  return (
                    <Card
                      key={request.id}
                      className={`rounded-3xl border bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${
                        request.has_unread ? "border-blue-200 ring-1 ring-blue-100" : "border-slate-200"
                      }`}
                    >
                      <CardContent className="p-4 sm:p-5">
                        <div className="grid gap-5 xl:grid-cols-[1fr_auto]">
                          <div className="min-w-0 space-y-4">
                            <div className="flex flex-wrap items-center gap-2">
                              <div className="rounded-2xl bg-slate-950 px-3 py-2 text-sm font-bold text-white">
                                {request.tracking_number}
                              </div>
                              <Badge variant="outline" className={`rounded-full px-3 py-1 ${getStatusColor(request.status)}`}>
                                {getStatusLabel(request.status)}
                              </Badge>
                              <Badge variant="outline" className={`rounded-full px-3 py-1 ${getPriorityColor(request.priority)}`}>
                                اولویت {getPriorityLabel(request.priority)}
                              </Badge>
                              {request.has_unread && <Badge className="rounded-full bg-blue-600 text-white">خوانده نشده</Badge>}
                              <Badge
                                variant="outline"
                                className={`rounded-full px-3 py-1 ${getSlaBadgeClass(request.sla_status, request.sla_due_at)}`}
                              >
                                {getSlaLabel(request.sla_status, request.sla_due_at)}
                              </Badge>
                            </div>

                            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                              <div className="rounded-2xl bg-slate-50 p-3">
                                <div className="mb-2 flex items-center gap-2 text-xs text-slate-500">
                                  <User className="h-4 w-4" />
                                  مشتری
                                </div>
                                <p className="truncate text-sm font-semibold text-slate-900">{request.customer.name}</p>
                                <p className="mt-1 text-xs text-slate-500" dir="ltr">
                                  {request.customer.phone}
                                </p>
                              </div>

                              <div className="rounded-2xl bg-slate-50 p-3">
                                <div className="mb-2 flex items-center gap-2 text-xs text-slate-500">
                                  <MapPin className="h-4 w-4" />
                                  مبدا
                                </div>
                                <p className="line-clamp-2 text-sm font-semibold text-slate-900">{route.origin}</p>
                              </div>

                              <div className="rounded-2xl bg-slate-50 p-3">
                                <div className="mb-2 flex items-center gap-2 text-xs text-slate-500">
                                  <MapPin className="h-4 w-4" />
                                  مقصد
                                </div>
                                <p className="line-clamp-2 text-sm font-semibold text-slate-900">{route.destination}</p>
                              </div>

                              <div className="rounded-2xl bg-slate-50 p-3">
                                <div className="mb-2 flex items-center gap-2 text-xs text-slate-500">
                                  <Truck className="h-4 w-4" />
                                  روش حمل
                                </div>
                                <p className="line-clamp-2 text-sm font-semibold text-slate-900">{formatTransport(request)}</p>
                              </div>
                            </div>

                            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-500">
                              <span className="flex items-center gap-1">
                                <CalendarDays className="h-4 w-4" />
                                ثبت: {new Date(request.created_at).toLocaleDateString("fa-IR")}
                              </span>
                              {request.sla_due_at ? (
                                <span className={`flex items-center gap-1 ${getSLAStatusColor(request.sla_status)}`}>
                                  <Clock className="h-4 w-4" />
                                  <span>
                                    مهلت پاسخ‌گویی: {formatSlaDueAt(request.sla_due_at)}
                                    {remainingSlaTime ? ` - ${remainingSlaTime}` : ""}
                                  </span>
                                </span>
                              ) : (
                                <span className="flex items-center gap-1 text-slate-400">
                                  <Clock className="h-4 w-4" />
                                  مهلت ثبت نشده
                                </span>
                              )}
                              {request.cargo.description && (
                                <span className="flex min-w-0 items-center gap-1">
                                  <Package className="h-4 w-4 shrink-0" />
                                  <span className="truncate">{request.cargo.description}</span>
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="flex flex-col gap-2 sm:flex-row xl:w-40 xl:flex-col xl:justify-center">
                            <Button className="rounded-2xl bg-blue-600 hover:bg-blue-700" onClick={() => navigate(`/expert/requests/${request.id}`)}>
                              <Eye className="ml-2 h-4 w-4" />
                              مشاهده / خلاصه
                            </Button>
                            {request.status === "new" && (
                              <Button variant="outline" className="rounded-2xl" onClick={() => handleAssignToMe(request.id)}>
                                <User className="ml-2 h-4 w-4" />
                                ارجاع به من
                              </Button>
                            )}
                            {request.status === "assigned" && (
                              <Button variant="outline" className="rounded-2xl" onClick={() => handleStatusChange(request.id, "in_progress")}>
                                <Clock className="ml-2 h-4 w-4" />
                                شروع پیگیری
                              </Button>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}

            <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
              <CardContent className="flex flex-col gap-3 p-4 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
                <span>نمایش {visibleRequests.length} مورد از صفحه فعلی</span>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" className="rounded-full" disabled>
                    قبلی
                  </Button>
                  <span className="rounded-full bg-blue-50 px-3 py-1 font-medium text-blue-700">صفحه ۱</span>
                  <Button variant="outline" size="sm" className="rounded-full" disabled>
                    بعدی
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default ExpertConsole;
