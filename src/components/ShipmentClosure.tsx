import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { closeShipment, getClosure, type ClosureView, type ClosureItem } from "@/lib/closureApi";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";

const when = (value: string) => formatDualCalendarInstant(value, "fa", {timeZoneName:"short"});
const sourceSections:Record<string,string>={ACTUAL_QUANTITY_KNOWN:"shipment-cargo",ALL_CARGO_DELIVERED:"shipment-deliveries",
  REQUIRED_DOCUMENTS_READY:"documents-heading",NO_OPEN_EXCEPTIONS:"issues-heading",NO_OPEN_FOLLOW_UPS:"issues-heading",
  NO_OPEN_OPERATIONAL_WORK:"issues-heading",MODE_UNDEFINED:"next-action-heading"};
function openSource(id:string) {
  const target=document.getElementById(id);
  let parent:HTMLElement|null=target;
  while(parent){if(parent instanceof HTMLDetailsElement)parent.open=true;parent=parent.parentElement;}
  requestAnimationFrame(()=>target?.scrollIntoView({block:"start"}));
}
export function ClosureItems({items}: {items: ClosureItem[]}) {
  const ordered=[...items].sort((a,b)=>Number(a.state==="PASS")-Number(b.state==="PASS") || Number(b.mandatory)-Number(a.mandatory));
  return <ul className="space-y-2">{ordered.map(item=><li key={item.code} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border p-3">
    <span>{item.label}<small className="mx-2 text-slate-500">{item.mandatory?"الزامی":"اطلاعاتی"}</small></span>
    <strong className={item.state==="PASS"?"text-emerald-700":"text-amber-800"}>{item.state==="PASS"?"کامل":item.state==="UNKNOWN"?"نامشخص":"کامل نیست"}</strong>
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
      {view.assessment.message&&<p className="rounded-xl bg-amber-50 p-3">{view.assessment.message}؛ مدیر سازمان باید قواعد را تعریف کند.</p>}
      {view.assessment.policy&&<p className="text-sm text-slate-600">نسخه قواعد: {view.assessment.policy.version} · بررسی در {when(view.assessment.assessed_at)}</p>}
      <ClosureItems items={[...view.assessment.items,...view.assessment.missing.filter(item=>!view.assessment.items.some(existing=>existing.code===item.code))]}/>
      {view.assessment.lifecycle_status!=="completed"?<p>بستن فقط پس از تکمیل پرونده ممکن است.</p>:view.assessment.policy&&<div className="flex flex-wrap gap-3">
        {view.can_close&&<Button disabled={busy||!view.assessment.normal_ready} onClick={()=>setConfirm("NORMAL")}>بستن پرونده</Button>}
        {view.can_close_exceptionally&&<Button variant="outline" disabled={busy} onClick={()=>setConfirm("EXCEPTIONAL")}>بستن با استثنای مدیر</Button>}
      </div>}
      {confirm&&<div className="space-y-3 rounded-xl border border-amber-300 bg-amber-50 p-4" role="group" aria-label="تأیید بستن">
        <p>پس از بستن، بازگشایی و عملیات تازه ممکن نیست. کمبودهای فعلی در سابقهٔ تصمیم حفظ می‌شوند.</p>
        <label className="block">{confirm==="EXCEPTIONAL"?"دلیل بستن با استثنا (الزامی)":"توضیح (اختیاری)"}<textarea value={reason} maxLength={1000} onChange={e=>setReason(e.target.value)} className="mt-2 min-h-24 w-full rounded-xl border bg-white p-3"/></label>
        <div className="flex flex-wrap gap-2"><Button disabled={busy} onClick={()=>void submit()}>تأیید نهایی بستن</Button><Button variant="outline" disabled={busy} onClick={()=>setConfirm(null)}>انصراف</Button></div>
      </div>}
    </>}
  </section>;
}
