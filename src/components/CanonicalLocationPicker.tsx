import { useEffect, useRef, useState } from "react";
import CanonicalReferencePointPicker from "@/components/CanonicalReferencePointPicker";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { routeSelectClass } from "@/components/RouteAuthoringSection";
import {
  createExpertLocation, fetchCanonicalAdmin1, fetchCanonicalCities, fetchCanonicalCountries,
  listLogisticsPoints, listLogisticsPointTypes,
  type CanonicalAdmin1, type CanonicalCity, type CanonicalCountry, type LogisticsPointTypeView,
  type LogisticsPointView, type OperationalLocationRef,
} from "@/lib/api";

export type CanonicalEndpointRef = OperationalLocationRef & { country_id: number; display_label?: string };

export default function CanonicalLocationPicker({label,value,onChange,allowCreate=true,allowAdmin1=false,allowPhysicalPoints=false,onCreated}:{
  label:string; value:CanonicalEndpointRef|null; onChange:(value:CanonicalEndpointRef|null)=>void; allowCreate?:boolean; allowAdmin1?:boolean; allowPhysicalPoints?:boolean; onCreated?:(point:LogisticsPointView)=>void;
}) {
  const [countries,setCountries]=useState<CanonicalCountry[]>([]),[admin1,setAdmin1]=useState<CanonicalAdmin1[]>([]),[cities,setCities]=useState<CanonicalCity[]>([]),[locations,setLocations]=useState<LogisticsPointView[]>([]),[types,setTypes]=useState<LogisticsPointTypeView[]>([]);
  const [country,setCountry]=useState<CanonicalCountry>(),[region,setRegion]=useState<CanonicalAdmin1>(),[city,setCity]=useState<CanonicalCity>();
  const [location,setLocation]=useState(""),[countryQuery,setCountryQuery]=useState(""),[regionQuery,setRegionQuery]=useState(""),[query,setQuery]=useState(""),[cityQuery,setCityQuery]=useState(""),[adding,setAdding]=useState(false),[name,setName]=useState(""),[type,setType]=useState(""),[address,setAddress]=useState(""),[description,setDescription]=useState(""),[busy,setBusy]=useState(false),[loading,setLoading]=useState("initial"),[error,setError]=useState("");
  const requestVersion=useRef(0);
  const [hasMore,setHasMore]=useState(false),[searchedQuery,setSearchedQuery]=useState("");
  const [physicalOpen,setPhysicalOpen]=useState(false);
  const uniqueCities=(rows:CanonicalCity[])=>Array.from(new Map(rows.map(row=>[row.geoname_id,row])).values());
  useEffect(()=>{let live=true; const version=requestVersion; void Promise.all([fetchCanonicalCountries(),listLogisticsPointTypes()]).then(([geo,kinds])=>{if(live){setCountries(geo.items);setTypes(kinds.items.filter(item=>item.is_active));}}).catch(()=>{if(live)setError("دریافت جغرافیای معتبر ممکن نشد.");}).finally(()=>{if(live)setLoading("");});return()=>{live=false;version.current++;};},[]);
  const resetCity=()=>{setCity(undefined);setCities([]);setLocations([]);setLocation("");setQuery("");setCityQuery("");setSearchedQuery("");setHasMore(false);setAdding(false);onChange(null);};
  const chooseCountry=async(id:string)=>{
    const version=++requestVersion.current, row=countries.find(item=>String(item.id)===id);
    setCountry(row);setRegion(undefined);setRegionQuery("");setAdmin1([]);resetCity();setLoading("");setError("");
    if(!row)return;
    setLoading("admin1");
    try{const response=await fetchCanonicalAdmin1(row.code);if(version===requestVersion.current)setAdmin1(response.items);}
    catch{if(version===requestVersion.current)setError("دریافت استان/ایالت ممکن نشد.");}
    finally{if(version===requestVersion.current)setLoading("");}
  };
  const loadCities=async(row:CanonicalAdmin1,term:string,offset=0)=>{
    const version=++requestVersion.current;setLoading("cities");setError("");
    try{const response=await fetchCanonicalCities(row.geoname_id,term,offset);if(version===requestVersion.current){setCities(old=>uniqueCities(offset?[...old,...response.items]:response.items));setHasMore(!!response.has_more);setSearchedQuery(term);}}
    catch{if(version===requestVersion.current)setError("دریافت شهرها ممکن نشد.");}
    finally{if(version===requestVersion.current)setLoading("");}
  };
  const chooseRegion=(identity:string)=>{++requestVersion.current;const row=admin1.find(item=>String(item.geoname_id)===identity);setRegion(row);resetCity();setLoading("");if(row)void loadCities(row,"");};
  const loadLocations=async(row:CanonicalCity,term="")=>{
    const version=++requestVersion.current;setLoading("locations");setError("");
    try{const response=await listLogisticsPoints({city_geoname_id:row.geoname_id,q:term,active:"true",per_page:100});if(version===requestVersion.current)setLocations(response.items);}
    catch{if(version===requestVersion.current)setError("دریافت مکان‌های سازمان ممکن نشد.");}
    finally{if(version===requestVersion.current)setLoading("");}
  };
  const chooseCity=(identity:string)=>{++requestVersion.current;const row=[...cities,...(city?[city]:[])].find(item=>String(item.geoname_id)===identity);setCity(row);setLocation("");setLocations([]);setQuery("");setAdding(false);setLoading("");onChange(row&&country?{country_id:country.id,source_type:"city",source_id:row.source_id,display_label:[row.name_fa,region?.name_fa,country.name_fa].filter(Boolean).join(" · ")}:null);if(row)void loadLocations(row);};
  const searchCities=()=>{if(region)void loadCities(region,cityQuery);};
  const searchLocations=()=>{if(city)void loadLocations(city,query);};
  const chooseLocation=(publicId:string)=>{setLocation(publicId);const row=locations.find(item=>item.public_id===publicId);onChange(row&&country?{country_id:country.id,source_type:"logistics_point",source_id:row.public_id,display_label:row.fa_name}:city&&country?{country_id:country.id,source_type:"city",source_id:city.source_id,display_label:city.name_fa}:null);};
  const create=async()=>{if(!city||!name.trim())return;setBusy(true);setError("");try{const result=await createExpertLocation({name,city_geoname_id:city.geoname_id,point_type_public_id:type||null,address:address||null,description:description||null});setLocations(old=>[result.item,...old.filter(item=>item.public_id!==result.item.public_id)]);onCreated?.(result.item);setAdding(false);setName("");setLocation(result.item.public_id);if(country)onChange({country_id:country.id,source_type:"logistics_point",source_id:result.item.public_id,display_label:result.item.fa_name});}catch(caught){setError(caught instanceof Error?caught.message:"ایجاد مکان ممکن نشد.");}finally{setBusy(false);}};
  const normalize=(text:string)=>text.toLocaleLowerCase().replace(/[أإآ]/g,"ا").replace(/[يى]/g,"ی").replace(/ك/g,"ک").replace(/[\s‌]/g,"");
  const includes=(values:Array<string|undefined>,term:string)=>!term.trim()||values.some(value=>normalize(value||"").includes(normalize(term.trim())));
  const visibleCountries=countries.filter(item=>item.id===country?.id||includes([item.name_fa,item.name_en,item.code],countryQuery));
  const visibleAdmin1=admin1.filter(item=>item.geoname_id===region?.geoname_id||includes([item.name_fa,item.name_en,item.code],regionQuery));
  return <fieldset disabled={busy} className="space-y-3 rounded-xl border p-3"><legend className="px-1 font-medium">{label}</legend>
    <label className="block space-y-2 text-sm">کشور<Input aria-label={`${label} جست‌وجوی کشور`} value={countryQuery} onChange={e=>setCountryQuery(e.target.value)} placeholder="جست‌وجوی کشور"/><select aria-label={`${label} کشور`} className={routeSelectClass} value={country?.id||""} onChange={e=>void chooseCountry(e.target.value)}><option value="">انتخاب کشور</option>{visibleCountries.map(item=><option key={item.id} value={item.id}>{item.name_fa}{item.geography_supported===false?" — جزئیات جغرافیایی موجود نیست":""}</option>)}</select></label>
    {allowPhysicalPoints&&country&&<details onToggle={event=>setPhysicalOpen(event.currentTarget.open)}><summary className="cursor-pointer text-sm">انتخاب فرودگاه، بندر یا گمرک</summary>{physicalOpen&&<CanonicalReferencePointPicker key={country.id} country={country} label={label} onChange={ref=>{++requestVersion.current;resetCity();setRegion(undefined);setLoading("");onChange({...ref,country_id:country.id});}}/>}</details>}
    {country?.geography_supported===false&&<p role="status" className="rounded bg-amber-50 p-2 text-sm">کشور در فهرست معتبر است؛ پوشش استان و شهر آن هنوز فراهم نشده است.</p>}
    <label className="block space-y-2 text-sm">استان / ایالت<Input aria-label={`${label} جست‌وجوی استان`} disabled={!country} value={regionQuery} onChange={e=>setRegionQuery(e.target.value)} placeholder="جست‌وجوی استان / ایالت"/><select aria-label={`${label} استان`} className={routeSelectClass} disabled={!country} value={region?.geoname_id||""} onChange={e=>void chooseRegion(e.target.value)}><option value="">انتخاب استان / ایالت</option>{visibleAdmin1.map(item=><option key={item.geoname_id} value={item.geoname_id}>استان — {item.name_fa}</option>)}</select></label>
    {allowAdmin1&&region&&country&&<Button type="button" variant="outline" onClick={()=>{++requestVersion.current;setCity(undefined);setLocations([]);setAdding(false);setLocation("");onChange({country_id:country.id,source_type:"province",source_id:region.source_id,display_label:region.name_fa});}}>استفاده از استان — {region.name_fa}</Button>}
    <label className="block space-y-2 text-sm">شهر<div className="flex gap-2"><Input aria-label={`${label} جست‌وجوی شهر`} disabled={!region} value={cityQuery} onChange={e=>setCityQuery(e.target.value)} placeholder="جست‌وجوی شهر"/><Button type="button" variant="outline" disabled={!region} onClick={()=>void searchCities()}>جست‌وجو</Button></div><select aria-label={`${label} شهر`} className={routeSelectClass} disabled={!region} value={city?.geoname_id||""} onChange={e=>void chooseCity(e.target.value)}><option value="">انتخاب شهر</option>{uniqueCities([...(city?[city]:[]),...cities]).map(item=><option key={item.geoname_id} value={item.geoname_id}>شهر — {item.name_fa}</option>)}</select></label>
    {hasMore&&region&&<Button type="button" variant="outline" disabled={loading==="cities"} onClick={()=>void loadCities(region,searchedQuery,cities.length)}>نمایش شهرهای بیشتر</Button>}
    <label className="block space-y-2 text-sm">مکان سازمان (اختیاری)<div className="flex gap-2"><Input aria-label={`${label} جست‌وجوی مکان سازمان`} disabled={!city} value={query} onChange={e=>setQuery(e.target.value)} placeholder="کارخانه، انبار، پایانه…"/><Button type="button" variant="outline" disabled={!city} onClick={()=>void searchLocations()}>جست‌وجو</Button></div><select aria-label={`${label} مکان سازمان`} className={routeSelectClass} disabled={!city} value={location} onChange={e=>chooseLocation(e.target.value)}><option value="">بدون مکان سازمانی؛ خود شهر</option>{locations.map(item=><option key={item.public_id} value={item.public_id}>{item.point_type?.fa_name||"مکان سازمان"} — {item.fa_name}{item.governance_state==="PENDING_REVIEW"?" · در انتظار بررسی":""}</option>)}</select></label>
    {allowCreate&&<Button disabled={!city||busy} type="button" variant="outline" onClick={()=>setAdding(value=>!value)}>{adding?"بستن فرم":"افزودن مکان جدید"}</Button>}
    {adding&&<div className="grid gap-2 rounded-lg bg-slate-50 p-3 sm:grid-cols-2"><label>نام مکان<Input required value={name} onChange={e=>setName(e.target.value)}/></label><label>نوع (اختیاری)<select className={routeSelectClass} value={type} onChange={e=>setType(e.target.value)}><option value="">بدون نوع</option>{types.map(item=><option key={item.public_id} value={item.public_id}>{item.fa_name}</option>)}</select></label><label>نشانی (اختیاری)<Input value={address} onChange={e=>setAddress(e.target.value)}/></label><label>توضیحات (اختیاری)<Input value={description} onChange={e=>setDescription(e.target.value)}/></label><div className="sm:col-span-2"><Button type="button" disabled={busy||!name.trim()} onClick={()=>void create()}>{busy?"در حال ثبت…":"ایجاد و استفاده فوری"}</Button><p className="mt-1 text-xs text-slate-600">مکان بلافاصله قابل استفاده و برای بررسی مدیر سازمان علامت‌گذاری می‌شود.</p></div></div>}
    {loading&&<p role="status" className="text-sm text-slate-600">{loading==="initial"?"در حال دریافت جغرافیای معتبر…":loading==="admin1"?"در حال دریافت استان‌ها / ایالت‌ها…":loading==="cities"?"در حال دریافت شهرها…":"در حال جست‌وجوی مکان‌های سازمان…"}</p>}
    {!loading&&region&&cities.length===0&&<p className="text-sm text-slate-600">شهر منطبق یافت نشد.</p>}
    {!loading&&city&&locations.length===0&&<p className="text-sm text-slate-600">مکان سازمانی منطبق یافت نشد؛ خود شهر همچنان قابل انتخاب است.</p>}
    {city&&<details className="text-xs text-slate-500"><summary>نام دیگر و شناسه جغرافیایی</summary>{city.name_en} · GeoNames {city.geoname_id}</details>}
    {value&&<p className="text-sm text-emerald-800">{label} انتخاب شد.</p>}{error&&<p role="alert" className="text-sm text-red-700">{error}</p>}
  </fieldset>;
}
