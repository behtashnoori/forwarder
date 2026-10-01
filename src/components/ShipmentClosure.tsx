import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import OperationalPermission from "@/components/OperationalPermission";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { closeShipment, getClosure, type ClosureView, type ClosureItem } from "@/lib/closureApi";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";

const when = (value: string) => formatDualCalendarInstant(value, "fa", {timeZoneName:"short"});
const sourceSections:Record<string,string>={ACTUAL_QUANTITY_KNOWN:"shipment-cargo",ALL_CARGO_DELIVERED:"shipment-deliveries",
  REQUIRED_DOCUMENTS_READY:"documents-heading",NO_OPEN_EXCEPTIONS:"issues-heading",NO_OPEN_FOLLOW_UPS:"issues-heading",
  NO_OPEN_OPERATIONAL_WORK:"issues-heading",MODE_UNDEFINED:"next-action-heading",
  FINAL_DELIVERY_EXISTS:"shipment-deliveries",REQUIRED_OPERATIONAL_STAGES_COMPLETE:"shipment-operational-stages",
  NO_BLOCKING_OPERATIONAL_ISSUE:"issues-heading",ACTUAL_CARGO_UNKNOWN:"shipment-cargo",
  ACTUAL_ALLOCATION_DIFFERS_FROM_PLANNED:"shipment-cargo",DELIVERED_DIFFERS_FROM_PLANNED:"shipment-deliveries",
  OPTIONAL_DOCUMENTS_ABSENT:"documents-heading",ETA_UNAVAILABLE:"shipment-route",NON_BLOCKING_OPERATIONAL_WARNINGS:"issues-heading"};
function openSource(id:string) {
  const target=document.getElementById(id);
  let parent:HTMLElement|null=target;
  while(parent){if(parent instanceof HTMLDetailsElement)parent.open=true;parent=parent.parentElement;}
  requestAnimationFrame(()=>target?.scrollIntoView({block:"start"}));
}
export function ClosureItems({items}: {items: ClosureItem[]}) {
  const ordered=[...items].sort((a,b)=>Number(a.state==="PASS")-Number(b.state==="PASS") || Number(b.mandatory)-Number(a.mandatory));
  return <ul className="space-y-2">{ordered.map(item=><li key={item.code} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border p-3">
    <span>{item.label}<small className="mx-2 text-slate-500">{item.mandatory?"مسدودکننده":"هشدار غیرمسدودکننده"}</small></span>
    <strong className={item.state==="PASS"?"text-emerald-700":"text-amber-800"}>{item.state==="PASS"?(item.mandatory?"کامل":"هشدار ندارد"):item.state==="UNKNOWN"?"نامشخص":item.mandatory?"کامل نیست":"نیازمند توجه"}</strong>
    {sourceSections[item.code]&&<a className="text-sm text-blue-700 underline" href={`#${sourceSections[item.code]}`} onClick={()=>openSource(sourceSections[item.code])}>مشاهده اطلاعات جاری</a>}
  </li>)}</ul>;
}

export default function ShipmentClosure({shipment, reload}: {shipment:string; reload:()=>Promise<unknown>}) {
  const [view,setView]=useState<ClosureView|null>(null);
  const [error,setError]=useState("");
  const [reason,setReason]=useState("");
  const [confirm,setConfirm]=useState<"NORMAL"|"EXCEPTIONAL"|null>(null);
  const [busy,setBusy]=useState(false);
  const generation=useRef(0);
  const abort=useRef<AbortController|null>(null);
  const command=useRef({signature:"",key:""});
  const load=useCallback(async()=>{
    const revision=++generation.current; abort.current?.abort(); abort.current=new AbortController();
    setView(null);setConfirm(null);
    try {const result=await getClosure(shipment,abort.current.signal);if(revision===generation.current)setView(result.data);}
    catch {if(revision===generation.current)setError("دریافت بررسی بستن ممکن نشد؛ دوباره تلاش کنید.");}
  },[shipment]);
  useEffect(()=>{
    void load();
    const invalidate=()=>{generation.current++;};
    const changed=()=>{if(document.hidden){generation.current++;abort.current?.abort();setView(null);setConfirm(null);}else void load();};
    const focus=()=>{void load();};
    document.addEventListener("visibilitychange",changed);window.addEventListener("focus",focus);window.addEventListener("pageshow",focus);
    return ()=>{invalidate();abort.current?.abort();document.removeEventListener("visibilitychange",changed);window.removeEventListener("focus",focus);window.removeEventListener("pageshow",focus);};
  },[load]);
  const submit=async()=>{
    if(!view||!confirm||busy)return;
    if(confirm==="EXCEPTIONAL"&&!reason.trim()){setError("دلیل بستن با استثنا را وارد کنید.");return;}
    const signature=JSON.stringify([shipment,view.assessment.fingerprint,confirm,reason]);
    if(command.current.signature!==signature)command.current={signature,key:crypto.randomUUID()};
    setBusy(true);setError("");
    try {await closeShipment(shipment,view.assessment,confirm,reason,command.current.key);await load();await reload();}
    catch(caught){setError(caught instanceof ApiError&&caught.status===409?"اطلاعات تغییر کرده است؛ بررسی تازه را بخوانید و دوباره تصمیم بگیرید.":"ثبت بستن ممکن نشد؛ مجوز و اطلاعات پرونده را بررسی کنید.");await load();}
    finally{setBusy(false);}
  };
  const currentItems=view ? [...view.assessment.items,...view.assessment.missing.filter(item=>!view.assessment.items.some(existing=>existing.code===item.code))] : [];
  const blockers=currentItems.filter(item=>item.mandatory&&item.state!=="PASS");
  const warnings=currentItems.filter(item=>!item.mandatory&&item.state!=="PASS");
  const completed=currentItems.filter(item=>item.state==="PASS");
  const lifecyclePending=!!view&&!view.decision&&!['completed','closed'].includes(view.assessment.lifecycle_status);
  const lifecycleCancelled=view?.assessment.lifecycle_status==='cancelled';
  const criteriaReady=!!view?.assessment.policy&&!blockers.length;
  const normalReady=!!view?.assessment.normal_ready&&view.assessment.lifecycle_status==='completed';
  const completionPercent=currentItems.length?Math.round(completed.length*100/currentItems.length):0;
  return <section aria-label="بررسی بستن پرونده" className="space-y-4 rounded-2xl border bg-white p-4 sm:p-5">
    <div className="flex flex-wrap justify-between gap-3"><h2 className="text-xl font-bold">بررسی بستن پرونده</h2><Button variant="outline" disabled={busy} onClick={()=>{setError("");void load();}}>بررسی دوباره</Button></div>
    {error&&<p role="alert" className="text-red-700">{error}</p>}
    {!view&&!error&&<p role="status">در حال دریافت اطلاعات جاری…</p>}
    {view?.decision?<div className="space-y-3"><p className="font-bold text-emerald-800">پرونده بسته شده است · {view.decision.kind==="EXCEPTIONAL"?"با استثنای مدیر":"پس از تکمیل الزامات"}</p>
      <p>{view.decision.actor} · {when(view.decision.occurred_at)}</p>{view.decision.reason&&<p className="whitespace-pre-wrap break-words">دلیل: {view.decision.reason}</p>}
      <p>نسخه قواعد هنگام بستن: {view.decision.assessment.policy?.version}</p>
      <p className="text-sm text-slate-600">اصلاح سابقه، ثبت دیرهنگام واقعیت‌های قبلی و تکمیل اسناد مجاز است. عملیات تازه مجاز نیست. سابقهٔ تصمیم بستن ثابت می‌ماند.</p>
      <details><summary className="cursor-pointer font-semibold">الزامات و کمبودهای هنگام بستن</summary><div className="mt-3 space-y-3"><ClosureItems items={[...view.decision.assessment.items,...view.decision.missing_items.filter(item=>!view.decision?.assessment.items.some(existing=>existing.code===item.code))]}/></div></details>
    </div>:view&&<>
      <div className={`rounded-2xl border p-4 sm:p-5 ${normalReady?"border-emerald-300 bg-emerald-50":"border-amber-300 bg-amber-50"}`}>
        <p className="text-xs font-bold">نتیجه بررسی جاری</p>
        <h3 className={`mt-1 text-2xl font-black ${normalReady?"text-emerald-900":"text-amber-950"}`}>{normalReady?"آماده بستن عادی":criteriaReady&&lifecyclePending?lifecycleCancelled?"پرونده لغو شده و قابل بستن نیست":"معیارها کامل‌اند؛ اجرای حمل باقی مانده است":"هنوز آماده بستن نیست"}</h3>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/70" role="progressbar" aria-label="پیشرفت آمادگی بستن" aria-valuemin={0} aria-valuemax={100} aria-valuenow={completionPercent}><div className={`h-full rounded-full ${normalReady?"bg-emerald-700":"bg-amber-700"}`} style={{width:`${completionPercent}%`}}/></div>
        <p className="mt-2 text-sm">{completed.length} از {currentItems.length} معیار کامل · {blockers.length} مسدودکننده سیاست · {lifecyclePending?1:0} پیش‌نیاز چرخه عمر · {warnings.length} هشدار</p>
        {lifecyclePending&&<p className="mt-2 text-sm font-semibold">{lifecycleCancelled?"پرونده لغو شده است و انتقال به بستن ندارد.":"بستن فقط پس از ثبت رخدادهای واقعی همه بخش‌های فعال مسیر و تکمیل خودکار محموله ممکن است."}</p>}
      </div>
      {view.assessment.message&&<p className="rounded-xl bg-amber-50 p-3">{view.assessment.message}؛ مدیر سازمان باید قواعد را تعریف کند.</p>}
      {view.assessment.policy&&<p className="text-sm text-slate-600">نسخه قواعد: {view.assessment.policy.version} · بررسی در {when(view.assessment.assessed_at)}</p>}
      {lifecyclePending&&!lifecycleCancelled&&<section aria-labelledby="closure-lifecycle-heading" className="space-y-2 rounded-xl border border-amber-300 bg-amber-50 p-3"><h3 id="closure-lifecycle-heading" className="font-bold text-amber-950">پیش‌نیاز چرخه عمر</h3><p className="text-sm">اجرای مسیر هنوز کامل نشده است. این پیش‌نیاز مستقل از معیارهای سیاست بستن است و هشدارهای کالای واقعی یا ETA جای آن را نمی‌گیرند.</p><OperationalPermission permission="milestone_event.create"><Link className="inline-flex min-h-11 items-center font-semibold text-blue-700 underline" to={`/operations/shipments/${shipment}/route#shipment-next-action`}>رفتن به اجرای مسیر</Link></OperationalPermission></section>}
      {!!blockers.length&&<section aria-labelledby="closure-blockers-heading" className="space-y-2"><h3 id="closure-blockers-heading" className="font-bold text-amber-950">پیش از بستن باید حل شود</h3><ClosureItems items={blockers}/></section>}
      {!!warnings.length&&<section aria-labelledby="closure-warnings-heading" className="space-y-2"><h3 id="closure-warnings-heading" className="font-bold">هشدارهای غیرمسدودکننده</h3><ClosureItems items={warnings}/></section>}
      {!!completed.length&&<details className="rounded-xl border bg-slate-50 p-3"><summary className="cursor-pointer font-semibold">موارد کامل‌شده ({completed.length})</summary><div className="mt-3"><ClosureItems items={completed}/></div></details>}
      {view.assessment.lifecycle_status==="completed"&&view.assessment.policy&&<div className="space-y-3">
        {view.can_close&&<Button className="min-h-12 w-full sm:w-auto" disabled={busy||!normalReady} onClick={()=>setConfirm("NORMAL")}>بستن پرونده</Button>}
        {view.can_close_exceptionally&&<details open className="rounded-xl border border-amber-200 bg-amber-50 p-3"><summary className="cursor-pointer text-sm font-semibold text-amber-950">اختیار استثنایی مدیر</summary><p className="mt-2 text-sm text-amber-900">این مسیر کمبودها را نادیده نمی‌گیرد؛ آن‌ها در تصمیم ثابت بستن حفظ می‌شوند.</p><Button className="mt-3" variant="outline" disabled={busy} onClick={()=>setConfirm("EXCEPTIONAL")}>بستن با استثنای مدیر</Button></details>}
      </div>}
      {confirm&&<div className="space-y-3 rounded-xl border border-amber-300 bg-amber-50 p-4" role="group" aria-label="تأیید بستن">
        <p>پس از بستن، بازگشایی و عملیات تازه ممکن نیست. کمبودهای فعلی در سابقهٔ تصمیم حفظ می‌شوند.</p>
        <label className="block">{confirm==="EXCEPTIONAL"?"دلیل بستن با استثنا (الزامی)":"توضیح (اختیاری)"}<textarea value={reason} maxLength={1000} onChange={e=>setReason(e.target.value)} className="mt-2 min-h-24 w-full rounded-xl border bg-white p-3"/></label>
        <div className="flex flex-wrap gap-2"><Button disabled={busy} onClick={()=>void submit()}>تأیید نهایی بستن</Button><Button variant="outline" disabled={busy} onClick={()=>setConfirm(null)}>انصراف</Button></div>
      </div>}
    </>}
  </section>;
}
