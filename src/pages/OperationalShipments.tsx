import { useEffect, useState } from "react";
import { Link } from "react-router";
import OperationsNav from "@/components/OperationsNav";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, listOperationalShipments, type OperationalShipmentSummary } from "@/lib/api";
import { useI18n } from "@/i18n";
import OperationalAnyPermission from "@/components/OperationalAnyPermission";

const filterLabels: Record<string, string> = {
 status: "وضعیت محموله", customer: "مشتری", origin: "مبدأ", destination: "مقصد",
 overdue: "فقط موارد دارای تأخیر", date_from: "از تاریخ", date_to: "تا تاریخ",
};

export default function OperationalShipments(){
 const {t,direction,locale}=useI18n(); const [rows,setRows]=useState<OperationalShipmentSummary[]>([]); const [loading,setLoading]=useState(true); const [error,setError]=useState(""); const [page,setPage]=useState(1); const [more,setMore]=useState(false); const [filters,setFilters]=useState({status:"",customer:"",origin:"",destination:"",overdue:"",date_from:"",date_to:""});
 const load=()=>{setLoading(true);setError("");const q=new URLSearchParams({...filters,page:String(page)});listOperationalShipments(q.toString()).then(r=>{setRows(r.data);setMore(r.meta.has_more)}).catch(e=>setError(e instanceof ApiError&&e.status===403?t("operations.forbidden"):e instanceof Error?e.message:t("operations.error"))).finally(()=>setLoading(false));};
 // Pagination reloads automatically; edited filters apply only via the explicit button.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 useEffect(load,[page]);
 const customerLabel=(row:OperationalShipmentSummary)=>typeof row.customer==="string"?row.customer:row.customer?.display_name||t("operations.notApplicable");
 return <main className="min-h-screen overflow-x-hidden bg-slate-50 p-3 sm:p-5 md:p-8" dir={direction}><div className="mx-auto max-w-7xl space-y-5"><OperationsNav/><header className="flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-2xl font-bold">{t("operations.shipmentsTitle")}</h1><p>{t("operations.shipmentsSubtitle")}</p></div><OperationalAnyPermission permissions={["operational_shipment.create_direct","operational_shipment.create_from_quote","operational_shipment.create"]}><Button asChild><Link to="/operations/shipments/new">{t("operations.newOperation")}</Link></Button></OperationalAnyPermission></header>
 <Card><CardContent className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4">{Object.entries(filters).map(([name,value])=><div className="min-w-0" key={name}><Label htmlFor={`filter-${name}`}>{filterLabels[name]}</Label><Input id={`filter-${name}`} aria-label={filterLabels[name]} value={value} onChange={e=>setFilters({...filters,[name]:e.target.value})}/></div>)}<Button onClick={()=>{setPage(1);load()}} disabled={loading}>{t("operations.applyFilters")}</Button></CardContent></Card>
 {error&&<div role="alert" className="rounded bg-red-50 p-3 text-red-700">{error}<Button variant="link" onClick={load}>{t("operations.retry")}</Button></div>}{loading?<p role="status" aria-live="polite">{t("operations.loading")}</p>:!rows.length?<p className="rounded bg-white p-8 text-center">محموله عملیاتی منطبق با فیلترها یافت نشد. فیلترها را پاک کنید یا نخستین محموله عملیاتی را ایجاد کنید.</p>:<div className="grid gap-4 md:grid-cols-2">{rows.map(r=><Link aria-label={`مشاهده محموله عملیاتی ${customerLabel(r)}`} className="min-w-0 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary" key={r.public_id} to={`/operations/shipments/${r.public_id}`}><Card className="h-full"><CardContent className="min-w-0 space-y-2 p-5"><div className="flex flex-wrap justify-between gap-2"><strong className="truncate">{customerLabel(r)}</strong><span className="rounded-full border px-2 py-0.5 text-xs">{r.source.type==="direct"?t("operations.source.direct"):t("operations.source.quote")}</span></div><p className="break-words">{r.route_leg.origin.display_name} → {r.route_leg.destination.display_name}</p><p>{new Date(r.route_leg.planned_departure).toLocaleString(locale)} — {new Date(r.route_leg.planned_arrival).toLocaleString(locale)}</p><p>{t("operations.projectOptional")}: <bdi dir="ltr">{r.project_public_id||"—"}</bdi></p><p>{t("operations.source")}: <bdi dir="ltr">{r.source.shipment_request_id??t("operations.notApplicable")}</bdi> · {t("operations.acceptedQuote")}: <bdi dir="ltr">{r.source.accepted_quote_id??t("operations.notApplicable")}</bdi></p><p>{r.current_milestone||"—"} · {r.open_work_item_count}</p></CardContent></Card></Link>)}</div>}<div className="flex items-center justify-center gap-2"><Button aria-label="صفحه قبل" disabled={page===1||loading} onClick={()=>setPage(p=>p-1)}>‹</Button><span>صفحه {page}</span><Button aria-label="صفحه بعد" disabled={!more||loading} onClick={()=>setPage(p=>p+1)}>›</Button></div></div></main>;
}
