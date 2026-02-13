import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  ArrowRight,
  User, 
  MapPin, 
  Truck, 
  Package, 
  Clock,
  MessageSquare,
  FileText,
  AlertCircle,
  CheckCircle,
  Send,
  Phone,
  Calendar,
  Weight,
  DollarSign
} from "lucide-react";
import PageNav from "@/components/PageNav";
import { useToast } from "@/hooks/use-toast";
import { 
  fetchExpertRequestDetail, 
  fetchExperts,
  assignRequest,
  changeRequestStatus,
  addMessage,
  type ExpertUser 
} from "@/lib/api";

interface RequestDetail {
  id: number;
  tracking_number: string;
  status: string;
  priority: string;
  created_at: string;
  sla_due_at?: string;
  sla_status: "on_time" | "due_soon" | "overdue";
  assigned_to?: {
    id: number;
    name: string;
    username: string;
  };
  customer: {
    first_name?: string;
    last_name?: string;
    phone: string;
    full_name: string;
  };
  route: {
    origin: {
      province: string;
      county: string;
      city: string;
    };
    destination: {
      province: string;
      county: string;
      city: string;
    };
  };
  transport_method?: string;  // Legacy field
  international_transport_method?: string;
  domestic_transport_method?: string;
  transport_method_preference?: string;
  cargo: {
    description?: string;
    weight?: number;
    volume?: number;
    value?: number;
    special_instructions?: string;
  };
  dates: {
    pickup_date?: string;
    delivery_date?: string;
  };
  timeline: Array<{
    id: number;
    action: string;
    old_status?: string;
    new_status?: string;
    note?: string;
    created_at: string;
    created_by: string;
  }>;
  messages: Array<{
    id: number;
    type: string;
    subject?: string;
    content: string;
    is_read_by_customer: boolean;
    customer_response?: string;
    created_at: string;
    created_by: string;
  }>;
  has_unread: boolean;
}

const RequestDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [request, setRequest] = useState<RequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("details");
  const [newMessage, setNewMessage] = useState({
    type: "internal_note",
    subject: "",
    content: ""
  });
  const [sendingMessage, setSendingMessage] = useState(false);

  // Mock expert ID - in real app, this would come from auth context
  const expertId = 1;

  useEffect(() => {
    if (id) {
      loadRequestDetail();
    }
  }, [id]);

  const loadRequestDetail = async () => {
    try {
      setLoading(true);
      const data = await fetchExpertRequestDetail(Number(id));
      setRequest(data);
    } catch (error) {
      toast({
        title: "خطا",
        description: "خطا در دریافت جزئیات درخواست",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    try {
      await changeRequestStatus(Number(id), newStatus, `تغییر وضعیت به ${newStatus}`);

      toast({
        title: "موفق",
        description: "وضعیت درخواست به‌روزرسانی شد"
      });

      // Update local state immediately
      setRequest(prev => prev ? { ...prev, status: newStatus } : null);

      // Show success message with navigation hint
      setTimeout(() => {
        toast({
          title: "هدایت",
          description: `درخواست به تب "${getStatusLabel(newStatus)}" منتقل شد`,
        });
      }, 1000);

    } catch (error) {
      toast({
        title: "خطا",
        description: "خطا در تغییر وضعیت",
        variant: "destructive"
      });
    }
  };


  const handleSendMessage = async () => {
    if (!newMessage.content.trim()) {
      toast({
        title: "خطا",
        description: "محتوای پیام الزامی است",
        variant: "destructive"
      });
      return;
    }

    try {
      setSendingMessage(true);
      await addMessage(
        Number(id),
        newMessage.type as "internal_note" | "customer_message",
        newMessage.content,
        newMessage.subject,
        expertId
      );

      toast({
        title: "موفق",
        description: "پیام با موفقیت ارسال شد"
      });

      setNewMessage({ type: "internal_note", subject: "", content: "" });
      loadRequestDetail();
    } catch (error) {
      toast({
        title: "خطا",
        description: "خطا در ارسال پیام",
        variant: "destructive"
      });
    } finally {
      setSendingMessage(false);
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

  const getActionLabel = (action: string) => {
    const labels: Record<string, string> = {
      status_change: "تغییر وضعیت",
      assignment: "ارجاع",
      message_added: "پیام اضافه شد",
      note: "یادداشت"
    };
    return labels[action] || action;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Clock className="w-8 h-8 animate-spin text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600">در حال بارگذاری...</p>
        </div>
      </div>
    );
  }

  if (!request) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto space-y-6">
          <PageNav backTo="/expert" backLabel="بازگشت به کنسول" />
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">درخواست یافت نشد</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4 flex-wrap">
            <PageNav backTo="/expert" backLabel="بازگشت به کنسول" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {request.tracking_number}
              </h1>
              <p className="text-gray-600">جزئیات درخواست حمل و نقل</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <Badge className={getStatusColor(request.status)}>
              {getStatusLabel(request.status)}
            </Badge>
            {request.sla_due_at && (
              <Badge 
                variant={request.sla_status === "overdue" ? "destructive" : "secondary"}
                className={request.sla_status === "due_soon" ? "bg-yellow-100 text-yellow-800" : ""}
              >
                SLA: {new Date(request.sla_due_at).toLocaleDateString("fa-IR")}
              </Badge>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList>
                <TabsTrigger value="details">جزئیات</TabsTrigger>
                <TabsTrigger value="notes">یادداشت‌ها</TabsTrigger>
                <TabsTrigger value="messages">پیام‌ها</TabsTrigger>
              </TabsList>

              <TabsContent value="details" className="space-y-4">
                {/* Customer Information */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <User className="w-5 h-5" />
                      اطلاعات مشتری
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium text-gray-600">نام</label>
                        <p className="text-gray-900">{request.customer.full_name}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-600">تلفن</label>
                        <p className="text-gray-900">{request.customer.phone}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Route Information */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <MapPin className="w-5 h-5" />
                      مسیر حمل
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <h4 className="font-medium text-gray-900 mb-3">مبدا</h4>
                        <div className="space-y-2 text-sm">
                          <p><span className="text-gray-600">استان:</span> {request.route.origin.province}</p>
                          <p><span className="text-gray-600">شهرستان:</span> {request.route.origin.county}</p>
                          <p><span className="text-gray-600">شهر:</span> {request.route.origin.city}</p>
                        </div>
                      </div>
                      <div>
                        <h4 className="font-medium text-gray-900 mb-3">مقصد</h4>
                        <div className="space-y-2 text-sm">
                          <p><span className="text-gray-600">استان:</span> {request.route.destination.province}</p>
                          <p><span className="text-gray-600">شهرستان:</span> {request.route.destination.county}</p>
                          <p><span className="text-gray-600">شهر:</span> {request.route.destination.city}</p>
                        </div>
                      </div>
                    </div>
                    
                    {(request.transport_method || request.international_transport_method || request.domestic_transport_method) && (
                      <div className="space-y-2 pt-3 border-t">
                        <div className="flex items-center gap-2">
                          <Truck className="w-4 h-4 text-gray-600" />
                          <span className="text-sm text-gray-600">روش حمل:</span>
                        </div>
                        <div className="space-y-1 pr-6">
                          {request.international_transport_method && (
                            <div className="text-sm">
                              <span className="text-gray-600">بین‌المللی:</span>
                              <span className="font-medium mr-2">{request.international_transport_method}</span>
                            </div>
                          )}
                          {request.domestic_transport_method && (
                            <div className="text-sm">
                              <span className="text-gray-600">داخلی:</span>
                              <span className="font-medium mr-2">{request.domestic_transport_method}</span>
                            </div>
                          )}
                          {request.transport_method && !request.international_transport_method && !request.domestic_transport_method && (
                            <div className="text-sm font-medium">{request.transport_method}</div>
                          )}
                          {request.transport_method_preference === "forwarder_suggestion" && (
                            <div className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
                              پیشنهاد فورواردر
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Cargo Information */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Package className="w-5 h-5" />
                      اطلاعات کالا
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {request.cargo.description && (
                      <div>
                        <label className="text-sm font-medium text-gray-600">توضیحات</label>
                        <p className="text-gray-900">{request.cargo.description}</p>
                      </div>
                    )}
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {request.cargo.weight && (
                        <div className="flex items-center gap-2">
                          <Weight className="w-4 h-4 text-gray-600" />
                          <div>
                            <p className="text-sm text-gray-600">وزن</p>
                            <p className="font-medium">{request.cargo.weight} کیلوگرم</p>
                          </div>
                        </div>
                      )}
                      {request.cargo.volume && (
                        <div className="flex items-center gap-2">
                          <Package className="w-4 h-4 text-gray-600" />
                          <div>
                            <p className="text-sm text-gray-600">حجم</p>
                            <p className="font-medium">{request.cargo.volume} متر مکعب</p>
                          </div>
                        </div>
                      )}
                      {request.cargo.value && (
                        <div className="flex items-center gap-2">
                          <DollarSign className="w-4 h-4 text-gray-600" />
                          <div>
                            <p className="text-sm text-gray-600">ارزش</p>
                            <p className="font-medium">{request.cargo.value.toLocaleString()} تومان</p>
                          </div>
                        </div>
                      )}
                    </div>

                    {request.cargo.special_instructions && (
                      <div>
                        <label className="text-sm font-medium text-gray-600">دستورالعمل‌های خاص</label>
                        <p className="text-gray-900">{request.cargo.special_instructions}</p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Dates */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Calendar className="w-5 h-5" />
                      تاریخ‌ها
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {request.dates.pickup_date && (
                        <div>
                          <label className="text-sm font-medium text-gray-600">تاریخ تحویل</label>
                          <p className="text-gray-900">
                            {new Date(request.dates.pickup_date).toLocaleDateString("fa-IR")}
                          </p>
                        </div>
                      )}
                      {request.dates.delivery_date && (
                        <div>
                          <label className="text-sm font-medium text-gray-600">تاریخ تحویل نهایی</label>
                          <p className="text-gray-900">
                            {new Date(request.dates.delivery_date).toLocaleDateString("fa-IR")}
                          </p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="notes" className="space-y-4">
                {/* Add Note Form */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <FileText className="w-5 h-5" />
                      افزودن یادداشت داخلی
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <label className="text-sm font-medium text-gray-600">موضوع</label>
                      <Input
                        placeholder="موضوع یادداشت (اختیاری)"
                        value={newMessage.subject}
                        onChange={(e) => setNewMessage({...newMessage, subject: e.target.value})}
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-600">محتوا</label>
                      <Textarea
                        placeholder="محتوای یادداشت..."
                        value={newMessage.content}
                        onChange={(e) => setNewMessage({...newMessage, content: e.target.value})}
                        rows={4}
                      />
                    </div>
                    <Button 
                      onClick={handleSendMessage}
                      disabled={sendingMessage || !newMessage.content.trim()}
                    >
                      <Send className="w-4 h-4 ml-2" />
                      {sendingMessage ? "در حال ارسال..." : "ارسال یادداشت"}
                    </Button>
                  </CardContent>
                </Card>

                {/* Messages List */}
                <div className="space-y-4">
                  {request.messages
                    .filter(msg => msg.type === "internal_note")
                    .map((message) => (
                    <Card key={message.id}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between mb-2">
                          <h4 className="font-medium">{message.subject || "یادداشت داخلی"}</h4>
                          <div className="text-sm text-gray-500">
                            {new Date(message.created_at).toLocaleDateString("fa-IR")}
                          </div>
                        </div>
                        <p className="text-gray-700 mb-2">{message.content}</p>
                        <div className="text-sm text-gray-500">
                          توسط: {message.created_by}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="messages" className="space-y-4">
                {/* Add Customer Message Form */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <MessageSquare className="w-5 h-5" />
                      ارسال پیام به مشتری
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <label className="text-sm font-medium text-gray-600">موضوع</label>
                      <Input
                        placeholder="موضوع پیام"
                        value={newMessage.subject}
                        onChange={(e) => setNewMessage({...newMessage, subject: e.target.value})}
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-600">محتوای پیام</label>
                      <Textarea
                        placeholder="پیام خود را بنویسید..."
                        value={newMessage.content}
                        onChange={(e) => setNewMessage({...newMessage, content: e.target.value})}
                        rows={4}
                      />
                    </div>
                    <Button 
                      onClick={() => {
                        setNewMessage({...newMessage, type: "customer_message"});
                        handleSendMessage();
                      }}
                      disabled={sendingMessage || !newMessage.content.trim()}
                    >
                      <Send className="w-4 h-4 ml-2" />
                      {sendingMessage ? "در حال ارسال..." : "ارسال پیام"}
                    </Button>
                  </CardContent>
                </Card>

                {/* Customer Messages List */}
                <div className="space-y-4">
                  {request.messages
                    .filter(msg => msg.type === "customer_message")
                    .map((message) => (
                    <Card key={message.id}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between mb-2">
                          <h4 className="font-medium">{message.subject}</h4>
                          <div className="text-sm text-gray-500">
                            {new Date(message.created_at).toLocaleDateString("fa-IR")}
                          </div>
                        </div>
                        <p className="text-gray-700 mb-3">{message.content}</p>
                        {message.customer_response && (
                          <div className="bg-gray-50 p-3 rounded-lg mb-2">
                            <p className="text-sm font-medium text-gray-600 mb-1">پاسخ مشتری:</p>
                            <p className="text-gray-700">{message.customer_response}</p>
                          </div>
                        )}
                        <div className="text-sm text-gray-500">
                          توسط: {message.created_by}
                          {message.is_read_by_customer && (
                            <span className="mr-2 text-green-600">• خوانده شده</span>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </TabsContent>
            </Tabs>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Status Actions */}
            <Card>
              <CardHeader>
                <CardTitle>عملیات</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Select onValueChange={handleStatusChange}>
                  <SelectTrigger>
                    <SelectValue placeholder="تغییر وضعیت" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="in_progress">در حال پیگیری</SelectItem>
                    <SelectItem value="quoted">ارسال پیشنهاد</SelectItem>
                    <SelectItem value="waiting_for_customer">منتظر مشتری</SelectItem>
                    <SelectItem value="won">برنده</SelectItem>
                    <SelectItem value="lost">باخته</SelectItem>
                    <SelectItem value="closed">بستن</SelectItem>
                  </SelectContent>
                </Select>
              </CardContent>
            </Card>

            {/* Timeline */}
            <Card>
              <CardHeader>
                <CardTitle>تایم‌لاین</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {request.timeline.map((event, index) => (
                    <div key={event.id} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                        {index < request.timeline.length - 1 && (
                          <div className="w-px h-8 bg-gray-300 mt-2"></div>
                        )}
                      </div>
                      <div className="flex-1 pb-4">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-medium">{getActionLabel(event.action)}</span>
                          {event.old_status && event.new_status && (
                            <span className="text-xs text-gray-500">
                              {getStatusLabel(event.old_status)} → {getStatusLabel(event.new_status)}
                            </span>
                          )}
                        </div>
                        {event.note && (
                          <p className="text-sm text-gray-600 mb-1">{event.note}</p>
                        )}
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <span>{new Date(event.created_at).toLocaleDateString("fa-IR")}</span>
                          <span>•</span>
                          <span>{event.created_by}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Request Info */}
            <Card>
              <CardHeader>
                <CardTitle>اطلاعات درخواست</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">شماره پیگیری:</span>
                  <span className="font-medium">{request.tracking_number}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">تاریخ ثبت:</span>
                  <span>{new Date(request.created_at).toLocaleDateString("fa-IR")}</span>
                </div>
                {request.assigned_to && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">مسئول:</span>
                    <span>{request.assigned_to.name}</span>
                  </div>
                )}
                {request.sla_due_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">مهلت SLA:</span>
                    <span className={request.sla_status === "overdue" ? "text-red-600" : ""}>
                      {new Date(request.sla_due_at).toLocaleDateString("fa-IR")}
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RequestDetail;
