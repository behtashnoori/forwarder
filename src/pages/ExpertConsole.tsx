import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import {
  BarChart3,
  CalendarDays,
  CheckCircle,
  ChevronDown,
  Clock,
  Eye,
  Filter,
  LogOut,
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import { useI18n } from "@/i18n";
import { logoutAndClearExpertSession } from "@/lib/authSession";

type ShipmentRequest = ExpertRequest & {
  international_transport_method?: string;
  domestic_transport_method?: string;
  transport_method_preference?: string;
};
type KPI = KPIs;

const expertId = 1;

const ExpertConsole = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { locale, statusLabel, t, tf } = useI18n();
  const [requests, setRequests] = useState<ShipmentRequest[]>([]);
  const [kpis, setKpis] = useState<KPI | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("new");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
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
      if (statusFilter && statusFilter !== "all" && activeTab === "all") {
        params.status = statusFilter;
      }

      const data = await fetchExpertRequests(params);
      setRequests(data.requests || []);
    } catch (error) {
      toast({
        title: t("common.error"),
        description: t("requestDetail.fetchError"),
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [activeTab, searchTerm, statusFilter, t, toast]);

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
        title: t("common.success"),
        description: t("expert.assignToMe"),
      });

      loadRequests();
      loadKPIs();
    } catch (error) {
      toast({
        title: t("common.error"),
        description: t("requestDetail.changeStatusError"),
        variant: "destructive",
      });
    }
  };

  const handleStatusChange = async (requestId: number, newStatus: string) => {
    try {
      await changeRequestStatus(requestId, newStatus, `تغییر وضعیت به ${newStatus}`);

      toast({
        title: t("common.success"),
        description: t("requestDetail.statusUpdated"),
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
        title: t("common.error"),
        description: t("requestDetail.changeStatusError"),
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

  const totalKpiCount = useMemo(() => {
    if (!kpis) return 0;
    return kpis.counts.new + kpis.counts.in_progress + kpis.counts.waiting_for_customer + kpis.counts.closed_today;
  }, [kpis]);

  const clearFilters = () => {
    setSearchTerm("");
    setStatusFilter("");
  };

  const formatRoute = (request: ShipmentRequest) => {
    const { route } = request;
    let origin: string;
    let destination: string;

    if (route.shipping_type === "international") {
      origin = [route.origin.international_city, route.origin.country].filter(Boolean).join("، ");
      destination = [route.destination.international_city, route.destination.country].filter(Boolean).join("، ");
      // Append the structured in-Iran destination point when present.
      if (route.iran_destination?.label) {
        destination = [destination, route.iran_destination.label].filter(Boolean).join(" ← ");
      }
    } else {
      origin = [route.origin.city, route.origin.county, route.origin.province].filter(Boolean).join("، ");
      destination = [route.destination.city, route.destination.county, route.destination.province].filter(Boolean).join("، ");
    }

    return {
      origin: origin || t("expert.unknownOrigin"),
      destination: destination || t("expert.unknownDestination"),
    };
  };

  const formatTransport = (request: ShipmentRequest) => {
    if (request.international_transport_method) return `${t("shipping.type.international")}: ${request.international_transport_method}`;
    if (request.domestic_transport_method) return `${t("shipping.type.domestic")}: ${request.domestic_transport_method}`;
    if (request.transport_method) return request.transport_method;
    return t("expert.transportMissing");
  };

  const statusItems = [
    { value: "all", label: t("status.all") },
    { value: "new", label: statusLabel("new") },
    { value: "assigned", label: statusLabel("assigned") },
    { value: "in_progress", label: statusLabel("in_progress") },
    { value: "waiting_for_customer", label: statusLabel("waiting_for_customer") },
    { value: "closed", label: statusLabel("completed") },
  ];

  const statusFilterItems = [
    { value: "all", label: t("status.allStatuses") },
    { value: "new", label: statusLabel("new") },
    { value: "assigned", label: statusLabel("assigned") },
    { value: "in_progress", label: statusLabel("in_progress") },
    { value: "quoted", label: statusLabel("quoted") },
    { value: "waiting_for_customer", label: statusLabel("waiting_for_customer") },
    { value: "won", label: statusLabel("won") },
    { value: "lost", label: t("status.rejectedOrLost") },
    { value: "closed", label: t("status.closedOperational") },
  ];

  const metricCards = kpis
    ? [
        {
          label: t("expert.newRequests"),
          value: kpis.counts.new,
          icon: Plus,
          tone: "text-blue-700 bg-blue-50 border-blue-100",
        },
        {
          label: statusLabel("in_progress"),
          value: kpis.counts.in_progress,
          icon: Clock,
          tone: "text-violet-700 bg-violet-50 border-violet-100",
        },
        {
          label: statusLabel("waiting_for_customer"),
          value: kpis.counts.waiting_for_customer,
          icon: MessageSquare,
          tone: "text-orange-700 bg-orange-50 border-orange-100",
        },
        {
          label: t("status.closedToday"),
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
                  <h1 className="text-2xl font-bold text-slate-950 sm:text-3xl">{t("expert.title")}</h1>
                  <p className="mt-2 text-sm leading-6 text-slate-500 sm:text-base">{t("expert.subtitle")}</p>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-3 sm:items-end">
              <div className="flex flex-wrap items-center gap-2">
                <Button variant="outline" size="sm" onClick={loadRequests} disabled={loading} className="rounded-full">
                  <RefreshCw className={`ml-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                  {t("common.refresh")}
                </Button>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="rounded-full">
                      <User className="ml-2 h-4 w-4" />
                      {currentExpert ? currentExpert.full_name : t("expert.profileFallback")}
                      <ChevronDown className="mr-2 h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <div className="border-b px-3 py-2">
                      <p className="text-sm font-medium">{currentExpert?.full_name || t("expert.profileFallback")}</p>
                      <p className="text-xs text-slate-500">{currentExpert?.role || t("common.roleExpert")}</p>
                    </div>
                    <DropdownMenuItem
                      onClick={async () => {
                        await logoutAndClearExpertSession();
                        navigate("/", { replace: true });
                      }}
                    >
                      <LogOut className="ml-2 h-4 w-4" />
                      {t("common.logout")}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </div>
        </section>

        {kpis && (
          <section>
            <Card className="rounded-3xl border-blue-100 bg-white shadow-sm">
              <CardContent className="p-5 sm:p-6">
                <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <p className="text-sm font-medium text-blue-700">{t("expert.kpiSummary")}</p>
                    <h2 className="mt-1 text-xl font-bold text-slate-950">{t("expert.todayOperationalView")}</h2>
                  </div>
                  <div className="rounded-2xl bg-slate-50 px-4 py-3 text-right">
                    <p className="text-xs text-slate-500">{t("expert.totalVisibleRequests")}</p>
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
          </section>
        )}

        <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
          <CardContent className="space-y-4 p-4 sm:p-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
              <Filter className="h-4 w-4 text-blue-600" />
              {t("expert.searchFilterTitle")}
            </div>
            <div className="grid gap-3 lg:grid-cols-[1fr_12rem_auto]">
              <div className="relative min-w-0">
                <Search className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  placeholder={t("expert.searchPlaceholder")}
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  className="h-11 rounded-2xl border-slate-200 bg-slate-50 pr-10"
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="h-11 rounded-2xl border-slate-200 bg-slate-50">
                  <SelectValue placeholder={t("expert.statusPlaceholder")} />
                </SelectTrigger>
                <SelectContent>
                  {statusFilterItems.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button variant="outline" onClick={clearFilters} className="h-11 rounded-2xl">
                {t("common.clearFilters")}
              </Button>
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
                <h2 className="text-xl font-bold text-slate-950">{t("expert.freightRequests")}</h2>
                <p className="mt-1 text-sm text-slate-500">{tf("expert.showingRequests", { count: requests.length })}</p>
              </div>
              <div className="rounded-full border border-slate-200 bg-white px-4 py-2 text-xs text-slate-500 shadow-sm">
                {t("expert.sortNewest")}
              </div>
            </div>

            {loading ? (
              <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                <CardContent className="flex justify-center py-12">
                  <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
                </CardContent>
              </Card>
            ) : requests.length === 0 ? (
              <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                <CardContent className="p-10 text-center">
                  <Package className="mx-auto mb-4 h-12 w-12 text-slate-300" />
                  <p className="font-medium text-slate-700">{t("expert.noRequestsTitle")}</p>
                  <p className="mt-1 text-sm text-slate-500">{t("expert.noRequestsDescription")}</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {requests.map((request) => {
                  const route = formatRoute(request);
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
                                {statusLabel(request.status)}
                              </Badge>
                              {request.has_unread && <Badge className="rounded-full bg-blue-600 text-white">{t("common.unread")}</Badge>}
                            </div>

                            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                              <div className="rounded-2xl bg-slate-50 p-3">
                                <div className="mb-2 flex items-center gap-2 text-xs text-slate-500">
                                  <User className="h-4 w-4" />
                                  {t("common.customerName")}
                                </div>
                                <p className="truncate text-sm font-semibold text-slate-900">{request.customer.name}</p>
                                <p className="mt-1 text-xs text-slate-500" dir="ltr">
                                  {request.customer.phone}
                                </p>
                              </div>

                              <div className="rounded-2xl bg-slate-50 p-3">
                                <div className="mb-2 flex items-center gap-2 text-xs text-slate-500">
                                  <MapPin className="h-4 w-4" />
                                  {t("common.origin")}
                                </div>
                                <p className="line-clamp-2 text-sm font-semibold text-slate-900">{route.origin}</p>
                              </div>

                              <div className="rounded-2xl bg-slate-50 p-3">
                                <div className="mb-2 flex items-center gap-2 text-xs text-slate-500">
                                  <MapPin className="h-4 w-4" />
                                  {t("common.destination")}
                                </div>
                                <p className="line-clamp-2 text-sm font-semibold text-slate-900">{route.destination}</p>
                              </div>

                              <div className="rounded-2xl bg-slate-50 p-3">
                                <div className="mb-2 flex items-center gap-2 text-xs text-slate-500">
                                  <Truck className="h-4 w-4" />
                                  {t("common.transportMethod")}
                                </div>
                                <p className="line-clamp-2 text-sm font-semibold text-slate-900">{formatTransport(request)}</p>
                              </div>
                            </div>

                            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-500">
                              <span className="flex items-center gap-1">
                                <CalendarDays className="h-4 w-4" />
                                {t("expert.createdPrefix")}: {new Date(request.created_at).toLocaleDateString(locale)}
                              </span>
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
                              {t("expert.viewDetails")}
                            </Button>
                            {request.status === "new" && (
                              <Button variant="outline" className="rounded-2xl" onClick={() => handleAssignToMe(request.id)}>
                                <User className="ml-2 h-4 w-4" />
                                {t("expert.assignToMe")}
                              </Button>
                            )}
                            {request.status === "assigned" && (
                              <Button variant="outline" className="rounded-2xl" onClick={() => handleStatusChange(request.id, "in_progress")}>
                                <Clock className="ml-2 h-4 w-4" />
                                {t("expert.startFollowUp")}
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
                <span>{tf("expert.showingCurrentPage", { count: requests.length })}</span>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" className="rounded-full" disabled>
                    {t("common.previous")}
                  </Button>
                  <span className="rounded-full bg-blue-50 px-3 py-1 font-medium text-blue-700">{t("common.pageOne")}</span>
                  <Button variant="outline" size="sm" className="rounded-full" disabled>
                    {t("common.next")}
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
