import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  Bell, 
  Search, 
  Filter, 
  Clock, 
  User, 
  MapPin, 
  Truck, 
  Package, 
  AlertCircle,
  CheckCircle,
  Eye,
  MessageSquare,
  Plus,
  RefreshCw,
  Settings,
  LogOut,
  ChevronDown
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import PageNav from "@/components/PageNav";
import { 
  fetchExpertRequests, 
  fetchKPIs, 
  fetchExperts,
  assignRequest,
  changeRequestStatus,
  fetchNotifications,
  type ExpertRequest, 
  type KPIs,
  type ExpertUser 
} from "@/lib/api";

// Use types from API
type ShipmentRequest = ExpertRequest;
type KPI = KPIs;

const ExpertConsole = () => {
  const { toast } = useToast();
  const [requests, setRequests] = useState<ShipmentRequest[]>([]);
  const [kpis, setKpis] = useState<KPI | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("new");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [unreadCount, setUnreadCount] = useState(0);
  const [currentExpert, setCurrentExpert] = useState<ExpertUser | null>(null);

  // Mock expert ID - in real app, this would come from auth context
  const expertId = 1;

  useEffect(() => {
    loadRequests();
    loadKPIs();
    loadNotifications();
    loadCurrentExpert();
    
    // Poll for updates every 30 seconds
    const interval = setInterval(() => {
      loadRequests();
      loadNotifications();
    }, 30000);

    return () => clearInterval(interval);
  }, [activeTab, searchTerm, statusFilter, priorityFilter]);

  const loadRequests = async () => {
    try {
      setLoading(true);
      
      const params: any = {
        page: 1,
        per_page: 50,
        sort_by: "created_at",
        sort_order: "desc"
      };

      // Set status based on active tab first
      if (activeTab !== "all" && activeTab !== "closed") {
        params.status = activeTab;
      } else if (activeTab === "closed") {
        // For closed tab, show won, lost, and closed statuses
        params.status = "won,lost,closed";
      }
      
      // Apply additional filters
      if (searchTerm) {
        params.search = searchTerm;
      }
      if (priorityFilter && priorityFilter !== "all") {
        params.priority = priorityFilter;
      }
      
      // Status filter should only apply when no specific tab is selected
      // or when "all" tab is active
      if (statusFilter && statusFilter !== "all" && activeTab === "all") {
        params.status = statusFilter;
      }

      const data = await fetchExpertRequests(params);
      setRequests(data.requests || []);
    } catch (error) {
      toast({
        title: "خطا",
        description: "خطا در دریافت درخواست‌ها",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const loadKPIs = async () => {
    try {
      const data = await fetchKPIs(expertId);
      setKpis(data);
    } catch (error) {
      console.error("Error loading KPIs:", error);
    }
  };

  const loadNotifications = async () => {
    try {
      const data = await fetchNotifications(expertId, true);
      setUnreadCount(data.unread_count || 0);
    } catch (error) {
      console.error("Error loading notifications:", error);
    }
  };

  const loadCurrentExpert = async () => {
    try {
      // Try to get expert from localStorage first
      const storedExpert = localStorage.getItem('expert_user');
      if (storedExpert) {
        const expert = JSON.parse(storedExpert);
        setCurrentExpert(expert);
        return;
      }

      // Fallback to API
      const experts = await fetchExperts();
      const expert = experts.find(e => e.id === expertId) || experts[0];
      setCurrentExpert(expert);
    } catch (error) {
      console.error("Error loading current expert:", error);
    }
  };

  const handleAssignToMe = async (requestId: number) => {
    try {
      await assignRequest(requestId, expertId);

      toast({
        title: "موفق",
        description: "درخواست به شما ارجاع داده شد"
      });

      loadRequests();
      loadKPIs();
    } catch (error) {
      toast({
        title: "خطا",
        description: "خطا در ارجاع درخواست",
        variant: "destructive"
      });
    }
  };

  const handleStatusChange = async (requestId: number, newStatus: string) => {
    try {
      await changeRequestStatus(requestId, newStatus, `تغییر وضعیت به ${newStatus}`);

      toast({
        title: "موفق",
        description: "وضعیت درخواست به‌روزرسانی شد"
      });

      // Update the local state immediately for better UX
      setRequests(prevRequests => 
        prevRequests.map(req => 
          req.id === requestId 
            ? { ...req, status: newStatus }
            : req
        )
      );

      // Switch to appropriate tab based on new status
      if (newStatus === "in_progress") {
        setActiveTab("in_progress");
      } else if (newStatus === "waiting_for_customer") {
        setActiveTab("waiting_for_customer");
      } else if (newStatus === "closed" || newStatus === "won" || newStatus === "lost") {
        setActiveTab("all"); // Show all requests including closed ones
      }

      loadKPIs();
    } catch (error) {
      toast({
        title: "خطا",
        description: "خطا در تغییر وضعیت",
        variant: "destructive"
      });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "new": return "bg-blue-100 text-blue-800";
      case "assigned": return "bg-yellow-100 text-yellow-800";
      case "in_progress": return "bg-purple-100 text-purple-800";
      case "quoted": return "bg-indigo-100 text-indigo-800";
      case "waiting_for_customer": return "bg-orange-100 text-orange-800";
      case "won": return "bg-green-100 text-green-800";
      case "lost": return "bg-red-100 text-red-800";
      case "closed": return "bg-gray-100 text-gray-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "urgent": return "bg-red-100 text-red-800";
      case "high": return "bg-orange-100 text-orange-800";
      case "normal": return "bg-blue-100 text-blue-800";
      case "low": return "bg-gray-100 text-gray-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  const getSLAStatusColor = (slaStatus: string) => {
    switch (slaStatus) {
      case "overdue": return "text-red-600";
      case "due_soon": return "text-yellow-600";
      case "on_time": return "text-green-600";
      default: return "text-gray-600";
    }
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      new: "جدید",
      assigned: "ارجاع شده",
      in_progress: "در حال پیگیری",
      quoted: "پیشنهاد ارسال شده",
      waiting_for_customer: "منتظر مشتری",
      won: "برنده",
      lost: "باخته",
      closed: "مختومه"
    };
    return labels[status] || status;
  };

  const getPriorityLabel = (priority: string) => {
    const labels: Record<string, string> = {
      urgent: "فوری",
      high: "بالا",
      normal: "عادی",
      low: "پایین"
    };
    return labels[priority] || priority;
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4 flex-wrap">
            <PageNav backTo="/" showLogout />
            <div>
              <h1 className="text-3xl font-bold text-gray-900">کنسول کارشناس</h1>
              <p className="text-gray-600 mt-1">مدیریت درخواست‌های حمل و نقل</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="sm"
              onClick={loadRequests}
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 ml-2 ${loading ? "animate-spin" : ""}`} />
              به‌روزرسانی
            </Button>
            <div className="relative">
              <Button variant="outline" size="sm">
                <Bell className="w-4 h-4 ml-2" />
                اعلان‌ها
                {unreadCount > 0 && (
                  <Badge className="absolute -top-2 -right-2 bg-red-500 text-white text-xs">
                    {unreadCount}
                  </Badge>
                )}
              </Button>
            </div>
            
            {/* Expert Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  <User className="w-4 h-4 ml-2" />
                  {currentExpert ? currentExpert.full_name : "کارشناس"}
                  <ChevronDown className="w-4 h-4 mr-2" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="px-3 py-2 border-b">
                  <p className="text-sm font-medium">{currentExpert?.full_name || "کارشناس"}</p>
                  <p className="text-xs text-gray-500">{currentExpert?.email || "email@example.com"}</p>
                </div>
                <DropdownMenuItem>
                  <Settings className="w-4 h-4 mr-2" />
                  تنظیمات پروفایل
                </DropdownMenuItem>
                <DropdownMenuItem>
                  <User className="w-4 h-4 mr-2" />
                  درخواست‌های من
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => {
                  localStorage.removeItem('expert_user');
                  window.location.href = '/';
                }}>
                  <LogOut className="w-4 h-4 mr-2" />
                  خروج
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {/* Status Summary Card */}
        {kpis && (
          <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">خلاصه وضعیت درخواست‌ها</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-600">{kpis.counts.new}</div>
                      <div className="text-sm text-gray-600">جدید</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-600">{kpis.counts.in_progress}</div>
                      <div className="text-sm text-gray-600">در حال پیگیری</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-orange-600">{kpis.counts.waiting_for_customer}</div>
                      <div className="text-sm text-gray-600">منتظر مشتری</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">{kpis.counts.closed_today}</div>
                      <div className="text-sm text-gray-600">مختومه امروز</div>
                    </div>
                  </div>
                </div>
                <div className="hidden md:block">
                  <div className="text-right">
                    <div className="text-sm text-gray-500 mb-1">کل درخواست‌ها</div>
                    <div className="text-3xl font-bold text-gray-800">
                      {kpis.counts.new + kpis.counts.in_progress + kpis.counts.waiting_for_customer + kpis.counts.closed_today}
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* KPI Cards */}
        {kpis && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">درخواست‌های جدید</p>
                    <p className="text-2xl font-bold text-blue-600">{kpis.counts.new}</p>
                  </div>
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <Plus className="w-6 h-6 text-blue-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">در حال پیگیری</p>
                    <p className="text-2xl font-bold text-purple-600">{kpis.counts.in_progress}</p>
                  </div>
                  <div className="p-2 bg-purple-100 rounded-lg">
                    <Clock className="w-6 h-6 text-purple-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">منتظر مشتری</p>
                    <p className="text-2xl font-bold text-orange-600">{kpis.counts.waiting_for_customer}</p>
                  </div>
                  <div className="p-2 bg-orange-100 rounded-lg">
                    <MessageSquare className="w-6 h-6 text-orange-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">مختومه امروز</p>
                    <p className="text-2xl font-bold text-green-600">{kpis.counts.closed_today}</p>
                  </div>
                  <div className="p-2 bg-green-100 rounded-lg">
                    <CheckCircle className="w-6 h-6 text-green-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* SLA Alert */}
        {(kpis?.sla.overdue || 0) > 0 && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-red-600" />
                <div>
                  <p className="font-medium text-red-800">
                    {kpis?.sla.overdue} درخواست از مهلت SLA گذشته است
                  </p>
                  <p className="text-sm text-red-600">
                    لطفاً درخواست‌های عقب‌افتاده را اولویت دهید
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Filters */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute right-3 top-3 w-4 h-4 text-gray-400" />
                  <Input
                    placeholder="جستجو در درخواست‌ها..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pr-10"
                  />
                </div>
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full md:w-48">
                  <SelectValue placeholder="فیلتر وضعیت" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">همه وضعیت‌ها</SelectItem>
                  <SelectItem value="new">جدید</SelectItem>
                  <SelectItem value="assigned">ارجاع شده</SelectItem>
                  <SelectItem value="in_progress">در حال پیگیری</SelectItem>
                  <SelectItem value="quoted">پیشنهاد ارسال شده</SelectItem>
                  <SelectItem value="waiting_for_customer">منتظر مشتری</SelectItem>
                  <SelectItem value="won">برنده</SelectItem>
                  <SelectItem value="lost">باخته</SelectItem>
                  <SelectItem value="closed">مختومه</SelectItem>
                </SelectContent>
              </Select>
              <Select value={priorityFilter} onValueChange={setPriorityFilter}>
                <SelectTrigger className="w-full md:w-48">
                  <SelectValue placeholder="فیلتر اولویت" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">همه اولویت‌ها</SelectItem>
                  <SelectItem value="urgent">فوری</SelectItem>
                  <SelectItem value="high">بالا</SelectItem>
                  <SelectItem value="normal">عادی</SelectItem>
                  <SelectItem value="low">پایین</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Main Content */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-7">
            <TabsTrigger value="new">
              جدید
              {kpis?.counts.new && (
                <Badge variant="secondary" className="mr-2">
                  {kpis.counts.new}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="assigned">
              ارجاع شده
            </TabsTrigger>
            <TabsTrigger value="in_progress">
              در حال پیگیری
              {kpis?.counts.in_progress && (
                <Badge variant="secondary" className="mr-2">
                  {kpis.counts.in_progress}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="quoted">
              پیشنهاد
            </TabsTrigger>
            <TabsTrigger value="waiting_for_customer">
              منتظر مشتری
              {kpis?.counts.waiting_for_customer && (
                <Badge variant="secondary" className="mr-2">
                  {kpis.counts.waiting_for_customer}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="closed">
              مختومه
              {kpis?.counts.closed_today && (
                <Badge variant="secondary" className="mr-2">
                  {kpis.counts.closed_today}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="all">همه</TabsTrigger>
          </TabsList>

          <TabsContent value={activeTab} className="space-y-4">
            {loading ? (
              <div className="flex justify-center py-8">
                <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
              </div>
            ) : requests.length === 0 ? (
              <Card>
                <CardContent className="p-8 text-center">
                  <Package className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">درخواستی یافت نشد</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {requests.map((request) => (
                  <Card key={request.id} className={`${request.has_unread ? "border-blue-300 bg-blue-50" : ""}`}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 space-y-3">
                          {/* Header */}
                          <div className="flex items-center gap-3">
                            <h3 className="font-semibold text-lg">
                              {request.tracking_number}
                            </h3>
                            {/* Status Badge - More Prominent */}
                            <div className="flex items-center gap-2">
                              <div className={`w-3 h-3 rounded-full ${
                                request.status === 'new' ? 'bg-blue-500' :
                                request.status === 'in_progress' ? 'bg-purple-500' :
                                request.status === 'waiting_for_customer' ? 'bg-orange-500' :
                                request.status === 'won' ? 'bg-green-500' :
                                request.status === 'lost' ? 'bg-red-500' :
                                request.status === 'closed' ? 'bg-gray-500' :
                                'bg-blue-500'
                              }`}></div>
                              <Badge className={`${getStatusColor(request.status)} font-semibold`}>
                                {getStatusLabel(request.status)}
                              </Badge>
                            </div>
                            <Badge className={getPriorityColor(request.priority)}>
                              {getPriorityLabel(request.priority)}
                            </Badge>
                            {request.has_unread && (
                              <Badge className="bg-blue-500 text-white animate-pulse">
                                جدید
                              </Badge>
                            )}
                          </div>

                          {/* Customer Info */}
                          <div className="flex items-center gap-2 text-sm text-gray-600">
                            <User className="w-4 h-4" />
                            <span>{request.customer.name}</span>
                            <span>•</span>
                            <span>{request.customer.phone}</span>
                          </div>

                          {/* Route */}
                          <div className="flex items-center gap-2 text-sm text-gray-600">
                            <MapPin className="w-4 h-4" />
                            <span>
                              {request.route.origin.city} → {request.route.destination.city}
                            </span>
                            {(request.transport_method || request.international_transport_method || request.domestic_transport_method) && (
                              <>
                                <span>•</span>
                                <span className="flex items-center gap-1">
                                  <Truck className="w-4 h-4" />
                                  {request.international_transport_method && `بین‌المللی: ${request.international_transport_method}`}
                                  {request.domestic_transport_method && `داخلی: ${request.domestic_transport_method}`}
                                  {request.transport_method && !request.international_transport_method && !request.domestic_transport_method && request.transport_method}
                                  {request.transport_method_preference === "forwarder_suggestion" && " (پیشنهاد فورواردر)"}
                                </span>
                              </>
                            )}
                          </div>

                          {/* Cargo Info */}
                          {request.cargo.description && (
                            <div className="text-sm text-gray-600">
                              <Package className="w-4 h-4 inline ml-1" />
                              {request.cargo.description}
                            </div>
                          )}

                          {/* Timestamps */}
                          <div className="flex items-center gap-4 text-xs text-gray-500">
                            <span>
                              ثبت: {new Date(request.created_at).toLocaleDateString("fa-IR")}
                            </span>
                            {request.sla_due_at && (
                              <span className={getSLAStatusColor(request.sla_status)}>
                                SLA: {new Date(request.sla_due_at).toLocaleDateString("fa-IR")}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex flex-col gap-2">
                          <Button
                            size="sm"
                            onClick={() => window.open(`/expert/requests/${request.id}`, "_blank")}
                          >
                            <Eye className="w-4 h-4 ml-2" />
                            مشاهده
                          </Button>
                          
                          {request.status === "new" && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleAssignToMe(request.id)}
                            >
                              <User className="w-4 h-4 ml-2" />
                              ارجاع به من
                            </Button>
                          )}
                          
                          {request.status === "assigned" && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleStatusChange(request.id, "in_progress")}
                            >
                              <Clock className="w-4 h-4 ml-2" />
                              شروع پیگیری
                            </Button>
                          )}
                          
                          {request.status === "in_progress" && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleStatusChange(request.id, "waiting_for_customer")}
                            >
                              <MessageSquare className="w-4 h-4 ml-2" />
                              انتظار مشتری
                            </Button>
                          )}
                          
                          {request.status === "waiting_for_customer" && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleStatusChange(request.id, "won")}
                            >
                              <CheckCircle className="w-4 h-4 ml-2" />
                              برنده
                            </Button>
                          )}
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

export default ExpertConsole;
