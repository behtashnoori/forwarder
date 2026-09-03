import {useCallback,useEffect,useState} from "react";
import {Button} from "@/components/ui/button";
import {Card,CardContent,CardHeader,CardTitle} from "@/components/ui/card";
import {Input} from "@/components/ui/input";
import {Textarea} from "@/components/ui/textarea";
import {addOrganizationGlobalPointToNetwork,listOrganizationGlobalPoints,transitionOrganizationGlobalPointAdoption,
  updateOrganizationGlobalPointAdoption,type OrganizationGlobalPoint} from "@/lib/api";

const labels={AVAILABLE:"GLOBAL · AVAILABLE",ADOPTED:"GLOBAL · ADOPTED",
  INACTIVE_FOR_ORGANIZATION:"GLOBAL · INACTIVE FOR ORGANIZATION",PLATFORM_DEPRECATED:"GLOBAL · PLATFORM DEPRECATED"};

export default function OrganizationGlobalNetworkTab(){
 const [rows,setRows]=useState<OrganizationGlobalPoint[]>([]),[error,setError]=useState("");
 const [filters,setFilters]=useState({q:"",country:"",type:"",mode:"",corridor:"",adoption_state:""});
 const [selected,setSelected]=useState<OrganizationGlobalPoint|null>(null);
 const [form,setForm]=useState({organization_reference_code:"",display_label:"",notes:""});
 const load=useCallback(async()=>{try{setError("");const x=await listOrganizationGlobalPoints(filters);setRows(x.items)}catch(e){setError(e instanceof Error?e.message:"Unable to load global network")}},[filters]);
 useEffect(()=>{void load()},[load]);
 const choose=(row:OrganizationGlobalPoint)=>{setSelected(row);setForm({organization_reference_code:row.adoption?.organization_reference_code||"",display_label:row.adoption?.display_label||"",notes:row.adoption?.notes||""})};
 const save=async()=>{if(!selected?.adoption)return;try{await updateOrganizationGlobalPointAdoption(selected.adoption,form);await load()}catch(e){setError(e instanceof Error?e.message:"Version conflict")}};
 const lifecycle=async(action:"activate"|"deactivate")=>{if(!selected?.adoption)return;try{await transitionOrganizationGlobalPointAdoption(selected.adoption,action);await load()}catch(e){setError(e instanceof Error?e.message:"Lifecycle change failed")}};
 const addFromReference=async()=>{if(!selected||!window.confirm("این نقطه به شبکه لجستیکی سازمان افزوده شود؟"))return;try{await addOrganizationGlobalPointToNetwork(selected.public_id,form);await load()}catch(e){setError(e instanceof Error?e.message:"خطا در افزودن نقطه از شبکه مرجع")}};
 return <div className="space-y-4" data-testid="organization-global-network" dir="rtl"><Card><CardHeader><CardTitle>افزودن از شبکه مرجع</CardTitle><p className="text-sm text-muted-foreground">یک نقطهٔ تأییدشدهٔ پلتفرم را انتخاب کنید تا مستقیماً به شبکهٔ عملیاتی سازمان افزوده شود. اطلاعات حاکمیتی و سابقهٔ منبع در پس‌زمینه حفظ می‌شود.</p></CardHeader><CardContent className="grid gap-2 md:grid-cols-3">
  <Input aria-label="Global search" placeholder="جستجو" value={filters.q} onChange={e=>setFilters({...filters,q:e.target.value})}/>
  <Input aria-label="Global country" placeholder="کشور" value={filters.country} onChange={e=>setFilters({...filters,country:e.target.value})}/>
  <Input aria-label="Global type" placeholder="نوع" value={filters.type} onChange={e=>setFilters({...filters,type:e.target.value})}/>
  <Input aria-label="Global mode" placeholder="شیوه حمل" value={filters.mode} onChange={e=>setFilters({...filters,mode:e.target.value})}/>
  <Input aria-label="Global corridor" placeholder="کریدور" value={filters.corridor} onChange={e=>setFilters({...filters,corridor:e.target.value})}/>
  <select aria-label="Adoption state" className="rounded border px-3" value={filters.adoption_state} onChange={e=>setFilters({...filters,adoption_state:e.target.value})}><option value="">همه</option>{Object.entries(labels).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select>
 </CardContent></Card>{error&&<p role="alert" className="rounded border border-red-300 bg-red-50 p-3">{error}</p>}
 <div className="grid gap-4 lg:grid-cols-2"><Card><CardContent className="space-y-2 p-4">{rows.map(row=><button key={row.public_id} onClick={()=>choose(row)} className="w-full rounded border p-3 text-right"><b>{row.immutable_code} · {row.fa_name}</b><span className="block text-xs text-muted-foreground">{row.country.code} · {row.point_type.code} · {labels[row.organization_state]}</span></button>)}</CardContent></Card>
 <Card><CardHeader><CardTitle>{selected?selected.fa_name:"جزئیات نقطه جهانی"}</CardTitle></CardHeader><CardContent className="grid gap-3">{selected&&<><p>{labels[selected.organization_state]}</p><p>{selected.en_name} · {selected.geography.city}</p>
  <Input aria-label="Organization reference code" placeholder="کد داخلی سازمان" value={form.organization_reference_code} onChange={e=>setForm({...form,organization_reference_code:e.target.value})}/>
  <Input aria-label="Organization display label" placeholder="برچسب نمایشی سازمان" value={form.display_label} onChange={e=>setForm({...form,display_label:e.target.value})}/>
  <Textarea aria-label="Organization notes" placeholder="یادداشت سازمان" value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})}/>
  {(selected.organization_state==="AVAILABLE"||(selected.organization_state==="ADOPTED"&&selected.adoption?.materialization.state==="NOT_MATERIALIZED"))&&<Button onClick={()=>void addFromReference()}>افزودن به شبکهٔ سازمان</Button>}
  {selected.adoption&&<Button variant="outline" onClick={()=>void save()}>ذخیره اطلاعات سازمان</Button>}
  {selected.organization_state==="ADOPTED"&&<Button variant="destructive" onClick={()=>void lifecycle("deactivate")}>لغو پذیرش سازمان</Button>}
  {selected.adoption&&<p className="font-medium text-xs text-muted-foreground">جزئیات حاکمیتی: {selected.adoption.materialization.state.replace("_"," ")}</p>}
  {selected.adoption?.materialization.state==="MATERIALIZED"&&<a className="text-blue-700 underline" href={`#logistics-point-${selected.adoption.materialization.logistics_point_public_id}`}>مشاهده مکان عملیاتی سازمان</a>}
  {selected.organization_state==="INACTIVE_FOR_ORGANIZATION"&&<Button onClick={()=>void lifecycle("activate")}>Reactivate adoption</Button>}
  {selected.organization_state==="PLATFORM_DEPRECATED"&&<p className="text-red-700">Platform deprecated; materialized operational history is retained and new materialization or reactivation is unavailable.</p>}
 </>}</CardContent></Card></div></div>
}
