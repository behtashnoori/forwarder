import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createCargoAlias, createCargoCatalogItem, listCargoCatalog, setCargoCatalogActive, updateCargoAlias, updateCargoCatalogItem, type CargoCatalogItem } from "@/lib/api";

const emptyForm = { immutable_code:"", fa_name:"", en_name:"", cargo_type_public_id:"", default_uom_public_id:"", part_number:"", customer_item_code:"", hs_code:"", brand:"", model:"", description:"" };

export default function CargoCatalogAdminTab() {
  const [items,setItems]=useState<CargoCatalogItem[]>([]),[q,setQ]=useState(""),[active,setActive]=useState("all"),[cargoType,setCargoType]=useState(""),[error,setError]=useState("");
  const [form,setForm]=useState(emptyForm),[editing,setEditing]=useState<CargoCatalogItem|null>(null),[alias,setAlias]=useState<Record<string,string>>({});
  const load=useCallback(async()=>{try{setItems((await listCargoCatalog({q,active,cargo_type:cargoType||undefined})).items);setError("");}catch{setError("بارگذاری کاتالوگ انجام نشد / Cargo catalog could not be loaded.");}},[q,active,cargoType]);
  useEffect(()=>{void load();},[load]);
  const save=async()=>{try{if(editing){const {immutable_code:_code,...changes}=form;await updateCargoCatalogItem(editing.public_id,{...changes,version:editing.version});}else{await createCargoCatalogItem(form);}setEditing(null);setForm(emptyForm);await load();}catch{setError("اطلاعات نامعتبر یا نسخه قدیمی است / Invalid data or version conflict.");}};
  const beginEdit=(item:CargoCatalogItem)=>{setEditing(item);setForm({immutable_code:item.immutable_code,fa_name:item.fa_name,en_name:item.en_name||"",cargo_type_public_id:item.cargo_type.public_id,default_uom_public_id:item.default_uom?.public_id||"",part_number:item.part_number||"",customer_item_code:item.customer_item_code||"",hs_code:item.hs_code||"",brand:item.brand||"",model:item.model||"",description:item.description||""});};
  return <div className="space-y-4" dir="auto">
    {error&&<p role="alert" className="rounded bg-red-50 p-3 text-red-700">{error}</p>}
    <Card><CardHeader><CardTitle>کاتالوگ کالا / Cargo Catalog</CardTitle></CardHeader><CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {Object.keys(emptyForm).map(name=><Input key={name} aria-label={name.replace(/_/g," ")} placeholder={name.replace(/_/g," ")} readOnly={name==="immutable_code"&&Boolean(editing)} value={form[name as keyof typeof form]} onChange={e=>setForm({...form,[name]:e.target.value})}/>)}
      <div className="flex flex-wrap gap-2"><Button className="min-h-11" onClick={()=>void save()}>{editing?"ذخیره / Save":"ایجاد / Create"}</Button>{editing&&<Button variant="outline" onClick={()=>{setEditing(null);setForm(emptyForm);}}>لغو / Cancel</Button>}</div>
    </CardContent></Card>
    <Card><CardContent className="space-y-3 pt-6">
      <div className="grid gap-2 sm:grid-cols-3"><Input aria-label="Catalog search" placeholder="جستجو / Search" value={q} onChange={e=>setQ(e.target.value)}/><select aria-label="Active state filter" className="min-h-11 rounded border px-3" value={active} onChange={e=>setActive(e.target.value)}><option value="all">همه / All</option><option value="true">فعال / Active</option><option value="false">غیرفعال / Inactive</option></select><Input aria-label="Cargo type public ID filter" placeholder="CargoType public ID" value={cargoType} onChange={e=>setCargoType(e.target.value)}/></div>
      <div className="grid gap-3 lg:grid-cols-2">{items.map(item=><article key={item.public_id} className="min-w-0 rounded border p-3">
        <div className="flex flex-wrap items-start justify-between gap-2"><div className="min-w-0"><p className="break-words font-semibold">{item.fa_name} <span dir="ltr">{item.en_name}</span></p><code className="break-all text-xs">{item.immutable_code}</code></div><span>{item.is_active?"فعال / Active":"غیرفعال / Inactive"}</span></div>
        <p className="mt-2 break-words text-sm">{item.cargo_type.fa_name} · {item.part_number||"—"} · {item.customer_item_code||"—"}</p>
        <div className="mt-3 flex flex-wrap gap-2"><Button variant="outline" onClick={()=>beginEdit(item)}>ویرایش / Edit</Button><Button variant="outline" onClick={async()=>{try{await setCargoCatalogActive(item.public_id,!item.is_active,item.version);await load();}catch{setError("Version conflict.");}}}>{item.is_active?"Deactivate":"Activate"}</Button></div>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row"><Input aria-label={`Alias for ${item.immutable_code}`} value={alias[item.public_id]||""} onChange={e=>setAlias({...alias,[item.public_id]:e.target.value})}/><Button variant="outline" onClick={async()=>{await createCargoAlias(item.public_id,{alias_text:alias[item.public_id],language:"und",alias_type:"COMMON_NAME"});setAlias({...alias,[item.public_id]:""});await load();}}>افزودن نام / Add alias</Button></div>
        <ul className="mt-2 space-y-1 text-sm">{item.aliases?.map(entry=><li className="flex flex-wrap items-center justify-between gap-2" key={entry.public_id}><span className={entry.is_active?"":"line-through"}>{entry.alias_text} ({entry.alias_type})</span><Button size="sm" variant="ghost" onClick={async()=>{await updateCargoAlias(item.public_id,entry.public_id,{is_active:!entry.is_active});await load();}}>{entry.is_active?"Deactivate":"Activate"}</Button></li>)}</ul>
      </article>)}</div>
    </CardContent></Card>
  </div>;
}
