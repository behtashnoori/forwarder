import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getClosureConfiguration, saveClosurePolicy, type ClosureConfiguration, type Criterion } from "@/lib/closureApi";
import { localDateTimeInputToUtc } from "@/lib/localDateTime";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import { useI18n } from "@/i18n";

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
    <p className="text-sm text-slate-600">معیارهای عمومی همراه با معیارهای روش‌های حمل پرونده بررسی می‌شوند. هر تغییر نسخهٔ تازه می‌سازد و تصمیم‌های قبلی را تغییر نمی‌دهد.</p>
    {error&&<p role="alert" className="text-red-700">{error}</p>}
    {!data?<Button variant="outline" onClick={()=>void load()}>دریافت قواعد</Button>:<>
      {!data.versions.length&&<p className="rounded-xl bg-amber-50 p-3">قواعد هنوز تعریف نشده است؛ بستن پرونده تا زمان تعریف قواعد در دسترس نیست.</p>}
      {!editing&&<Button onClick={()=>{setCriteria((data.versions[0]?.criteria??[]).map(row=>({...row})));setEffective("");setError("");setEditing(true);}}>تعریف نسخه تازه قواعد</Button>}
      {editing&&<div className="space-y-4 rounded-xl border p-4">
        <label className="block">شروع اعتبار (زمان محلی)<Input type="datetime-local" value={effective} onChange={e=>setEffective(e.target.value)}/></label>
        <p className="text-sm text-slate-600">نسخه‌های بعدی باید در آینده و پس از نسخهٔ قبلی معتبر شوند.</p>
        {criteria.map((item,index)=><div key={index} className="grid gap-3 rounded-xl bg-slate-50 p-3 sm:grid-cols-2">
          <label>دامنه<select aria-label={`دامنه معیار ${index+1}`} value={item.scope} className="mt-1 w-full rounded border bg-white p-2" onChange={e=>setCriteria(old=>old.map((row,i)=>i===index?{...row,scope:e.target.value}:row))}>{data.scopes.map(scope=><option key={scope} value={scope}>{scopeLabel(scope)}</option>)}</select></label>
          <label>معیار<select aria-label={`معیار ${index+1}`} value={item.code} className="mt-1 w-full rounded border bg-white p-2" onChange={e=>setCriteria(old=>old.map((row,i)=>i===index?{...row,code:e.target.value}:row))}>{Object.entries(data.criteria).map(([code,label])=><option key={code} value={code}>{label}</option>)}</select></label>
          <label className="flex items-center gap-2"><input type="checkbox" checked={item.mandatory} onChange={e=>setCriteria(old=>old.map((row,i)=>i===index?{...row,mandatory:e.target.checked}:row))}/>الزامی برای بستن عادی</label>
          <Button variant="outline" onClick={()=>setCriteria(old=>old.filter((_,i)=>i!==index))}>حذف معیار {index+1}</Button>
        </div>)}
        <div className="flex flex-wrap gap-2"><Button variant="outline" onClick={()=>setCriteria(old=>[...old,{scope:"GENERAL",code:Object.keys(data.criteria)[0],mandatory:true}])}>افزودن معیار</Button><Button disabled={busy} onClick={()=>void save()}>ثبت نسخه قواعد</Button><Button variant="outline" disabled={busy} onClick={()=>setEditing(false)}>انصراف</Button></div>
      </div>}
      {data.versions.map(version=><details key={version.public_id} className="rounded-xl border p-4"><summary className="cursor-pointer font-semibold">نسخه {version.version} · از {formatDualCalendarInstant(version.effective_from,"fa",{timeZoneName:"short"})}</summary><ul className="mt-3 space-y-2">{version.criteria.map(item=><li key={item.public_id}>{scopeLabel(item.scope)} · {item.label} · {item.mandatory?"الزامی":"اطلاعاتی"}</li>)}</ul></details>)}
    </>}
  </section>;
}
