import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, ChevronLeft, ChevronRight, Plus, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { ApiError, createGlobalLogisticsPoint, listGlobalLogisticsPoints, listLogisticsPointTypes,
  transitionGlobalLogisticsPoint, updateGlobalLogisticsPoint,
  type GlobalLogisticsPoint } from "@/lib/api";

const modes = ["ROAD", "RAIL", "SEA", "AIR", "MULTIMODAL"];
const initialForm = { immutable_code: "", point_type_public_id: "", country_code: "",
  fa_name: "", en_name: "", facility_identity_key: "", city_name: "", short_address: "",
  timezone: "", aliases: "", supported_modes: "", external_codes: "", corridor_tags: "",
  source_organization: "", source_reference: "" };

function payload(form: typeof initialForm) {
  const split = (value: string) => value.split(",").map((x) => x.trim()).filter(Boolean);
  return { immutable_code: form.immutable_code, point_type_public_id: form.point_type_public_id,
    country_code: form.country_code, fa_name: form.fa_name, en_name: form.en_name,
    facility_identity_key: form.facility_identity_key, city_name: form.city_name || undefined,
    short_address: form.short_address || undefined, timezone: form.timezone || undefined,
    aliases: split(form.aliases).map((value) => ({ value })), supported_modes: split(form.supported_modes),
    external_codes: split(form.external_codes).map((value) => {
      const [scheme, ...rest] = value.split(":"); return { scheme, value: rest.join(":") };
    }), corridor_tags: split(form.corridor_tags),
    sources: form.source_organization && form.source_reference ? [{ organization: form.source_organization,
      reference: form.source_reference, version: "unspecified" }] : [] };
}

const stateTone = (value: string) => value === "ACTIVE" || value === "VERIFIED"
  ? "bg-emerald-50 text-emerald-700" : value === "DEPRECATED"
    ? "bg-slate-100 text-slate-600" : value === "REVIEWED" ? "bg-blue-50 text-blue-700" : "bg-amber-50 text-amber-700";

export default function GlobalLogisticsNetworkAdminTab() {
  const { toast } = useToast();
  const [rows, setRows] = useState<GlobalLogisticsPoint[]>([]);
  const [types, setTypes] = useState<Array<{ public_id: string; immutable_code: string }>>([]);
  const [filters, setFilters] = useState({ q: "", country: "", type: "", status: "ALL", verification: "", mode: "", corridor: "" });
  const [page, setPage] = useState(1); const [pages, setPages] = useState(1);
  const [selected, setSelected] = useState<GlobalLogisticsPoint | null>(null);
  const [form, setForm] = useState(initialForm); const [busy, setBusy] = useState(false);
  const [gateFailures, setGateFailures] = useState<Array<{ code: string; message: string }>>([]);

  const load = useCallback(async () => {
    setBusy(true);
    try { const data = await listGlobalLogisticsPoints({ ...filters, page }); setRows(data.items); setPages(data.pages || 1); }
    catch (error) { toast({ title: "خطا در دریافت کاتالوگ", description: String(error), variant: "destructive" }); }
    finally { setBusy(false); }
  }, [filters, page, toast]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => { listLogisticsPointTypes(true).then((x) => setTypes(x.items)).catch(() => setTypes([])); }, []);

  const choose = (row: GlobalLogisticsPoint) => {
    setSelected(row); setGateFailures([]); setForm({ immutable_code: row.immutable_code,
      point_type_public_id: row.point_type.public_id, country_code: row.country.code, fa_name: row.fa_name,
      en_name: row.en_name, facility_identity_key: row.facility_identity_key, city_name: row.geography.city || "",
      short_address: row.geography.short_address || "", timezone: row.geography.timezone || "",
      aliases: row.aliases.map((x) => x.value).join(", "), supported_modes: row.supported_modes.join(", "),
      external_codes: row.external_codes.map((x) => `${x.scheme}:${x.value}`).join(", "),
      corridor_tags: row.corridor_tags.join(", "), source_organization: row.sources[0]?.organization || "",
      source_reference: row.sources[0]?.reference || "" });
  };
  const reset = () => { setSelected(null); setForm(initialForm); setGateFailures([]); };
  const save = async () => {
    setBusy(true);
    try {
      if (selected) {
        const data = payload(form); const { immutable_code, country_code, facility_identity_key, ...editable } = data;
        await updateGlobalLogisticsPoint(selected, editable);
      } else {
        try { await createGlobalLogisticsPoint(payload(form)); }
        catch (error) {
          if (!(error instanceof ApiError) || error.code !== "PROBABLE_DUPLICATE_REVIEW_REQUIRED" ||
              !window.confirm("نقطه‌های مشابه یافت شد. ایجاد به‌عنوان هویت مستقل تأیید شود؟")) throw error;
          const reason = window.prompt("دلیل حاکمیتی تمایز این نقطه") || "";
          await createGlobalLogisticsPoint({ ...payload(form), confirm_probable_duplicate: true,
            duplicate_review_reason: reason });
        }
      }
      reset(); await load(); toast({ title: selected ? "نقطه به‌روزرسانی شد" : "پیش‌نویس ایجاد شد" });
    } catch (error) { toast({ title: "ذخیره انجام نشد", description: String(error), variant: "destructive" }); }
    finally { setBusy(false); }
  };
  const action = async (name: "review" | "verify" | "activate" | "deprecate") => {
    if (!selected) return;
    if (name === "deprecate" && !window.confirm("این نقطه منسوخ شود؟ هویت و تاریخچه حفظ خواهد شد.")) return;
    setBusy(true); setGateFailures([]);
    try { const extra = name === "review" || name === "verify" ? { evidence_reference: window.prompt("مرجع شواهد") || "" }
      : name === "deprecate" ? { reason: "Deprecated by Platform Admin" } : {};
      const result = await transitionGlobalLogisticsPoint(selected, name, extra); choose(result.item); await load();
    } catch (error) {
      const details = error instanceof ApiError ? error.details as { failures?: Array<{ code: string; message: string }> } : undefined;
      setGateFailures(details?.failures || []);
      toast({ title: "عملیات انجام نشد", description: String(error), variant: "destructive" });
    } finally { setBusy(false); }
  };

  return <div className="space-y-4" data-testid="global-logistics-network">
    <Card><CardHeader className="flex-row items-center justify-between"><div><CardTitle>Global Logistics Network</CardTitle>
      <p className="mt-1 text-sm text-slate-500">کاتالوگ حاکمیتی نقاط لجستیکی پلتفرم</p></div>
      <Button variant="outline" onClick={() => void load()} disabled={busy}><RefreshCw className="ml-2 h-4 w-4"/>بازخوانی</Button></CardHeader>
      <CardContent className="grid gap-2 md:grid-cols-4">
        <Input aria-label="Search global points" placeholder="جستجو" value={filters.q} onChange={(e) => { setPage(1); setFilters({...filters,q:e.target.value}); }}/>
        <Input aria-label="Country filter" placeholder="کشور (IR)" value={filters.country} onChange={(e) => setFilters({...filters,country:e.target.value})}/>
        <select aria-label="Lifecycle filter" className="rounded-md border px-3" value={filters.status} onChange={(e) => setFilters({...filters,status:e.target.value})}><option value="ALL">همه وضعیت‌ها</option><option>DRAFT</option><option>ACTIVE</option><option>DEPRECATED</option></select>
        <select aria-label="Verification filter" className="rounded-md border px-3" value={filters.verification} onChange={(e) => setFilters({...filters,verification:e.target.value})}><option value="">همه تأییدها</option><option>UNVERIFIED</option><option>REVIEWED</option><option>VERIFIED</option></select>
        <select aria-label="Type filter" className="rounded-md border px-3" value={filters.type} onChange={(e) => setFilters({...filters,type:e.target.value})}><option value="">همه انواع</option>{types.map((x)=><option key={x.public_id} value={x.immutable_code}>{x.immutable_code}</option>)}</select>
        <select aria-label="Mode filter" className="rounded-md border px-3" value={filters.mode} onChange={(e) => setFilters({...filters,mode:e.target.value})}><option value="">همه شیوه‌ها</option>{modes.map((x)=><option key={x}>{x}</option>)}</select>
        <Input aria-label="Corridor filter" placeholder="کریدور" value={filters.corridor} onChange={(e) => setFilters({...filters,corridor:e.target.value})}/>
        <Button onClick={reset}><Plus className="ml-2 h-4 w-4"/>ایجاد پیش‌نویس</Button>
      </CardContent></Card>
    <div className="grid gap-4 lg:grid-cols-2"><Card><CardContent className="space-y-2 p-4">
      {rows.map((row)=><button key={row.public_id} onClick={()=>choose(row)} className="flex w-full items-center justify-between rounded-xl border p-3 text-right">
        <span><strong>{row.immutable_code}</strong><small className="block text-slate-500">{row.fa_name} / {row.en_name} · {row.country.code} · {row.point_type.code}</small></span>
        <span className="flex gap-1"><Badge className={stateTone(row.lifecycle_status)}>{row.lifecycle_status}</Badge><Badge className={stateTone(row.verification_status)}>{row.verification_status}</Badge></span>
      </button>)}
      {!rows.length && <p className="p-8 text-center text-slate-500">موردی یافت نشد</p>}
      <div className="flex items-center justify-center gap-2"><Button aria-label="Previous page" variant="outline" disabled={page<=1} onClick={()=>setPage(page-1)}><ChevronRight/></Button><span>{page} / {pages}</span><Button aria-label="Next page" variant="outline" disabled={page>=pages} onClick={()=>setPage(page+1)}><ChevronLeft/></Button></div>
    </CardContent></Card><Card><CardHeader><CardTitle>{selected ? `جزئیات ${selected.immutable_code}` : "ایجاد پیش‌نویس"}</CardTitle></CardHeader><CardContent className="grid gap-2 md:grid-cols-2">
      {([['immutable_code','کد ثابت'],['country_code','کشور'],['fa_name','نام فارسی'],['en_name','نام انگلیسی'],['facility_identity_key','هویت تأسیسات'],['city_name','شهر'],['timezone','منطقه زمانی'],['aliases','نام‌های جایگزین'],['supported_modes','شیوه‌ها'],['external_codes','کدهای خارجی'],['corridor_tags','کریدورها'],['source_organization','سازمان منبع'],['source_reference','مرجع منبع']] as const).map(([key,label])=><Input key={key} aria-label={label} placeholder={label} value={form[key]} disabled={!!selected && ['immutable_code','country_code','facility_identity_key'].includes(key)} onChange={(e)=>setForm({...form,[key]:e.target.value})}/>) }
      <Textarea aria-label="نشانی" placeholder="نشانی کوتاه" value={form.short_address} onChange={(e)=>setForm({...form,short_address:e.target.value})}/>
      <select aria-label="نوع نقطه" disabled={false} value={form.point_type_public_id} onChange={(e)=>setForm({...form,point_type_public_id:e.target.value})} className="rounded-md border px-3"><option value="">انتخاب نوع</option>{types.map((x)=><option key={x.public_id} value={x.public_id}>{x.immutable_code}</option>)}</select>
      <Button onClick={()=>void save()} disabled={busy}>{selected ? "ذخیره تغییرات" : "ایجاد DRAFT"}</Button>
      {selected && <div className="col-span-full flex flex-wrap gap-2"><Button onClick={()=>void action('review')} disabled={selected.verification_status!=='UNVERIFIED'}>Review</Button><Button onClick={()=>void action('verify')} disabled={selected.verification_status!=='REVIEWED'}>Verify</Button><Button onClick={()=>void action('activate')} disabled={selected.lifecycle_status!=='DRAFT'}>Activate</Button><Button variant="destructive" onClick={()=>void action('deprecate')} disabled={selected.lifecycle_status!=='ACTIVE'}>Deprecate</Button></div>}
      {gateFailures.length>0 && <div className="col-span-full rounded-xl border border-red-200 bg-red-50 p-3 text-red-700"><p className="flex items-center gap-2 font-semibold"><AlertTriangle className="h-4 w-4"/>Activation gate failures</p><ul>{gateFailures.map((x)=><li key={x.code}>{x.code}: {x.message}</li>)}</ul></div>}
      {selected && <p className="col-span-full text-xs text-slate-500">Opaque ID: {selected.public_id} · Version {selected.version} · {selected.sources.length} provenance record(s)</p>}
    </CardContent></Card></div>
  </div>;
}
