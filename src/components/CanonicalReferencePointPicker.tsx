import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { fetchInternationalCityPage, searchIranDestinations, type OperationalLocationRef } from "@/lib/api";

/** Retain existing physical reference points without mixing legacy city identities into City. */
export default function CanonicalReferencePointPicker({country,label,onChange}:{
  country:{id:number;code:string};label:string;onChange:(ref:OperationalLocationRef)=>void;
}) {
  const [kind,setKind]=useState<"airport"|"port"|"customs">("airport");
  const [query,setQuery]=useState(""),[search,setSearch]=useState({query:"",offset:0});
  const [rows,setRows]=useState<Array<{key:string;label:string;ref:OperationalLocationRef}>>([]);
  const [more,setMore]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState("");
  useEffect(()=>{
    let live=true;setBusy(true);setError("");
    const load=async()=>{
      if(country.code==="IR"&&kind==="customs"){
        const response=await searchIranDestinations(search.query,50,"customs");
        return {items:response.data.map(row=>({key:`customs_office:${row.identity.id}`,label:row.display_name,ref:{source_type:"customs_office" as const,source_id:row.identity.id}})),has_more:false};
      }
      const response=await fetchInternationalCityPage(country.id,search.query,search.offset,kind==="customs"?"port":kind,true);
      return {items:response.items.map(row=>({key:`international_city:${row.id}`,label:row.name,ref:{source_type:"international_city" as const,source_id:row.id}})),has_more:response.has_more};
    };
    void load().then(response=>{if(live){setRows(old=>Array.from(new Map((search.offset?[...old,...response.items]:response.items).map(row=>[row.key,row])).values()));setMore(response.has_more);}}).catch(()=>{if(live)setError("دریافت نقاط مرجع ممکن نشد.");}).finally(()=>{if(live)setBusy(false);});
    return()=>{live=false;};
  },[country.id,country.code,kind,search]);
  const typeLabel=kind==="airport"?"فرودگاه":kind==="port"?"بندر":"گمرک";
  return <div className="space-y-2 rounded border p-3">
    <p className="text-sm">نقاط مرجع حمل موجود در کشور؛ این نقاط با شهرهای فهرست جغرافیایی یکی نیستند.</p>
    <select aria-label={`${label} نوع نقطه مرجع`} value={kind} onChange={event=>{setKind(event.target.value as typeof kind);setRows([]);setSearch({query:"",offset:0});setQuery("");}} className="min-h-11 w-full rounded border px-3">
      <option value="airport">فرودگاه</option><option value="port">بندر</option>{country.code==="IR"&&<option value="customs">گمرک</option>}
    </select>
    <div className="flex gap-2"><Input aria-label={`${label} جست‌وجوی نقطه مرجع`} value={query} onChange={event=>setQuery(event.target.value)}/><Button type="button" variant="outline" onClick={()=>setSearch({query,offset:0})}>جست‌وجو</Button></div>
    <select aria-label={`${label} نقطه مرجع`} className="min-h-11 w-full rounded border px-3" defaultValue="" disabled={busy} onChange={event=>{const row=rows.find(item=>item.key===event.target.value);if(row)onChange(row.ref);}}>
      <option value="">انتخاب {typeLabel}</option>{rows.map(row=><option key={row.key} value={row.key}>{typeLabel} — {row.label}</option>)}
    </select>
    {more&&<Button type="button" variant="outline" disabled={busy} onClick={()=>setSearch(current=>({...current,offset:current.offset+50}))}>نمایش نقاط بیشتر</Button>}
    {busy&&<p role="status">در حال دریافت نقاط مرجع…</p>}{error&&<p role="alert">{error}</p>}
  </div>;
}
