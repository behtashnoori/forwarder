import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router";
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
  Plus,
  Search,
  Send,
  Truck,
  User,
  Weight,
  type LucideIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import PageNav from "@/components/PageNav";
import OperationsNav from "@/components/OperationsNav";
import OperationalAnyPermission from "@/components/OperationalAnyPermission";
import CaseDocumentsTab from "@/components/CaseDocumentsTab";
import CommercialProgress, {
  type CommercialProgressStep,
} from "@/components/CommercialProgress";
import RequestCargoSummary from "@/components/RequestCargoSummary";
import { QuoteModal } from "@/components/QuoteModal";
import OperationalEventLocationSelector, {
  type OperationalEventLocation,
} from "@/components/OperationalEventLocationSelector";
import { useToast } from "@/hooks/use-toast";
import {
  formatMoney as formatBusinessMoney,
  formatQuantity,
  formatQuoteMoney,
} from "@/lib/formatQuantity";
import {
  addMessage,
  addTrackingUnitUpdate,
  changeRequestStatus,
  fetchExpertRequestDetail,
  fetchRequestOrganizationCustomer,
  fetchTrackingManagement,
  enableTrackingManagement,
  updateTrackingUnitMetadata,
  linkRequestOrganizationCustomer,
  listOperationalShipments,
  searchRequestOrganizationCustomers,
  type RequestCommercialProjection,
  type RequestOrganizationCustomer,
  type RequestOrganizationCustomerState,
  type TrackingManagementData,
  type OperationalShipmentSummary,
  type RequestCargoItem,
} from "@/lib/api";
import { useI18n } from "@/i18n";
import {
  localDateTimeInputToUtc,
  toLocalDateTimeInputValue,
} from "@/lib/localDateTime";
import {
  formatDualCalendarDate,
  formatDualCalendarInstant,
} from "@/lib/dualCalendar";
import { getRequestTransportMethod } from "@/lib/transportPresentation";

interface RequestDetail {
  id: number;
  public_id: string;
  tracking_number: string;
  status: string;
  priority: string;
  created_at: string;
  sla_due_at?: string;
  sla_status: "on_time" | "due_soon" | "overdue";
  assigned_to?: {
    id: number;
    name: string;
  };
  customer: {
    first_name?: string;
    last_name?: string;
    phone: string;
    full_name: string;
  };
  route?: {
    shipping_type?: string;
    origin?: {
      province?: string | null;
      county?: string | null;
      city?: string | null;
      country?: string | null;
      international_city?: string | null;
      address?: string | null;
    };
    destination?: {
      province?: string | null;
      county?: string | null;
      city?: string | null;
      country?: string | null;
      international_city?: string | null;
      address?: string | null;
    };
    iran_destination?: {
      type?: string | null;
      label?: string | null;
      province?: string | null;
    } | null;
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
  cargo_items?: RequestCargoItem[];
  dates: {
    pickup_date?: string;
    delivery_date?: string;
  };
  timeline: Array<{
    id: number;
    action: string;
    title: string;
    description?: string | null;
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
  commercial: RequestCommercialProjection;
  latest_quote?: {
    id: number;
    public_id: string;
    amount: number;
    currency: string;
    note?: string | null;
    valid_until?: string | null;
    created_at: string;
    created_by?: string | null;
    customer_response?: "accepted" | "discussion" | "declined" | null;
    customer_response_message?: string | null;
    responded_at?: string | null;
  } | null;
  quote_history?: Array<{
    id: number;
    public_id: string;
    amount: number;
    currency: string;
    note?: string | null;
    valid_until?: string | null;
    created_at: string;
    created_by?: string | null;
    customer_response?: "accepted" | "discussion" | "declined" | null;
    customer_response_message?: string | null;
    responded_at?: string | null;
  }>;
}

type RouteLocation = NonNullable<NonNullable<RequestDetail["route"]>["origin"]>;

const emptyLocation: RouteLocation = {};

const formatDateValue = (
  value: string | undefined,
  locale: string,
  fallback: string,
) => formatDualCalendarInstant(value, locale, { fallback, includeTime: false });
const displayValue = (
  value: string | number | null | undefined,
  fallback: string,
) => {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
};
const formatMeasurement = (
  value: number | null | undefined,
  unit: string,
  locale: string,
  fallback: string,
) => {
  const quantity = formatQuantity(value, locale, fallback);
  return quantity === fallback ? fallback : `${quantity} ${unit}`;
};
const formatMoney = (
  value: number | null | undefined,
  locale: string,
  fallback: string,
  unit: string,
) => {
  return formatBusinessMoney(value, unit, locale, fallback);
};
const customerResponseLabel = (
  response: RequestCommercialProjection["latest_quote_response"],
  hasQuote: boolean,
) => {
  if (response === "accepted") return "پیشنهاد پذیرفته شده است";
  if (response === "discussion") return "مشتری درخواست مذاکره کرده است";
  if (response === "declined") return "پیشنهاد رد شده است";
  return hasQuote ? "هنوز پاسخی ثبت نشده است" : "هنوز پیشنهادی ارسال نشده است";
};
const RequestDetail = () => {
  const { id } = useParams<{ id: string }>();
  const { toast } = useToast();
  const { locale, statusLabel, t, tf, transportLabel } = useI18n();
  const missingValue = t("common.notRegistered");

  const [request, setRequest] = useState<RequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [quoteModalOpen, setQuoteModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("details");
  const [newMessage, setNewMessage] = useState({
    type: "internal_note",
    subject: "",
    content: "",
  });
  const [sendingMessage, setSendingMessage] = useState(false);
  const [organizationCustomerState, setOrganizationCustomerState] =
    useState<RequestOrganizationCustomerState | null>(null);
  const [organizationCustomerLoading, setOrganizationCustomerLoading] =
    useState(false);
  const [organizationCustomerError, setOrganizationCustomerError] = useState<
    string | null
  >(null);
  const [organizationCustomerSearch, setOrganizationCustomerSearch] =
    useState("");
  const [organizationCustomerCandidates, setOrganizationCustomerCandidates] =
    useState<RequestOrganizationCustomer[]>([]);
  const [
    organizationCustomerSearchLoading,
    setOrganizationCustomerSearchLoading,
  ] = useState(false);
  const [
    organizationCustomerSearchComplete,
    setOrganizationCustomerSearchComplete,
  ] = useState(false);
  const [organizationCustomerSaving, setOrganizationCustomerSaving] =
    useState(false);
  const [selectedOrganizationCustomerId, setSelectedOrganizationCustomerId] =
    useState<number | null>(null);
  const [operationalShipments, setOperationalShipments] = useState<
    OperationalShipmentSummary[]
  >([]);

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

  const loadRequestDetail = useCallback(async () => {
    try {
      setLoading(true);
      if (!id) return;
      const data = await fetchExpertRequestDetail(id);
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

  const loadOrganizationCustomer = useCallback(
    async (requestPublicId: string) => {
      try {
        setOrganizationCustomerLoading(true);
        setOrganizationCustomerError(null);
        const data = await fetchRequestOrganizationCustomer(requestPublicId);
        setOrganizationCustomerState(data);
      } catch {
        setOrganizationCustomerState(null);
        setOrganizationCustomerError("اطلاعات مشتری سازمان در دسترس نیست.");
      } finally {
        setOrganizationCustomerLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (id) {
      loadRequestDetail();
    }
  }, [id, loadRequestDetail]);

  useEffect(() => {
    if (!request) return;
    listOperationalShipments(
      new URLSearchParams({
        request_public_id: request.public_id,
        per_page: "100",
      }).toString(),
    )
      .then((result) => setOperationalShipments(result.data))
      .catch(() => setOperationalShipments([]));
  }, [request]);

  useEffect(() => {
    if (request?.public_id) {
      void loadOrganizationCustomer(request.public_id);
    }
  }, [loadOrganizationCustomer, request?.public_id]);

  const handleOrganizationCustomerSearch = async () => {
    if (!request) return;
    try {
      setOrganizationCustomerSearchLoading(true);
      setOrganizationCustomerSearchComplete(false);
      setSelectedOrganizationCustomerId(null);
      setOrganizationCustomerError(null);
      const data = await searchRequestOrganizationCustomers(request.public_id, {
        search: organizationCustomerSearch.trim() || undefined,
        per_page: 8,
      });
      setOrganizationCustomerCandidates(data.customers);
    } catch {
      setOrganizationCustomerCandidates([]);
      setOrganizationCustomerError("جستجوی مشتری سازمان انجام نشد.");
    } finally {
      setOrganizationCustomerSearchLoading(false);
      setOrganizationCustomerSearchComplete(true);
    }
  };

  const handleOrganizationCustomerLink = async () => {
    if (!request || !selectedOrganizationCustomerId) return;
    try {
      setOrganizationCustomerSaving(true);
      setOrganizationCustomerError(null);
      const data = await linkRequestOrganizationCustomer(
        request.public_id,
        selectedOrganizationCustomerId,
      );
      setOrganizationCustomerState(data);
      setSelectedOrganizationCustomerId(null);
      setOrganizationCustomerCandidates([]);
      setOrganizationCustomerSearchComplete(false);
      toast({
        title: "مشتری سازمان",
        description:
          data.operation === "relink"
            ? "مشتری سازمان این درخواست تغییر کرد."
            : "مشتری سازمان به درخواست متصل شد.",
      });
      await loadRequestDetail();
    } catch {
      setOrganizationCustomerError("اتصال مشتری سازمان انجام نشد.");
    } finally {
      setOrganizationCustomerSaving(false);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    try {
      if (!id) return;
      await changeRequestStatus(id, newStatus, `تغییر وضعیت به ${newStatus}`);

      toast({
        title: t("common.success"),
        description: t("requestDetail.statusUpdated"),
      });

      await loadRequestDetail();

      setTimeout(() => {
        toast({
          title: t("common.success"),
          description: tf("requestDetail.redirected", {
            status: statusLabel(newStatus),
          }),
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
      if (!id) return;
      await addMessage(
        id,
        "internal_note",
        newMessage.content,
        newMessage.subject,
        expertId,
      );

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

  const requestTransportLabel = useMemo(() => {
    const method = getRequestTransportMethod({
      shipping_type: request?.route?.shipping_type,
      transport_method: request?.transport_method,
      international_transport_method: request?.international_transport_method,
      domestic_transport_method: request?.domestic_transport_method,
      transport_method_preference: request?.transport_method_preference,
    });
    return method ? transportLabel(method) : t("transport.requestMissing");
  }, [request, t, transportLabel]);

  const renderLocationBox = (
    title: string,
    location: RouteLocation,
    tone: "origin" | "destination",
  ) => {
    const accent =
      tone === "origin"
        ? "bg-emerald-50 text-emerald-700 border-emerald-100"
        : "bg-blue-50 text-blue-700 border-blue-100";
    const isInternational = request?.route?.shipping_type === "international";
    return (
      <div className={`rounded-2xl border p-4 ${accent}`}>
        <div className="mb-4 flex items-center gap-2">
          <MapPin className="h-5 w-5" />
          <h3 className="font-bold">{title}</h3>
        </div>
        <div className="space-y-3 text-sm">
          {isInternational ? (
            <>
              <InfoRow
                label={t("requestDetail.country")}
                value={displayValue(location.country, missingValue)}
              />
              <InfoRow
                label={t("requestDetail.cityPort")}
                value={displayValue(location.international_city, missingValue)}
              />
              {location.address ? (
                <InfoRow
                  label={t("requestDetail.address")}
                  value={displayValue(location.address, missingValue)}
                />
              ) : null}
            </>
          ) : (
            <>
              <InfoRow
                label={t("requestDetail.province")}
                value={displayValue(location.province, missingValue)}
              />
              <InfoRow
                label={t("requestDetail.county")}
                value={displayValue(location.county, missingValue)}
              />
              <InfoRow
                label={t("requestDetail.city")}
                value={displayValue(location.city, missingValue)}
              />
            </>
          )}
        </div>
      </div>
    );
  };

  const renderIranDestinationBox = () => {
    const iranDest = request?.route?.iran_destination;
    if (!iranDest?.type) {
      return null;
    }
    const typeLabel =
      iranDest.type === "port"
        ? t("requestDetail.iranDestTypePort")
        : iranDest.type === "customs"
          ? t("requestDetail.iranDestTypeCustoms")
          : t("requestDetail.iranDestTypeCity");
    const icon =
      iranDest.type === "port"
        ? "🚢"
        : iranDest.type === "customs"
          ? "🛃"
          : "🏙️";
    return (
      <div className="rounded-2xl border border-amber-100 bg-amber-50 p-4 text-amber-800">
        <div className="mb-4 flex items-center gap-2">
          <MapPin className="h-5 w-5" />
          <h3 className="font-bold">
            {t("requestDetail.iranDestinationTitle")}
          </h3>
        </div>
        <div className="space-y-3 text-sm">
          <InfoRow
            label={t("requestDetail.pointType")}
            value={`${icon} ${typeLabel}`}
          />
          <InfoRow
            label={t("requestDetail.cityPort")}
            value={displayValue(iranDest.label, missingValue)}
          />
          <InfoRow
            label={t("requestDetail.province")}
            value={displayValue(iranDest.province, missingValue)}
          />
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-slate-50"
        dir="rtl"
      >
        <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
          <CardContent className="flex flex-col items-center gap-4 p-10 text-center">
            <div className="rounded-2xl bg-blue-50 p-4">
              <Clock className="h-8 w-8 animate-spin text-blue-600" />
            </div>
            <p className="text-slate-600">
              {t("requestDetail.loadingDetails")}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!request) {
    return (
      <div className="min-h-screen bg-slate-50 p-4 sm:p-6" dir="rtl">
        <div className="mx-auto max-w-7xl space-y-6">
          <PageNav
            backTo="/expert"
            backLabel={t("requestDetail.backToConsole")}
            showLogout
            logoutTo="/expert"
          />
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

  const internalNotes = request.messages.filter(
    (message) => message.type === "internal_note",
  );
  const latestQuoteAlreadyConverted = request.latest_quote
    ? operationalShipments.some(
        (shipment) =>
          shipment.source.accepted_quote_id === request.latest_quote?.id,
      )
    : false;
  const cargo = request.cargo ?? {};
  const hasLegacyCargo = Object.values(cargo).some(
    (value) => value != null && value !== "",
  );
  const origin = request.route?.origin ?? emptyLocation;
  const destination = request.route?.destination ?? emptyLocation;
  const terminalCommercialState = ["won", "lost", "closed"].includes(
    request.status,
  );
  const quoteResponse = request.latest_quote?.customer_response ?? null;
  const scrollToCommercialSection = (id: string) => {
    setActiveTab("details");
    requestAnimationFrame(() =>
      document
        .getElementById(id)
        ?.scrollIntoView({ behavior: "smooth", block: "start" }),
    );
  };
  const commercialSteps: CommercialProgressStep[] = [
    {
      label: "ثبت درخواست",
      state: "complete",
      detail: "درخواست و کد پیگیری ثبت شده‌اند.",
    },
    {
      label: "تخصیص کارشناس",
      state: request.assigned_to
        ? "complete"
        : terminalCommercialState
          ? "not_applicable"
          : "current",
      detail: request.assigned_to?.name || "در انتظار تخصیص کارشناس",
    },
    {
      label: "آماده‌سازی پیشنهاد",
      state: request.latest_quote
        ? "complete"
        : terminalCommercialState
          ? "not_applicable"
          : request.assigned_to
            ? "current"
            : "pending",
      detail: request.latest_quote
        ? "آخرین پیشنهاد در همین صفحه قابل مشاهده است."
        : "هنوز پیشنهادی ثبت نشده است.",
    },
    {
      label: "پاسخ مشتری",
      state: quoteResponse
        ? "complete"
        : terminalCommercialState
          ? "not_applicable"
          : request.latest_quote
            ? "current"
            : "pending",
      detail: customerResponseLabel(
        request.commercial.latest_quote_response,
        !!request.latest_quote,
      ),
    },
    {
      label: "جمع‌بندی تجاری",
      state: terminalCommercialState
        ? "complete"
        : quoteResponse
          ? "current"
          : "pending",
      detail: terminalCommercialState
        ? request.commercial.request_status_label_fa
        : "پس از بررسی پاسخ مشتری، نتیجه به‌صورت صریح ثبت می‌شود.",
    },
  ];
  const commercialAction = (() => {
    if (operationalShipments.length > 0) {
      return (
        <Button asChild variant="secondary">
          <Link
            to={`/operations/shipments/${operationalShipments[0].public_id}`}
          >
            مشاهده محموله عملیاتی
          </Link>
        </Button>
      );
    }
    if (
      request.status === "won" &&
      quoteResponse === "accepted" &&
      request.latest_quote &&
      !latestQuoteAlreadyConverted
    ) {
      if (!organizationCustomerState?.customer) {
        return (
          <Button
            variant="secondary"
            onClick={() => scrollToCommercialSection("organization-customer")}
          >
            انتخاب مشتری سازمان
          </Button>
        );
      }
      return (
        <OperationalAnyPermission
          permissions={[
            "operational_shipment.create_from_quote",
            "operational_shipment.create",
          ]}
          fallback={
            <p className="text-sm text-blue-50">
              مجوز ایجاد محموله از پیشنهاد پذیرفته‌شده در دسترس نیست.
            </p>
          }
        >
          <Button asChild variant="secondary">
            <Link
              to={`/operations/shipments/new?source=accepted_quote&accepted_quote_id=${request.latest_quote.id}&request_ref=${encodeURIComponent(request.tracking_number)}`}
            >
              ایجاد محموله عملیاتی
            </Link>
          </Button>
        </OperationalAnyPermission>
      );
    }
    switch (request.commercial.next_action.code) {
      case "expert_review_negotiation":
        return (
          <Button variant="secondary" onClick={() => setQuoteModalOpen(true)}>
            بازنگری پیشنهاد
          </Button>
        );
      case "expert_continue_review":
        return (
          <Button variant="secondary" onClick={() => setQuoteModalOpen(true)}>
            آماده‌سازی پیشنهاد
          </Button>
        );
      case "expert_finalize_accepted":
      case "expert_conclude_declined":
        return (
          <Button
            variant="secondary"
            onClick={() => scrollToCommercialSection("commercial-conclusion")}
          >
            ثبت جمع‌بندی تجاری
          </Button>
        );
      case "expert_review_request":
        return (
          <Button
            variant="secondary"
            onClick={() => scrollToCommercialSection("request-facts")}
          >
            بررسی اطلاعات درخواست
          </Button>
        );
      default:
        return undefined;
    }
  })();
  const commercialActionDescription =
    operationalShipments.length > 0
      ? "محموله عملیاتی ایجاد شده است؛ ادامه کار در فضای عملیات انجام می‌شود."
      : request.status === "won" &&
          quoteResponse === "accepted" &&
          !latestQuoteAlreadyConverted
        ? organizationCustomerState?.customer
          ? "پیشنهاد پذیرفته و جمع‌بندی تجاری ثبت شده است. ایجاد محموله یک اقدام صریح و کنترل‌شده است."
          : "پیش از ایجاد محموله، مشتری سازمان این درخواست را مشخص کنید."
        : request.commercial.next_action.code === "waiting_for_customer"
          ? "پیشنهاد ارسال شده است؛ تا دریافت پاسخ مشتری نیازی به اقدام دیگری نیست."
          : terminalCommercialState
            ? "نتیجه تجاری ثبت شده و اقدام تجاری دیگری برای این درخواست باز نیست."
            : "اقدام پیشنهادی از وضعیت ثبت‌شده درخواست و آخرین پاسخ مشتری استخراج شده است.";

  return (
    <div className="min-h-screen bg-slate-50" dir="rtl">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
        <OperationsNav />
        <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm lg:p-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex min-w-0 items-start gap-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-sm">
                <FileText className="h-7 w-7" />
              </div>
              <div className="min-w-0">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <Badge
                    variant="outline"
                    className={`rounded-full px-3 py-1 ${getStatusColor(request.status)}`}
                  >
                    {request.commercial.request_status_label_fa}
                  </Badge>
                </div>
                <h1 className="break-words text-2xl font-bold text-slate-950 sm:text-3xl">
                  {request.tracking_number}
                </h1>
                <p className="mt-2 text-sm text-slate-500 sm:text-base">
                  {t("requestDetail.title")}
                </p>
              </div>
            </div>
            <PageNav
              backTo="/expert"
              backLabel={t("requestDetail.backToConsole")}
              showLogout
              logoutTo="/expert"
              className="flex-wrap lg:justify-end"
            />
          </div>
        </section>

        <CommercialProgress
          title="از درخواست تا جمع‌بندی تجاری"
          facts={[
            { label: "کد پیگیری", value: request.tracking_number, ltr: true },
            {
              label: "مشتری",
              value: request.customer.full_name || missingValue,
            },
            {
              label: "کارشناس",
              value: request.assigned_to?.name || "در انتظار تخصیص",
            },
            {
              label: "وضعیت درخواست",
              value: request.commercial.request_status_label_fa,
            },
            {
              label: "وضعیت پیشنهاد",
              value: customerResponseLabel(
                request.commercial.latest_quote_response,
                !!request.latest_quote,
              ),
            },
          ]}
          steps={commercialSteps}
          nextAction={
            operationalShipments.length > 0
              ? "ادامه در فضای عملیات"
              : request.commercial.next_action.label_fa
          }
          nextActionDescription={commercialActionDescription}
          action={commercialAction}
        />

        <details
          open={operationalShipments.length > 0}
          className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <summary className="cursor-pointer font-bold text-slate-950">
            دسترسی به پروژه و عملیات (
            {operationalShipments.length.toLocaleString("fa-IR")})
          </summary>
          <div className="mt-4 space-y-2">
            {operationalShipments.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                هنوز محموله عملیاتی از این درخواست ایجاد نشده است. پس از پذیرش
                پیشنهاد و جمع‌بندی تجاری، ساخت عملیات از همین صفحه در دسترس قرار
                می‌گیرد.
              </p>
            ) : (
              operationalShipments.map((shipment) => {
                const projection = shipment.operational_projection;
                const route = shipment.route_summary
                  ? `${shipment.route_summary.origin.display_name} ← ${shipment.route_summary.destination.display_name}`
                  : shipment.route_leg
                    ? `${shipment.route_leg.origin.display_name} ← ${shipment.route_leg.destination.display_name}`
                    : "مسیر عملیاتی هنوز تعریف نشده";
                return (
                  <Link
                    key={shipment.public_id}
                    className="block rounded-xl border p-3 hover:border-blue-300 hover:bg-blue-50/40"
                    to={`/operations/shipments/${shipment.public_id}`}
                  >
                    <strong>
                      {projection?.identity.label || "محموله عملیاتی"}
                    </strong>
                    <p className="mt-1 text-sm">
                      {route} ·{" "}
                      {projection?.stage_progress.current?.display_name_fa ||
                        "مرحله نامشخص"}
                    </p>
                    {projection?.recommended_action && (
                      <p className="mt-1 text-xs font-bold text-blue-800">
                        اقدام بعدی: {projection.recommended_action.label}
                      </p>
                    )}
                  </Link>
                );
              })
            )}
          </div>
        </details>
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="space-y-5"
        >
          <TabsList className="flex h-auto w-full flex-wrap justify-start gap-2 rounded-3xl border border-slate-200 bg-white p-2 shadow-sm">
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
            <TabsTrigger
              value="tracking"
              className="rounded-2xl px-5 py-2 text-slate-600 data-[state=active]:bg-blue-600 data-[state=active]:text-white"
            >
              {t("multiTracking.internalTitle")}
            </TabsTrigger>
            <TabsTrigger
              value="documents"
              className="rounded-2xl px-5 py-2 text-slate-600 data-[state=active]:bg-blue-600 data-[state=active]:text-white"
            >
              مستندات پرونده
            </TabsTrigger>
          </TabsList>

          <TabsContent value="details" className="space-y-0">
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
              <main id="request-facts" className="min-w-0 space-y-6">
                <RequestCargoSummary
                  items={request.cargo_items || []}
                  className="rounded-3xl border-slate-200 bg-white shadow-sm"
                />

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
                    <InfoPanel
                      icon={User}
                      label={t("common.customerName")}
                      value={displayValue(
                        request.customer.full_name,
                        missingValue,
                      )}
                    />
                    <InfoPanel
                      icon={Phone}
                      label={t("common.phone")}
                      value={displayValue(request.customer.phone, missingValue)}
                      ltr
                    />
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
                      {renderLocationBox(
                        t("common.destination"),
                        destination,
                        "destination",
                      )}
                    </div>

                    {renderIranDestinationBox()}

                    <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                      <div className="flex flex-wrap items-center gap-3">
                        <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-violet-50 text-violet-700">
                          <Truck className="h-5 w-5" />
                        </span>
                        <div>
                          <p className="text-xs text-slate-500">
                            {t("transport.requestMethod")}
                          </p>
                          <p className="font-semibold text-slate-900">
                            {requestTransportLabel}
                          </p>
                        </div>
                        {request.transport_method_preference ===
                          "forwarder_suggestion" && (
                          <Badge className="rounded-full bg-blue-50 text-blue-700 hover:bg-blue-50">
                            {t("requestFlow.forwarderSuggestion")}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {hasLegacyCargo && (
                  <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                    <CardHeader className="pb-3">
                      <CardTitle className="flex items-center gap-3 text-lg text-slate-950">
                        <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-violet-50 text-violet-700">
                          <Package className="h-5 w-5" />
                        </span>
                        {t("requestForm.legacyCargo")}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                        <p className="text-xs text-slate-500">
                          {t("common.description")}
                        </p>
                        <p className="mt-2 text-sm font-medium leading-7 text-slate-900">
                          {displayValue(cargo.description, missingValue)}
                        </p>
                      </div>
                      <div className="grid gap-3 sm:grid-cols-3">
                        <InfoPanel
                          icon={Weight}
                          label={t("requestDetail.weight")}
                          value={formatMeasurement(
                            cargo.weight,
                            t("common.weightKg"),
                            locale,
                            missingValue,
                          )}
                        />
                        <InfoPanel
                          icon={Package}
                          label={t("requestDetail.volume")}
                          value={formatMeasurement(
                            cargo.volume,
                            t("common.volumeM3"),
                            locale,
                            missingValue,
                          )}
                        />
                        <InfoPanel
                          icon={DollarSign}
                          label={t("common.value")}
                          value={formatMoney(
                            cargo.value,
                            locale,
                            missingValue,
                            t("requestDetail.moneyUnit"),
                          )}
                        />
                      </div>
                      <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                        <p className="text-xs text-slate-500">
                          {t("common.specialInstructions")}
                        </p>
                        <p className="mt-2 text-sm font-medium leading-7 text-slate-900">
                          {displayValue(
                            cargo.special_instructions,
                            missingValue,
                          )}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                )}

                <Card
                  id="current-quote"
                  className="rounded-3xl border-slate-200 bg-white shadow-sm"
                >
                  <CardHeader className="pb-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <CardTitle className="flex items-center gap-3 text-lg text-slate-950">
                        <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-amber-50 text-amber-700">
                          <DollarSign className="h-5 w-5" />
                        </span>
                        {t("requestDetail.quoteSectionTitle")}
                      </CardTitle>
                      {!terminalCommercialState &&
                        (!request.latest_quote ||
                          request.latest_quote.customer_response ===
                            "discussion") && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="gap-2"
                            onClick={() => setQuoteModalOpen(true)}
                          >
                            <Plus className="h-4 w-4" />
                            {request.latest_quote
                              ? t("requestDetail.revisedQuote")
                              : t("requestDetail.setQuote")}
                          </Button>
                        )}
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {request.latest_quote ? (
                      <>
                        <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                          <div className="flex items-baseline justify-between gap-2">
                            <span className="text-xs text-slate-500">
                              {t("common.amount")}
                            </span>
                            <span className="text-lg font-bold text-slate-900">
                              {formatQuoteMoney(
                                request.latest_quote.amount,
                                request.latest_quote.currency,
                                locale,
                                missingValue,
                              )}
                            </span>
                          </div>
                          {request.latest_quote.valid_until && (
                            <p className="mt-2 text-xs text-slate-500">
                              {t("requestDetail.quoteValidUntil")}:{" "}
                              {formatDualCalendarDate(
                                request.latest_quote.valid_until,
                                locale,
                              )}
                            </p>
                          )}
                          {request.latest_quote.note && (
                            <p className="mt-2 border-t border-slate-100 pt-2 text-sm text-slate-700">
                              {request.latest_quote.note}
                            </p>
                          )}
                        </div>
                        {request.latest_quote.customer_response ===
                        "accepted" ? (
                          <div className="space-y-3 rounded-2xl bg-green-50 p-3 text-sm font-medium text-green-800">
                            <div className="flex items-center gap-2">
                              <CheckCircle2 className="h-4 w-4 shrink-0" />
                              {t("requestDetail.customerAccepted")}
                            </div>
                            {latestQuoteAlreadyConverted ? (
                              <p className="text-xs font-normal leading-6">
                                محموله عملیاتی این پیشنهاد قبلاً ایجاد شده است.
                              </p>
                            ) : organizationCustomerState?.customer ? (
                              <OperationalAnyPermission
                                permissions={[
                                  "operational_shipment.create_from_quote",
                                  "operational_shipment.create",
                                ]}
                                fallback={
                                  <p className="text-xs font-normal leading-6">
                                    برای ایجاد محموله عملیاتی، مجوز مربوط به
                                    ساخت از پیشنهاد پذیرفته‌شده لازم است.
                                  </p>
                                }
                              >
                                <Button asChild size="sm">
                                  <Link
                                    to={`/operations/shipments/new?source=accepted_quote&accepted_quote_id=${request.latest_quote.id}&request_ref=${encodeURIComponent(request.tracking_number)}`}
                                  >
                                    {t("operations.create")}
                                  </Link>
                                </Button>
                              </OperationalAnyPermission>
                            ) : (
                              <p className="text-xs font-normal leading-6">
                                برای ادامه، ابتدا مشتری سازمان این درخواست را
                                انتخاب کنید.
                              </p>
                            )}
                          </div>
                        ) : request.latest_quote.customer_response ===
                          "discussion" ? (
                          <div className="space-y-2 rounded-2xl bg-amber-50 p-3 text-sm text-amber-900">
                            <div className="flex items-center gap-2 font-medium">
                              <MessageSquare className="h-4 w-4 shrink-0" />
                              {t("requestDetail.customerDiscussion")}
                            </div>
                            <p className="whitespace-pre-wrap break-words">
                              {request.latest_quote.customer_response_message}
                            </p>
                          </div>
                        ) : request.latest_quote.customer_response ===
                          "declined" ? (
                          <div className="flex items-center gap-2 rounded-2xl bg-red-50 p-3 text-sm font-medium text-red-800">
                            <AlertCircle className="h-4 w-4 shrink-0" />
                            {t("requestDetail.customerDeclined")}
                          </div>
                        ) : (
                          <div className="flex items-center gap-2 rounded-2xl bg-slate-50 p-3 text-sm text-slate-600">
                            <Clock className="h-4 w-4 shrink-0" />
                            {t("requestDetail.customerPending")}
                          </div>
                        )}
                        {request.latest_quote.responded_at && (
                          <p className="text-xs text-slate-500">
                            {t("requestDetail.responseTime")}:{" "}
                            {formatDualCalendarInstant(
                              request.latest_quote.responded_at,
                              locale,
                            )}
                          </p>
                        )}
                        {(request.quote_history?.length ?? 0) > 1 && (
                          <details className="space-y-2 border-t border-slate-100 pt-3">
                            <summary className="cursor-pointer text-xs font-semibold text-slate-600">
                              {t("requestDetail.quoteHistory")} (
                              {(
                                (request.quote_history?.length ?? 1) - 1
                              ).toLocaleString("fa-IR")}
                              )
                            </summary>
                            <div className="mt-3 space-y-2">
                              {request.quote_history?.slice(1).map((quote) => (
                                <div
                                  key={quote.public_id}
                                  className="rounded-xl border border-slate-100 bg-white p-3 text-sm"
                                >
                                  <div className="flex flex-wrap items-center justify-between gap-2">
                                    <span className="font-semibold text-slate-900">
                                      {formatQuoteMoney(
                                        quote.amount,
                                        quote.currency,
                                        locale,
                                        missingValue,
                                      )}
                                    </span>
                                    <span className="text-xs text-slate-500">
                                      {formatDualCalendarInstant(
                                        quote.created_at,
                                        locale,
                                      )}
                                    </span>
                                  </div>
                                  <p className="mt-2 text-slate-600">
                                    {quote.customer_response === "accepted"
                                      ? t("requestDetail.customerAccepted")
                                      : quote.customer_response === "discussion"
                                        ? t("requestDetail.customerDiscussion")
                                        : quote.customer_response === "declined"
                                          ? t("requestDetail.customerDeclined")
                                          : t("requestDetail.customerPending")}
                                  </p>
                                  {quote.customer_response_message && (
                                    <p className="mt-2 whitespace-pre-wrap break-words rounded-lg bg-amber-50 p-2 text-amber-900">
                                      {quote.customer_response_message}
                                    </p>
                                  )}
                                </div>
                              ))}
                            </div>
                          </details>
                        )}
                      </>
                    ) : (
                      <p className="text-sm text-slate-500">
                        {t("requestDetail.noQuoteYet")}
                      </p>
                    )}
                  </CardContent>
                </Card>
              </main>

              <aside className="min-w-0 space-y-6">
                <div id="organization-customer">
                  <OrganizationCustomerCard
                    candidates={organizationCustomerCandidates}
                    error={organizationCustomerError}
                    linkState={organizationCustomerState}
                    loading={organizationCustomerLoading}
                    onLink={handleOrganizationCustomerLink}
                    onSearch={handleOrganizationCustomerSearch}
                    onSearchChange={setOrganizationCustomerSearch}
                    onSelectCustomer={setSelectedOrganizationCustomerId}
                    saving={organizationCustomerSaving}
                    search={organizationCustomerSearch}
                    searchLoading={organizationCustomerSearchLoading}
                    searchComplete={organizationCustomerSearchComplete}
                    selectedCustomerId={selectedOrganizationCustomerId}
                  />
                </div>
                {!terminalCommercialState && (
                  <OperationsCard
                    commercial={request.commercial}
                    handleStatusChange={handleStatusChange}
                    statusLabel={statusLabel}
                  />
                )}
                <details className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                  <summary className="cursor-pointer font-bold text-slate-950">
                    {t("requestDetail.timeline")} (
                    {request.timeline.length.toLocaleString("fa-IR")})
                  </summary>
                  <div className="mt-4">
                    <TimelineCard
                      timeline={request.timeline}
                      formatDate={(value) =>
                        formatDateValue(value, locale, missingValue)
                      }
                      statusLabel={statusLabel}
                      t={t}
                      embedded
                    />
                  </div>
                </details>
                <details className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                  <summary className="cursor-pointer font-bold text-slate-950">
                    {t("publicTracking.requestInfo")}
                  </summary>
                  <div className="mt-4 space-y-3 text-sm">
                    <InfoRow
                      label={t("common.trackingNumber")}
                      value={request.tracking_number}
                    />
                    <InfoRow
                      label={t("common.createdAt")}
                      value={formatDateValue(
                        request.created_at,
                        locale,
                        missingValue,
                      )}
                    />
                    <InfoRow
                      label={t("requestDetail.assignee")}
                      value={request.assigned_to?.name || missingValue}
                    />
                  </div>
                </details>
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
                  <label className="text-sm font-medium text-slate-600">
                    {t("common.subject")}
                  </label>
                  <Input
                    placeholder={t("requestDetail.subjectPlaceholder")}
                    value={newMessage.subject}
                    onChange={(event) =>
                      setNewMessage({
                        ...newMessage,
                        subject: event.target.value,
                      })
                    }
                    className="rounded-2xl bg-slate-50"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-600">
                    {t("common.content")}
                  </label>
                  <Textarea
                    placeholder={t("requestDetail.contentPlaceholder")}
                    value={newMessage.content}
                    onChange={(event) =>
                      setNewMessage({
                        ...newMessage,
                        content: event.target.value,
                      })
                    }
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
                  {sendingMessage
                    ? t("requestDetail.saving")
                    : t("requestDetail.addNote")}
                </Button>
              </CardContent>
            </Card>

            <div className="grid gap-4">
              {internalNotes.length === 0 ? (
                <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
                  <CardContent className="p-8 text-center text-sm text-slate-500">
                    {t("requestDetail.noNotes")}
                  </CardContent>
                </Card>
              ) : (
                internalNotes.map((message) => (
                  <Card
                    key={message.id}
                    className="rounded-3xl border-slate-200 bg-white shadow-sm"
                  >
                    <CardContent className="p-5">
                      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                        <h4 className="font-semibold text-slate-950">
                          {message.subject || t("action.note")}
                        </h4>
                        <span className="text-xs text-slate-500">
                          {formatDateValue(
                            message.created_at,
                            locale,
                            missingValue,
                          )}
                        </span>
                      </div>
                      <p className="leading-7 text-slate-700">
                        {message.content}
                      </p>
                      <div className="mt-4 text-sm text-slate-500">
                        {t("requestDetail.by")}: {message.created_by}
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>
          <TabsContent value="tracking">
            <TrackingManagementCard
              requestId={request.public_id}
              locale={locale}
              t={t}
              toast={toast}
            />
          </TabsContent>
          <TabsContent value="documents">
            <CaseDocumentsTab caseId={request.public_id} />
          </TabsContent>
        </Tabs>

        <QuoteModal
          open={quoteModalOpen}
          onOpenChange={setQuoteModalOpen}
          requestId={request.public_id}
          onSuccess={loadRequestDetail}
        />
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

const InfoPanel = ({
  icon: Icon,
  label,
  value,
  ltr = false,
}: InfoPanelProps) => (
  <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
    <div className="mb-2 flex items-center gap-2 text-xs text-slate-500">
      <Icon className="h-4 w-4" />
      {label}
    </div>
    <p
      className="break-words text-sm font-semibold text-slate-900"
      dir={ltr ? "ltr" : "rtl"}
    >
      {value}
    </p>
  </div>
);

const InfoRow = ({ label, value }: { label: string; value: string }) => (
  <div className="flex items-start justify-between gap-4 rounded-2xl bg-slate-50 px-4 py-3">
    <span className="shrink-0 text-slate-500">{label}</span>
    <span className="min-w-0 break-words text-left font-medium text-slate-900">
      {value}
    </span>
  </div>
);

const OrganizationCustomerCard = ({
  candidates,
  error,
  linkState,
  loading,
  onLink,
  onSearch,
  onSearchChange,
  onSelectCustomer,
  saving,
  search,
  searchComplete,
  searchLoading,
  selectedCustomerId,
}: {
  candidates: RequestOrganizationCustomer[];
  error: string | null;
  linkState: RequestOrganizationCustomerState | null;
  loading: boolean;
  onLink: () => void;
  onSearch: () => void;
  onSearchChange: (value: string) => void;
  onSelectCustomer: (customerId: number) => void;
  saving: boolean;
  search: string;
  searchComplete: boolean;
  searchLoading: boolean;
  selectedCustomerId: number | null;
}) => {
  const linkedCustomer = linkState?.customer ?? null;
  const isRelinking =
    !!linkedCustomer &&
    !!selectedCustomerId &&
    selectedCustomerId !== linkedCustomer.id;

  return (
    <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg text-slate-950">
          <Link2 className="h-5 w-5 text-blue-600" />
          مشتری سازمان
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm leading-6 text-slate-600">
          مشتری موجود همین سازمان را به درخواست متصل کنید. ساخت یا حذف مشتری از
          این صفحه انجام نمی‌شود.
        </p>
        {loading ? (
          <div className="flex items-center gap-2 rounded-2xl bg-slate-50 p-4 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            در حال دریافت اطلاعات مشتری سازمان
          </div>
        ) : (
          <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
            <p className="mb-2 text-xs text-slate-500">مشتری فعلی</p>
            {linkedCustomer ? (
              <div className="space-y-2">
                <p className="font-semibold text-slate-950">
                  {linkedCustomer.name}
                </p>
                <p className="text-sm text-slate-600">
                  {linkedCustomer.company_name || "شرکت ثبت نشده"}
                </p>
                <InfoRow
                  label="تلفن"
                  value={linkedCustomer.phone || "ثبت نشده"}
                />
                <InfoRow
                  label="ایمیل"
                  value={linkedCustomer.email || "ثبت نشده"}
                />
              </div>
            ) : (
              <p className="text-sm leading-6 text-slate-600">
                هنوز مشتری سازمان برای این درخواست انتخاب نشده است.
              </p>
            )}
          </div>
        )}

        {!loading && linkState && !linkState.has_available_customers && (
          <div className="rounded-2xl border border-amber-100 bg-amber-50 p-3 text-sm leading-6 text-amber-800">
            ابتدا مدیر سازمان باید مشتری را در فهرست مشتریان سازمان ثبت کند.
          </div>
        )}

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
            placeholder="جستجو با نام یا نام شرکت"
            className="rounded-2xl bg-slate-50"
          />
          <Button
            type="button"
            variant="outline"
            onClick={onSearch}
            disabled={searchLoading || saving}
            className="shrink-0 rounded-2xl"
            aria-label="جستجوی مشتری سازمان"
          >
            {searchLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
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
                  className={`w-full rounded-2xl border p-3 text-right transition ${selected ? "border-blue-300 bg-blue-50 text-blue-950" : "border-slate-100 bg-white text-slate-800 hover:bg-slate-50"}`}
                >
                  <span className="block text-sm font-semibold">
                    {customer.name}
                  </span>
                  <span className="mt-1 block text-xs text-slate-500">
                    {customer.company_name || "بدون نام شرکت"} ·{" "}
                    {customer.phone || "بدون تلفن"}
                  </span>
                </button>
              );
            })}
          </div>
        )}
        {searchComplete && !error && candidates.length === 0 && (
          <p className="rounded-2xl border border-dashed border-slate-200 p-3 text-sm text-slate-500">
            مشتری سازمانی مطابق جستجو پیدا نشد.
          </p>
        )}

        {isRelinking && (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-800">
            با تأیید، مشتری فعلی این درخواست با مشتری انتخاب‌شده جایگزین می‌شود.
          </div>
        )}
        {error && (
          <div className="rounded-2xl border border-red-100 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}
        <Button
          type="button"
          onClick={onLink}
          disabled={!selectedCustomerId || saving}
          className="w-full rounded-2xl bg-blue-600 hover:bg-blue-700"
        >
          {saving ? (
            <Loader2 className="ml-2 h-4 w-4 animate-spin" />
          ) : (
            <Link2 className="ml-2 h-4 w-4" />
          )}
          {isRelinking ? "تغییر مشتری سازمان" : "اتصال مشتری انتخاب‌شده"}
        </Button>
      </CardContent>
    </Card>
  );
};

const TrackingManagementCard = ({
  requestId,
  locale,
  t,
  toast,
}: {
  requestId: string;
  locale: string;
  t: (key: string) => string;
  toast: ReturnType<typeof useToast>["toast"];
}) => {
  const [data, setData] = useState<TrackingManagementData | null>(null);
  const [busy, setBusy] = useState(false);
  const [editUnitId, setEditUnitId] = useState("");
  const [editUnit, setEditUnit] = useState({
    display_name: "",
    vehicle_reference: "",
  });
  const [updateUnitId, setUpdateUnitId] = useState("");
  const [update, setUpdate] = useState({
    status: "in_transit",
    customer_message: "",
    internal_note: "",
    is_customer_visible: true,
    occurred_at: toLocalDateTimeInputValue(new Date()),
  });
  const [eventLocation, setEventLocation] = useState<OperationalEventLocation>({
    kind: "manual",
    locationText: "",
  });

  const load = useCallback(async () => {
    try {
      setData(await fetchTrackingManagement(requestId));
    } catch {
      toast({
        title: t("common.error"),
        description: t("multiTracking.fetchError"),
        variant: "destructive",
      });
    }
  }, [requestId, t, toast]);
  useEffect(() => {
    load();
  }, [load]);
  const run = async (
    operation: () => Promise<TrackingManagementData>,
    success: string,
  ) => {
    try {
      setBusy(true);
      setData(await operation());
      toast({ title: success });
    } catch {
      toast({
        title: t("common.error"),
        description: t("multiTracking.saveError"),
        variant: "destructive",
      });
    } finally {
      setBusy(false);
    }
  };
  const submitUpdate = () => {
    const occurredAtUtc = localDateTimeInputToUtc(update.occurred_at);
    if (!occurredAtUtc) {
      toast({
        title: t("common.error"),
        description: t("multiTracking.saveError"),
        variant: "destructive",
      });
      return;
    }
    void run(
      () =>
        addTrackingUnitUpdate(requestId, Number(updateUnitId), {
          ...update,
          logistics_point_public_id:
            eventLocation.kind === "private"
              ? eventLocation.publicId
              : undefined,
          location_reference_id:
            eventLocation.kind === "reference" ? eventLocation.id : undefined,
          location_text:
            eventLocation.kind === "manual"
              ? eventLocation.locationText || undefined
              : undefined,
          occurred_at: occurredAtUtc,
        }),
      t("multiTracking.updateAdded"),
    );
  };

  if (!data)
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <Loader2 className="mx-auto h-6 w-6 animate-spin" />
        </CardContent>
      </Card>
    );
  return (
    <div className="space-y-5">
      <Card className="rounded-3xl border-slate-200 shadow-sm">
        <CardHeader>
          <CardTitle>{t("multiTracking.internalTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant={data.enabled ? "default" : "outline"}>
              {data.enabled
                ? t("multiTracking.enabled")
                : t("multiTracking.disabled")}
            </Badge>
            <span className="text-sm text-slate-500">{data.tracking_code}</span>
          </div>
          {!data.enabled && (
            <Button
              disabled={!data.eligible || busy}
              onClick={() =>
                run(
                  () => enableTrackingManagement(requestId),
                  t("multiTracking.enabledSuccess"),
                )
              }
            >
              {t("multiTracking.enable")}
            </Button>
          )}
          {!data.eligible && !data.enabled && (
            <p className="text-sm text-amber-700">
              {t("multiTracking.notEligible")}
            </p>
          )}
        </CardContent>
      </Card>
      {data.enabled && (
        <>
          <Card className="rounded-3xl border-slate-200 shadow-sm">
            <CardHeader>
              <CardTitle>{t("multiTracking.editUnit")}</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-4">
              <Select
                value={editUnitId}
                onValueChange={(value) => {
                  const selected = data.unit_tracking?.units.find(
                    (u) => String(u.id) === value,
                  );
                  setEditUnitId(value);
                  setEditUnit({
                    display_name: selected?.display_name || "",
                    vehicle_reference: selected?.vehicle_reference || "",
                  });
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t("multiTracking.selectUnit")} />
                </SelectTrigger>
                <SelectContent>
                  {data.unit_tracking?.units.map((u) => (
                    <SelectItem key={u.id} value={String(u.id)}>
                      {u.display_name || u.unit_code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                value={editUnit.display_name}
                onChange={(e) =>
                  setEditUnit({ ...editUnit, display_name: e.target.value })
                }
                placeholder={t("multiTracking.displayName")}
              />
              <Input
                value={editUnit.vehicle_reference}
                onChange={(e) =>
                  setEditUnit({
                    ...editUnit,
                    vehicle_reference: e.target.value,
                  })
                }
                placeholder={t("multiTracking.vehicleReference")}
                title={t("multiTracking.vehicleReferenceHelp")}
              />
              <Button
                disabled={busy || !editUnitId}
                onClick={() =>
                  run(
                    () =>
                      updateTrackingUnitMetadata(
                        requestId,
                        Number(editUnitId),
                        editUnit,
                      ),
                    t("multiTracking.unitUpdated"),
                  )
                }
              >
                {t("multiTracking.save")}
              </Button>
            </CardContent>
          </Card>
          <Card className="rounded-3xl border-slate-200 shadow-sm">
            <CardHeader>
              <CardTitle>{t("multiTracking.addUpdate")}</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-2">
              <Select value={updateUnitId} onValueChange={setUpdateUnitId}>
                <SelectTrigger>
                  <SelectValue placeholder={t("multiTracking.selectUnit")} />
                </SelectTrigger>
                <SelectContent>
                  {data.unit_tracking?.units.map((u) => (
                    <SelectItem key={u.id} value={String(u.id)}>
                      {u.display_name || u.unit_code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select
                value={update.status}
                onValueChange={(status) => setUpdate({ ...update, status })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[
                    "not_started",
                    "loading",
                    "departed",
                    "in_transit",
                    "at_checkpoint",
                    "delayed",
                    "arrived_destination",
                    "delivered",
                    "cancelled",
                  ].map((v) => (
                    <SelectItem key={v} value={v}>
                      {t(`multiTracking.status.${v}`)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <OperationalEventLocationSelector
                value={eventLocation}
                onChange={setEventLocation}
              />
              <Input
                type="datetime-local"
                value={update.occurred_at}
                onChange={(e) =>
                  setUpdate({ ...update, occurred_at: e.target.value })
                }
              />
              <Textarea
                value={update.customer_message}
                onChange={(e) =>
                  setUpdate({ ...update, customer_message: e.target.value })
                }
                placeholder={t("multiTracking.customerMessage")}
              />
              <Textarea
                value={update.internal_note}
                onChange={(e) =>
                  setUpdate({ ...update, internal_note: e.target.value })
                }
                placeholder={t("multiTracking.internalNote")}
              />
              <label className="flex items-center gap-2 text-sm">
                <Checkbox
                  checked={update.is_customer_visible}
                  onCheckedChange={(checked) =>
                    setUpdate({
                      ...update,
                      is_customer_visible: checked === true,
                    })
                  }
                />
                {t("multiTracking.customerVisible")}
              </label>
              <Button
                disabled={busy || !updateUnitId || !update.occurred_at}
                onClick={submitUpdate}
              >
                {t("multiTracking.addUpdate")}
              </Button>
            </CardContent>
          </Card>
          {!data.unit_tracking?.units.length && (
            <p className="rounded-xl border border-dashed p-5 text-sm text-muted-foreground">
              {t("multiTracking.emptyUnits")}
            </p>
          )}
          <div className="grid gap-4 md:grid-cols-2">
            {data.unit_tracking?.units.map((u) => (
              <Card key={u.id}>
                <CardContent className="p-5">
                  <p className="font-bold">{u.display_name || u.unit_code}</p>
                  {u.vehicle_reference && (
                    <p className="text-sm text-slate-600">
                      {t("multiTracking.vehicleReference")}:{" "}
                      <span dir="ltr">{u.vehicle_reference}</span>
                    </p>
                  )}
                  <p className="text-sm text-slate-500">
                    {t(`multiTracking.status.${u.latest_status}`)} ·{" "}
                    {u.latest_location || "—"}
                  </p>
                  {u.allocated_cargo?.length ? (
                    <p className="mt-2 text-sm">
                      کالا:{" "}
                      {u.allocated_cargo
                        .map(
                          (c) =>
                            `${c.cargo_name} — ${formatQuantity(c.allocated_quantity, locale)} ${c.uom_symbol}`,
                        )
                        .join(" · ")}
                    </p>
                  ) : null}
                  <p className="mt-2 text-xs text-slate-400" dir="auto">
                    {u.latest_event_at
                      ? formatDualCalendarInstant(u.latest_event_at, locale)
                      : t("multiTracking.noUpdates")}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

const OperationsCard = ({
  commercial,
  handleStatusChange,
  statusLabel,
}: {
  commercial: RequestCommercialProjection;
  handleStatusChange: (newStatus: string) => void;
  statusLabel: (status: string) => string;
}) => (
  <Card
    id="commercial-conclusion"
    className="rounded-3xl border-slate-200 bg-white shadow-sm"
  >
    <CardHeader className="pb-3">
      <CardTitle className="flex items-center gap-2 text-lg text-slate-950">
        <CheckCircle2 className="h-5 w-5 text-emerald-600" />
        وضعیت تجاری درخواست
      </CardTitle>
    </CardHeader>
    <CardContent>
      <p className="mb-3 text-sm leading-6 text-slate-500">
        پاسخ مشتری، وضعیت درخواست را خودکار تغییر نمی‌دهد. پس از بررسی پاسخ،
        وضعیت تجاری را صریحاً انتخاب کنید.
      </p>
      <div className="mb-3 rounded-2xl bg-slate-50 p-3 text-sm text-slate-700">
        اقدام بعدی:{" "}
        <span className="font-semibold text-slate-950">
          {commercial.next_action.label_fa}
        </span>
      </div>
      <Select onValueChange={handleStatusChange}>
        <SelectTrigger className="rounded-2xl bg-slate-50">
          <SelectValue placeholder="تغییر صریح وضعیت درخواست" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="in_progress">
            {statusLabel("in_progress")}
          </SelectItem>
          <SelectItem value="waiting_for_customer">
            {statusLabel("waiting_for_customer")}
          </SelectItem>
          <SelectItem value="won">{statusLabel("won")}</SelectItem>
          <SelectItem value="lost">رد شده / از دست رفته</SelectItem>
          <SelectItem value="closed">بسته شده</SelectItem>
        </SelectContent>
      </Select>
    </CardContent>
  </Card>
);

const TimelineCard = ({
  timeline,
  formatDate,
  statusLabel,
  t,
  embedded = false,
}: {
  timeline: RequestDetail["timeline"];
  formatDate: (value: string) => string;
  statusLabel: (status: string) => string;
  t: ReturnType<typeof useI18n>["t"];
  embedded?: boolean;
}) => (
  <Card
    className={
      embedded
        ? "border-0 bg-transparent shadow-none"
        : "rounded-3xl border-slate-200 bg-white shadow-sm"
    }
  >
    {!embedded && (
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg text-slate-950">
          <Clock className="h-5 w-5 text-blue-600" />
          {t("requestDetail.timeline")}
        </CardTitle>
      </CardHeader>
    )}
    <CardContent className={embedded ? "p-0" : undefined}>
      {timeline.length === 0 ? (
        <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4 text-sm text-slate-500">
          {t("requestDetail.noEvents")}
        </div>
      ) : (
        <div className="space-y-0">
          {timeline.map((event, index) => (
            <div key={event.id} className="grid grid-cols-[auto_1fr] gap-3">
              <div className="flex flex-col items-center">
                <div className="mt-1 h-3 w-3 rounded-full bg-blue-600 ring-4 ring-blue-50" />
                {index < timeline.length - 1 && (
                  <div className="mt-2 h-full min-h-12 w-px bg-slate-200" />
                )}
              </div>
              <div className="pb-5">
                <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-slate-950">
                      {event.title}
                    </span>
                    {event.old_status && event.new_status && (
                      <div className="flex flex-wrap gap-2 text-xs text-slate-600">
                        <Badge
                          variant="outline"
                          className="rounded-full bg-white"
                        >
                          از: {statusLabel(event.old_status)}
                        </Badge>
                        <Badge
                          variant="outline"
                          className="rounded-full bg-white"
                        >
                          به: {statusLabel(event.new_status)}
                        </Badge>
                      </div>
                    )}
                  </div>
                  {event.description && (
                    <p className="mb-2 whitespace-pre-wrap break-words text-sm leading-6 text-slate-600">
                      {event.description}
                    </p>
                  )}
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <span>زمان: {formatDate(event.created_at)}</span>
                    <span>•</span>
                    <span>توسط: {event.created_by}</span>
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
