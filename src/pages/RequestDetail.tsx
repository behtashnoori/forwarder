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
  Link2,
  Loader2,
  MapPin,
  MessageSquare,
  Package,
  Phone,
  Search,
  Send,
  Truck,
  Unlink,
  User,
  Weight,
  type LucideIcon,
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
import {
  addMessage,
  changeRequestStatus,
  fetchExpertRequestDetail,
  fetchShipmentRequestCustomerLink,
  linkShipmentRequestCustomer,
  searchCRMLinkCustomers,
  unlinkShipmentRequestCustomer,
  type CRMLinkCustomer,
  type CRMShipmentRequestLinkState,
} from "@/lib/api";
import { useI18n } from "@/i18n";

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
  route?: {
    origin?: {
      province?: string | null;
      county?: string | null;
      city?: string | null;
    };
    destination?: {
      province?: string | null;
      county?: string | null;
      city?: string | null;
    };
  };
  transport_method?: string;
  international_transport_method?: string;
  domestic_transport_method?: string;
  transport_method_preference?: string;
  cargo?: {
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

type RouteLocation = NonNullable<NonNullable<RequestDetail["route"]>["origin"]>;

const emptyLocation: RouteLocation = {};

const formatDateValue = (value: string | undefined, locale: string, fallback: string) =>
  value ? new Date(value).toLocaleDateString(locale) : fallback;
const displayValue = (value: string | number | null | undefined, fallback: string) => {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
};
const formatMeasurement = (value: number | null | undefined, unit: string, locale: string, fallback: string) => {
  if (value === null || value === undefined) return fallback;
  return `${value.toLocaleString(locale)} ${unit}`;
};
const formatMoney = (value: number | null | undefined, locale: string, fallback: string, unit: string) => {
  if (value === null || value === undefined) return fallback;
  return `${value.toLocaleString(locale)} ${unit}`;
};
const crmLinkAllowedRoles = new Set(["admin", "crm_manager", "supervisor", "business_expert"]);

const RequestDetail = () => {
  const { id } = useParams<{ id: string }>();
  const { toast } = useToast();
  const { actionLabel, locale, statusLabel, t, tf } = useI18n();
  const missingValue = t("common.notRegistered");

  const [request, setRequest] = useState<RequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("details");
  const [newMessage, setNewMessage] = useState({
    type: "internal_note",
    subject: "",
    content: "",
  });
  const [sendingMessage, setSendingMessage] = useState(false);
  const [crmLinkState, setCrmLinkState] = useState<CRMShipmentRequestLinkState | null>(null);
  const [crmLinkLoading, setCrmLinkLoading] = useState(false);
  const [crmSearch, setCrmSearch] = useState("");
  const [crmCandidates, setCrmCandidates] = useState<CRMLinkCustomer[]>([]);
  const [crmSearchLoading, setCrmSearchLoading] = useState(false);
  const [crmSaving, setCrmSaving] = useState(false);
  const [selectedCrmCustomerId, setSelectedCrmCustomerId] = useState<number | null>(null);
  const [crmLinkNote, setCrmLinkNote] = useState("");

  const storedExpert = useMemo(() => {
    try {
      const stored = localStorage.getItem("expert_user");
      if (stored) {
        return JSON.parse(stored) as { id?: number; role?: string };
      }
    } catch {
      // Ignore malformed stored expert data and fall back to the default expert id.
    }
    return null;
  }, []);
  const expertId = typeof storedExpert?.id === "number" ? storedExpert.id : 1;
  const canUseCrmLink = !!storedExpert?.role && crmLinkAllowedRoles.has(storedExpert.role);

  const loadRequestDetail = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchExpertRequestDetail(Number(id));
      setRequest(data);
    } catch (error) {
      toast({
        title: t("common.error"),
        description: t("requestDetail.fetchError"),
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [id, t, toast]);

  const loadCrmLinkState = useCallback(async () => {
    if (!id || !canUseCrmLink) return;
    try {
      setCrmLinkLoading(true);
      const data = await fetchShipmentRequestCustomerLink(Number(id));
      setCrmLinkState(data);
    } catch (error) {
      toast({
        title: "CRM",
        description: "وضعیت لینک مشتری CRM دریافت نشد",
        variant: "destructive",
      });
    } finally {
      setCrmLinkLoading(false);
    }
  }, [canUseCrmLink, id, toast]);

  useEffect(() => {
    if (id) {
      loadRequestDetail();
    }
  }, [id, loadRequestDetail]);

  useEffect(() => {
    if (id && canUseCrmLink) {
      loadCrmLinkState();
    }
  }, [canUseCrmLink, id, loadCrmLinkState]);

  const handleCrmCustomerSearch = async () => {
    if (!canUseCrmLink) return;
    try {
      setCrmSearchLoading(true);
      setSelectedCrmCustomerId(null);
      const data = await searchCRMLinkCustomers({
        search: crmSearch.trim() || undefined,
        per_page: 8,
      });
      setCrmCandidates(data.customers);
    } catch (error) {
      toast({
        title: "CRM",
        description: "جستجوی مشتری CRM انجام نشد",
        variant: "destructive",
      });
    } finally {
      setCrmSearchLoading(false);
    }
  };

  const handleCrmLink = async () => {
    if (!id || !selectedCrmCustomerId) return;
    try {
      setCrmSaving(true);
      const data = await linkShipmentRequestCustomer(Number(id), selectedCrmCustomerId, crmLinkNote);
      setCrmLinkState(data);
      setSelectedCrmCustomerId(null);
      setCrmLinkNote("");
      toast({
        title: "CRM",
        description: "مشتری CRM به درخواست لینک شد",
      });
    } catch (error) {
      toast({
        title: "CRM",
        description: "لینک مشتری CRM انجام نشد",
        variant: "destructive",
      });
    } finally {
      setCrmSaving(false);
    }
  };

  const handleCrmUnlink = async () => {
    if (!id) return;
    try {
      setCrmSaving(true);
      const data = await unlinkShipmentRequestCustomer(Number(id), crmLinkNote);
      setCrmLinkState(data);
      setCrmLinkNote("");
      toast({
        title: "CRM",
        description: "لینک مشتری CRM حذف شد",
      });
    } catch (error) {
      toast({
        title: "CRM",
        description: "حذف لینک مشتری CRM انجام نشد",
        variant: "destructive",
      });
    } finally {
      setCrmSaving(false);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    try {
      await changeRequestStatus(Number(id), newStatus, `تغییر وضعیت به ${newStatus}`);

      toast({
        title: t("common.success"),
        description: t("requestDetail.statusUpdated"),
      });

      setRequest((prev) => (prev ? { ...prev, status: newStatus } : null));

      setTimeout(() => {
        toast({
          title: t("common.success"),
          description: tf("requestDetail.redirected", { status: statusLabel(newStatus) }),
        });
      }, 1000);
    } catch (error) {
      toast({
        title: t("common.error"),
        description: t("requestDetail.changeStatusError"),
        variant: "destructive",
      });
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.content.trim()) {
      toast({
        title: t("common.error"),
        description: t("requestDetail.noteRequired"),
        variant: "destructive",
      });
      return;
    }

    try {
      setSendingMessage(true);
      await addMessage(Number(id), "internal_note", newMessage.content, newMessage.subject, expertId);

      toast({
        title: t("common.success"),
        description: t("requestDetail.noteSaved"),
      });

      setNewMessage({ type: "internal_note", subject: "", content: "" });
      loadRequestDetail();
    } catch (error) {
      toast({
        title: t("common.error"),
        description: t("requestDetail.noteError"),
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

  const transportLabel = useMemo(() => {
    if (!request) return missingValue;
    if (request.international_transport_method) return `${t("shipping.type.international")}: ${request.international_transport_method}`;
    if (request.domestic_transport_method) return `${t("shipping.type.domestic")}: ${request.domestic_transport_method}`;
    if (request.transport_method) return request.transport_method;
    return missingValue;
  }, [missingValue, request, t]);

  const renderLocationBox = (title: string, location: RouteLocation, tone: "origin" | "destination") => {
    const accent = tone === "origin" ? "bg-emerald-50 text-emerald-700 border-emerald-100" : "bg-blue-50 text-blue-700 border-blue-100";
    return (
      <div className={`rounded-2xl border p-4 ${accent}`}>
        <div className="mb-4 flex items-center gap-2">
          <MapPin className="h-5 w-5" />
          <h3 className="font-bold">{title}</h3>
        </div>
        <div className="space-y-3 text-sm">
          <InfoRow label={t("requestDetail.province")} value={displayValue(location.province, missingValue)} />
          <InfoRow label={t("requestDetail.county")} value={displayValue(location.county, missingValue)} />
          <InfoRow label={t("requestDetail.city")} value={displayValue(location.city, missingValue)} />
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
            <p className="text-slate-600">{t("requestDetail.loadingDetails")}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!request) {
    return (
      <div className="min-h-screen bg-slate-50 p-4 sm:p-6" dir="rtl">
        <div className="mx-auto max-w-7xl space-y-6">
          <PageNav backTo="/expert" backLabel={t("requestDetail.backToConsole")} showLogout logoutTo="/expert" />
          <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
            <CardContent className="flex flex-col items-center justify-center p-12 text-center">
              <AlertCircle className="mx-auto mb-4 h-12 w-12 text-slate-300" />
              <p className="text-slate-600">{t("requestDetail.notFound")}</p>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const internalNotes = request.messages.filter((message) => message.type === "internal_note");
  const cargo = request.cargo ?? {};
  const origin = request.route?.origin ?? emptyLocation;
  const destination = request.route?.destination ?? emptyLocation;

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
                    {statusLabel(request.status)}
                  </Badge>
                </div>
                <h1 className="break-words text-2xl font-bold text-slate-950 sm:text-3xl">{request.tracking_number}</h1>
                <p className="mt-2 text-sm text-slate-500 sm:text-base">{t("requestDetail.title")}</p>
              </div>
            </div>
            <PageNav backTo="/expert" backLabel={t("requestDetail.backToConsole")} showLogout logoutTo="/expert" className="flex-wrap lg:justify-end" />
          </div>
        </section>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-5">
          <TabsList className="flex h-auto w-full justify-start gap-2 rounded-3xl border border-slate-200 bg-white p-2 shadow-sm">
            <TabsTrigger
              value="details"
              className="rounded-2xl px-5 py-2 text-slate-600 data-[state=active]:bg-blue-600 data-[state=active]:text-white"
            >
              {t("common.details")}
            </TabsTrigger>
            <TabsTrigger
              value="notes"
              className="rounded-2xl px-5 py-2 text-slate-600 data-[state=active]:bg-blue-600 data-[state=active]:text-white"
            >
              {t("common.notes")}
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
                      {t("requestDetail.customerInfo")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="grid gap-4 sm:grid-cols-2">
                    <InfoPanel icon={User} label={t("common.customerName")} value={displayValue(request.customer.full_name, missingValue)} />
                    <InfoPanel icon={Phone} label={t("common.phone")} value={displayValue(request.customer.phone, missingValue)} ltr />
                  </CardContent>
                </Card>

                <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-3 text-lg text-slate-950">
                      <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">
                        <MapPin className="h-5 w-5" />
                      </span>
                      {t("requestDetail.transportRoute")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-center">
                      {renderLocationBox(t("common.origin"), origin, "origin")}
                      <div className="hidden h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-slate-500 md:flex">
                        <ArrowLeft className="h-5 w-5" />
                      </div>
                      {renderLocationBox(t("common.destination"), destination, "destination")}
                    </div>

                    <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                      <div className="flex flex-wrap items-center gap-3">
                        <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-violet-50 text-violet-700">
                          <Truck className="h-5 w-5" />
                        </span>
                        <div>
                          <p className="text-xs text-slate-500">{t("common.transportMethod")}</p>
                          <p className="font-semibold text-slate-900">{transportLabel}</p>
                        </div>
                        {request.transport_method_preference === "forwarder_suggestion" && (
                          <Badge className="rounded-full bg-blue-50 text-blue-700 hover:bg-blue-50">{t("requestFlow.forwarderSuggestion")}</Badge>
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
                      {t("requestDetail.cargoInfo")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                      <p className="text-xs text-slate-500">{t("common.description")}</p>
                      <p className="mt-2 text-sm font-medium leading-7 text-slate-900">{displayValue(cargo.description, missingValue)}</p>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-3">
                      <InfoPanel icon={Weight} label={t("requestDetail.weight")} value={formatMeasurement(cargo.weight, t("common.weightKg"), locale, missingValue)} />
                      <InfoPanel icon={Package} label={t("requestDetail.volume")} value={formatMeasurement(cargo.volume, t("common.volumeM3"), locale, missingValue)} />
                      <InfoPanel
                        icon={DollarSign}
                        label={t("common.value")}
                        value={formatMoney(cargo.value, locale, missingValue, t("requestDetail.moneyUnit"))}
                      />
                    </div>
                    <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                      <p className="text-xs text-slate-500">{t("common.specialInstructions")}</p>
                      <p className="mt-2 text-sm font-medium leading-7 text-slate-900">{displayValue(cargo.special_instructions, missingValue)}</p>
                    </div>
                  </CardContent>
                </Card>
              </main>

              <aside className="min-w-0 space-y-6">
                <CrmCustomerLinkCard
                  canUseCrmLink={canUseCrmLink}
                  candidates={crmCandidates}
                  linkState={crmLinkState}
                  loading={crmLinkLoading}
                  note={crmLinkNote}
                  onLink={handleCrmLink}
                  onNoteChange={setCrmLinkNote}
                  onSearch={handleCrmCustomerSearch}
                  onSearchChange={setCrmSearch}
                  onSelectCustomer={setSelectedCrmCustomerId}
                  onUnlink={handleCrmUnlink}
                  saving={crmSaving}
                  search={crmSearch}
                  searchLoading={crmSearchLoading}
                  selectedCustomerId={selectedCrmCustomerId}
                />
                <OperationsCard handleStatusChange={handleStatusChange} statusLabel={statusLabel} t={t} />
                <TimelineCard
                  timeline={request.timeline}
                  actionLabel={actionLabel}
                  formatDate={(value) => formatDateValue(value, locale, missingValue)}
                  statusLabel={statusLabel}
                  t={t}
                />
                <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg text-slate-950">{t("publicTracking.requestInfo")}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <InfoRow label={t("common.trackingNumber")} value={request.tracking_number} />
                    <InfoRow label={t("common.createdAt")} value={formatDateValue(request.created_at, locale, missingValue)} />
                    <InfoRow label={t("requestDetail.assignee")} value={request.assigned_to?.name || missingValue} />
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
                  {t("requestDetail.addNote")}
                </CardTitle>
                <p className="text-sm font-normal leading-6 text-slate-500">
                  {t("requestDetail.noteHint")}
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-600">{t("common.subject")}</label>
                  <Input
                    placeholder={t("requestDetail.subjectPlaceholder")}
                    value={newMessage.subject}
                    onChange={(event) => setNewMessage({ ...newMessage, subject: event.target.value })}
                    className="rounded-2xl bg-slate-50"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-600">{t("common.content")}</label>
                  <Textarea
                    placeholder={t("requestDetail.contentPlaceholder")}
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
                  {sendingMessage ? t("requestDetail.saving") : t("requestDetail.addNote")}
                </Button>
              </CardContent>
            </Card>

            <div className="grid gap-4">
              {internalNotes.length === 0 ? (
                <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                  <CardContent className="p-8 text-center text-sm text-slate-500">{t("requestDetail.noNotes")}</CardContent>
                </Card>
              ) : (
                internalNotes.map((message) => (
                  <Card key={message.id} className="rounded-3xl border-slate-200 bg-white shadow-sm">
                    <CardContent className="p-5">
                      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                        <h4 className="font-semibold text-slate-950">{message.subject || t("action.note")}</h4>
                        <span className="text-xs text-slate-500">{formatDateValue(message.created_at, locale, missingValue)}</span>
                      </div>
                      <p className="leading-7 text-slate-700">{message.content}</p>
                      <div className="mt-4 text-sm text-slate-500">{t("requestDetail.by")}: {message.created_by}</div>
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
  icon: LucideIcon;
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

const CrmCustomerLinkCard = ({
  canUseCrmLink,
  candidates,
  linkState,
  loading,
  note,
  onLink,
  onNoteChange,
  onSearch,
  onSearchChange,
  onSelectCustomer,
  onUnlink,
  saving,
  search,
  searchLoading,
  selectedCustomerId,
}: {
  canUseCrmLink: boolean;
  candidates: CRMLinkCustomer[];
  linkState: CRMShipmentRequestLinkState | null;
  loading: boolean;
  note: string;
  onLink: () => void;
  onNoteChange: (value: string) => void;
  onSearch: () => void;
  onSearchChange: (value: string) => void;
  onSelectCustomer: (customerId: number) => void;
  onUnlink: () => void;
  saving: boolean;
  search: string;
  searchLoading: boolean;
  selectedCustomerId: number | null;
}) => {
  const linkedCustomer = linkState?.customer ?? null;
  const isRelinking = !!linkedCustomer && !!selectedCustomerId && selectedCustomerId !== linkedCustomer.id;

  return (
    <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg text-slate-950">
          <Link2 className="h-5 w-5 text-blue-600" />
          لینک مشتری CRM
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!canUseCrmLink ? (
          <div className="rounded-2xl border border-amber-100 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
            دسترسی لینک CRM برای نقش فعلی فعال نیست.
          </div>
        ) : loading ? (
          <div className="flex items-center gap-2 rounded-2xl border border-slate-100 bg-slate-50 p-4 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            در حال دریافت وضعیت لینک CRM
          </div>
        ) : (
          <>
            <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
              <p className="mb-3 text-xs text-slate-500">وضعیت فعلی</p>
              {linkedCustomer ? (
                <div className="space-y-3">
                  <div>
                    <p className="font-semibold text-slate-950">{linkedCustomer.name}</p>
                    <p className="text-sm text-slate-600">{linkedCustomer.company_name || "شرکت ثبت نشده"}</p>
                  </div>
                  <div className="grid gap-2 text-sm text-slate-600">
                    <InfoRow label="تلفن" value={linkedCustomer.phone || linkedCustomer.mobile || "ثبت نشده"} />
                    <InfoRow label="ایمیل" value={linkedCustomer.email || "ثبت نشده"} />
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={onUnlink}
                    disabled={saving}
                    className="w-full rounded-2xl border-red-200 text-red-700 hover:bg-red-50 hover:text-red-800"
                  >
                    {saving ? <Loader2 className="ml-2 h-4 w-4 animate-spin" /> : <Unlink className="ml-2 h-4 w-4" />}
                    حذف لینک CRM
                  </Button>
                </div>
              ) : (
                <p className="text-sm leading-6 text-slate-600">این درخواست هنوز به مشتری CRM لینک نشده است.</p>
              )}
            </div>

            <div className="space-y-3">
              <div className="flex gap-2">
                <Input
                  value={search}
                  onChange={(event) => onSearchChange(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      onSearch();
                    }
                  }}
                  placeholder="جستجوی نام، شرکت، تلفن یا ایمیل"
                  className="rounded-2xl bg-slate-50"
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={onSearch}
                  disabled={searchLoading || saving}
                  className="shrink-0 rounded-2xl"
                  aria-label="جستجوی مشتری CRM"
                >
                  {searchLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                </Button>
              </div>

              {candidates.length > 0 && (
                <div className="space-y-2">
                  {candidates.map((customer) => {
                    const selected = selectedCustomerId === customer.id;
                    return (
                      <button
                        key={customer.id}
                        type="button"
                        onClick={() => onSelectCustomer(customer.id)}
                        className={`w-full rounded-2xl border p-3 text-right transition ${
                          selected
                            ? "border-blue-300 bg-blue-50 text-blue-950"
                            : "border-slate-100 bg-white text-slate-800 hover:border-slate-200 hover:bg-slate-50"
                        }`}
                      >
                        <span className="block text-sm font-semibold">{customer.name}</span>
                        <span className="mt-1 block text-xs text-slate-500">
                          {customer.company_name || "بدون شرکت"} · {customer.phone || customer.mobile || "بدون تلفن"}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}

              <Textarea
                value={note}
                onChange={(event) => onNoteChange(event.target.value)}
                rows={2}
                placeholder="یادداشت لینک CRM (اختیاری)"
                className="rounded-2xl bg-slate-50"
              />

              {isRelinking && (
                <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-800">
                  این درخواست از قبل به یک مشتری CRM لینک شده است. با ادامه، لینک قبلی فقط به مشتری انتخاب‌شده تغییر می‌کند و وضعیت عملیاتی درخواست تغییر نمی‌کند.
                </div>
              )}

              <Button
                type="button"
                onClick={onLink}
                disabled={!selectedCustomerId || saving}
                className="w-full rounded-2xl bg-blue-600 hover:bg-blue-700"
              >
                {saving ? <Loader2 className="ml-2 h-4 w-4 animate-spin" /> : <Link2 className="ml-2 h-4 w-4" />}
                {isRelinking ? "تغییر لینک به مشتری انتخاب‌شده" : "لینک به مشتری انتخاب‌شده"}
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
};

const OperationsCard = ({
  handleStatusChange,
  statusLabel,
  t,
}: {
  handleStatusChange: (newStatus: string) => void;
  statusLabel: (status: string) => string;
  t: ReturnType<typeof useI18n>["t"];
}) => (
  <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
    <CardHeader className="pb-3">
      <CardTitle className="flex items-center gap-2 text-lg text-slate-950">
        <CheckCircle2 className="h-5 w-5 text-emerald-600" />
        {t("requestDetail.operations")}
      </CardTitle>
    </CardHeader>
    <CardContent>
      <p className="mb-3 text-sm leading-6 text-slate-500">
        {t("requestDetail.operationsHint")}
      </p>
      <Select onValueChange={handleStatusChange}>
        <SelectTrigger className="rounded-2xl bg-slate-50">
          <SelectValue placeholder={t("requestDetail.changeStatus")} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="in_progress">{statusLabel("in_progress")}</SelectItem>
          <SelectItem value="waiting_for_customer">{statusLabel("waiting_for_customer")}</SelectItem>
          <SelectItem value="won">{statusLabel("won")}</SelectItem>
          <SelectItem value="lost">{t("status.rejectedOrLost")}</SelectItem>
          <SelectItem value="closed">{t("requestDetail.close")}</SelectItem>
        </SelectContent>
      </Select>
    </CardContent>
  </Card>
);

const TimelineCard = ({
  timeline,
  actionLabel,
  formatDate,
  statusLabel,
  t,
}: {
  timeline: RequestDetail["timeline"];
  actionLabel: (action: string) => string;
  formatDate: (value: string) => string;
  statusLabel: (status: string) => string;
  t: ReturnType<typeof useI18n>["t"];
}) => (
  <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
    <CardHeader className="pb-3">
      <CardTitle className="flex items-center gap-2 text-lg text-slate-950">
        <Clock className="h-5 w-5 text-blue-600" />
        {t("requestDetail.timeline")}
      </CardTitle>
    </CardHeader>
    <CardContent>
      {timeline.length === 0 ? (
        <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4 text-sm text-slate-500">{t("requestDetail.noEvents")}</div>
      ) : (
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
                    <span className="text-sm font-semibold text-slate-950">{actionLabel(event.action)}</span>
                    {event.old_status && event.new_status && (
                      <Badge variant="outline" className="rounded-full bg-white">
                        {statusLabel(event.old_status)} ← {statusLabel(event.new_status)}
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
      )}
    </CardContent>
  </Card>
);

export default RequestDetail;
