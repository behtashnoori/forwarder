import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createShipmentCargoItem, listShipmentCargoItems, request, updateShipmentCargoItem, type ShipmentCargoItem } from "@/lib/api";

type Option={public_id:string;code:string;name:string;cargo_type_public_id?:string;default_uom_public_id?:string|null;symbol?:string};
export default function ShipmentCargoItems({shipmentPublicId,legacyDescription}:{shipmentPublicId:string;legacyDescription?:string|null}){
 const [items,setItems]=useState<ShipmentCargoItem[]>([]),[options,setOptions]=useState<{catalog:Option[];cargo_types:Option[];uoms:Option[]}>({catalog:[],cargo_types:[],uoms:[]}),[error,setError]=useState("");
 const [form,setForm]=useState({line_number:"1",catalog_item_public_id:"",display_name:"",cargo_type_public_id:"",quantity:"",uom_public_id:"",part_number:"",customer_item_code:"",hs_code:"",brand:"",model:"",description:""});
 const [edits,setEdits]=useState<Record<string,string>>({});
 const load=useCallback(async()=>{try{const [lines,opts]=await Promise.all([listShipmentCargoItems(shipmentPublicId),request<{catalog:Option[];cargo_types:Option[];uoms:Option[]}>('/api/internal/cargo-options')]);setItems(lines.items);setOptions(opts);setError("");}catch{setError("بارگذاری اقلام انجام نشد / Cargo lines could not be loaded.");}},[shipmentPublicId]);
 useEffect(()=>{void load();},[load]);
 const choose=(id:string)=>{const row=options.catalog.find(x=>x.public_id===id);setForm({...form,catalog_item_public_id:id,cargo_type_public_id:row?.cargo_type_public_id||form.cargo_type_public_id,uom_public_id:row?.default_uom_public_id||form.uom_public_id,display_name:row?.name||form.display_name});};
 const create=async()=>{try{await createShipmentCargoItem(shipmentPublicId,{...form,line_number:Number(form.line_number),quantity:form.quantity,catalog_item_public_id:form.catalog_item_public_id||undefined});setForm({...form,line_number:String(Number(form.line_number)+1),catalog_item_public_id:"",display_name:"",quantity:"",part_number:"",customer_item_code:"",hs_code:"",brand:"",model:"",description:""});await load();}catch{setError("شماره خط، مقدار، نوع کالا و واحد را بررسی کنید / Check line, quantity, CargoType and UOM.");}};
 return <Card dir="auto"><CardHeader><CardTitle>اقلام ساختاریافته / Structured cargo items</CardTitle></CardHeader><CardContent className="space-y-4">
  {error&&<p aria-live="polite" className="rounded bg-red-50 p-3 text-red-700">{error}</p>}
  <div className="rounded border bg-amber-50 p-3"><strong>شرح قدیمی کالا / Legacy cargo description (preserved separately)</strong><p className="break-words">{legacyDescription||"ثبت نشده / Not provided"}</p></div>
  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
   <Input aria-label="Cargo line number" type="number" min="1" value={form.line_number} onChange={e=>setForm({...form,line_number:e.target.value})}/>
   <select aria-label="Catalog item" className="min-h-11 min-w-0 rounded border px-3" value={form.catalog_item_public_id} onChange={e=>choose(e.target.value)}><option value="">ورود دستی / Manual entry</option>{options.catalog.map(x=><option key={x.public_id} value={x.public_id}>{x.code} — {x.name}</option>)}</select>
   <Input aria-label="Cargo display name" placeholder="نام نمایشی / Display name" value={form.display_name} onChange={e=>setForm({...form,display_name:e.target.value})}/>
   <select aria-label="Cargo type" className="min-h-11 min-w-0 rounded border px-3" value={form.cargo_type_public_id} onChange={e=>setForm({...form,cargo_type_public_id:e.target.value})}><option value="">نوع کالا / Cargo type</option>{options.cargo_types.map(x=><option key={x.public_id} value={x.public_id}>{x.name}</option>)}</select>
   <Input aria-label="Cargo quantity" type="number" min="0.000001" step="any" placeholder="مقدار / Quantity" value={form.quantity} onChange={e=>setForm({...form,quantity:e.target.value})}/>
   <select aria-label="Unit of measure" className="min-h-11 min-w-0 rounded border px-3" value={form.uom_public_id} onChange={e=>setForm({...form,uom_public_id:e.target.value})}><option value="">واحد / Unit of measure</option>{options.uoms.map(x=><option key={x.public_id} value={x.public_id}>{x.name} ({x.symbol})</option>)}</select>
   {(["part_number","customer_item_code","hs_code","brand","model","description"] as const).map(name=><Input key={name} aria-label={name.replace(/_/g," ")} placeholder={name.replace(/_/g," ")} value={form[name]} onChange={e=>setForm({...form,[name]:e.target.value})}/>)}
   <Button className="min-h-11" onClick={()=>void create()}>افزودن / Add cargo line</Button>
  </div>
  <div className="grid gap-3 lg:grid-cols-2">{items.map(x=><article className="min-w-0 rounded border p-3 text-sm" key={x.public_id}>
   <div className="flex flex-wrap justify-between gap-2"><strong className="break-words">#{x.line_number} · {x.display_name_snapshot}</strong><span>{x.source==="catalog"?"پیوندی / Linked":"دستی / Manual"}</span></div>
   <p className="mt-1 break-words">{x.cargo_type_code_snapshot} · {x.cargo_type_fa_snapshot} · {x.uom_code_snapshot} ({x.uom_symbol_snapshot})</p>
   <p className="mt-1 break-words">{x.part_number_snapshot||"—"} / {x.customer_item_code_snapshot||"—"} / {x.hs_code_snapshot||"—"}</p>
   {x.description_snapshot&&<p className="mt-1 break-words">{x.description_snapshot}</p>}
   <div className="mt-3 flex flex-wrap items-center gap-2"><Input aria-label={`Edit quantity line ${x.line_number}`} className="w-28" type="number" min="0.000001" step="any" value={edits[x.public_id]??x.quantity} onChange={e=>setEdits({...edits,[x.public_id]:e.target.value})}/><span>{x.uom_symbol_snapshot}</span><Button variant="outline" onClick={async()=>{try{await updateShipmentCargoItem(shipmentPublicId,x.public_id,{quantity:edits[x.public_id]??x.quantity,version:x.version});await load();}catch{setError("نسخه تغییر کرده است / Version conflict. Refresh and retry.");}}}>ذخیره / Save</Button><span>v{x.version}</span></div>
  </article>)}</div>
 </CardContent></Card>;
}
