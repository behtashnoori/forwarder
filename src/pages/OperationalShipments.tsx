import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, ArrowLeft, CheckCircle2, CircleDashed, Route as RouteIcon } from "lucide-react";
import { Link } from "react-router";
import { useCurrentAuthorityRefresh } from "@/hooks/useCurrentAuthorityRefresh";
import OperationsNav from "@/components/OperationsNav";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, listOperationalShipments, type OperationalShipmentSummary } from "@/lib/api";
import { useI18n } from "@/i18n";
import OperationalAnyPermission from "@/components/OperationalAnyPermission";
import OperationalPermission from "@/components/OperationalPermission";
import SavedViewControls from "@/components/SavedViewControls";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";

const filterLabels: Record<string, string> = {
  status: "وضعیت محموله", customer: "مشتری", origin: "مبدأ", destination: "مقصد",
  overdue: "دارای تأخیر (true/false)", date_from: "از تاریخ", date_to: "تا تاریخ",
};

type QueueFilter = "all" | "attention" | "ready" | "unconfigured";

const attentionLabels = {
  BLOCKER: "مانع",
  NEEDS_ACTION: "نیازمند اقدام",
  WARNING: "هشدار",
  INFORMATIONAL: "اطلاعاتی",
} as const;

export default function OperationalShipments() {
  const { t, direction, locale, businessLabel } = useI18n();
  const [rows, setRows] = useState<OperationalShipmentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [more, setMore] = useState(false);
  const [activeOnly, setActiveOnly] = useState(true);
  const [queueFilter, setQueueFilter] = useState<QueueFilter>("all");
  const [filters, setFilters] = useState({status:"", customer:"", origin:"", destination:"", overdue:"", date_from:"", date_to:""});
  const translate = useRef(t);
  useEffect(() => { translate.current = t; }, [t]);
  const appliedFilters = useRef(filters);
  const generation = useRef(0);
  const retire = useCallback(() => { generation.current++; }, []);
  const load = useCallback((activeFilters = appliedFilters.current, onlyActive = activeOnly) => {
    const current = ++generation.current;
    setLoading(true); setError("");
    const q = new URLSearchParams({...activeFilters, page:String(page), ...(onlyActive ? {active:"true"} : {})});
    void listOperationalShipments(q.toString()).then(result => {
      if (current === generation.current) { setRows(result.data); setMore(result.meta.has_more); }
    }).catch(caught => {
      if (current === generation.current) {
        setRows([]); setMore(false);
        setError(caught instanceof ApiError && caught.status === 403 ? translate.current("operations.forbidden") : translate.current("operations.error"));
      }
    }).finally(() => { if (current === generation.current) setLoading(false); });
  }, [page, activeOnly]);
  useEffect(() => { load(); return retire; }, [load, retire]);
  const refresh = useCallback(() => load(), [load]);
  useCurrentAuthorityRefresh(refresh, retire);

  const visibleRows = useMemo(() => rows.filter(row => {
    const projection = row.operational_projection;
    if (queueFilter === "attention") return Boolean(projection?.readiness.blocker_count || projection?.readiness.warning_count);
    if (queueFilter === "ready") return Boolean(projection?.recommended_action && !projection.readiness.blocker_count);
    if (queueFilter === "unconfigured") return Boolean(projection && (!projection.stage_progress.configured || projection.tasks.some(task => task.status === "UNKNOWN")));
    return true;
  }), [rows, queueFilter]);
  const customerLabel = (row: OperationalShipmentSummary) => typeof row.customer === "string" ? row.customer : row.customer?.display_name || t("operations.notApplicable");
  const routeLabel = (row: OperationalShipmentSummary) => row.route_summary
    ? `${row.route_summary.origin.display_name} ${direction === "rtl" ? "←" : "→"} ${row.route_summary.destination.display_name}`
    : row.route_leg ? `${row.route_leg.origin.display_name} ${direction === "rtl" ? "←" : "→"} ${row.route_leg.destination.display_name}` : "مسیر هنوز تعریف نشده است";
  const applyFilters = (next = filters) => { appliedFilters.current = next; if (page === 1) load(next, activeOnly); else setPage(1); };

  return <main className="min-h-screen overflow-x-hidden bg-slate-50 p-3 sm:p-5 md:p-8" dir={direction}>
    <div className="mx-auto max-w-7xl space-y-5">
      <OperationsNav />
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div><p className="text-sm font-bold text-blue-700">صف اول عملیات</p><h1 className="text-2xl font-black">محموله‌ها بر اساس اولویت اقدام</h1><p className="mt-1 text-sm text-slate-600">موانع و پیگیری‌های باز نخست؛ سپس پرونده‌های قدیمی‌تر. هر ردیف فقط یک اقدام پیشنهادی دارد.</p></div>
        <div className="flex flex-wrap gap-2"><Button type="button" variant={activeOnly ? "default" : "outline"} aria-pressed={activeOnly} onClick={() => { setPage(1); setActiveOnly(value => !value); }}>{activeOnly ? "نمایش همه وضعیت‌ها" : "بازگشت به محموله‌های فعال"}</Button><OperationalAnyPermission permissions={["operational_shipment.create_direct","operational_shipment.create_from_quote","operational_shipment.create"]}><Button asChild><Link to="/operations/shipments/new">{t("operations.newOperation")}</Link></Button></OperationalAnyPermission></div>
      </header>

      <Card><CardContent className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4">{Object.entries(filters).map(([name,value]) => <div className="min-w-0" key={name}><Label htmlFor={`filter-${name}`}>{filterLabels[name]}</Label><Input id={`filter-${name}`} aria-label={filterLabels[name]} value={value} onChange={event => setFilters({...filters,[name]:event.target.value})}/></div>)}<Button onClick={() => applyFilters()} disabled={loading}>{t("operations.applyFilters")}</Button></CardContent></Card>
      <OperationalPermission permission="personal_dashboard.read"><SavedViewControls filters={filters} onApply={next => { setFilters(next); applyFilters(next); }} /></OperationalPermission>

      <div className="flex flex-wrap gap-2" role="group" aria-label="فیلتر صف عملیاتی">
        {([['all','همه'],['attention','نیازمند توجه'],['ready','آماده اقدام'],['unconfigured','داده نامشخص']] as const).map(([value,label]) => <Button key={value} variant={queueFilter===value?"default":"outline"} onClick={() => setQueueFilter(value)} aria-pressed={queueFilter===value}>{label}</Button>)}
      </div>

      {error && <div role="alert" className="rounded bg-red-50 p-3 text-red-700">{error}<Button variant="link" onClick={() => load()}>{t("operations.retry")}</Button></div>}
      {loading ? <p role="status" aria-live="polite">{t("operations.loading")}</p> : !visibleRows.length ? <p className="rounded bg-white p-8 text-center">در این نمای عملیاتی محموله‌ای منطبق با فیلترها وجود ندارد.</p> : <section aria-label="صف محموله‌ها" className="space-y-3">
        {visibleRows.map(row => {
          const projection = row.operational_projection;
          const action = projection?.recommended_action;
          const attention = projection?.attention[0];
          return <article key={row.public_id} className={`rounded-2xl border bg-white p-4 shadow-sm sm:p-5 ${projection?.priority.band === "BLOCKED" ? "border-amber-300" : "border-slate-200"}`}>
            <div className="grid gap-4 lg:grid-cols-[1.25fr_1fr_1fr_auto] lg:items-center">
              <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><Link className="text-lg font-bold text-slate-950 hover:text-blue-800" aria-label={`مشاهده محموله عملیاتی ${customerLabel(row)}`} to={`/operations/shipments/${row.public_id}`}>{projection?.identity.label || customerLabel(row)}</Link><span className="rounded-full border px-2 py-0.5 text-xs">{businessLabel(row.status)}</span>{projection?.priority.band === "BLOCKED" && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-900">نیازمند توجه</span>}</div>{projection?.identity.label&&projection.identity.label!==customerLabel(row)&&<p className="mt-1 text-sm text-slate-600">{customerLabel(row)}</p>}<p className="mt-1 text-sm text-slate-600">مسئول فعلی پرونده: {row.responsible_expert?.display_name || "نامعلوم"}</p><p className="mt-2 flex items-center gap-2 text-sm"><RouteIcon className="h-4 w-4 shrink-0 text-blue-700"/>{routeLabel(row)}</p><p className="mt-1 text-xs text-slate-500">آخرین به‌روزرسانی: {row.latest_update?`${row.latest_update.label} · ${formatDualCalendarInstant(row.latest_update.recorded_at,locale,{fallback:"نامعلوم"})}`:"رویدادی ثبت نشده است"}</p><details className="mt-2 text-xs text-slate-400"><summary className="cursor-pointer">شناسه فنی</summary><bdi dir="ltr">{row.public_id}</bdi></details></div>
              <div><p className="text-xs text-slate-500">پیشرفت عملیات</p><p className="mt-1 font-semibold">{projection?.stage_progress.current?.display_name_fa || (projection?.stage_progress.total ? "مراحل کامل" : "نامشخص")}</p><div className="mt-2 h-1.5 rounded-full bg-slate-100"><div className="h-full rounded-full bg-blue-700" style={{width:`${projection?.stage_progress.total ? projection.stage_progress.completed * 100 / projection.stage_progress.total : 0}%`}}/></div><p className="mt-1 text-xs text-slate-500">پیشرفت عملیات: {projection?.stage_progress.completed ?? 0} از {projection?.stage_progress.total || "—"} مرحله · آمادگی پرونده: {projection?.readiness.percent ?? 0}٪</p></div>
              <div><p className="text-xs text-slate-500">مهم‌ترین موضوع</p>{attention ? <div className="mt-1 flex gap-2 text-sm text-amber-900"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0"/><span><span className="mb-1 inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-bold text-slate-700">{attentionLabels[attention.category]}</span><strong className="block">{attention.label}</strong><span className="mt-1 block text-xs text-slate-500">{attention.reason}</span></span></div> : <p className="mt-1 flex items-center gap-2 text-sm text-emerald-800"><CheckCircle2 className="h-4 w-4"/>مانع ثبت‌شده‌ای دیده نشد</p>}<p className="mt-2 text-xs text-slate-500">آخرین تغییر: {formatDualCalendarInstant(row.updated_at, locale, {fallback:"نامعلوم"})}</p></div>
              <div className="lg:w-48">{action ? <><p className="text-xs font-bold text-blue-700">اقدام بعدی</p><p className="mt-1 text-sm font-bold">{action.label}</p><Button asChild className="mt-3 w-full"><Link to={action.href}>انجام اقدام <ArrowLeft className="ms-2 h-4 w-4"/></Link></Button></> : <><p className="flex items-center gap-2 text-sm text-slate-600"><CircleDashed className="h-4 w-4"/>اقدامی پیشنهاد نشده</p><Button asChild variant="outline" className="mt-3 w-full"><Link to={`/operations/shipments/${row.public_id}`}>مشاهده خلاصه</Link></Button></>}</div>
            </div>
          </article>;
        })}
      </section>}
      <div className="flex items-center justify-center gap-2"><Button aria-label="صفحه قبل" disabled={page===1||loading} onClick={() => setPage(value => value-1)}>‹</Button><span>صفحه {page}</span><Button aria-label="صفحه بعد" disabled={!more||loading} onClick={() => setPage(value => value+1)}>›</Button></div>
    </div>
  </main>;
}
