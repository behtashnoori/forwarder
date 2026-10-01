import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getShipmentHistory, type ShipmentHistoryPage } from "@/lib/api";
import { useI18n } from "@/i18n";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Link } from "react-router";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import { formatUnitSymbol } from "@/lib/formatQuantity";

const categories: Record<string, string> = {
  SHIPMENT: "محموله", ROUTE: "مسیر", ROUTE_OCCURRENCE: "رخداد مسیر",
  CHECKPOINT: "نقطه کنترل", EXECUTION_STAGE: "مرحله عملیاتی", DELAY: "تأخیرها",
  EXCEPTION: "استثناها", WORK_ITEM: "موارد نیازمند رسیدگی", REFERENCE: "مراجع عملیاتی",
  DOCUMENT: "اسناد", AUDIT: "اقدامات عملیاتی",
  EXECUTION: "اجرا", CARGO: "کالا و تخصیص", TRACKING: "پیگیری", DELIVERY: "تحویل",
  OPERATIONAL_STAGE: "مراحل عملیاتی", CLOSURE: "تکمیل و بستن",
};

export default function UnifiedShipmentHistory({ shipmentPublicId }: { shipmentPublicId: string }) {
  const { businessLabel, locale } = useI18n();
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState("ALL");
  const [data, setData] = useState<ShipmentHistoryPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);
  const requestVersion=useRef(0);
  const load = useCallback(async () => {
    const version=++requestVersion.current;
    setLoading(true); setError(""); setForbidden(false);
    try { const response=await getShipmentHistory(shipmentPublicId, page, 50, category);if(version===requestVersion.current)setData(response.data); }
    catch (caught) {
      if(version!==requestVersion.current)return;
      if (caught instanceof ApiError && caught.status === 403) setForbidden(true);
      else setError("دریافت تاریخچه عملیات ممکن نشد. دوباره تلاش کنید.");
    }
    finally { if(version===requestVersion.current)setLoading(false); }
  }, [shipmentPublicId, page, category]);
  useEffect(() => { void load(); }, [load]);
  const displayTime = (value: string) => formatDualCalendarInstant(value, locale, { timeZoneName: "short" });
  const visible = data?.items.filter(item => category === "ALL" || item.category === category) || [];
  return <Card dir="rtl" aria-label="تاریخچه عملیات حمل">
    <CardHeader><div className="flex flex-wrap items-center justify-between gap-2"><CardTitle>تاریخچه عملیات حمل</CardTitle><Button variant="outline" disabled={loading} onClick={() => void load()}>به‌روزرسانی تاریخچه</Button></div></CardHeader>
    <CardContent className="space-y-4">
      {loading ? <p role="status">در حال دریافت تاریخچه…</p> : forbidden ? <p role="status">شما به تاریخچه این محموله دسترسی ندارید.</p> : error ? <div role="alert">{error} <Button variant="outline" onClick={() => void load()}>تلاش مجدد</Button></div> : <>
        <label className="block max-w-sm">دسته‌بندی
          <select className="mt-1 min-h-11 w-full rounded border px-2" value={category} onChange={event => {setPage(1);setCategory(event.target.value);}}>
            <option value="ALL">همه</option>{Object.entries(categories).map(([code, name]) => <option key={code} value={code}>{name}</option>)}
          </select>
        </label>
        {!data?.total ? <p>در محدوده دسترسی شما سابقه‌ای برای این محموله ثبت نشده است.</p> : !visible.length ? <p>در این دسته سابقه‌ای ثبت نشده است.</p> : <ol className="space-y-3">
          {visible.map(item => <li key={item.history_id} className="min-w-0 rounded border p-3">
            <div className="flex flex-wrap items-start justify-between gap-2"><strong>{item.business_label || businessLabel(item.business_type)}</strong><span className="rounded bg-slate-100 px-2 py-1 text-xs">{categories[item.category] || "اقدام عملیاتی"}</span></div>
            <p>{item.occurred_at ? <>زمان وقوع: <time dateTime={item.occurred_at} dir="auto">{displayTime(item.occurred_at)}</time></> : item.recorded_at ? <>زمان ثبت: <time dateTime={item.recorded_at} dir="auto">{displayTime(item.recorded_at)}</time></> : "زمان در منبع ثبت نشده است."}</p>
            {item.actor && <p>اقدام‌کننده: {item.actor}</p>}
            {item.execution_label && <p>اجرا: {item.execution_label}</p>}
            {item.stage_label && <p>مرحله عملیاتی: {item.stage_label}</p>}
            {item.cargo_label && <p>کالا: {item.cargo_label}</p>}
            {item.before_quantity != null && item.after_quantity != null && <p>مقدار: {Number(item.before_quantity).toLocaleString("fa-IR")} ← {Number(item.after_quantity).toLocaleString("fa-IR")}</p>}
            {item.quantity != null && <p>مقدار: {Number(item.quantity).toLocaleString("fa-IR")} {formatUnitSymbol(item.uom_symbol || "", locale)}</p>}
            {item.destination_label && <p>مقصد: {item.destination_label}</p>}
            <details className="mt-2 text-sm text-slate-600"><summary className="cursor-pointer">جزئیات و سابقه ثبت</summary>
            {item.occurred_at && item.recorded_at && <p>ثبت سیستمی: <time dateTime={item.recorded_at}>{displayTime(item.recorded_at)}</time></p>}
            {item.source_is_projection && <p>این مورد از وضعیت عملیات شناسایی شده است.</p>}
            {item.source_type && <p>منبع: {item.source_type === "direct" ? "عملیات مستقیم" : "درخواست و پیشنهاد پذیرفته‌شده"}</p>}
            {item.request_public_id && <p><Link className="text-blue-700 underline" to={`/expert/requests/${item.request_public_id}`}>مشاهده درخواست مبدأ</Link></p>}
            {item.route_revision != null && <p>نسخه مسیر: {item.route_revision}</p>}
            {item.source_route_revision != null && <p>بازنگری از نسخه مسیر {item.source_route_revision}</p>}
            {item.source_milestone_public_id && <p>این مرحله از بازنگری پیشین مسیر منتقل شده است.</p>}
            {item.milestone_type && <p>مرحله: {businessLabel(item.milestone_type)}</p>}
            {item.document_label && <p>سند: {item.document_label}</p>}
            {item.reference_type_label && <p>نوع مرجع: {item.reference_type_label}</p>}
            {item.reference_value && <p className="break-all">شماره مرجع: <bdi dir="ltr">{item.reference_value}</bdi></p>}
            {item.supersedes_reference_public_id && <p>این مرجع جایگزین مرجع پیشین شده است.</p>}
            {item.evidence_attached && <p>مدرک مرتبط ثبت شده است.</p>}
            {item.reason_label && <p className="break-words">دلیل: {item.reason_label}</p>}
            {item.note && <p className="break-words">یادداشت: {item.note}</p>}
            {item.supersedes_event_public_id && <p>این رخداد جایگزین گزارش پیشین شده است.</p>}
            {item.related_event_public_id && <p>این تصمیم به گزارش وقوع پیشین مرتبط است.</p>}
            {item.relationship_status === "UNRESOLVED" && <p>ارتباط با گزارش پیشین در داده‌های موجود مشخص نیست.</p>}
            </details>
          </li>)}
        </ol>}
        {data && data.total > data.per_page && <nav className="flex items-center gap-2" aria-label="صفحه‌بندی تاریخچه"><Button variant="outline" disabled={page <= 1} onClick={() => setPage(value => value - 1)}>صفحه قبل</Button><span>صفحه {page}</span><Button variant="outline" disabled={!data.has_more} onClick={() => setPage(value => value + 1)}>صفحه بعد</Button></nav>}
      </>}
    </CardContent>
  </Card>;
}
