import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { getPlanTimes, selectPlanTime, type LegTime, type PlanTimes } from "@/lib/routeTimeApi";
import { ReferenceRanges } from "@/components/OrganizationRouteTimesTab";
import { routeSelectClass } from "@/components/RouteAuthoringSection";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import { useI18n } from "@/i18n";

type Plan={id:number;revision_number:number;status:string};
export default function RouteReferenceTimes({shipmentId,plans}:{shipmentId:string;plans:Plan[]}){
  const {transportLabel}=useI18n();
  const [selectedId,setSelectedId]=useState(plans.find(plan=>plan.status==="draft")?.id??plans[0]?.id);
  const [data,setData]=useState<PlanTimes|null>(null),[error,setError]=useState(""),[loading,setLoading]=useState(true),[pending,setPending]=useState<number|null>(null);
  const [revision,setRevision]=useState(0);
  const command=useRef({signature:"",key:""});
  useEffect(()=>{
    const controller=new AbortController(); let alive=true;
    setData(null);setError("");setLoading(true);
    if(!selectedId){setLoading(false);return;}
    getPlanTimes(shipmentId,selectedId,controller.signal).then(result=>{if(alive)setData(result.data);})
      .catch(caught=>{if(alive)setError(caught instanceof Error?caught.message:"دریافت مبنای زمان ممکن نشد.");})
      .finally(()=>{if(alive)setLoading(false);});
    return()=>{alive=false;controller.abort();};
  },[shipmentId,selectedId,plans,revision]);
  const refresh=useCallback(()=>setRevision(value=>value+1),[]);
  const choose=async(leg:LegTime)=>{
    if(!selectedId||!leg.applicable)return;
    const signature=JSON.stringify([selectedId,leg.leg_id,leg.leg_version,leg.selected?.selection_revision,leg.applicable.public_id]);
    if(command.current.signature!==signature)command.current={signature,key:crypto.randomUUID()};
    setPending(leg.leg_id);setError("");
    try{await selectPlanTime(shipmentId,selectedId,leg,command.current.key);refresh();}
    catch(caught){setData(null);setError(caught instanceof ApiError&&caught.status===409?"برنامه یا مرجع تغییر کرده است؛ تازه‌سازی کنید و دوباره انتخاب کنید.":caught instanceof Error?caught.message:"ثبت مبنا ممکن نشد.");}
    finally{setPending(null);}
  };
  return <section dir="rtl" className="space-y-4 p-3 sm:p-4" aria-label="مبنای زمان برنامه مسیر">
    <p className="text-sm leading-7 text-slate-600">مرجع سازمان، راهنمای برنامه‌ریزی است. انتخاب نسخه برای برنامه صریح است و تغییر مدیر، انتخاب ثبت‌شده را عوض نمی‌کند.</p>
    <div className="flex flex-col gap-3 sm:flex-row"><label className="flex-1 space-y-2">برنامه مسیر<select aria-label="برنامه مبنای زمان" className={routeSelectClass} value={selectedId??""} onChange={event=>setSelectedId(Number(event.target.value))}>{plans.map(plan=><option key={plan.id} value={plan.id}>نسخه برنامه {plan.revision_number} · {plan.status==="draft"?"پیش‌نویس":plan.status==="active"?"فعال":"سابقه"}</option>)}</select></label><Button variant="outline" disabled={pending!==null} onClick={refresh}>تازه‌سازی مبنای زمان</Button></div>
    {error&&<p role="alert" className="rounded bg-red-50 p-3 text-red-800">{error}</p>}
    {loading?<p role="status">در حال دریافت مبنای زمان…</p>:data?.items.length===0?<p>هنوز بخشی در این برنامه تعریف نشده است.</p>:data?.items.map(leg=><article key={leg.leg_id} className="space-y-3 rounded-2xl border bg-white p-4" data-time-leg={leg.leg_id}>
      <h3 className="font-semibold">بخش {leg.sequence_number} · {leg.origin_label} ← {leg.destination_label}</h3><p className="text-sm">{leg.transport_mode?transportLabel(leg.transport_mode):"روش حمل تعریف نشده"}</p>
      <h4 className="font-medium">مبنای ثبت‌شده برنامه{leg.selected?` · نسخه مرجع ${leg.selected.reference.version}`:""}</h4><ReferenceRanges value={leg.selected?.reference??null}/>
      {leg.selected&&!leg.selection_matches_leg&&<p role="status" className="rounded bg-amber-50 p-3 text-amber-900">بخش مسیر پس از این انتخاب تغییر کرده است. مبنای قبلی در سابقه می‌ماند؛ برای استفاده، مرجع مطابق مسیر را دوباره انتخاب کنید.</p>}
      <div className="space-y-2 border-t pt-3"><h4 className="font-medium">مرجع قابل استفاده{leg.applicable?` · نسخه ${leg.applicable.version}`:""}</h4><ReferenceRanges value={leg.applicable}/>
      <p className="text-xs text-slate-600">مبنای اعتبار: {leg.time_basis==="PLANNED_DEPARTURE"?"حرکت برنامه‌ریزی‌شده":"زمان ثبت انتخاب"} · {formatDualCalendarInstant(leg.reference_at,"fa-IR")}</p>
      {leg.can_select&&<Button disabled={pending!==null||!leg.applicable||(leg.selection_matches_leg&&leg.selected?.reference.public_id===leg.applicable.public_id)} onClick={()=>void choose(leg)}>{pending===leg.leg_id?"در حال ثبت…":"ثبت این نسخه برای برنامه"}</Button>}
      {!leg.can_select&&<p className="text-sm text-slate-600">مبنای این برنامه فقط خواندنی است.</p>}</div>
      {!!leg.history.length&&<details className="border-t pt-3"><summary className="cursor-pointer">سابقه انتخاب مبنا</summary><div className="mt-3 space-y-3">{leg.history.map(row=><div key={row.public_id} className="space-y-2 rounded border p-3"><p>انتخاب {row.selection_revision} · نسخه مرجع {row.reference.version}</p><ReferenceRanges value={row.reference}/><p className="text-xs">ثبت: {formatDualCalendarInstant(row.recorded_at,"fa-IR")}</p></div>)}</div></details>}
    </article>)}
  </section>;
}
