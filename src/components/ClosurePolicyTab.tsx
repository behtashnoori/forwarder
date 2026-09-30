import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getClosureConfiguration, saveClosurePolicy, type ClosureConfiguration, type Criterion } from "@/lib/closureApi";
import { localDateTimeInputToUtc } from "@/lib/localDateTime";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import { useI18n } from "@/i18n";

const V1_CRITERIA: Criterion[] = [
  {scope:"GENERAL",code:"FINAL_DELIVERY_EXISTS",mandatory:true},
  {scope:"GENERAL",code:"REQUIRED_OPERATIONAL_STAGES_COMPLETE",mandatory:true},
  {scope:"GENERAL",code:"NO_BLOCKING_OPERATIONAL_ISSUE",mandatory:true},
  {scope:"GENERAL",code:"REQUIRED_DOCUMENTS_READY",mandatory:true},
  {scope:"GENERAL",code:"ACTUAL_CARGO_UNKNOWN",mandatory:false},
  {scope:"GENERAL",code:"ACTUAL_ALLOCATION_DIFFERS_FROM_PLANNED",mandatory:false},
  {scope:"GENERAL",code:"DELIVERED_DIFFERS_FROM_PLANNED",mandatory:false},
  {scope:"GENERAL",code:"OPTIONAL_DOCUMENTS_ABSENT",mandatory:false},
  {scope:"GENERAL",code:"ETA_UNAVAILABLE",mandatory:false},
  {scope:"GENERAL",code:"NON_BLOCKING_OPERATIONAL_WARNINGS",mandatory:false},
];
const localInput=(date:Date)=>new Date(date.getTime()-date.getTimezoneOffset()*60000).toISOString().slice(0,16);

export default function ClosurePolicyTab() {
  const {transportLabel}=useI18n();
  const [data,setData]=useState<ClosureConfiguration|null>(null);
  const [criteria,setCriteria]=useState<Criterion[]>([]);
  const [editing,setEditing]=useState(false);
  const [effective,setEffective]=useState("");
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);
  const generation=useRef(0);
  const command=useRef({signature:"",key:""});
  const load=useCallback(async()=>{
    const revision=++generation.current;setData(null);setEditing(false);
    try{const result=await getClosureConfiguration();if(revision===generation.current)setData(result.data);}
    catch{if(revision===generation.current)setError("دریافت قواعد ممکن نشد؛ مجوز مدیر سازمان را بررسی کنید.");}
  },[]);
  useEffect(()=>{
    void load();
    const invalidate=()=>{generation.current++;};
    const focus=()=>{void load();};
    const visibility=()=>{if(document.hidden){generation.current++;setData(null);setEditing(false);}else void load();};
    window.addEventListener("focus",focus);window.addEventListener("pageshow",focus);document.addEventListener("visibilitychange",visibility);
    return()=>{invalidate();window.removeEventListener("focus",focus);window.removeEventListener("pageshow",focus);document.removeEventListener("visibilitychange",visibility);};
  },[load]);
  const scopeLabel=(scope:string)=>scope==="GENERAL"?"همه حمل‌ها":transportLabel(scope);
  const save=async()=>{
    const at=localDateTimeInputToUtc(effective);
    if(!data||!at||!criteria.length){setError("تاریخ شروع اعتبار و حداقل یک معیار را انتخاب کنید.");return;}
    const payload={expected_version:data.versions[0]?.version??0,effective_from:at,criteria:criteria.map(({scope,code,mandatory})=>({scope,code,mandatory}))};
    const signature=JSON.stringify(payload);
    if(signature!==command.current.signature)command.current={signature,key:crypto.randomUUID()};
    setBusy(true);setError("");
    try{await saveClosurePolicy(payload,command.current.key);await load();}
    catch{setError("ثبت نشد؛ معیار تکراری، تاریخ اعتبار و تغییر هم‌زمان نسخه را بررسی کنید.");}
    finally{setBusy(false);}
  };
  return <section className="space-y-4 rounded-2xl border bg-white p-4 sm:p-6" aria-label="قواعد بستن پرونده">
    <h2 className="text-xl font-bold">قواعد بستن پرونده</h2>
    <p className="text-sm text-slate-600">معیارهای عمومی همراه با معیارهای روش‌های حمل پرونده بررسی می‌شوند. بستن عادی فقط پس از تکمیل پرونده ممکن است؛ بستن استثنایی مدیر مسیر جداگانه‌ای دارد. هر تغییر نسخهٔ تازه می‌سازد و تصمیم‌های قبلی را تغییر نمی‌دهد.</p>
    {error&&<p role="alert" className="text-red-700">{error}</p>}
    {!data?<Button variant="outline" onClick={()=>void load()}>دریافت قواعد</Button>:<>
      {!data.versions.length&&<p className="rounded-xl bg-amber-50 p-3">قواعد هنوز تعریف نشده است؛ بستن پرونده تا زمان تعریف قواعد در دسترس نیست.</p>}
      {!editing&&<Button onClick={()=>{setCriteria(V1_CRITERIA.map(row=>({...row})));setEffective(localInput(new Date(Date.now()+(data.versions.length?5*60*1000:0))));setError("");setEditing(true);}}>تعریف نسخه V1 قواعد</Button>}
      {editing&&<div className="space-y-4 rounded-xl border p-4">
        <label className="block">شروع اعتبار (زمان محلی)<Input type="datetime-local" value={effective} onChange={e=>setEffective(e.target.value)}/></label>
        <p className="text-sm text-slate-600">نسخه‌های بعدی باید در آینده و پس از نسخهٔ قبلی معتبر شوند.</p>
        <div className="grid gap-3 md:grid-cols-2">{criteria.map(item=><div key={item.code} className={`rounded-xl p-3 ${item.mandatory?"bg-red-50":"bg-amber-50"}`}><strong>{data.criteria[item.code]}</strong><p className="text-sm">{item.mandatory?"مسدودکننده بستن عادی":"هشدار غیرمسدودکننده"}</p></div>)}</div>
        <p className="text-sm text-slate-600">طبقه‌بندی مسدودکننده/هشدار ثابت است و مدیر نمی‌تواند هشدار را به مانع بستن تبدیل کند.</p>
        <div className="flex flex-wrap gap-2"><Button disabled={busy} onClick={()=>void save()}>ثبت نسخه قواعد</Button><Button variant="outline" disabled={busy} onClick={()=>setEditing(false)}>انصراف</Button></div>
      </div>}
      {data.versions.map(version=><details key={version.public_id} className="rounded-xl border p-4"><summary className="cursor-pointer font-semibold">نسخه {version.version} · از {formatDualCalendarInstant(version.effective_from,"fa",{timeZoneName:"short"})}</summary><ul className="mt-3 space-y-2">{version.criteria.map(item=><li key={item.public_id}>{scopeLabel(item.scope)} · {item.label} · {item.mandatory?"الزامی":"اطلاعاتی"}</li>)}</ul></details>)}
    </>}
  </section>;
}
