import { useState } from "react";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { archiveSavedView, createSavedView, listSavedViews, updateSavedView } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { applySavedViewDefinition, isCompatibleSavedView, toSavedViewDefinition, unsupportedSavedViewFilters, type OperationalShipmentFilters } from "@/saved-view/operational-shipments-adapter";

function SavedViewControlsInner({filters,onApply}:{filters:OperationalShipmentFilters;onApply:(filters:OperationalShipmentFilters)=>void}){
 const client=useQueryClient(),[selected,setSelected]=useState(""),[name,setName]=useState(""),[message,setMessage]=useState("");
 const query=useQuery({queryKey:["saved-views","OPERATIONAL_SHIPMENTS"],queryFn:()=>listSavedViews()});
 const selectedView=query.data?.data.find(view=>view.public_id===selected);
 const refresh=()=>client.invalidateQueries({queryKey:["saved-views","OPERATIONAL_SHIPMENTS"]});
 const mutation=useMutation({mutationFn:async(action:"create"|"update"|"archive")=>{if(action==="create")return createSavedView({name:name.trim(),definition:toSavedViewDefinition(filters)});if(!selectedView)throw new Error("نمای ذخیره‌شده انتخاب نشده است.");if(action==="update")return updateSavedView(selectedView.public_id,{expected_version:selectedView.version,definition:toSavedViewDefinition(filters)});return archiveSavedView(selectedView.public_id,selectedView.version)},onSuccess:async()=>{setMessage("نمای ذخیره‌شده با موفقیت ثبت شد.");await refresh();},onError:(error)=>setMessage(error instanceof Error?error.message:"ذخیره نما ناموفق بود.")});
 const unsupported=unsupportedSavedViewFilters(filters);
 return <section className="rounded-lg border bg-white p-4" aria-labelledby="saved-views-heading"><h2 id="saved-views-heading" className="font-semibold">نماهای ذخیره‌شده</h2><div className="mt-3 grid gap-3 sm:grid-cols-[minmax(10rem,1fr)_minmax(10rem,1fr)_auto]">
  <div><Label htmlFor="saved-view-selector">نمای ذخیره‌شده</Label><select id="saved-view-selector" className="min-h-10 w-full rounded-md border bg-background px-3" value={selected} onChange={e=>setSelected(e.target.value)}><option value="">انتخاب نما</option>{query.data?.data.map(view=><option key={view.public_id} value={view.public_id}>{view.name}</option>)}</select></div>
  <div><Label htmlFor="saved-view-name">نام نمای جدید</Label><Input id="saved-view-name" maxLength={120} value={name} onChange={e=>setName(e.target.value)}/></div>
  <div className="flex flex-wrap items-end gap-2"><Button disabled={!name.trim()||unsupported.length>0||mutation.isPending} onClick={()=>mutation.mutate("create")}>ذخیره نما</Button><Button variant="outline" disabled={!selectedView||!isCompatibleSavedView(selectedView)} onClick={()=>selectedView&&onApply(applySavedViewDefinition(selectedView.runtime_definition||selectedView.definition,filters))}>اعمال نما</Button><Button variant="outline" disabled={!selectedView||unsupported.length>0||mutation.isPending} onClick={()=>mutation.mutate("update")}>به‌روزرسانی نما</Button><Button variant="ghost" disabled={!selectedView||mutation.isPending} onClick={()=>mutation.mutate("archive")}>بایگانی</Button></div>
 </div>{unsupported.length>0&&<p role="status" className="mt-2 text-sm text-amber-700">این نسخه فقط وضعیت و بازه زمانی را ذخیره می‌کند؛ برای ذخیره، فیلترهای ناسازگار را پاک کنید.</p>}{query.isError&&<p role="alert" className="mt-2 text-sm text-red-700">بارگذاری نماها ناموفق بود. <Button variant="link" onClick={()=>query.refetch()}>تلاش دوباره</Button></p>}{selectedView&&!isCompatibleSavedView(selectedView)&&<p role="status" className="mt-2 text-sm text-amber-700">این نما با نسخه فعلی سازگار نیست و اعمال نمی‌شود.</p>}{message&&<p aria-live="polite" className="mt-2 text-sm">{message}</p>}</section>;
}

export default function SavedViewControls(props:{filters:OperationalShipmentFilters;onApply:(filters:OperationalShipmentFilters)=>void}){
 const [queryClient]=useState(()=>new QueryClient({defaultOptions:{queries:{retry:false}}}));
 return <QueryClientProvider client={queryClient}><SavedViewControlsInner {...props}/></QueryClientProvider>;
}
