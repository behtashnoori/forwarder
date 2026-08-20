import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createCargoAlias, createCargoCatalogItem, getCargoCatalogShipmentUsage, listCargoCatalog, setCargoCatalogActive, updateCargoAlias, updateCargoCatalogItem, type CargoCatalogItem, type CargoShipmentUsage } from "@/lib/api";

const emptyForm = { immutable_code:"", fa_name:"", en_name:"", cargo_type_public_id:"", default_uom_public_id:"", part_number:"", customer_item_code:"", hs_code:"", brand:"", model:"", description:"" };

export default function CargoCatalogAdminTab() {
  const [items,setItems]=useState<CargoCatalogItem[]>([]),[q,setQ]=useState(""),[active,setActive]=useState("all"),[cargoType,setCargoType]=useState(""),[error,setError]=useState("");
  const [form,setForm]=useState(emptyForm),[editing,setEditing]=useState<CargoCatalogItem|null>(null),[alias,setAlias]=useState<Record<string,string>>({});
  const [usage,setUsage]=useState<CargoShipmentUsage|null>(null),[usageLoading,setUsageLoading]=useState(false);
  const load=useCallback(async()=>{try{setItems((await listCargoCatalog({q,active,cargo_type:cargoType||undefined})).items);setError("");}catch{setError("بارگذاری کاتالوگ انجام نشد / Cargo catalog could not be loaded.");}},[q,active,cargoType]);
  useEffect(()=>{void load();},[load]);
  const save=async()=>{try{if(editing){const {immutable_code:_code,...changes}=form;await updateCargoCatalogItem(editing.public_id,{...changes,version:editing.version});}else{await createCargoCatalogItem(form);}setEditing(null);setForm(emptyForm);await load();}catch{setError("اطلاعات نامعتبر یا نسخه قدیمی است / Invalid data or version conflict.");}};
  const beginEdit=(item:CargoCatalogItem)=>{setEditing(item);setForm({immutable_code:item.immutable_code,fa_name:item.fa_name,en_name:item.en_name||"",cargo_type_public_id:item.cargo_type.public_id,default_uom_public_id:item.default_uom?.public_id||"",part_number:item.part_number||"",customer_item_code:item.customer_item_code||"",hs_code:item.hs_code||"",brand:item.brand||"",model:item.model||"",description:item.description||""});};
  return <div className="space-y-4" dir="auto">
    {error&&<p role="alert" className="rounded bg-red-50 p-3 text-red-700">{error}</p>}
    <Card><CardHeader><CardTitle>فهرست استاندارد کالاها</CardTitle></CardHeader><CardContent className="space-y-3"><p className="text-sm text-muted-foreground">فهرست استاندارد کالاهایی که اطلاعات آن‌ها یک‌بار تعریف می‌شود و در محموله‌های مختلف قابل استفاده است. از «مشاهده محموله‌ها» می‌توانید ببینید این کالا در کدام محموله‌ها ثبت شده و آخرین وضعیت و موقعیت هرکدام چیست.</p><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {Object.keys(emptyForm).map(name=><Input key={name} aria-label={name.replace(/_/g," ")} placeholder={name.replace(/_/g," ")} readOnly={name==="immutable_code"&&Boolean(editing)} value={form[name as keyof typeof form]} onChange={e=>setForm({...form,[name]:e.target.value})}/>)}
      <div className="flex flex-wrap gap-2"><Button className="min-h-11" onClick={()=>void save()}>{editing?"ذخیره / Save":"ایجاد / Create"}</Button>{editing&&<Button variant="outline" onClick={()=>{setEditing(null);setForm(emptyForm);}}>لغو / Cancel</Button>}</div>
    </div></CardContent></Card>
    <Card><CardContent className="space-y-3 pt-6">
      <div className="grid gap-2 sm:grid-cols-3"><Input aria-label="Catalog search" placeholder="جستجو / Search" value={q} onChange={e=>setQ(e.target.value)}/><select aria-label="Active state filter" className="min-h-11 rounded border px-3" value={active} onChange={e=>setActive(e.target.value)}><option value="all">همه / All</option><option value="true">فعال / Active</option><option value="false">غیرفعال / Inactive</option></select><Input aria-label="Cargo type public ID filter" placeholder="CargoType public ID" value={cargoType} onChange={e=>setCargoType(e.target.value)}/></div>
      {items.length===0&&<p className="rounded border border-dashed p-5 text-sm text-muted-foreground">هنوز کالای استانداردی تعریف نشده است. کالاهای پرتکرار را یک‌بار ثبت کنید تا هنگام افزودن اقلام محموله، اطلاعات یکسان و قابل استفاده مجدد باشند.</p>}
      <div className="grid gap-3 lg:grid-cols-2">{items.map(item=><article key={item.public_id} className="min-w-0 rounded border p-3">
        <div className="flex flex-wrap items-start justify-between gap-2"><div className="min-w-0"><p className="break-words font-semibold">{item.fa_name} <span dir="ltr">{item.en_name}</span></p><code className="break-all text-xs">{item.immutable_code}</code></div><span>{item.is_active?"فعال / Active":"غیرفعال / Inactive"}</span></div>
        <p className="mt-2 break-words text-sm">{item.cargo_type.fa_name} · {item.part_number||"—"} · {item.customer_item_code||"—"}</p>
        <div className="mt-3 flex flex-wrap gap-2"><Button variant="outline" onClick={()=>beginEdit(item)}>ویرایش / Edit</Button><Button variant="outline" onClick={async()=>{try{await setCargoCatalogActive(item.public_id,!item.is_active,item.version);await load();}catch{setError("Version conflict.");}}}>{item.is_active?"Deactivate":"Activate"}</Button><Button variant="outline" onClick={async()=>{try{setUsageLoading(true);setUsage(await getCargoCatalogShipmentUsage(item.public_id));setError("");}catch{setError("بارگذاری محموله‌های کالا انجام نشد.");}finally{setUsageLoading(false);}}}>مشاهده محموله‌ها</Button></div>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row"><Input aria-label={`Alias for ${item.immutable_code}`} value={alias[item.public_id]||""} onChange={e=>setAlias({...alias,[item.public_id]:e.target.value})}/><Button variant="outline" onClick={async()=>{await createCargoAlias(item.public_id,{alias_text:alias[item.public_id],language:"und",alias_type:"COMMON_NAME"});setAlias({...alias,[item.public_id]:""});await load();}}>افزودن نام / Add alias</Button></div>
        <ul className="mt-2 space-y-1 text-sm">{item.aliases?.map(entry=><li className="flex flex-wrap items-center justify-between gap-2" key={entry.public_id}><span className={entry.is_active?"":"line-through"}>{entry.alias_text} ({entry.alias_type})</span><Button size="sm" variant="ghost" onClick={async()=>{await updateCargoAlias(item.public_id,entry.public_id,{is_active:!entry.is_active});await load();}}>{entry.is_active?"Deactivate":"Activate"}</Button></li>)}</ul>
      </article>)}</div>
    </CardContent></Card>
    {usageLoading&&<p>در حال بارگذاری…</p>}
    {usage&&<Card><CardHeader><CardTitle>{usage.cargo_item.fa_name} · {usage.summary.shipment_count} محموله</CardTitle></CardHeader><CardContent className="space-y-3">{usage.items.length===0?<p>این کالا هنوز در هیچ محموله‌ای استفاده نشده است.</p>:usage.items.map(row=><article className="rounded border p-3" key={row.shipment_cargo_line_public_id}><a className="font-semibold text-blue-700 underline" href={`/operations/shipments/${row.operational_shipment_public_id}`}>{row.project_code||row.shipment_request_reference||row.operational_shipment_public_id}</a><p>{row.quantity} {row.uom} · {row.status}</p><p>{row.current_location||"موقعیت ثبت نشده"}</p><time className="text-xs text-muted-foreground">{row.latest_event_at?new Date(row.latest_event_at).toLocaleString():"—"}</time></article>)}</CardContent></Card>}
  </div>;
}
