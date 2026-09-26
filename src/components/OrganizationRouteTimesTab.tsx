import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, fetchCountries, fetchProvinces, listLogisticsPoints, searchIranDestinations, type OperationalLocationRef } from "@/lib/api";
import { RouteLocationPicker, routeSelectClass, type RouteLocationCatalog } from "@/components/RouteAuthoringSection";
import { createRouteTime, listRouteTimes, reviseRouteTime, timeRange, type RouteTime, type TimeVersion } from "@/lib/routeTimeApi";
import { localDateTimeInputToUtc } from "@/lib/localDateTime";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import { useI18n } from "@/i18n";

export function ReferenceRanges({ value }: {value: TimeVersion | null}) {
  return <dl className="grid gap-3 rounded-xl bg-slate-50 p-3 sm:grid-cols-2"><div><dt className="text-sm text-slate-500">حرکت</dt><dd className="mt-1 font-semibold">{timeRange(value?.movement_min_minutes,value?.movement_max_minutes)}</dd></div><div><dt className="text-sm text-slate-500">توقف / عملیات / انتظار</dt><dd className="mt-1 font-semibold">{timeRange(value?.stop_min_minutes,value?.stop_max_minutes)}</dd></div></dl>;
}

function ReferenceForm({ reference, saved, cancel }: {reference: RouteTime | null; saved: () => void; cancel: () => void}) {
  const { transportLabel } = useI18n();
  const [catalog,setCatalog] = useState<RouteLocationCatalog>({provinces:[],iran:[],facilities:[],countries:[]});
  const [origin,setOrigin] = useState<OperationalLocationRef | null>(null);
  const [destination,setDestination] = useState<OperationalLocationRef | null>(null);
  const [mode,setMode] = useState("");
  const previous=reference?.versions[0];
  const hours = (value: number | null | undefined) => value == null ? "" : String(value/60);
  const [ranges,setRanges] = useState([hours(previous?.movement_min_minutes),hours(previous?.movement_max_minutes),hours(previous?.stop_min_minutes),hours(previous?.stop_max_minutes)]);
  const [effective,setEffective] = useState("");
  const [error,setError] = useState("");
  const [busy,setBusy] = useState(false);
  const command=useRef({signature:"",key:""});
  useEffect(() => {
    if (reference) return;
    let alive=true;
    Promise.all([fetchProvinces(),searchIranDestinations(),listLogisticsPoints({active:"true",per_page:100}),fetchCountries()])
      .then(([provinces,iran,points,countries]) => {if(alive)setCatalog({provinces,iran:iran.data,facilities:points.items,countries});})
      .catch(() => {if(alive)setError("دریافت مکان‌های معتبر ممکن نشد؛ فرم را دوباره باز کنید.");});
    return () => {alive=false;};
  },[reference]);
  const searchIran=(query:string) => { void searchIranDestinations(query).then(result=>setCatalog(old=>({...old,iran:result.data}))).catch(()=>setError("جست‌وجوی مکان ممکن نشد.")); };
  const submit=async () => {
    const date=effective ? localDateTimeInputToUtc(effective) : null;
    const values=ranges.map(value=>value.trim()==="" ? null : Number(value)*60);
    if(!date || values.some(value=>value!==null && (!Number.isFinite(value) || Math.abs(value-Math.round(value))>0.000001))) {setError("تاریخ اعتبار و بازه‌ها را بررسی کنید؛ دقت زمان تا دقیقه است.");return;}
    const [movement_min_minutes,movement_max_minutes,stop_min_minutes,stop_max_minutes]=values.map(value=>value===null?null:Math.round(value));
    if((values[0]===null)!==(values[1]===null) || (values[2]===null)!==(values[3]===null) || (values[0]===null&&values[2]===null)) {setError("حداقل یک بازه کامل حرکت یا توقف لازم است.");return;}
    const durations={movement_min_minutes,movement_max_minutes,stop_min_minutes,stop_max_minutes,effective_from:date};
    if(!reference && (!origin||!destination||!mode)){setError("مبدأ، مقصد و روش حمل را انتخاب کنید.");return;}
    const payload=reference?{...durations,expected_version:reference.latest_version}:{...durations,origin:origin!,destination:destination!,transport_mode:mode};
    const signature=JSON.stringify(payload);
    if(command.current.signature!==signature)command.current={signature,key:crypto.randomUUID()};
    setBusy(true);setError("");
    try{
      if(reference)await reviseRouteTime(reference.public_id,{...durations,expected_version:reference.latest_version},command.current.key);
      else await createRouteTime({...durations,origin:origin!,destination:destination!,transport_mode:mode},command.current.key);
      saved();
    }catch(caught){setError(caught instanceof ApiError && caught.status===409?"اطلاعات تغییر کرده است؛ فرم را ببندید و فهرست را تازه کنید.":caught instanceof Error?caught.message:"ثبت مرجع ممکن نشد.");}
    finally{setBusy(false);}
  };
  const labels=["حداقل حرکت (ساعت)","حداکثر حرکت (ساعت)","حداقل توقف (ساعت)","حداکثر توقف (ساعت)"];
  return <section className="space-y-4 rounded-2xl border border-blue-200 bg-white p-4" aria-label="فرم زمان مرجع">
    <h3 className="text-lg font-semibold">{reference?"ثبت نسخه تازه زمان مرجع":"تعریف زمان مرجع مسیر"}</h3>
    {reference?<p>{reference.origin_label} ← {reference.destination_label} · {transportLabel(reference.transport_mode)}</p>:<>
      <div className="grid min-w-0 gap-4 md:grid-cols-2"><RouteLocationPicker id="reference-origin" label="مبدأ مرجع" value={origin} onChange={setOrigin} catalog={catalog} searchIran={searchIran}/><RouteLocationPicker id="reference-destination" label="مقصد مرجع" value={destination} onChange={setDestination} catalog={catalog} searchIran={searchIran}/></div>
      <label className="block space-y-2">روش حمل مرجع<select aria-label="روش حمل مرجع" className={routeSelectClass} value={mode} onChange={event=>setMode(event.target.value)}><option value="">انتخاب روش حمل</option>{["road","rail","sea","air","multimodal_transfer","customs_handling"].map(value=><option key={value} value={value}>{transportLabel(value)}</option>)}</select></label>
    </>}
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{labels.map((label,index)=><label key={label} className="block space-y-2">{label}<Input aria-label={label} type="number" step="any" value={ranges[index]} onChange={event=>setRanges(old=>old.map((value,i)=>i===index?event.target.value:value))}/></label>)}</div>
    <p className="text-sm text-slate-600">حرکت و توقف جدا ثبت می‌شوند. برای بازه نامشخص، هر دو کادر را خالی بگذارید.</p>
    <label className="block max-w-md space-y-2">شروع اعتبار<Input aria-label="شروع اعتبار" type="datetime-local" value={effective} onChange={event=>setEffective(event.target.value)}/></label>
    <p className="text-sm text-slate-600">زمان با منطقه زمانی دستگاه شما ثبت می‌شود. نسخه تازه باید در آینده معتبر شود؛ برنامه‌های قبلی تغییر نمی‌کنند.</p>
    {error&&<p role="alert" className="rounded bg-red-50 p-3 text-red-800">{error}</p>}
    <div className="flex gap-2"><Button disabled={busy} onClick={()=>void submit()}>{busy?"در حال ثبت…":"ثبت زمان مرجع"}</Button><Button variant="outline" disabled={busy} onClick={cancel}>انصراف</Button></div>
  </section>;
}

export default function OrganizationRouteTimesTab(){
  const {transportLabel}=useI18n();
  const [items,setItems]=useState<RouteTime[]>([]),[page,setPage]=useState(1),[hasNext,setHasNext]=useState(false);
  const [loading,setLoading]=useState(true),[error,setError]=useState(""),[editing,setEditing]=useState<RouteTime|null|undefined>(undefined);
  const load=useCallback(async()=>{setLoading(true);setError("");try{const result=(await listRouteTimes(page)).data;setItems(result.items);setHasNext(result.has_next);}catch(caught){setItems([]);setError(caught instanceof Error?caught.message:"دریافت مرجع‌ها ممکن نشد.");}finally{setLoading(false);}},[page]);
  useEffect(()=>{void load();},[load]);
  return <section dir="rtl" className="space-y-4" aria-label="زمان مرجع مسیر سازمان">
    <Card className="rounded-3xl"><CardHeader><CardTitle>زمان مرجع مسیر</CardTitle><p className="text-sm leading-7 text-slate-600">بازه‌های حرکت و توقف برای برنامه‌ریزی سازمان. این مقادیر، زمان رسیدن یا تعهد خدمات نیستند.</p></CardHeader><CardContent className="flex flex-wrap gap-2"><Button onClick={()=>setEditing(null)}>تعریف مرجع تازه</Button><Button variant="outline" onClick={()=>void load()}>تازه‌سازی مرجع‌ها</Button></CardContent></Card>
    {editing!==undefined&&<ReferenceForm key={editing?.public_id??"new"} reference={editing} cancel={()=>setEditing(undefined)} saved={()=>{setEditing(undefined);void load();}}/>}
    {error&&<p role="alert" className="rounded bg-red-50 p-3 text-red-800">{error}</p>}
    {loading?<p role="status">در حال دریافت زمان‌های مرجع…</p>:!items.length&&!error?<p className="rounded-xl border bg-white p-5">زمان مرجع تعریف نشده است. هیچ زمان پیش‌فرضی اعمال نمی‌شود.</p>:items.map(item=><Card key={item.public_id} className="rounded-2xl" data-reference-id={item.public_id}><CardHeader><CardTitle>{item.origin_label} ← {item.destination_label}</CardTitle><p>{transportLabel(item.transport_mode)}</p></CardHeader><CardContent className="space-y-3">
      <p className="text-sm font-medium">مرجع معتبر اکنون{item.current?` · نسخه ${item.current.version}`:""}</p><ReferenceRanges value={item.current}/>
      <Button variant="outline" onClick={()=>setEditing(item)}>ثبت نسخه تازه</Button>
      <details className="rounded-xl border p-3"><summary className="cursor-pointer font-medium">تاریخچه نسخه‌ها ({item.versions.length})</summary><div className="mt-3 space-y-4">{item.versions.map(version=><article key={version.public_id} className="space-y-2 border-t pt-3"><h4 className="font-semibold">نسخه {version.version}</h4><ReferenceRanges value={version}/><p className="text-sm">اعتبار از {formatDualCalendarInstant(version.effective_from,"fa-IR")} تا {version.effective_until?formatDualCalendarInstant(version.effective_until,"fa-IR"):"بدون پایان تعیین‌شده"}</p><p className="text-xs text-slate-600">ثبت‌کننده: {version.recorded_by||"ثبت‌شده"} · ثبت: {formatDualCalendarInstant(version.recorded_at,"fa-IR")}</p></article>)}</div></details>
    </CardContent></Card>)}
    <div className="flex justify-center gap-3"><Button variant="outline" disabled={page===1||loading} onClick={()=>setPage(value=>value-1)}>صفحه قبل</Button><span>صفحه {page}</span><Button variant="outline" disabled={!hasNext||loading} onClick={()=>setPage(value=>value+1)}>صفحه بعد</Button></div>
  </section>;
}
