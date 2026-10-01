import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Clock3, PackageSearch } from "lucide-react";
import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useCurrentAuthorityRefresh } from "@/hooks/useCurrentAuthorityRefresh";
import { ApiError, getOperationalWorkspace, type OperationalWorkspaceSnapshot } from "@/lib/api";

const attentionLabels = {
  BLOCKER: "مانع",
  NEEDS_ACTION: "نیازمند اقدام",
  WARNING: "هشدار",
  INFORMATIONAL: "اطلاعاتی",
} as const;

export default function OperationalPriorityOverview() {
  const [snapshot, setSnapshot] = useState<OperationalWorkspaceSnapshot>();
  const [error, setError] = useState("");
  const generation = useRef(0);
  const retire = useCallback(() => { generation.current++; }, []);
  const load = useCallback(async () => {
    const current = ++generation.current;
    try {
      const value = await getOperationalWorkspace(5);
      if (current === generation.current) { setSnapshot(value); setError(""); }
    } catch (caught) {
      if (current === generation.current) setError(caught instanceof ApiError && caught.status === 403 ? "" : "نمای عملیاتی اکنون در دسترس نیست.");
    }
  }, []);
  useEffect(() => { void load(); return retire; }, [load, retire]);
  useCurrentAuthorityRefresh(load, retire);
  if (error) return <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{error}</p>;
  if (!snapshot) return <p className="rounded-xl bg-white p-4 text-sm text-slate-500" role="status">در حال آماده‌سازی اولویت‌های عملیاتی…</p>;
  const { data, meta } = snapshot;
  const freshnessProblem = meta.attention_projection && meta.attention_projection.state !== "FRESH";
  return <section aria-labelledby="expert-operational-priority-heading" className="space-y-4">
    <div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-sm font-bold text-blue-700">صف عملیاتی من</p><h2 id="expert-operational-priority-heading" className="text-xl font-black text-slate-950">امروز چه چیزی باید جلو برود؟</h2><p className="mt-1 text-sm text-slate-600">اولویت‌ها از واقعیت‌های همان محموله و اختیار جاری شما ساخته شده‌اند.</p></div><Button asChild variant="outline"><Link to="/operations">باز کردن فضای کار کامل</Link></Button></div>
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Card><CardContent className="flex items-center gap-3 p-4"><PackageSearch className="h-6 w-6 text-blue-700"/><div><p className="text-xs text-slate-500">فعال</p><strong className="text-xl">{meta.active_shipment_count}</strong></div></CardContent></Card>
      <Card><CardContent className="flex items-center gap-3 p-4"><AlertTriangle className="h-6 w-6 text-amber-700"/><div><p className="text-xs text-slate-500">نیازمند توجه</p><strong className="text-xl">{meta.needs_attention_count ?? "—"}</strong></div></CardContent></Card>
      <Card><CardContent className="flex items-center gap-3 p-4"><CheckCircle2 className="h-6 w-6 text-emerald-700"/><div><p className="text-xs text-slate-500">اقدام روشن</p><strong className="text-xl">{meta.ready_now_count ?? "—"}</strong></div></CardContent></Card>
      <Card><CardContent className="flex items-center gap-3 p-4"><Clock3 className={`h-6 w-6 ${freshnessProblem ? "text-amber-700" : "text-slate-500"}`}/><div><p className="text-xs text-slate-500">تازگی Attention</p><strong className="text-sm">{freshnessProblem ? "نیازمند بررسی" : "به‌روز"}</strong></div></CardContent></Card>
    </div>
    {!!data.active_shipments.length && <div className="divide-y overflow-hidden rounded-2xl border bg-white">{data.active_shipments.slice(0,5).map(shipment => {
      const projection = shipment.operational_projection;
      const action = projection?.recommended_action;
      return <div key={shipment.public_id} className="grid gap-3 p-4 md:grid-cols-[1.3fr_1fr_auto] md:items-center"><div><strong>{projection?.identity.label || "محموله عملیاتی"}</strong><p className="mt-1 text-xs text-slate-500">{typeof shipment.customer === "string" ? shipment.customer : shipment.customer?.display_name || "مشتری ثبت نشده"} · {projection?.stage_progress.current?.display_name_fa || "مرحله نامشخص"}</p></div><div className="text-sm">{projection?.attention[0] ? <p className="text-amber-900"><span className="mb-1 inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-bold text-slate-700">{attentionLabels[projection.attention[0].category]}</span><b className="block">{projection.attention[0].label}</b><span className="mt-1 block text-xs text-slate-500">{projection.attention[0].reason}</span></p> : <p className="text-emerald-800">مانع ثبت‌شده‌ای دیده نشد</p>}</div>{action ? <Button asChild><Link to={action.href}>{action.label}</Link></Button> : <Button asChild variant="outline"><Link to={`/operations/shipments/${shipment.public_id}`}>مشاهده</Link></Button>}</div>;
    })}</div>}
  </section>;
}
