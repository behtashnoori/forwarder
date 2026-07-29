import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { createDocumentDefinition, fetchDocumentDefinitions, setDocumentDefinitionActive, updateDocumentDefinition, type DocumentDefinition, type DocumentFormat } from "@/lib/api";

const formats: Array<[DocumentFormat, string]> = [["jpeg","تصویر JPG/JPEG"],["png","تصویر PNG"],["webp","تصویر WebP"],["pdf","فایل PDF"],["docx","فایل Word"],["xlsx","فایل Excel"]];
const blank = {code:"",title:"",description:"",is_required:false,allowed_formats:[] as DocumentFormat[],max_file_size_bytes:10*1024*1024,max_active_file_count:1,sort_order:0,applicability_scope:"all" as const};

export default function DocumentDefinitionsTab() {
  const [items,setItems]=useState<DocumentDefinition[]>([]); const [form,setForm]=useState(blank); const [editing,setEditing]=useState<number|null>(null); const [error,setError]=useState("");
  const load=()=>fetchDocumentDefinitions().then(r=>setItems(r.items)).catch(e=>setError(String(e.message||e)));
  useEffect(()=>{ void load(); },[]);
  const submit=async()=>{setError(""); try { if(editing) await updateDocumentDefinition(editing,form); else await createDocumentDefinition(form); setEditing(null);setForm(blank);load(); } catch(e){setError(e instanceof Error?e.message:"خطا");}};
  return <div className="space-y-4">
    <Card><CardHeader><CardTitle>مدیریت مستندات</CardTitle></CardHeader><CardContent className="grid gap-3 md:grid-cols-2">
      <Input aria-label="کد داخلی" placeholder="کد داخلی مانند bill_of_lading" disabled={!!editing} value={form.code} onChange={e=>setForm({...form,code:e.target.value})}/>
      <Input aria-label="عنوان" placeholder="عنوان" value={form.title} onChange={e=>setForm({...form,title:e.target.value})}/>
      <Textarea className="md:col-span-2" placeholder="توضیحات و راهنما" value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/>
      <div className="md:col-span-2 flex flex-wrap gap-4">{formats.map(([id,label])=><label key={id} className="flex gap-2"><Checkbox checked={form.allowed_formats.includes(id)} onCheckedChange={v=>setForm({...form,allowed_formats:v?[...form.allowed_formats,id]:form.allowed_formats.filter(x=>x!==id)})}/>{label}</label>)}</div>
      <label>حداکثر حجم (مگابایت)<Input type="number" min={1} value={Math.round(form.max_file_size_bytes/1048576)} onChange={e=>setForm({...form,max_file_size_bytes:Number(e.target.value)*1048576})}/></label>
      <label>حداکثر تعداد فایل<Input type="number" min={1} value={form.max_active_file_count} onChange={e=>setForm({...form,max_active_file_count:Number(e.target.value)})}/></label>
      <label>ترتیب نمایش<Input type="number" value={form.sort_order} onChange={e=>setForm({...form,sort_order:Number(e.target.value)})}/></label>
      <label className="flex items-center gap-2"><Checkbox checked={form.is_required} onCheckedChange={v=>setForm({...form,is_required:!!v})}/>الزامی</label>
      <select aria-label="دامنه کاربرد" value={form.applicability_scope} onChange={e=>setForm({...form,applicability_scope:e.target.value as "all"})}><option value="all">همه پرونده‌ها</option><option value="domestic">حمل داخلی</option><option value="international">حمل بین‌المللی</option></select>
      {error&&<p className="md:col-span-2 text-red-600">{error}</p>}
      <Button onClick={submit}>{editing?"ذخیره تغییرات":"ایجاد تعریف"}</Button>
    </CardContent></Card>
    <Card><CardContent className="overflow-auto p-4"><table className="w-full text-sm"><thead><tr><th>عنوان</th><th>کد</th><th>نوع</th><th>فرمت‌ها</th><th>استفاده</th><th>وضعیت</th><th>عملیات</th></tr></thead><tbody>{items.map(x=><tr key={x.id} className="border-t"><td>{x.title}</td><td dir="ltr">{x.code}</td><td>{x.is_required?"الزامی":"اختیاری"}</td><td>{x.allowed_formats.join("، ")}</td><td>{x.usage_count}</td><td>{x.is_active?"فعال":"غیرفعال"}</td><td className="space-x-2"><Button variant="outline" onClick={()=>{setEditing(x.id);setForm({...blank,...x,description:x.description||""})}}>ویرایش</Button><Button variant="outline" onClick={()=>setDocumentDefinitionActive(x.id,!x.is_active).then(load)}>{x.is_active?"غیرفعال‌سازی":"فعال‌سازی"}</Button></td></tr>)}</tbody></table></CardContent></Card>
  </div>;
}
