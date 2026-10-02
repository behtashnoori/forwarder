import RequestedEndpointComparison from "@/components/RequestedEndpointComparison";
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useCurrentAuthorityRefresh } from "@/hooks/useCurrentAuthorityRefresh";
import ShipmentOwnerTransfer from "@/components/ShipmentOwnerTransfer";
import { Link, useParams } from "react-router";
import OperationalPermission from "@/components/OperationalPermission";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  ApiError,
  commandRouteCheckpoint,
  correctRouteMilestone,
  getOperationalProjection,
  getOperationalShipment,
  getRoutePlan,
  getRouteTimeline,
  listRouteExceptions,
  listRoutePlans,
  recordOperationalEvent,
  reconcileRouteExceptions,
  reconcileRouteTimeline,
  replanRoute,
  resolveRouteException,
  verifyRouteMilestone,
  type OperationalShipmentSummary,
  type RouteException,
  type RoutePlanDetail,
  type RoutePlanSummary,
  type RouteTimeline,
} from "@/lib/api";
import { useI18n } from "@/i18n";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import ShipmentCargoItems from "@/components/ShipmentCargoItems";
import OperationalExecutionSection from "@/components/OperationalExecutionSection";
import OperationalConditionsSection from "@/components/OperationalConditionsSection";
import OperationalActionsSection from "@/components/OperationalActionsSection";
import UnifiedShipmentHistory from "@/components/UnifiedShipmentHistory";
import DocumentReadinessSection from "@/components/DocumentReadinessSection";
import ShipmentEconomicsSection from "@/components/ShipmentEconomicsSection";
import ShipmentExternalReferences from "@/components/ShipmentExternalReferences";
import ShipmentDocuments from "@/components/ShipmentDocuments";
import OperationsNav from "@/components/OperationsNav";
import OccurrenceTimeAction from "@/components/OccurrenceTimeAction";
import RouteAuthoringSection from "@/components/RouteAuthoringSection";
import RouteReferenceTimes from "@/components/RouteReferenceTimes";
import RouteActualSection from "@/components/RouteActualSection";
import RouteStageTransportExecutionSection from "@/components/RouteStageTransportExecutionSection";
import ReportedFactsSection from "@/components/ReportedFactsSection";
import ShipmentClosure from "@/components/ShipmentClosure";
import DeliverySection from "@/components/DeliverySection";
import ShipmentOperationalStages from "@/components/ShipmentOperationalStages";
import { ShipmentEta } from "@/components/CargoEta";
import CargoAllocationTraceSection from "@/components/CargoAllocationTraceSection";
import OperationalGuidance from "@/components/OperationalGuidance";
import {
  formatRouteTransportModes,
  getRequestTransportMethod,
} from "@/lib/transportPresentation";

const key = () => crypto.randomUUID();
const safeError = (error: unknown) => {
  if (error instanceof ApiError) {
    if (error.status === 403) return "شما مجوز انجام این اقدام را ندارید.";
    const code = error.code.toUpperCase();
    if (code === "OCCURRENCE_ALREADY_REPORTED") return "این رخداد قبلاً ثبت شده است؛ برای تغییر زمان از اصلاح استفاده کنید.";
    if (code === "INVALID_ACTUAL_CHRONOLOGY") return "زمان رسیدن باید پس از زمان حرکت باشد؛ زمان وقوع را بررسی کنید.";
    if (code === "INVALID_LEG_TRANSITION") return "برای بخش مسیر مسدود یا لغوشده نمی‌توان رخداد ثبت کرد.";
    if (code === "INVALID_MILESTONE_TRANSITION" && error.message.includes("future")) return "زمان وقوع نمی‌تواند بیش از پنج دقیقه در آینده باشد.";
    if (error.status === 404) return "این محموله دیگر در دسترس نیست.";
    if (error.status === 409) return "اطلاعات عملیات تغییر کرده است. صفحه به‌روزرسانی شد؛ دوباره بررسی کنید.";
    if (error.status === 422 || error.status === 400) {
      if (code.includes("FUTURE")) return "زمان وقوع نمی‌تواند بیش از پنج دقیقه در آینده باشد.";
      if (code.includes("CHRONO") || code.includes("BEFORE") || code.includes("AFTER")) return "ترتیب زمانی رخدادهای مسیر معتبر نیست؛ زمان وقوع را بررسی کنید.";
      if (code.includes("BLOCK") || code.includes("CANCEL")) return "برای بخش مسیر مسدود یا لغوشده نمی‌توان رخداد ثبت کرد.";
      if (code.includes("DUPLICATE") || code.includes("ALREADY") || code.includes("EXIST")) return "این رخداد قبلاً ثبت شده است؛ برای تغییر زمان از اصلاح استفاده کنید.";
      return "اطلاعات واردشده را بررسی کنید.";
    }
    return "انجام این کار ممکن نشد.";
  }
  return "انجام این کار ممکن نشد.";
};
const when = (value: string | null | undefined, locale: string) =>
  formatDualCalendarInstant(value, locale, { fallback: "ثبت نشده", timeZoneName: "short" });
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const invalidIdentityMessage = "پیوند محموله دارای شناسه معتبر نیست.";
const inconsistentIdentityMessage = "شناسه بازگشتی محموله با پیوند بازشده یکسان نیست.";

export default function OperationalShipmentDetail() {
  const params = useParams();
  const routeShipmentPublicId = params.id || "";
  const allowedSections = ["summary","route","stages","cargo","documents","tracking","delivery","closure","history"] as const;
  const legacyHashSections: Record<string, typeof allowedSections[number]> = {
    "#shipment-overview": "summary", "#shipment-next-action": "summary", "#shipment-route": "route",
    "#shipment-cargo": "cargo", "#shipment-operational-details": "documents", "#shipment-deliveries": "delivery",
    "#shipment-operational-stages": "stages",
    "#shipment-closure": "closure", "#shipment-history": "history",
  };
  const activeSection = allowedSections.includes(params.section as typeof allowedSections[number])
    ? params.section!
    : legacyHashSections[window.location.hash] || "route";
  const legacyOverview = !params.section && !window.location.hash;
  const { t, direction, locale, businessLabel, transportLabel } = useI18n();
  const [data, setData] = useState<OperationalShipmentSummary>();
  const [plans, setPlans] = useState<RoutePlanSummary[]>([]);
  const [plan, setPlan] = useState<RoutePlanDetail>();
  const [draftPlan, setDraftPlan] = useState<RoutePlanDetail>();
  const [routePlansLoaded, setRoutePlansLoaded] = useState(false);
  const [cargoTraceOpen, setCargoTraceOpen] = useState(false);
  const [documentRepair,setDocumentRepair]=useState(false);
  useEffect(()=>setDocumentRepair(false),[routeShipmentPublicId]);
  const [referenceTimesOpen, setReferenceTimesOpen] = useState(false);
  const [etaOpen, setEtaOpen] = useState(false);
  const [reportsOpen, setReportsOpen] = useState(false);
  const [deliveriesOpen, setDeliveriesOpen] = useState(false);
  const [closureOpen, setClosureOpen] = useState(false);
  const [timeline, setTimeline] = useState<RouteTimeline>();
  const [exceptions, setExceptions] = useState<RouteException[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState("");
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const generation = useRef(0);
  const knownOwner = useRef<{publicId: string; version: number; label?: string} | null>(null);
  const [authorityEpoch, setAuthorityEpoch] = useState(0);
  const retire = useCallback(() => { generation.current++; }, []);
  const shipmentPublicId = UUID_PATTERN.test(routeShipmentPublicId) ? routeShipmentPublicId : "";
  const activePlan = useMemo(() => plans.find((item) => item.is_active), [plans]);
  // A direct operational shipment can legitimately exist before route planning.
  // The API represents that state as a null current route leg.
  const displayedLegs = plan?.legs || data?.route_legs || (data?.route_leg ? [data.route_leg] : []);

  const load = useCallback(async (revalidateOwner = false): Promise<boolean> => {
    const current = ++generation.current;
    if (!shipmentPublicId) {
      setError(invalidIdentityMessage);
      setData(undefined);
      return false;
    }
    try {
      setRoutePlansLoaded(false);
      setError("");
      const [shipment, projection] = await Promise.all([
        getOperationalShipment(shipmentPublicId),
        getOperationalProjection(shipmentPublicId).catch(() => undefined),
      ]);
      if (current !== generation.current) return false;
      if (!UUID_PATTERN.test(shipment.data.public_id) || shipment.data.public_id.toLowerCase() !== shipmentPublicId.toLowerCase()) {
        setError(inconsistentIdentityMessage);
        setData(undefined);
        return false;
      }
      const [revisions, routeTimeline, routeExceptions] = await Promise.all([
        listRoutePlans(shipmentPublicId),
        getRouteTimeline(shipmentPublicId),
        listRouteExceptions(shipmentPublicId),
      ]);
      if (current !== generation.current) return false;
      const active = revisions.data.find((item) => item.is_active);
      const activeDetail = active ? (await getRoutePlan(shipmentPublicId, active.id)).data : undefined;
      if (current !== generation.current) return false;
      const draft = !active && revisions.data.find((item) => item.status === "draft");
      const draftDetail = draft ? (await getRoutePlan(shipmentPublicId, draft.id)).data : undefined;
      if (current !== generation.current) return false;
      const previous = knownOwner.current;
      if (previous?.publicId === shipmentPublicId && (previous.label !== shipment.data.responsible_expert?.display_name ||
          (revalidateOwner && previous.version !== shipment.data.version))) {
        setAuthorityEpoch(value => value + 1); setReasons({}); setNotice("");
      }
      knownOwner.current = {publicId: shipmentPublicId, version: shipment.data.version, label: shipment.data.responsible_expert?.display_name};
      setData({ ...shipment.data, operational_projection: projection?.data });
      setPlans(revisions.data);
      setTimeline(routeTimeline.data);
      setExceptions(routeExceptions.data);
      setPlan(activeDetail);
      setDraftPlan(draftDetail);
      setRoutePlansLoaded(true);
      return true;
    } catch (caught) {
      if (current !== generation.current) return false;
      setData(undefined); setPlans([]); setPlan(undefined); setDraftPlan(undefined);
      setTimeline(undefined); setExceptions([]); setReasons({}); setNotice("");
      setError(safeError(caught));
      return false;
    }
  }, [shipmentPublicId]);

  useEffect(() => { setData(undefined); void load(); return retire; }, [load, retire]);
  useEffect(() => {
    setCargoTraceOpen(activeSection === "cargo");
    // Keep the specialist reference-time panel lazy on the legacy base route.
    // An explicit /route URL opens it, while the preserved base URL keeps the
    // established overview behavior and does not issue a surprise subrequest.
    setReferenceTimesOpen(params.section === "route");
    setEtaOpen(activeSection === "tracking");
    setReportsOpen(activeSection === "tracking");
    setDeliveriesOpen(activeSection === "delivery");
    setClosureOpen(activeSection === "closure");
  }, [activeSection, params.section]);
  const refreshAuthority = useCallback(() => load(true), [load]);
  useCurrentAuthorityRefresh(refreshAuthority, retire);

  const run = async (name: string, action: () => Promise<unknown>, success: string) => {
    if (pending) return;
    try {
      setPending(name); setError(""); setNotice("");
      const response = await action() as { data?: { replayed?: boolean; updated_checkpoints?: number } };
      const noOp = response?.data?.replayed || response?.data?.updated_checkpoints === 0;
      setNotice(noOp ? "تغییری در زمان‌بندی مسیر لازم نبود." : success);
      await load();
    } catch (caught) {
      setError(safeError(caught));
      if (caught instanceof ApiError && caught.status === 409) {
        await load();
        setError(safeError(caught));
      }
    } finally {
      setPending("");
    }
  };
  const requireReason = (name: string, action: (reason: string) => Promise<unknown>, success: string) => {
    const reason = reasons[name]?.trim();
    if (!reason) { setError("ثبت دلیل الزامی است."); return; }
    void run(name, () => action(reason), success);
  };

  if (!data && !error) return <p className="p-8" role="status">{t("operations.loading")}</p>;
  const documentReadOnly = data?.status === "closed" && !documentRepair;
  const openExceptions = exceptions.filter((item) => item.status === "open");
  const routeSummary = displayedLegs.length
    ? `${displayedLegs[0].origin.display_name || "مبدأ ثبت‌نشده"} ← ${displayedLegs.at(-1)?.destination.display_name || "مقصد ثبت‌نشده"}`
    : "هنوز مسیر عملیاتی ثبت نشده است";
  const routeConnector = direction === "rtl" ? "←" : "→";
  const requestTransportMethod = getRequestTransportMethod(data?.source.request_transport);
  const requestTransportSummary = requestTransportMethod
    ? transportLabel(requestTransportMethod)
    : data?.source.request_transport
      ? t("transport.requestMissing")
      : null;
  const actualRouteTransportSummary = formatRouteTransportModes(
    displayedLegs,
    transportLabel,
    direction,
  );
  const actionableLeg = displayedLegs.find((leg) => "status" in leg && !["blocked", "cancelled", "completed"].includes(leg.status) && (
    (!leg.actual_departure && leg.departure_milestone_id) ||
    (leg.actual_departure && !leg.actual_arrival && leg.arrival_milestone_id)
  ));
  return (
    <main className="shipment-workspace min-h-screen overflow-x-hidden bg-slate-50 p-3 sm:p-4 md:p-8" dir={direction}>
      <a href="#shipment-overview" className="sr-only z-50 rounded bg-white px-4 py-2 text-blue-800 focus:not-sr-only focus:fixed focus:start-4 focus:top-4 focus:ring-2 focus:ring-blue-600">
        پرش به محتوای پرونده حمل
      </a>
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-wrap gap-2"><Link className="inline-flex min-h-11 items-center rounded-md px-2 font-medium text-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600" to="/operations">← بازگشت به فضای کار امروز</Link><Link className="inline-flex min-h-11 items-center rounded-md px-2 font-medium text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600" to="/operations/shipments">→ {t("operations.back")}</Link></div>
        {error && <div role="alert" className="rounded bg-red-50 p-3 text-red-700">{error} <Button variant="link" onClick={() => void load()}>{t("operations.retry")}</Button></div>}
        {notice && <div role="status" className="rounded bg-emerald-50 p-3 text-emerald-800">{notice}</div>}
        {data && <Fragment key={`${data.public_id}:${authorityEpoch}`}>
          <header id="shipment-overview" className="scroll-mt-28 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="flex flex-col gap-4 bg-slate-900 px-4 py-5 text-white sm:flex-row sm:items-start sm:justify-between sm:px-6">
              <div className="min-w-0"><p className="text-sm text-slate-300">فضای کار عملیاتی محموله</p><h1 className="text-2xl font-bold sm:text-3xl">{data.operational_projection?.identity.label || "خلاصه محموله"}</h1><p className="mt-2 text-sm text-slate-300">{typeof data.customer === "string" ? data.customer : data.customer?.display_name || "مشتری ثبت نشده"} · {routeSummary}</p><details className="mt-2 text-xs text-slate-400"><summary className="cursor-pointer">شناسه فنی</summary><bdi className="mt-1 block break-all" dir="ltr">{data.public_id}</bdi></details></div>
              <span className="w-fit rounded-full bg-white/10 px-3 py-1.5 text-sm font-semibold ring-1 ring-white/20">{businessLabel(data.status)}</span>
            </div>
            <div className="grid gap-px bg-slate-100 sm:grid-cols-2 lg:grid-cols-3">
              <div className="bg-white p-4"><p className="text-xs text-slate-500">مشتری و پروژه</p><p className="mt-1 font-semibold">{typeof data.customer === "string" ? data.customer : data.customer?.display_name || "ثبت نشده"}</p>{data.project_public_id ? <Link className="mt-1 inline-block text-xs text-blue-700 underline" to={`/operations/projects/${data.project_public_id}/units`}>مشاهده پروژه مرتبط</Link> : <p className="mt-1 text-xs text-slate-500">{data.source.type === "direct" ? "محموله مستقیم؛ بدون پروژه" : "پروژه عملیاتی ثبت نشده"}</p>}</div>
              <div className="bg-white p-4"><p className="text-xs text-slate-500">مسئول فعلی پرونده</p><p className="mt-1 font-semibold">{data.responsible_expert?.display_name || "نامعلوم"}</p><p className="mt-1 text-xs text-slate-500">مالکیت از خود محموله خوانده می‌شود.</p></div>
              <div className="bg-white p-4"><p className="text-xs text-slate-500">مسیر فعال</p><p className="mt-1 font-semibold">{routeSummary}</p>{activePlan && <p className="mt-1 text-xs text-slate-500">نسخه {activePlan.revision_number}</p>}</div>
              {requestTransportSummary && <div className="bg-white p-4"><p className="text-xs text-slate-500">{t("transport.requestMethod")}</p><p className="mt-1 font-semibold">{requestTransportSummary}</p></div>}
              {actualRouteTransportSummary && <div className="bg-white p-4"><p className="text-xs text-slate-500">{t("transport.actualRoute")}</p><p className="mt-1 font-semibold">{actualRouteTransportSummary}</p></div>}
              <div className="bg-white p-4"><p className="text-xs text-slate-500">آخرین رخداد عملیاتی</p><p className="mt-1 font-semibold">{data.latest_update?.label || (data.recent_events[0] ? businessLabel(data.recent_events[0].event_type) : "هنوز رخدادی ثبت نشده")}</p>{data.latest_update ? <p className="mt-1 text-xs text-slate-500">ثبت: {when(data.latest_update.recorded_at, locale)}</p> : data.recent_events[0] && <p className="mt-1 text-xs text-slate-500">{when(data.recent_events[0].occurred_at, locale)}</p>}</div>
              <div className="bg-white p-4"><p className="text-xs text-slate-500">مرحله فعلی و تازگی پرونده</p><p className="mt-1 font-semibold">{data.current_milestone ? businessLabel(data.current_milestone) : "مرحله جاری ثبت نشده"}</p><p className="mt-1 text-xs text-slate-500">آخرین تغییر پرونده: {when(data.updated_at, locale)}</p></div>
              <div className="bg-white p-4"><p className="text-xs text-slate-500">موارد باز</p><p className="mt-1 font-semibold">{data.open_work_items.length} مورد پیگیری · {openExceptions.length} استثنا</p><p className="mt-1 text-xs text-slate-500">{data.source.type === "direct" ? "عملیات مستقیم" : "درخواست و پیشنهاد پذیرفته‌شده"}</p></div>
            </div>
          </header>

          <OperationsNav />
          <nav aria-label="بخش‌های پرونده حمل" className="sticky top-2 z-20 overflow-x-auto rounded-xl border border-slate-200 bg-white/95 p-2 shadow-sm backdrop-blur">
            <div className="flex min-w-max items-center gap-1">
              {[
                ["summary", "خلاصه"], ["route", "مسیر و اجرا"], ["stages", "مراحل عملیاتی"], ["cargo", "کالا و تخصیص"],
                ["documents", "اسناد"], ["tracking", "پیگیری و ETA"], ["delivery", "تحویل"],
                ["closure", "تکمیل و بستن"], ["history", "تاریخچه"],
              ].map(([section, label]) => <Link key={section} to={`/operations/shipments/${shipmentPublicId}/${section}`} aria-current={activeSection===section?"page":undefined} className={`inline-flex min-h-11 items-center rounded-lg px-3 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 ${activeSection===section?"bg-slate-900 text-white":"text-slate-700 hover:bg-slate-100"}`}>{label}</Link>)}
            </div>
          </nav>
          {(activeSection === "summary" || legacyOverview) && data.operational_projection && <OperationalGuidance projection={data.operational_projection} locale={locale} closed={data.status === "closed"} />}
          <section hidden={activeSection!=="stages"} className="scroll-mt-28"><ShipmentOperationalStages shipmentId={shipmentPublicId}/></section>
          <section hidden={activeSection!=="route"} id="shipment-next-action" aria-labelledby="next-action-heading" className="scroll-mt-28 space-y-3 rounded-2xl border border-blue-200 bg-blue-50/70 p-4 sm:p-5">
            <div><p className="text-xs font-semibold text-blue-700">اقدام جاری</p><h2 id="next-action-heading" className="text-xl font-bold">{data.status === "closed" ? "اصلاح و تکمیل سوابق" : "اقدامات مجاز بعدی"}</h2><p className="mt-1 text-sm text-slate-600">اقدامات این بخش فقط بر پایه وضعیت و مجوزهای ثبت‌شده در سامانه نمایش داده می‌شوند.</p></div>
            {data.status !== "closed" && routePlansLoaded && !activePlan && <RouteAuthoringSection shipmentId={shipmentPublicId} draft={draftPlan} hasDraft={plans.some((item) => item.status === "draft")} reload={load} />}
            {activePlan && <div className="grid gap-3 lg:grid-cols-2">{displayedLegs.map((leg, index) => {
              const actionable = !["blocked", "cancelled", "completed"].includes(leg.status);
              const action = actionable && !leg.actual_departure && leg.departure_milestone_id ? {label:"ثبت حرکت",id:leg.departure_milestone_id} : actionable && leg.actual_departure && !leg.actual_arrival && leg.arrival_milestone_id ? {label:"ثبت رسیدن",id:leg.arrival_milestone_id} : null;
              if (!action || (!legacyOverview && actionableLeg && leg.id !== actionableLeg.id)) return null;
              return <OperationalPermission key={leg.id} permission="milestone_event.create"><div className={`rounded-xl border bg-white p-4 ${leg.id===actionableLeg?.id?"border-blue-300 ring-1 ring-blue-100":"border-slate-200"}`}><p className="mb-2 text-sm text-slate-600">{leg.id===actionableLeg?.id?"اقدام اصلی · ":"اقدام بعدی مسیر · "}بخش {index+1}: {leg.origin.display_name} {routeConnector} {leg.destination.display_name}</p><OccurrenceTimeAction id={`leg-${leg.id}-time`} action={action.label} pending={!!pending} onSubmit={(occurredAt) => void run(`leg-${leg.id}`, () => recordOperationalEvent(shipmentPublicId, action.id, occurredAt, key()), "رخداد بخش مسیر ثبت شد.")} /></div></OperationalPermission>;
            })}</div>}
          </section>
          <section hidden={!(["route","cargo","tracking","delivery"] as string[]).includes(activeSection)} id="shipment-route" aria-labelledby="route-workspace-heading" className="scroll-mt-28 space-y-3">
          <div><p className="text-xs font-semibold text-slate-500">فضای کار محموله</p><h2 id="route-workspace-heading" className="text-xl font-bold">{activeSection==="cargo"?"کالا و تخصیص":activeSection==="tracking"?"پیگیری و زمان تقریبی رسیدن":activeSection==="delivery"?"تحویل":"مسیر و اجرای عملیاتی"}</h2></div>
          <Card hidden={activeSection!=="route"} className="border-slate-200 shadow-sm">
            <CardHeader><CardTitle>{t("operations.activeRoutePlan")}</CardTitle><p className="text-sm text-slate-500">برنامه مسیر: بخش مشترک، شاخه‌های مقصد و وضعیت برنامه‌ریزی‌شده</p></CardHeader>
            <CardContent className="space-y-3 text-sm">
              {!displayedLegs.length ? <p className="text-slate-600">برنامه مسیر هنوز آماده نشده است.</p> : displayedLegs.map((leg, index) => {
                return <article key={leg.id} className="min-w-0 rounded-xl border border-slate-200 p-4"><div className="flex flex-wrap items-center justify-between gap-2"><strong>بخش مسیر {index + 1}{leg.branch_label ? ` · ${leg.branch_label}` : ""}</strong><span className="rounded-full bg-slate-100 px-2 py-1 text-xs">{businessLabel(leg.status || "planned")}</span></div><p className="text-xs text-slate-500">{leg.parent_route_leg_id ? `شاخه از بخش ${plan?.legs.find((item) => item.id === leg.parent_route_leg_id)?.sequence_number ?? "—"}` : "بخش آغازین مشترک"}</p><p className="mt-2 break-words font-medium">{leg.origin.display_name || "ثبت نشده"} {routeConnector} {leg.destination.display_name || "ثبت نشده"}</p><p className="text-slate-600">{leg.transport_mode ? transportLabel(leg.transport_mode) : "روش حمل هنوز مشخص نیست"}</p><p className="mt-2 text-xs text-slate-600">برنامه‌ریزی‌شده: {when(leg.planned_departure, locale)} {routeConnector} {when(leg.planned_arrival, locale)}</p>{"projected_departure" in leg && <p className="text-xs text-slate-600">برآورد فعلی: {when(leg.projected_departure, locale)} {routeConnector} {when(leg.projected_arrival, locale)}</p>}{"actual_departure" in leg && <p className="text-xs text-slate-600">زمان واقعی رخدادهای قدیمی بخش: {when(leg.actual_departure, locale)} {routeConnector} {when(leg.actual_arrival, locale)}</p>}</article>;
              })}
              {!!plan?.cargo_destinations?.length && <section className="space-y-2 border-t pt-3"><h3 className="font-semibold">مقصد شاخه‌ای کالاها</h3><p className="text-slate-600">هر کالا به مقصد برنامه‌ریزی‌شده خودش متصل است؛ کالا و محموله تکثیر نشده‌اند.</p>{plan.cargo_destinations.map((destination) => { const leg = plan.legs.find((item) => item.id === destination.destination_route_leg_id); return <p className="rounded bg-slate-50 p-2" key={destination.id}><strong>{destination.cargo_display_name || "کالای ثبت‌شده"}</strong> · {leg?.branch_label || leg?.destination.display_name || "مقصد ثبت‌شده"}</p>; })}</section>}
            </CardContent>
          </Card>
          {activeSection==="route" && activePlan && <RouteStageTransportExecutionSection shipmentId={shipmentPublicId} planId={activePlan.id} closed={data.status === "closed"} />}
          {activeSection==="route" && !!plans.length && <details open={params.section==="route"||referenceTimesOpen} className="rounded-2xl border bg-white" onToggle={event=>setReferenceTimesOpen(event.currentTarget.open)}><summary className="cursor-pointer p-4 font-semibold">زمان مرجع و مبنای برنامه</summary>{(params.section==="route"||referenceTimesOpen)&&<RouteReferenceTimes shipmentId={shipmentPublicId} plans={plans}/>}</details>}
          {activeSection==="cargo" && activePlan && <details open className="rounded border bg-white" onToggle={(event) => setCargoTraceOpen(event.currentTarget.open)}>
            <summary className="cursor-pointer px-4 py-4 text-lg font-semibold">تخصیص و مسیر هر کالا</summary>
            {cargoTraceOpen && <div className="border-t p-3 sm:p-4"><CargoAllocationTraceSection shipmentId={shipmentPublicId} planId={activePlan.id} closed={data.status === "closed"} /></div>}
          </details>}
          {activeSection==="route" && plan && <RouteActualSection shipmentId={shipmentPublicId} plan={plan} reload={load} />}
          {activeSection==="tracking" && <details open className="rounded-xl border bg-white" onToggle={event => setEtaOpen(event.currentTarget.open)}><summary className="cursor-pointer p-3 font-semibold sm:p-4">زمان تقریبی رسیدن کالاها</summary>{etaOpen && <ShipmentEta shipmentId={shipmentPublicId} />}</details>}
          {activeSection==="tracking" && <details open className="rounded-xl border bg-white" onToggle={event => setReportsOpen(event.currentTarget.open)}><summary className="cursor-pointer p-3 font-semibold sm:p-4">گزارش موقعیت و تغییرات حمل</summary>{reportsOpen && <div className="border-t p-3 sm:p-4"><ReportedFactsSection shipmentId={shipmentPublicId} /></div>}</details>}
          {activeSection==="delivery" && <details open id="shipment-deliveries" className="rounded-xl border bg-white" onToggle={event => setDeliveriesOpen(event.currentTarget.open)}><summary className="cursor-pointer p-3 font-semibold sm:p-4">تحویل کالاها</summary>{deliveriesOpen && <div className="border-t p-3 sm:p-4"><DeliverySection shipmentId={shipmentPublicId} /></div>}</details>}
          </section>

          <details hidden={activeSection!=="cargo"} open={activeSection==="cargo"} id="shipment-cargo" className="scroll-mt-28 rounded border bg-white">
            <summary className="cursor-pointer px-4 py-4 text-lg font-semibold">جزئیات کالا، وسیله حمل و پیگیری</summary>
            <div className="border-t p-3 sm:p-4"><ShipmentCargoItems shipmentPublicId={data.public_id} projectPublicId={data.project_public_id} legacyDescription={(data as OperationalShipmentSummary & {legacy_cargo_description?:string|null}).legacy_cargo_description} stageScoped={Boolean(activePlan)} closed={data.status === "closed"} /></div>
          </details>

          <details hidden={!(["route","documents"] as string[]).includes(activeSection)} id="shipment-operational-details" className="scroll-mt-28 rounded border bg-white" open={activeSection==="documents"||legacyOverview}>
            <summary className="cursor-pointer px-4 py-4 text-lg font-semibold">{activeSection==="documents"?"اسناد و مراجع حمل":"جزئیات اجرای مسیر"}</summary>
            <div className="space-y-5 border-t p-3 sm:p-4">
              {activeSection==="route" && <div className="grid gap-4 lg:grid-cols-2">
                <Card><CardHeader><CardTitle>انحراف زمانی مسیر و استثناهای عملیاتی</CardTitle></CardHeader><CardContent className="space-y-2 text-sm">{(timeline?.delays?.length || exceptions.length) ? <>{timeline?.delays?.map((delay) => <p key={delay.checkpoint_id}>انحراف زمانی محاسبه‌شده مسیر: {Math.ceil(delay.seconds / 60)} دقیقه</p>)}{exceptions.map((item) => <p key={item.id}>استثنای عملیاتی ثبت‌شده · {businessLabel(item.status)}{item.reason ? ` · ${item.reason}` : ""}</p>)}</> : <p className="text-slate-600">انحراف زمانی یا استثنای عملیاتی ثبت‌شده‌ای وجود ندارد.</p>}</CardContent></Card>
              </div>}
              <div className="space-y-5">
              {activeSection === "route" && data.source.type !== "direct" && <RequestedEndpointComparison requested={data.operational_projection?.identity.requested_endpoints}
                origin={{label: displayedLegs[0]?.origin.display_name || "ثبت نشده", reference: displayedLegs[0]?.origin.canonical_reference}}
                destination={{label: displayedLegs.at(-1)?.destination.display_name || "ثبت نشده", reference: displayedLegs.at(-1)?.destination.canonical_reference}} />}
              <Card hidden={activeSection!=="route"}><CardHeader><CardTitle>{t("operations.sourceCard")}</CardTitle></CardHeader><CardContent className="grid gap-2 sm:grid-cols-2"><p>{t("operations.source")}: {data.source.type === "direct" ? "عملیات مستقیم" : "درخواست"}</p><p>{t("operations.requestLabel")}: {data.source.request_public_id ? <Link className="text-blue-700 underline" to={`/expert/requests/${data.source.request_public_id}`}>{t("common.request")}</Link> : t("operations.notApplicable")}</p><p>{t("operations.quoteLabel")}: {data.source.accepted_quote_id ? "پیشنهاد پذیرفته‌شده مرتبط" : t("operations.notApplicable")}</p></CardContent></Card>

          <section hidden={activeSection!=="route"} aria-labelledby="issues-heading" className="space-y-3">
            <div><p className="text-xs font-semibold text-slate-500">کنترل جاری</p><h2 id="issues-heading" className="text-xl font-bold">مسائل عملیاتی</h2><p className="mt-1 text-sm text-slate-600">انحراف زمانی، تأخیر، استثنا و موارد پیگیری در کنار هم دیده می‌شوند اما ماهیت مستقل خود را حفظ می‌کنند.</p></div>
            <OperationalConditionsSection shipmentPublicId={data.public_id} />
            <OperationalActionsSection shipmentPublicId={data.public_id} closed={data.status === "closed"} />
          </section>

          {activeSection==="route" && data.source.type !== "direct" && /^[0-9a-f]{8}-[0-9a-f-]{27}$/i.test(data.public_id) && <section aria-labelledby="project-execution-heading" className="space-y-3"><h2 id="project-execution-heading" className="text-xl font-bold">اجرای پروژه</h2><OperationalExecutionSection shipmentPublicId={data.public_id} shipmentVersion={data.version} closed={data.status === "closed"} /></section>}

          <section hidden={activeSection!=="documents"} aria-labelledby="documents-heading" className="space-y-3">
            <div><p className="text-xs font-semibold text-slate-500">اسناد و شواهد</p><h2 id="documents-heading" className="text-xl font-bold">اسناد محموله</h2><p className="mt-1 text-sm text-slate-600">ابتدا مدارک مورد نیاز و کسری‌ها، سپس فایل‌های موجود را بررسی کنید. شماره‌های حمل در بخش جداگانه پایین قرار دارند.</p></div>
            {data.status === "closed"&&<div className="rounded border bg-slate-50 p-3"><p>پرونده بسته شده است؛ نمایش اسناد فقط خواندنی است. اصلاح سوابق، تصمیم بستن یا عملیات انجام‌شده را تغییر نمی‌دهد.</p><Button variant="outline" className="mt-2" onClick={()=>setDocumentRepair(value=>!value)}>{documentRepair?"بازگشت به نمایش فقط خواندنی":"اصلاح سوابق اسناد"}</Button>{documentRepair&&<p className="mt-2 text-sm text-amber-800">فقط تکمیل یا اصلاح اسناد تاریخی با مجوز فعلی؛ عملیات تازه مجاز نیست.</p>}</div>}
            {data.source.type !== "direct" && /^[0-9a-f]{8}-[0-9a-f-]{27}$/i.test(data.public_id) && <DocumentReadinessSection readOnly={documentReadOnly} shipmentPublicId={data.public_id} shipmentVersion={data.version} projectReference={data.project_public_id} sourceRequestId={data.source.request_public_id} />}
            <ShipmentDocuments shipmentPublicId={data.public_id} readOnly={documentReadOnly} historicalRepair={data.status === "closed" && documentRepair}/><details className="rounded border bg-white"><summary className="cursor-pointer p-4 font-semibold">شماره‌ها و مراجع حمل</summary><ShipmentExternalReferences shipmentPublicId={data.public_id} requestId={data.source.request_public_id} readOnly={documentReadOnly}/></details>
          </section>

          <details hidden={activeSection!=="route"} className="rounded-xl border bg-white"><summary className="cursor-pointer px-4 py-4 text-lg font-semibold">جزئیات مالی محموله</summary><div className="border-t p-3 sm:p-4">{/^[0-9a-f]{8}-[0-9a-f-]{27}$/i.test(data.public_id) && <OperationalPermission permission="economics.revenue.view"><ShipmentEconomicsSection shipmentPublicId={data.public_id} sourceType={data.source.type} /></OperationalPermission>}</div></details>

          <Card hidden={activeSection!=="route"}>
            <CardHeader><CardTitle>{t("operations.timelineReconciliation")}</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <p>نسخه مسیر {timeline?.route_plan_revision ?? "—"} · نسخه به‌روزرسانی برآورد {timeline?.reconciliation_version ?? "—"} · آخرین به‌روزرسانی {when(timeline?.reconciled_at, locale)}</p>
              <div className="overflow-x-auto rounded border">
                <table className="min-w-[760px] w-full text-sm">
                  <thead><tr className="bg-slate-100 text-start"><th className="p-2">نقطه کنترل</th><th>برنامه‌ریزی‌شده</th><th>برآورد جاری</th><th>زمان واقعی</th><th>زمان مبنا / منبع</th><th>انحراف زمانی محاسبه‌شده</th></tr></thead>
                  <tbody>{(timeline?.planned || []).map((row) => {
                    const projected = timeline?.projected.find((item) => item.checkpoint_id === row.checkpoint_id);
                    const actual = timeline?.actual.find((item) => item.checkpoint_id === row.checkpoint_id);
                    const effective = timeline?.effective.find((item) => item.checkpoint_id === row.checkpoint_id);
                    const delay = timeline?.delays.find((item) => item.checkpoint_id === row.checkpoint_id);
                    return <tr key={row.checkpoint_id} className="border-t align-top">
                      <td className="p-2">نقطه کنترل</td>
                      <td>{when(row.arrival_at, locale)}<br />{when(row.departure_at, locale)}</td>
                      <td>{when(projected?.arrival_at, locale)}<br />{when(projected?.departure_at, locale)}</td>
                      <td>{when(actual?.arrival_at, locale)}<br />{when(actual?.departure_at, locale)}</td>
                      <td>{when(effective?.arrival_at, locale)} ({businessLabel(effective?.arrival_source)})<br />{when(effective?.departure_at, locale)} ({businessLabel(effective?.departure_source)})</td>
                      <td>{delay ? `${Math.ceil(delay.seconds / 60)} دقیقه` : "بدون انحراف زمانی"}</td>
                    </tr>;
                  })}</tbody>
                </table>
              </div>
              {!timeline?.planned.length && <p>{t("operations.noTimeline")}</p>}
              {activePlan && <OperationalPermission permission="route_plan.replan"><Button className="min-h-11" disabled={!!pending} onClick={() => void run("timeline", () => reconcileRouteTimeline(shipmentPublicId, activePlan.version, key()), "برآورد زمانی مسیر به‌روز شد.")}>{pending === "timeline" ? "در حال به‌روزرسانی…" : "به‌روزرسانی برآورد زمانی"}</Button></OperationalPermission>}
            </CardContent>
          </Card>

          <Card hidden={activeSection!=="route"}>
            <CardHeader><CardTitle>{t("operations.lifecycle")}</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {!plan?.checkpoints.length && <p>{t("operations.noCheckpoints")}</p>}
              {plan?.checkpoints.map((checkpoint) => <article key={checkpoint.id} className="rounded border p-3">
                <h3 className="font-semibold">نقطه کنترل {checkpoint.sequence_number} · {businessLabel(checkpoint.checkpoint_type)} · {businessLabel(checkpoint.status)} · نسخه {checkpoint.version}</h3>
                <p>ورود/خروج برنامه‌ریزی‌شده: {when(checkpoint.planned_arrival_at, locale)} / {when(checkpoint.planned_departure_at, locale)}</p>
                <p>برآورد جاری ورود/خروج: {when(checkpoint.projected_arrival_at, locale)} / {when(checkpoint.projected_departure_at, locale)}</p>
                <p>زمان واقعی ورود/خروج: {when(checkpoint.actual_arrival_at, locale)} / {when(checkpoint.actual_departure_at, locale)}</p>
                <div className="my-3 flex flex-wrap gap-2">
                  <OperationalPermission permission="checkpoint.report">
                    {(checkpoint.status === "planned" || checkpoint.status === "approaching") && <OccurrenceTimeAction id={`checkpoint-${checkpoint.id}-arrive`} action={direction === "rtl" ? "ثبت رسیدن" : "Report arrival"} pending={!!pending} onSubmit={(occurredAt) => void run(`${checkpoint.id}-arrive`, () => commandRouteCheckpoint(shipmentPublicId, checkpoint.id, "arrive", occurredAt, checkpoint.version, key()), direction === "rtl" ? "رسیدن ثبت شد." : "Arrival recorded.")} />}
                    {(checkpoint.status === "arrived" || checkpoint.status === "processing") && <OccurrenceTimeAction id={`checkpoint-${checkpoint.id}-processing`} action={direction === "rtl" ? "ثبت پایان عملیات" : "Report processing complete"} pending={!!pending} onSubmit={(occurredAt) => void run(`${checkpoint.id}-complete-processing`, () => commandRouteCheckpoint(shipmentPublicId, checkpoint.id, "complete-processing", occurredAt, checkpoint.version, key()), direction === "rtl" ? "پایان عملیات ثبت شد." : "Processing completion recorded.")} />}
                    {checkpoint.status === "ready_to_depart" && <OccurrenceTimeAction id={`checkpoint-${checkpoint.id}-depart`} action={direction === "rtl" ? "ثبت حرکت" : "Report departure"} pending={!!pending} onSubmit={(occurredAt) => void run(`${checkpoint.id}-depart`, () => commandRouteCheckpoint(shipmentPublicId, checkpoint.id, "depart", occurredAt, checkpoint.version, key()), direction === "rtl" ? "حرکت ثبت شد." : "Departure recorded.")} />}
                  </OperationalPermission>
                </div>
                <div className="grid gap-3 lg:grid-cols-2">{checkpoint.milestones.map((milestone) => {
                  const reasonKey = `milestone-${milestone.id}`;
                  return <div key={milestone.id} className="rounded bg-slate-50 p-3">
                    <strong>{businessLabel(milestone.type)}</strong> · وضعیت تأیید: {businessLabel(milestone.verification_state)} · نسخه مرحله {milestone.version}
                    <p>برنامه‌ریزی‌شده {when(milestone.planned_at, locale)} · برآورد جاری {when(milestone.projected_at, locale)} · زمان واقعی {when(milestone.occurred_at, locale)}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {milestone.verification_state === "reported" && <OperationalPermission permission="checkpoint.verify"><Button className="min-h-11" disabled={!!pending} onClick={() => void run(`verify-${milestone.id}`, () => verifyRouteMilestone(shipmentPublicId, checkpoint.id, milestone.id, milestone.version, key()), direction === "rtl" ? "مرحله تأیید یا دوباره تأیید شد." : "Milestone verified or re-verified.")}>{direction === "rtl" ? "تأیید / تأیید دوباره" : "Verify / re-verify"}</Button></OperationalPermission>}
                    </div>
                    {milestone.verification_state === "verified" && <OperationalPermission permission="milestone.correct"><div className="mt-2 space-y-2"><Input aria-label={direction === "rtl" ? `دلیل اصلاح ${businessLabel(milestone.type)}` : `Correction reason for ${milestone.type}`} placeholder={direction === "rtl" ? "دلیل اصلاح (الزامی)" : "Correction reason (required)"} value={reasons[reasonKey] || ""} onChange={(event) => setReasons({...reasons,[reasonKey]:event.target.value})}/><OccurrenceTimeAction id={`correction-${milestone.id}-time`} action={direction === "rtl" ? "ثبت اصلاح" : "Correct"} pending={!!pending} onSubmit={(occurredAt) => requireReason(reasonKey, (reason) => correctRouteMilestone(shipmentPublicId, checkpoint.id, milestone.id, occurredAt, reason, milestone.version, key()), direction === "rtl" ? "اصلاح مرحله ثبت شد." : "Milestone corrected.")} /></div></OperationalPermission>}
                  </div>;
                })}</div>
              </article>)}
            </CardContent>
          </Card>

          <Card hidden={activeSection!=="route"}>
            <CardHeader><CardTitle>{direction === "rtl" ? "بازبرنامه‌ریزی و نسخه‌های مسیر" : "Replan and route versions"}</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {plans.map((item) => <div key={item.id} className="rounded border p-3"><strong>نسخه مسیر {item.revision_number}</strong> · {item.is_active ? "نسخه فعال" : businessLabel(item.status)} · نسخه رکورد {item.version}{item.created_from_plan_id ? " · جایگزین نسخه پیشین" : ""}<br />{item.replan_reason && `دلیل بازبرنامه‌ریزی: ${item.replan_reason}`}<br /><span className="text-sm text-slate-600">واقعیت‌های پیمایش: {item.actual_traversal_count ?? 0} · انحراف‌های ثبت‌شده: {item.actual_deviation_count ?? 0}</span></div>)}
              {data.status !== "closed" && activePlan && <OperationalPermission permission="route_plan.replan"><div className="flex flex-col gap-2 sm:flex-row"><Input aria-label="دلیل بازبرنامه‌ریزی" placeholder="دلیل بازبرنامه‌ریزی (الزامی)" value={reasons.replan || ""} onChange={(event) => setReasons({...reasons,replan:event.target.value})}/><Button className="min-h-11" disabled={!!pending} onClick={() => requireReason("replan", (reason) => replanRoute(shipmentPublicId, activePlan.id, activePlan.version, reason, key()), "نسخه فعال تازه مسیر ایجاد شد.")}>بازبرنامه‌ریزی بخش‌های آینده</Button></div><p className="text-sm text-slate-600">بخش‌های انجام‌شده فقط خواندنی می‌مانند و فقط بخش‌های آینده به نسخه تازه منتقل می‌شوند.</p></OperationalPermission>}
            </CardContent>
          </Card>

          <Card hidden={activeSection!=="route"}>
            <CardHeader><CardTitle>{t("operations.routeExceptions")}</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {activePlan && <OperationalPermission permission="route_exception.manage"><Button className="min-h-11" disabled={!!pending} onClick={() => void run("exceptions", () => reconcileRouteExceptions(shipmentPublicId, activePlan.version, key()), "موارد استثنای مسیر به‌روز شد.")}>به‌روزرسانی موارد استثنای مسیر</Button></OperationalPermission>}
              {!exceptions.length && <p>{t("operations.noExceptions")}</p>}
              {exceptions.map((exception) => {
                const reasonKey = `exception-${exception.id}`;
                return <article key={exception.id} className="rounded border p-3">
                  <strong>مورد استثنای مسیر</strong> · {businessLabel(exception.status)} · شدت {businessLabel(exception.severity)} · نسخه {exception.version}
                  <p>{exception.checkpoint_id == null ? "در سطح محموله" : "مرتبط با نقطه کنترل"}</p>
                  <p>شناسایی {when(exception.detected_at, locale)} · مهلت رسیدگی {when(exception.due_at, locale)} · رفع {when(exception.resolved_at, locale)}</p>
                  <p>منبع رفع: {exception.resolution_source ? businessLabel(exception.resolution_source) : "رفع نشده"} · دلیل: {exception.resolution_reason || exception.reason || "ثبت نشده"}</p>
                  {exception.status === "open" && <OperationalPermission permission="route_exception.manage"><div className="mt-2 flex flex-col gap-2 sm:flex-row"><Input aria-label={`دلیل رفع ${exception.id}`} placeholder="دلیل رفع (الزامی)" value={reasons[reasonKey] || ""} onChange={(event) => setReasons({...reasons,[reasonKey]:event.target.value})}/><Button className="min-h-11" disabled={!!pending} onClick={() => requireReason(reasonKey, (reason) => resolveRouteException(exception.id, exception.version, reason, key()), "رفع استثنای عملیاتی ثبت شد.")}>ثبت رفع دستی</Button></div></OperationalPermission>}
                </article>;
              })}
              <h3 className="font-semibold">{t("operations.workQueue")}</h3>
              {!data.open_work_items.length && <p>در حال حاضر موردی نیازمند رسیدگی نیست.</p>}
              {data.open_work_items.map((item) => <div key={item.id} className="rounded border p-3"><strong>مورد نیازمند رسیدگی</strong> · {businessLabel(item.status)} · مهلت {when(item.due_at, locale)} · نسخه {item.version}</div>)}
            </CardContent>
          </Card>

              </div>
            </div>
          </details>
          <details hidden={activeSection!=="closure"} open={activeSection==="closure"} id="shipment-closure" className="scroll-mt-28 rounded-2xl border bg-white" onToggle={event=>setClosureOpen(event.currentTarget.open)}><summary className="min-h-11 cursor-pointer p-4 text-lg font-semibold">بررسی و بستن پرونده</summary>{closureOpen&&<ShipmentClosure shipment={shipmentPublicId} reload={load}/>}</details>
          <details hidden={activeSection!=="summary"} className="rounded-2xl border bg-white p-4">
            <summary className="min-h-11 cursor-pointer font-bold">مسئول و سابقه انتقال</summary>
            <OwnerTransferDetails shipment={data.public_id} />
          </details>
          <section hidden={activeSection!=="history"} id="shipment-history" aria-labelledby="history-heading" className="scroll-mt-28 space-y-3">
            <div><p className="text-xs font-semibold text-slate-500">روایت کامل و تغییرناپذیر</p><h2 id="history-heading" className="text-xl font-bold">تاریخچه یکپارچه محموله</h2></div>
            <UnifiedShipmentHistory shipmentPublicId={data.public_id} />
          </section>
        </Fragment>}
      </div>
    </main>
  );
}

function OwnerTransferDetails({shipment}: {shipment: string}) {
  const container = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const details = container.current?.closest("details");
    const changed = () => setOpen(Boolean(details?.open));
    details?.addEventListener("toggle", changed); changed();
    return () => details?.removeEventListener("toggle", changed);
  }, []);
  return <div ref={container} className="mt-3">{open && <ShipmentOwnerTransfer shipment={shipment} />}</div>;
}
