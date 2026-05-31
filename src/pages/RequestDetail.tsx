import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  Clock,
  DollarSign,
  FileText,
  MapPin,
  MessageSquare,
  Package,
  Phone,
  Send,
  Truck,
  User,
  Weight,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import PageNav from "@/components/PageNav";
import { useToast } from "@/hooks/use-toast";
import { addMessage, changeRequestStatus, fetchExpertRequestDetail } from "@/lib/api";

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
      province?: string | null;
      county?: string | null;
      city?: string | null;
    };
    destination: {
      province?: string | null;
      county?: string | null;
      city?: string | null;
    };
  };
  transport_method?: string;
  international_transport_method?: string;
  domestic_transport_method?: string;
  transport_method_preference?: string;
  cargo: {
    description?: string | null;
    weight?: number | null;
    volume?: number | null;
    value?: number | null;
    special_instructions?: string | null;
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
  latest_quote?: {
    id: number;
    amount: number;
    currency: string;
    note?: string | null;
    valid_until?: string | null;
    created_at: string;
    created_by?: string | null;
  } | null;
}

type RouteLocation = RequestDetail["route"]["origin"];

const missingValue = "ثبت نشده";

const formatDate = (value?: string) => (value ? new Date(value).toLocaleDateString("fa-IR") : missingValue);
const displayValue = (value?: string | number | null) => {
  if (value === null || value === undefined || value === "") return missingValue;
  return String(value);
};

const RequestDetail = () => {
  const { id } = useParams<{ id: string }>();
  const { toast } = useToast();

  const [request, setRequest] = useState<RequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("details");
  const [newMessage, setNewMessage] = useState({
    type: "internal_note",
    subject: "",
    content: "",
  });
  const [sendingMessage, setSendingMessage] = useState(false);

  const expertId = (() => {
    try {
      const stored = localStorage.getItem("expert_user");
      if (stored) {
        const expert = JSON.parse(stored) as { id?: number };
        if (typeof expert?.id === "number") return expert.id;
      }
    } catch {
      // Ignore malformed stored expert data and fall back to the default expert id.
    }
    return 1;
  })();

  const loadRequestDetail = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchExpertRequestDetail(Number(id));
      setRequest(data);
    } catch (error) {
      toast({
        title: "خطا",
        description: "خطا در دریافت جزئیات درخواست",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [id, toast]);

  useEffect(() => {
    if (id) {
      loadRequestDetail();
    }
  }, [id, loadRequestDetail]);

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      new: "جدید",
      assigned: "در انتظار بررسی",
      in_progress: "در حال بررسی",
      quoted: "پیشنهاد ارسال‌شده",
      waiting_for_customer: "منتظر مشتری",
      won: "پذیرفته‌شده",
      lost: "ردشده / از دست‌رفته",
      closed: "مختومه",
    };
    return labels[status] || status;
  };

  const handleStatusChange = async (newStatus: string) => {
    try {
      await changeRequestStatus(Number(id), newStatus, `تغییر وضعیت به ${newStatus}`);

      toast({
        title: "موفق",
        description: "وضعیت درخواست به‌روزرسانی شد",
      });

      setRequest((prev) => (prev ? { ...prev, status: newStatus } : null));

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
        variant: "destructive",
      });
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.content.trim()) {
      toast({
        title: "خطا",
        description: "محتوای یادداشت الزامی است",
        variant: "destructive",
      });
      return;
    }

    try {
      setSendingMessage(true);
      await addMessage(Number(id), "internal_note", newMessage.content, newMessage.subject, expertId);

      toast({
        title: "موفق",
        description: "یادداشت با موفقیت ثبت شد",
      });

      setNewMessage({ type: "internal_note", subject: "", content: "" });
      loadRequestDetail();
    } catch (error) {
      toast({
        title: "خطا",
        description: "خطا در ثبت یادداشت",
        variant: "destructive",
      });
    } finally {
      setSendingMessage(false);
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
        return "border-red-200 bg-red-50 text-red-700";
      case "closed":
        return "border-slate-200 bg-slate-100 text-slate-700";
      default:
        return "border-slate-200 bg-slate-100 text-slate-700";
    }
  };

  const getActionLabel = (action: string) => {
    const labels: Record<string, string> = {
      status_change: "تغییر وضعیت",
      assignment: "تخصیص",
      message_added: "پیام اضافه شد",
      note: "یادداشت",
    };
    return labels[action] || action;
  };

  const getSlaLabel = (slaStatus: string) => {
    const labels: Record<string, string> = {
      overdue: "گذشته از مهلت",
      due_soon: "نزدیک به مهلت",
      on_time: "به‌موقع",
    };
    return labels[slaStatus] || slaStatus;
  };

  const transportLabel = useMemo(() => {
    if (!request) return missingValue;
    if (request.international_transport_method) return `بین‌المللی: ${request.international_transport_method}`;
    if (request.domestic_transport_method) return `داخلی: ${request.domestic_transport_method}`;
    if (request.transport_method) return request.transport_method;
    return missingValue;
  }, [request]);

  const renderLocationBox = (title: string, location: RouteLocation, tone: "origin" | "destination") => {
    const accent = tone === "origin" ? "bg-emerald-50 text-emerald-700 border-emerald-100" : "bg-blue-50 text-blue-700 border-blue-100";
    return (
      <div className={`rounded-2xl border p-4 ${accent}`}>
        <div className="mb-4 flex items-center gap-2">
          <MapPin className="h-5 w-5" />
          <h3 className="font-bold">{title}</h3>
        </div>
        <div className="space-y-3 text-sm">
          <InfoRow label="استان" value={displayValue(location.province)} />
          <InfoRow label="شهرستان" value={displayValue(location.county)} />
          <InfoRow label="شهر" value={displayValue(location.city)} />
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50" dir="rtl">
        <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
          <CardContent className="flex flex-col items-center gap-4 p-10 text-center">
            <div className="rounded-2xl bg-blue-50 p-4">
              <Clock className="h-8 w-8 animate-spin text-blue-600" />
            </div>
            <p className="text-slate-600">در حال بارگذاری...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!request) {
    return (
      <div className="min-h-screen bg-slate-50 p-4 sm:p-6" dir="rtl">
        <div className="mx-auto max-w-7xl space-y-6">
          <PageNav backTo="/expert" backLabel="بازگشت به کنسول" showLogout logoutTo="/expert" />
          <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
            <CardContent className="flex flex-col items-center justify-center p-12 text-center">
              <AlertCircle className="mx-auto mb-4 h-12 w-12 text-slate-300" />
              <p className="text-slate-600">درخواست یافت نشد</p>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const internalNotes = request.messages.filter((message) => message.type === "internal_note");

  return (
    <div className="min-h-screen bg-slate-50" dir="rtl">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
        <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm lg:p-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex min-w-0 items-start gap-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-sm">
                <FileText className="h-7 w-7" />
              </div>
              <div className="min-w-0">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className={`rounded-full px-3 py-1 ${getStatusColor(request.status)}`}>
                    {getStatusLabel(request.status)}
                  </Badge>
                  {request.sla_due_at && (
                    <Badge
                      variant={request.sla_status === "overdue" ? "destructive" : "secondary"}
                      className={request.sla_status === "due_soon" ? "bg-amber-100 text-amber-800" : ""}
                    >
                      SLA: {formatDate(request.sla_due_at)}
                    </Badge>
                  )}
                </div>
                <h1 className="break-words text-2xl font-bold text-slate-950 sm:text-3xl">{request.tracking_number}</h1>
                <p className="mt-2 text-sm text-slate-500 sm:text-base">جزئیات درخواست حمل و نقل</p>
              </div>
            </div>
            <PageNav backTo="/expert" backLabel="بازگشت به کنسول" showLogout logoutTo="/expert" className="flex-wrap lg:justify-end" />
          </div>
        </section>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-5">
          <TabsList className="flex h-auto w-full justify-start gap-2 rounded-3xl border border-slate-200 bg-white p-2 shadow-sm">
            <TabsTrigger
              value="details"
              className="rounded-2xl px-5 py-2 text-slate-600 data-[state=active]:bg-blue-600 data-[state=active]:text-white"
            >
              جزئیات
            </TabsTrigger>
            <TabsTrigger
              value="notes"
              className="rounded-2xl px-5 py-2 text-slate-600 data-[state=active]:bg-blue-600 data-[state=active]:text-white"
            >
              یادداشت‌ها
            </TabsTrigger>
          </TabsList>

          <TabsContent value="details" className="space-y-0">
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
              <main className="min-w-0 space-y-6">
                <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-3 text-lg text-slate-950">
                      <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
                        <User className="h-5 w-5" />
                      </span>
                      اطلاعات مشتری
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="grid gap-4 sm:grid-cols-2">
                    <InfoPanel icon={User} label="نام مشتری" value={displayValue(request.customer.full_name)} />
                    <InfoPanel icon={Phone} label="تلفن" value={displayValue(request.customer.phone)} ltr />
                  </CardContent>
                </Card>

                <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-3 text-lg text-slate-950">
                      <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">
                        <MapPin className="h-5 w-5" />
                      </span>
                      مسیر حمل
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-center">
                      {renderLocationBox("مبدا", request.route.origin, "origin")}
                      <div className="hidden h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-slate-500 md:flex">
                        <ArrowLeft className="h-5 w-5" />
                      </div>
                      {renderLocationBox("مقصد", request.route.destination, "destination")}
                    </div>

                    <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                      <div className="flex flex-wrap items-center gap-3">
                        <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-violet-50 text-violet-700">
                          <Truck className="h-5 w-5" />
                        </span>
                        <div>
                          <p className="text-xs text-slate-500">روش حمل</p>
                          <p className="font-semibold text-slate-900">{transportLabel}</p>
                        </div>
                        {request.transport_method_preference === "forwarder_suggestion" && (
                          <Badge className="rounded-full bg-blue-50 text-blue-700 hover:bg-blue-50">پیشنهاد فورواردر</Badge>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-3 text-lg text-slate-950">
                      <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-violet-50 text-violet-700">
                        <Package className="h-5 w-5" />
                      </span>
                      اطلاعات کالا
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                      <p className="text-xs text-slate-500">توضیحات</p>
                      <p className="mt-2 text-sm font-medium leading-7 text-slate-900">{displayValue(request.cargo.description)}</p>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-3">
                      <InfoPanel icon={Weight} label="وزن" value={request.cargo.weight ? `${request.cargo.weight} کیلوگرم` : missingValue} />
                      <InfoPanel icon={Package} label="حجم" value={request.cargo.volume ? `${request.cargo.volume} متر مکعب` : missingValue} />
                      <InfoPanel
                        icon={DollarSign}
                        label="ارزش"
                        value={request.cargo.value ? `${request.cargo.value.toLocaleString("fa-IR")} تومان` : missingValue}
                      />
                    </div>
                    <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                      <p className="text-xs text-slate-500">دستورالعمل‌های خاص</p>
                      <p className="mt-2 text-sm font-medium leading-7 text-slate-900">{displayValue(request.cargo.special_instructions)}</p>
                    </div>
                  </CardContent>
                </Card>
              </main>

              <aside className="min-w-0 space-y-6">
                <OperationsCard handleStatusChange={handleStatusChange} />
                <TimelineCard
                  timeline={request.timeline}
                  getActionLabel={getActionLabel}
                  getStatusLabel={getStatusLabel}
                />
                <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg text-slate-950">اطلاعات درخواست</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <InfoRow label="شماره پیگیری" value={request.tracking_number} />
                    <InfoRow label="تاریخ ثبت" value={formatDate(request.created_at)} />
                    <InfoRow label="مسئول" value={request.assigned_to?.name || missingValue} />
                    <InfoRow label="مهلت SLA" value={formatDate(request.sla_due_at)} />
                    <InfoRow label="وضعیت SLA" value={getSlaLabel(request.sla_status)} />
                  </CardContent>
                </Card>
              </aside>
            </div>
          </TabsContent>

          <TabsContent value="notes" className="space-y-5">
            <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-3 text-lg text-slate-950">
                  <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
                    <MessageSquare className="h-5 w-5" />
                  </span>
                  ثبت یادداشت
                </CardTitle>
                <p className="text-sm font-normal leading-6 text-slate-500">
                  یادداشت شخصی برای به‌روز نگه داشتن وضعیت؛ فقط برای خودتان ثبت می‌شود و در همین بخش نمایش داده می‌شود.
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-600">موضوع</label>
                  <Input
                    placeholder="موضوع یادداشت (اختیاری)"
                    value={newMessage.subject}
                    onChange={(event) => setNewMessage({ ...newMessage, subject: event.target.value })}
                    className="rounded-2xl bg-slate-50"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-600">محتوا</label>
                  <Textarea
                    placeholder="محتوای یادداشت..."
                    value={newMessage.content}
                    onChange={(event) => setNewMessage({ ...newMessage, content: event.target.value })}
                    rows={5}
                    className="rounded-2xl bg-slate-50"
                  />
                </div>
                <Button
                  onClick={handleSendMessage}
                  disabled={sendingMessage || !newMessage.content.trim()}
                  className="rounded-2xl bg-blue-600 hover:bg-blue-700"
                >
                  <Send className="ml-2 h-4 w-4" />
                  {sendingMessage ? "در حال ثبت..." : "ثبت یادداشت"}
                </Button>
              </CardContent>
            </Card>

            <div className="grid gap-4">
              {internalNotes.length === 0 ? (
                <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                  <CardContent className="p-8 text-center text-sm text-slate-500">هنوز یادداشتی ثبت نشده است.</CardContent>
                </Card>
              ) : (
                internalNotes.map((message) => (
                  <Card key={message.id} className="rounded-3xl border-slate-200 bg-white shadow-sm">
                    <CardContent className="p-5">
                      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                        <h4 className="font-semibold text-slate-950">{message.subject || "یادداشت"}</h4>
                        <span className="text-xs text-slate-500">{formatDate(message.created_at)}</span>
                      </div>
                      <p className="leading-7 text-slate-700">{message.content}</p>
                      <div className="mt-4 text-sm text-slate-500">توسط: {message.created_by}</div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

type InfoPanelProps = {
  icon: typeof User;
  label: string;
  value: string;
  ltr?: boolean;
};

const InfoPanel = ({ icon: Icon, label, value, ltr = false }: InfoPanelProps) => (
  <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
    <div className="mb-2 flex items-center gap-2 text-xs text-slate-500">
      <Icon className="h-4 w-4" />
      {label}
    </div>
    <p className="break-words text-sm font-semibold text-slate-900" dir={ltr ? "ltr" : "rtl"}>
      {value}
    </p>
  </div>
);

const InfoRow = ({ label, value }: { label: string; value: string }) => (
  <div className="flex items-start justify-between gap-4 rounded-2xl bg-slate-50 px-4 py-3">
    <span className="shrink-0 text-slate-500">{label}</span>
    <span className="min-w-0 break-words text-left font-medium text-slate-900">{value}</span>
  </div>
);

const OperationsCard = ({ handleStatusChange }: { handleStatusChange: (newStatus: string) => void }) => (
  <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
    <CardHeader className="pb-3">
      <CardTitle className="flex items-center gap-2 text-lg text-slate-950">
        <CheckCircle2 className="h-5 w-5 text-emerald-600" />
        عملیات
      </CardTitle>
    </CardHeader>
    <CardContent>
      <Select onValueChange={handleStatusChange}>
        <SelectTrigger className="rounded-2xl bg-slate-50">
          <SelectValue placeholder="تغییر وضعیت" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="in_progress">در حال بررسی</SelectItem>
          <SelectItem value="waiting_for_customer">منتظر مشتری</SelectItem>
          <SelectItem value="won">پذیرفته‌شده</SelectItem>
          <SelectItem value="lost">ردشده / از دست‌رفته</SelectItem>
          <SelectItem value="closed">بستن</SelectItem>
        </SelectContent>
      </Select>
    </CardContent>
  </Card>
);

const TimelineCard = ({
  timeline,
  getActionLabel,
  getStatusLabel,
}: {
  timeline: RequestDetail["timeline"];
  getActionLabel: (action: string) => string;
  getStatusLabel: (status: string) => string;
}) => (
  <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
    <CardHeader className="pb-3">
      <CardTitle className="flex items-center gap-2 text-lg text-slate-950">
        <Clock className="h-5 w-5 text-blue-600" />
        تایم‌لاین
      </CardTitle>
    </CardHeader>
    <CardContent>
      <div className="space-y-0">
        {timeline.map((event, index) => (
          <div key={event.id} className="grid grid-cols-[auto_1fr] gap-3">
            <div className="flex flex-col items-center">
              <div className="mt-1 h-3 w-3 rounded-full bg-blue-600 ring-4 ring-blue-50" />
              {index < timeline.length - 1 && <div className="mt-2 h-full min-h-12 w-px bg-slate-200" />}
            </div>
            <div className="pb-5">
              <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-slate-950">{getActionLabel(event.action)}</span>
                  {event.old_status && event.new_status && (
                    <Badge variant="outline" className="rounded-full bg-white">
                      {getStatusLabel(event.old_status)} ← {getStatusLabel(event.new_status)}
                    </Badge>
                  )}
                </div>
                {event.note && <p className="mb-2 text-sm leading-6 text-slate-600">{event.note}</p>}
                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  <span>{formatDate(event.created_at)}</span>
                  <span>•</span>
                  <span>{event.created_by}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </CardContent>
  </Card>
);

export default RequestDetail;
