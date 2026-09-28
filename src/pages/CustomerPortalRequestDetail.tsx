import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router";
import { CheckCircle, Clock, MessageSquare, RefreshCw, XCircle } from "lucide-react";
import CustomerPortalLayout from "@/components/CustomerPortalLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  CustomerPortalApiError,
  fetchCustomerRequest,
  fetchCustomerSession,
  respondToCustomerQuote,
  type CustomerQuoteResponse,
  type CustomerRequestDetail,
  type CustomerRequestRouteEndpoint,
} from "@/lib/customerPortalApi";
import { formatDualCalendarDate, formatDualCalendarInstant } from "@/lib/dualCalendar";
import { formatQuoteMoney } from "@/lib/formatQuantity";
import { isLocalDateBeforeToday } from "@/lib/localDate";
import { useI18n } from "@/i18n";

function DetailField({ label, children }: { label: ReactNode; children: ReactNode }) {
  return <div className="min-w-0 rounded-lg border border-slate-100 bg-slate-50/70 p-3"><dt className="text-xs font-medium text-muted-foreground">{label}</dt><dd className="mt-1 break-words text-sm font-semibold text-slate-900">{children}</dd></div>;
}

function endpointLabel(endpoint: CustomerRequestRouteEndpoint | undefined) {
  if (!endpoint) return "—";
  const values = [endpoint.country, endpoint.province, endpoint.county, endpoint.city, endpoint.international_city, endpoint.address]
    .filter((value): value is string => Boolean(value?.trim()));
  return [...new Set(values)].join("، ") || "—";
}

export default function CustomerPortalRequestDetail() {
  const { requestId = "" } = useParams();
  const { t, locale, language, statusLabel, shippingTypeLabel, transportLabel } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const [data, setData] = useState<CustomerRequestDetail | null>(null);
  const [csrf, setCsrf] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [discussion, setDiscussion] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const session = await fetchCustomerSession();
      if (!session.authenticated || !session.csrf_token) {
        navigate("/customer", { replace: true, state: { from: location.pathname } });
        return;
      }
      setCsrf(session.csrf_token);
      setData(await fetchCustomerRequest(requestId));
    } catch (caught) {
      if (caught instanceof CustomerPortalApiError && caught.status === 401) {
        navigate("/customer", { replace: true, state: { from: location.pathname } });
        return;
      }
      setError(caught instanceof Error ? caught.message : t("common.error"));
    } finally {
      setLoading(false);
    }
  }, [location.pathname, navigate, requestId, t]);

  useEffect(() => { void load(); }, [load]);

  const respond = async (response: CustomerQuoteResponse) => {
    if (!data?.latest_quote || !csrf || (response === "discussion" && !discussion.trim())) return;
    setBusy(true);
    setError("");
    try {
      await respondToCustomerQuote(data.public_id, data.latest_quote, response, csrf, response === "discussion" ? discussion.trim() : undefined);
      setDiscussion("");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("customer.quoteResponseErrorTitle"));
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <CustomerPortalLayout privateNav><div className="flex justify-center p-16"><RefreshCw className="animate-spin" /></div></CustomerPortalLayout>;

  const quote = data?.latest_quote;
  const expired = Boolean(quote && !quote.customer_response && quote.valid_until && isLocalDateBeforeToday(quote.valid_until));
  const canRespond = Boolean(quote && !quote.customer_response && !expired);
  const selectedTransport = data ? (data.shipping_type === "domestic" ? data.domestic_transport_method : data.international_transport_method) || data.transport_method : null;
  const hasLegacyCargo = Boolean(data?.legacy_cargo && Object.entries(data.legacy_cargo).some(([, value]) => value != null && value !== ""));
  const transportPolicy = data?.transport_method_preference === "forwarder_suggestion"
    ? t("requestForm.forwarderSuggestionOption")
    : data?.transport_method_preference === "customer_choice"
      ? t("requestForm.customerChoiceOption")
      : t("common.notRegistered");

  return <CustomerPortalLayout privateNav>
    <div className="mb-4"><Button asChild variant="outline"><Link to="/customer/requests">{t("customer.backToPanel")}</Link></Button></div>
    {error && <p role="alert" className="mb-4 rounded bg-destructive/10 p-3 text-destructive">{error}</p>}
    {!data ? <Card><CardContent className="p-10 text-center">{t("customer.requestNotFoundTitle")}</CardContent></Card> : <div className="space-y-5">
      <Card><CardHeader><CardTitle className="flex flex-wrap items-center justify-between gap-3">{t("customer.requestDetails")}<Badge>{statusLabel(data.status)}</Badge></CardTitle></CardHeader><CardContent><dl className="grid gap-3 sm:grid-cols-3">
        <DetailField label={t("common.trackingNumber")}>{data.tracking_code || data.public_id}</DetailField>
        <DetailField label={t("common.shippingType")}>{shippingTypeLabel(data.shipping_type, { full: true })}</DetailField>
        <DetailField label={t("common.createdAt")}>{formatDualCalendarInstant(data.created_at, locale)}</DetailField>
      </dl></CardContent></Card>

      <Card><CardHeader><CardTitle>{t("customer.requestAssignee")}</CardTitle></CardHeader><CardContent><p className="text-lg font-bold">{data.assigned_expert?.display_name ?? t("customer.assignmentPending")}</p>{!data.assigned_expert && <p className="mt-2 text-sm text-muted-foreground">{t("customer.pendingAssignmentConfirmation")}</p>}</CardContent></Card>

      <Card><CardHeader><CardTitle>{t("customer.requestRoute")}</CardTitle></CardHeader><CardContent><dl className="grid gap-3 sm:grid-cols-2">
        <DetailField label={t("common.origin")}>{endpointLabel(data.route?.origin)}</DetailField>
        <DetailField label={t("common.destination")}>{endpointLabel(data.route?.destination)}</DetailField>
        {data.route?.iran_destination && <DetailField label={t("customer.iranDestination")}>{[data.route.iran_destination.label, data.route.iran_destination.province].filter(Boolean).join("، ") || t("common.notRegistered")}</DetailField>}
      </dl></CardContent></Card>

      <Card><CardHeader><CardTitle>{t("customer.transportSelection")}</CardTitle></CardHeader><CardContent><dl className="grid gap-3 sm:grid-cols-2">
        <DetailField label={t("customer.transportSelectionPolicy")}>{transportPolicy}</DetailField>
        {data.transport_method_preference === "customer_choice" && <DetailField label={t("customer.selectedTransportMethod")}>{selectedTransport ? transportLabel(selectedTransport) : t("common.notRegistered")}</DetailField>}
      </dl></CardContent></Card>

      <Card><CardHeader><CardTitle>{t("customer.cargoItems")}</CardTitle></CardHeader><CardContent>
        {data.cargo_items.length ? <ol className="space-y-3">{data.cargo_items.map((item) => <li key={item.public_id} className="rounded-lg border p-4">
          <p className="font-semibold">{item.position}. {item.description || item.cargo_type?.[language === "fa" ? "fa_name" : "en_name"] || t("common.notRegistered")}</p>
          {item.cargo_type && <p className="mt-1 text-sm text-muted-foreground">{t("requestForm.cargoType")}: {item.cargo_type[language === "fa" ? "fa_name" : "en_name"]}</p>}
          {item.quantity && item.uom && <p className="mt-1 text-sm" dir="ltr">{item.quantity} {item.uom.symbol}</p>}
        </li>)}</ol> : hasLegacyCargo ? <div className="space-y-1 text-sm">
          {data.legacy_cargo.description && <p>{data.legacy_cargo.description}</p>}
          {data.legacy_cargo.weight != null && <p>{t("common.weightKg")}: {data.legacy_cargo.weight}</p>}
          {data.legacy_cargo.volume != null && <p>{t("common.volumeM3")}: {data.legacy_cargo.volume}</p>}
          {data.legacy_cargo.value != null && <p>{t("common.value")}: {data.legacy_cargo.value}</p>}
        </div> : <p className="text-sm text-muted-foreground">{t("requestForm.noCargoItems")}</p>}
      </CardContent></Card>

      <Card><CardHeader><CardTitle>{t("customer.requestDates")}</CardTitle></CardHeader><CardContent><dl className="grid gap-3 sm:grid-cols-2">
        <DetailField label={t("customer.fromDate")}>{data.pickup_date ? formatDualCalendarDate(data.pickup_date, locale) : t("common.notRegistered")}</DetailField>
        <DetailField label={t("customer.toDate")}>{data.delivery_date ? formatDualCalendarDate(data.delivery_date, locale) : t("common.notRegistered")}</DetailField>
      </dl></CardContent></Card>

      <Card><CardHeader><CardTitle>{t("customer.specialInstructions")}</CardTitle></CardHeader><CardContent><p className="whitespace-pre-wrap text-sm leading-7">{data.special_instructions || t("customer.noSpecialInstructions")}</p></CardContent></Card>

      <Card><CardHeader><CardTitle>{t("customer.quoteTitle")}</CardTitle></CardHeader><CardContent className="space-y-4">
        {!quote ? <p>{t("customer.noQuote")}</p> : <>
          <div className="text-xl font-bold">{formatQuoteMoney(quote.amount, quote.currency, locale)}</div>
          {quote.valid_until && <p className="text-sm text-muted-foreground">{t("customer.quoteValidUntil")}: {formatDualCalendarDate(quote.valid_until, locale)}</p>}
          {quote.note && <p className="border-t pt-3 text-sm">{quote.note}</p>}
          {quote.customer_response === "accepted" && <p className="flex gap-2 rounded bg-green-50 p-3 text-green-800"><CheckCircle className="h-4 w-4" />{t("customer.quoteAccepted")}</p>}
          {quote.customer_response === "discussion" && <div className="rounded bg-amber-50 p-3 text-amber-900"><p className="flex gap-2"><MessageSquare className="h-4 w-4" />{t("customer.quoteDiscussion")}</p><p className="mt-2 whitespace-pre-wrap">{quote.customer_response_message}</p></div>}
          {quote.customer_response === "declined" && <p className="flex gap-2 rounded bg-red-50 p-3 text-red-800"><XCircle className="h-4 w-4" />{t("customer.quoteDeclined")}</p>}
          {expired && <p className="flex gap-2 rounded bg-muted p-3"><Clock className="h-4 w-4" />{t("customer.quoteExpired")}</p>}
          {canRespond && <div className="space-y-3 border-t pt-4"><div className="grid gap-2 sm:grid-cols-3"><Button disabled={busy} onClick={() => void respond("accepted")}>{t("customer.quoteAccept")}</Button><Button disabled={busy} variant="outline" onClick={() => document.getElementById("customer-discussion")?.focus()}>{t("customer.quoteNeedsDiscussion")}</Button><Button disabled={busy} variant="outline" onClick={() => void respond("declined")}>{t("customer.quoteDecline")}</Button></div><div className="rounded border border-amber-200 p-3"><label htmlFor="customer-discussion" className="text-sm font-medium">{t("customer.quoteDiscussionMessage")}</label><Textarea id="customer-discussion" maxLength={500} value={discussion} onChange={(event) => setDiscussion(event.target.value)} placeholder={t("customer.quoteDiscussionPlaceholder")} /><Button className="mt-2" disabled={busy || !discussion.trim()} onClick={() => void respond("discussion")}>{t("customer.quoteSendDiscussion")}</Button></div></div>}
        </>}
      </CardContent></Card>

      <Card><CardHeader><CardTitle>{t("customer.quoteHistory")}</CardTitle></CardHeader><CardContent className="space-y-3">
        {!data.quote_history.length ? <p className="text-sm text-muted-foreground">{t("customer.noQuote")}</p> : data.quote_history.map((item) => <div key={item.public_id} className="rounded border p-3"><div className="flex flex-wrap justify-between gap-2"><strong>{formatQuoteMoney(item.amount, item.currency, locale)}</strong><span className="text-xs text-muted-foreground">{formatDualCalendarInstant(item.created_at, locale)}</span></div><p className="mt-2 text-sm">{item.customer_response === "accepted" ? t("customer.quoteAccepted") : item.customer_response === "discussion" ? t("customer.quoteDiscussion") : item.customer_response === "declined" ? t("customer.quoteDeclined") : t("customer.quoteAwaitingResponse")}</p>{item.customer_response_message && <p className="mt-2 whitespace-pre-wrap rounded bg-amber-50 p-2 text-sm">{item.customer_response_message}</p>}</div>)}
      </CardContent></Card>
    </div>}
  </CustomerPortalLayout>;
}
