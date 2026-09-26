import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import CustomerPortalLayout from "@/components/CustomerPortalLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { downloadCustomerSharedDocument } from "@/lib/customerPortalApi";
import type { CustomerFactPage, CustomerReport, CustomerShipmentDetail, CustomerShipmentList } from "@/lib/customerShipmentApi";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import { usePrivateCustomerRead } from "@/hooks/usePrivateCustomerRead";
import { CargoEtaPanel } from "@/components/CargoEta";

const statuses = { planned: "برنامه‌ریزی‌شده", in_progress: "در حال انجام", completed: "تکمیل‌شده", closed: "بسته‌شده", cancelled: "لغوشده" };
const contexts = { SHIPMENT: "پرونده حمل", CARGO: "کالای شما", ROUTE_LEG: "مرحله مسیر", EXECUTION_UNIT: "اجرای حمل", DELIVERY: "تحویل کالای شما" };
const time = (value: string) => formatDualCalendarInstant(value, "fa-IR");
const amount = (value: string | null) => value === null ? "نامشخص" : Number(value).toLocaleString("fa-IR", { maximumFractionDigits: 6 });

function Pages({ value, onChange, label }: { value: Pick<CustomerFactPage<unknown>, "page" | "has_prev" | "has_next">; onChange: (page: number) => void; label: string }) {
  return <nav aria-label={label} className="flex flex-wrap items-center gap-2 pt-3">
    <Button size="sm" variant="outline" disabled={!value.has_prev} onClick={() => onChange(value.page - 1)}>صفحه قبل</Button>
    <span className="text-sm">صفحه {value.page.toLocaleString("fa-IR")}</span>
    <Button size="sm" variant="outline" disabled={!value.has_next} onClick={() => onChange(value.page + 1)}>صفحه بعد</Button>
  </nav>;
}

function Report({ report }: { report: CustomerReport }) {
  return <article className="space-y-2 rounded-lg border p-3">
    <p className="font-medium">{report.message}</p>
    {report.reported_location && <p>موقعیت گزارش‌شده: {report.reported_location}</p>}
    <p className="text-sm text-slate-600">{report.source_label} · {report.scope_label} · گزارش عملیاتی</p>
    <p className="text-xs text-slate-600">وقوع: {time(report.occurred_at)}<br />آخرین ثبت: {time(report.recorded_at)}</p>
    {report.status === "SUPERSEDED" ? <p className="text-sm text-amber-800">این گزارش اصلاح شده است.</p> : report.is_correction && <p className="text-sm text-slate-600">گزارش اصلاحی</p>}
  </article>;
}

export default function CustomerPortalShipments() {
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState(params.get("q") || "");
  const query = new URLSearchParams({ page: params.get("page") || "1", q: params.get("q") || "" });
  const { data, loading, error, refresh } = usePrivateCustomerRead<CustomerShipmentList>(`/api/customer/shipments?${query}`);
  return <CustomerPortalLayout privateNav><section dir="rtl" className="space-y-5 break-words">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><h1 className="text-2xl font-bold">حمل‌های من</h1><p className="mt-2 text-sm text-slate-600">پرونده‌های حمل مربوط به کالاهای مجاز شما</p></div><Button variant="outline" onClick={refresh}>تازه‌سازی</Button></div>
    <form className="flex flex-wrap gap-2" onSubmit={event => { event.preventDefault(); setParams({ q: search.trim(), page: "1" }); }}>
      <label className="min-w-0 flex-1">جست‌وجوی حمل<Input aria-label="جست‌وجوی حمل" maxLength={100} placeholder="نام کالای خود یا شناسه حمل" value={search} onChange={event => setSearch(event.target.value)} /></label>
      <Button type="submit" className="self-end">جست‌وجو</Button>
    </form>
    {error && <p role="alert" className="rounded-lg bg-red-50 p-4 text-red-800">{error}</p>}
    {loading ? <p role="status">در حال دریافت حمل‌ها…</p> : data && <>
      <p className="text-sm text-slate-600">{data.pagination.total.toLocaleString("fa-IR")} پرونده در دسترس شما</p>
      {!data.items.length ? <Card><CardContent className="p-6">حملی در این فهرست برای شما در دسترس نیست.</CardContent></Card> : data.items.map(item => <Card key={item.public_id}>
        <CardHeader><CardTitle className="text-lg">پرونده حمل <span dir="ltr">{item.public_id.slice(0, 8)}</span></CardTitle><p className="text-sm">وضعیت کلی پرونده: {statuses[item.status]}</p></CardHeader>
        <CardContent className="flex flex-wrap items-center justify-between gap-3"><div className="space-y-2 text-sm text-slate-600"><p>ایجاد: {time(item.created_at)}</p>{item.shared_transport && <p>این حمل به‌صورت مشترک انجام می‌شود.</p>}</div>
          <Button asChild variant="outline"><Link to={`/customer/shipments/${item.public_id}`}>مشاهده پرونده حمل</Link></Button></CardContent>
      </Card>)}
      <Pages label="صفحه‌بندی حمل‌ها" value={data.pagination} onChange={page => setParams({ q: params.get("q") || "", page: String(page) })} />
    </>}
  </section></CustomerPortalLayout>;
}

export function CustomerPortalShipmentDetail() {
  const { shipmentId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const query = new URLSearchParams(Object.fromEntries(["documents_page", "deliveries_page", "timeline_page"].map(key => [key, params.get(key) || "1"])));
  const { data, loading, error, refresh, invalidate } = usePrivateCustomerRead<CustomerShipmentDetail>(`/api/customer/shipments/${encodeURIComponent(shipmentId)}?${query}`);
  const page = (name: string, value: number) => { const next = new URLSearchParams(params); next.set(name, String(value)); setParams(next); };
  const download = (id: string, filename: string) => void downloadCustomerSharedDocument(id, filename).catch(error => invalidate(error instanceof Error ? error.message : "سند در دسترس نیست."));
  const cargoName = (id: string) => data?.cargo.find(item => item.public_id === id)?.label || "کالای شما";
  return <CustomerPortalLayout privateNav><div dir="rtl" className="space-y-5 break-words">
    <div className="flex flex-wrap items-center justify-between gap-2"><Button asChild variant="ghost"><Link to="/customer/shipments">بازگشت به حمل‌های من</Link></Button><Button variant="outline" onClick={refresh}>تازه‌سازی</Button></div>
    {error && <p role="alert" className="rounded-lg bg-red-50 p-4 text-red-800">{error}</p>}
    {loading ? <p role="status">در حال دریافت پرونده حمل…</p> : data && <>
      <Card><CardHeader><h1 className="text-2xl font-semibold leading-none tracking-tight">پرونده حمل <span dir="ltr">{data.public_id.slice(0, 8)}</span></h1></CardHeader><CardContent className="space-y-2">
        <p>وضعیت کلی پرونده: <strong>{statuses[data.status]}</strong></p>
        {data.shared_transport && <p className="rounded-lg bg-blue-50 p-3 text-blue-900">این حمل به‌صورت مشترک انجام می‌شود.</p>}
        <p className="text-sm text-slate-600">وضعیت و مقدار تحویل هر کالا در بخش همان کالا نمایش داده می‌شود.</p>
      </CardContent></Card>
      <section aria-labelledby="my-cargo" className="space-y-3"><h2 id="my-cargo" className="text-xl font-bold">کالاهای من</h2><div className="grid gap-3 md:grid-cols-2">{data.cargo.map(item => <Card key={item.public_id}>
        <CardHeader><CardTitle className="text-lg">{item.label}</CardTitle><p className="text-sm text-slate-600">{item.customer_label} · {item.type_label} · {item.uom_symbol}</p></CardHeader>
        <CardContent className="space-y-4"><dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">{[["درخواستی", item.requested], ["برنامه‌ریزی‌شده", item.planned], ["واقعی شناخته‌شده", item.known_actual], ["تحویل‌شده", item.delivered], ["مانده", item.remaining]].map(([label, value]) => <div key={label}><dt className="text-slate-600">{label}</dt><dd className="mt-1 font-semibold">{amount(value)} {value !== null && item.uom_symbol}</dd></div>)}</dl>
          {!item.has_delivery && <p className="text-sm text-slate-600">هنوز تحویلی برای این کالا ثبت نشده است.</p>}
          <CargoEtaPanel shipmentId={shipmentId} cargoId={item.public_id} customer />
          {item.excess !== null && Number(item.excess) > 0 && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">تحویل ثبت‌شده {amount(item.excess)} {item.uom_symbol} بیش از مقدار واقعی شناخته‌شده است.</p>}
        </CardContent></Card>)}</div></section>
      <Card><CardHeader><h2 className="text-2xl font-semibold leading-none tracking-tight">مسیر کالاهای من</h2><p className="text-sm text-slate-600">برنامه مسیر و نقاط اصلی مربوط به کالاهای شما</p></CardHeader><CardContent className="space-y-4">{data.routes.map(route => <section key={route.cargo_public_id} className="space-y-2"><h3 className="font-semibold">{cargoName(route.cargo_public_id)}</h3>
        {route.legs.length ? <ol className="space-y-2">{route.legs.map((leg, index) => <li key={index} className="rounded-lg bg-slate-50 p-3 text-sm"><span>{leg.origin || "مبدأ تعریف نشده"} ← {leg.destination || "مقصد تعریف نشده"}</span><p className="mt-1 text-slate-600">{leg.mode || "روش حمل تعریف نشده"}</p></li>)}</ol> : <p className="text-sm text-slate-600">مسیر این کالا هنوز تعریف نشده است.</p>}
      </section>)}</CardContent></Card>
      <Card><CardHeader><h2 className="text-2xl font-semibold leading-none tracking-tight">آخرین موقعیت‌های گزارش‌شده</h2><p className="text-sm text-slate-600">گزارش‌های مجاز برای بخش‌های مختلف حمل؛ هر گزارش زمان و منبع خودش را دارد.</p></CardHeader><CardContent className="space-y-3">{data.reported_locations.length ? data.reported_locations.map(report => <Report key={report.public_id} report={report} />) : <p>موقعیت گزارش‌شده‌ای در دسترس نیست.</p>}{data.reported_locations.length === 100 && <p className="text-sm">۱۰۰ گزارش اخیر نمایش داده می‌شود.</p>}</CardContent></Card>
      <Card><CardHeader><h2 className="text-2xl font-semibold leading-none tracking-tight">اسناد حمل من</h2></CardHeader><CardContent className="space-y-3">{data.documents.items.length ? data.documents.items.map(item => <article key={item.public_id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3"><div><strong dir="ltr">{item.filename}</strong><p className="text-sm text-slate-600">{contexts[item.context_type]} · نسخه {item.version}</p></div><Button variant="outline" onClick={() => download(item.public_id, item.filename)}>دریافت سند</Button></article>) : <p>سندی در این صفحه برای شما در دسترس نیست.</p>}<Pages label="صفحه‌بندی اسناد" value={data.documents} onChange={value => page("documents_page", value)} /></CardContent></Card>
      <Card><CardHeader><h2 className="text-2xl font-semibold leading-none tracking-tight">تحویل‌های من</h2></CardHeader><CardContent className="space-y-3">{data.deliveries.items.length ? data.deliveries.items.map(item => <article key={item.public_id} className="space-y-2 rounded-lg border p-3"><h3 className="font-semibold">{cargoName(item.cargo_public_id)}</h3><p>{amount(item.quantity)} {item.uom_symbol} · مقصد: {item.destination_text}</p><p className="text-xs text-slate-600">وقوع: {time(item.occurred_at)}<br />ثبت: {time(item.recorded_at)}</p><p className="text-sm">{item.status === "SUPERSEDED" ? "اصلاح شده؛ در جمع جاری محاسبه نمی‌شود" : item.is_correction ? "تحویل اصلاحی جاری" : "تحویل جاری"} · نسخه {item.revision}</p>
        {item.evidence.length ? item.evidence.map(document => <Button key={document.public_id} variant="outline" className="h-auto whitespace-normal" onClick={() => download(document.public_id, document.filename)}>مدرک تحویل · نسخه {document.version}</Button>) : <p className="text-sm text-slate-600">مدرکی برای این تحویل در دسترس شما نیست.</p>}
      </article>) : <p>تحویلی در این صفحه ثبت نشده است.</p>}<Pages label="صفحه‌بندی تحویل‌ها" value={data.deliveries} onChange={value => page("deliveries_page", value)} /></CardContent></Card>
      <Card><CardHeader><h2 className="text-2xl font-semibold leading-none tracking-tight">تاریخچه حمل</h2></CardHeader><CardContent className="space-y-3">{data.timeline.items.length ? data.timeline.items.map(report => <Report key={report.public_id} report={report} />) : <p>گزارشی در این صفحه برای شما در دسترس نیست.</p>}<Pages label="صفحه‌بندی تاریخچه" value={data.timeline} onChange={value => page("timeline_page", value)} /></CardContent></Card>
    </>}
  </div></CustomerPortalLayout>;
}
