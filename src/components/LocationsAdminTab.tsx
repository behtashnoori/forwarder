import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import {
  createAdminLocation,
  deactivateAdminLocation,
  fetchAdminCities,
  fetchAdminCounties,
  fetchAdminCountries,
  fetchAdminInternationalCities,
  fetchAdminIranPorts,
  fetchAdminProvinces,
  updateAdminLocation,
  type AdminLocationResource,
} from "@/lib/api";

/* --------------------------------------------------------------------------
 * Generic, reusable panel: list + add form + inline edit + soft deactivate
 * for one location resource. Used by the domestic, international, and ports
 * sections below so their CRUD behaviour stays identical.
 * ------------------------------------------------------------------------ */
type FieldType = "text" | "select" | "bool";

interface FieldDef {
  key: string;
  label: string;
  type: FieldType;
  required?: boolean;
  options?: { value: string; label: string }[];
}

interface LocationItem {
  id: number;
  name_fa: string;
  is_active: boolean;
  [key: string]: unknown;
}

interface ResourcePanelProps {
  title: string;
  resource: AdminLocationResource;
  fields: FieldDef[];
  load: () => Promise<{ items: LocationItem[] }>;
  /** Values merged into every create/update payload (e.g. a fixed parent id). */
  fixedPayload?: Record<string, unknown>;
  /** Re-run the loader whenever any of these change (cascade refresh). */
  deps?: unknown[];
  /** Clicking a row selects it (used to drive child cascades). */
  selectedId?: number | null;
  onSelect?: (item: LocationItem | null) => void;
  /** Extra text under each row's name. */
  subtitle?: (item: LocationItem) => string;
  /** Shown instead of the form when a parent has not been selected yet. */
  disabledHint?: string;
}

function emptyForm(fields: FieldDef[]): Record<string, string> {
  const form: Record<string, string> = {};
  fields.forEach((f) => {
    form[f.key] = f.type === "bool" ? "true" : f.type === "select" ? f.options?.[0]?.value ?? "" : "";
  });
  return form;
}

function buildPayload(fields: FieldDef[], form: Record<string, string>): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  fields.forEach((f) => {
    const raw = form[f.key];
    if (f.type === "bool") {
      payload[f.key] = raw === "true";
    } else if (f.key.endsWith("_id")) {
      payload[f.key] = raw ? Number(raw) : null;
    } else {
      payload[f.key] = raw ?? "";
    }
  });
  return payload;
}

function ResourcePanel({
  title, resource, fields, load, fixedPayload, deps = [], selectedId, onSelect, subtitle, disabledHint,
}: ResourcePanelProps) {
  const { toast } = useToast();
  const [items, setItems] = useState<LocationItem[]>([]);
  const [form, setForm] = useState<Record<string, string>>(() => emptyForm(fields));
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const disabled = Boolean(disabledHint);

  const reload = useCallback(() => {
    if (disabled) { setItems([]); return; }
    load().then((res) => setItems(res.items)).catch((err) =>
      toast({ title: "خطا", description: err instanceof Error ? err.message : "بارگذاری ناموفق بود", variant: "destructive" }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [disabled, ...deps]);

  useEffect(() => { reload(); }, [reload]);

  const requiredMissing = fields.some((f) => f.required && f.type !== "bool" && !form[f.key]?.trim());

  const submit = async () => {
    setBusy(true);
    try {
      await createAdminLocation(resource, { ...buildPayload(fields, form), ...fixedPayload });
      setForm(emptyForm(fields));
      reload();
      toast({ title: "افزوده شد", description: `${title} با موفقیت ثبت شد.` });
    } catch (err) {
      toast({ title: "خطا", description: err instanceof Error ? err.message : "ثبت ناموفق بود", variant: "destructive" });
    } finally {
      setBusy(false);
    }
  };

  const startEdit = (item: LocationItem) => {
    setEditingId(item.id);
    const next: Record<string, string> = {};
    fields.forEach((f) => {
      const v = item[f.key];
      next[f.key] = f.type === "bool" ? String(Boolean(v)) : v == null ? "" : String(v);
    });
    setEditForm(next);
  };

  const saveEdit = async (id: number) => {
    setBusy(true);
    try {
      await updateAdminLocation(resource, id, buildPayload(fields, editForm));
      setEditingId(null);
      reload();
      toast({ title: "ذخیره شد", description: "تغییرات اعمال شد." });
    } catch (err) {
      toast({ title: "خطا", description: err instanceof Error ? err.message : "ذخیره ناموفق بود", variant: "destructive" });
    } finally {
      setBusy(false);
    }
  };

  const deactivate = async (id: number) => {
    if (!window.confirm("این مورد غیرفعال شود؟ (حذف فیزیکی انجام نمی‌شود)")) return;
    try {
      await deactivateAdminLocation(resource, id);
      reload();
      toast({ title: "غیرفعال شد", description: "مورد از فهرست فعال حذف شد." });
    } catch (err) {
      toast({ title: "خطا", description: err instanceof Error ? err.message : "غیرفعال‌سازی ناموفق بود", variant: "destructive" });
    }
  };

  const renderField = (f: FieldDef, value: string, onChange: (v: string) => void) => {
    if (f.type === "select") {
      return (
        <Select value={value} onValueChange={onChange}>
          <SelectTrigger><SelectValue placeholder={f.label} /></SelectTrigger>
          <SelectContent>
            {(f.options ?? []).map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
          </SelectContent>
        </Select>
      );
    }
    if (f.type === "bool") {
      return (
        <Select value={value} onValueChange={onChange}>
          <SelectTrigger><SelectValue placeholder={f.label} /></SelectTrigger>
          <SelectContent>
            <SelectItem value="true">فعال</SelectItem>
            <SelectItem value="false">غیرفعال</SelectItem>
          </SelectContent>
        </Select>
      );
    }
    return <Input value={value} onChange={(e) => onChange(e.target.value)} placeholder={f.label} />;
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-3"><CardTitle className="text-base">{title}</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        {disabled ? (
          <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-500">{disabledHint}</p>
        ) : (
          <div className="space-y-2 rounded-xl border border-slate-100 bg-slate-50/60 p-3">
            <div className="grid gap-2 sm:grid-cols-2">
              {fields.map((f) => (
                <div key={f.key} className="space-y-1">
                  <label className="text-xs text-slate-500">{f.label}{f.required ? " *" : ""}</label>
                  {renderField(f, form[f.key] ?? "", (v) => setForm({ ...form, [f.key]: v }))}
                </div>
              ))}
            </div>
            <Button size="sm" className="w-full" disabled={busy || requiredMissing} onClick={submit}>افزودن</Button>
          </div>
        )}

        <div className="space-y-2">
          {items.length === 0 && !disabled && <p className="text-sm text-slate-400">موردی ثبت نشده است.</p>}
          {items.map((item) => (
            <div
              key={item.id}
              className={`rounded-xl border p-3 transition ${
                selectedId === item.id ? "border-blue-400 bg-blue-50" : "border-slate-200 bg-white"
              } ${onSelect ? "cursor-pointer" : ""}`}
              onClick={() => onSelect?.(selectedId === item.id ? null : item)}
            >
              {editingId === item.id ? (
                <div className="space-y-2" onClick={(e) => e.stopPropagation()}>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {fields.map((f) => (
                      <div key={f.key} className="space-y-1">
                        <label className="text-xs text-slate-500">{f.label}</label>
                        {renderField(f, editForm[f.key] ?? "", (v) => setEditForm({ ...editForm, [f.key]: v }))}
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" disabled={busy} onClick={() => saveEdit(item.id)}>ذخیره</Button>
                    <Button size="sm" variant="outline" onClick={() => setEditingId(null)}>انصراف</Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-slate-800">
                      {item.name_fa}
                      {!item.is_active && <Badge variant="secondary" className="mr-2 text-xs">غیرفعال</Badge>}
                    </p>
                    {subtitle && <p className="truncate text-xs text-slate-500">{subtitle(item)}</p>}
                  </div>
                  <div className="flex shrink-0 gap-1" onClick={(e) => e.stopPropagation()}>
                    <Button size="sm" variant="outline" onClick={() => startEdit(item)}>ویرایش</Button>
                    {item.is_active && (
                      <Button size="sm" variant="destructive" onClick={() => deactivate(item.id)}>غیرفعال</Button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/* -------------------------------------------------------------------------- */
const activeField: FieldDef = { key: "is_active", label: "وضعیت", type: "bool" };

function DomesticSection() {
  const [province, setProvince] = useState<LocationItem | null>(null);
  const [county, setCounty] = useState<LocationItem | null>(null);

  // Changing the selected province invalidates the selected county.
  const selectProvince = (p: LocationItem | null) => { setProvince(p); setCounty(null); };

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <ResourcePanel
        title="استان‌ها"
        resource="provinces"
        fields={[{ key: "name_fa", label: "نام استان", type: "text", required: true }, { key: "code", label: "کد", type: "text" }, activeField]}
        load={fetchAdminProvinces}
        selectedId={province?.id ?? null}
        onSelect={selectProvince}
        subtitle={(i) => (i.code ? `کد: ${i.code}` : "بدون کد")}
      />
      <ResourcePanel
        title={province ? `شهرستان‌های ${province.name_fa}` : "شهرستان‌ها"}
        resource="counties"
        fields={[{ key: "name_fa", label: "نام شهرستان", type: "text", required: true }, { key: "code", label: "کد", type: "text" }, activeField]}
        load={() => fetchAdminCounties(province?.id)}
        deps={[province?.id]}
        fixedPayload={{ province_id: province?.id }}
        selectedId={county?.id ?? null}
        onSelect={setCounty}
        disabledHint={province ? undefined : "ابتدا یک استان را انتخاب کنید."}
      />
      <ResourcePanel
        title={county ? `شهرهای ${county.name_fa}` : "شهرها"}
        resource="cities"
        fields={[{ key: "name_fa", label: "نام شهر", type: "text", required: true }, { key: "code", label: "کد", type: "text" }, activeField]}
        load={() => fetchAdminCities(county?.id)}
        deps={[county?.id]}
        fixedPayload={{ county_id: county?.id }}
        disabledHint={county ? undefined : "ابتدا یک استان و شهرستان را انتخاب کنید."}
      />
    </div>
  );
}

function InternationalSection() {
  const [country, setCountry] = useState<LocationItem | null>(null);

  const cityTypeField: FieldDef = {
    key: "city_type", label: "نوع", type: "select",
    options: [{ value: "city", label: "شهر" }, { value: "port", label: "بندر" }, { value: "airport", label: "فرودگاه" }],
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ResourcePanel
        title="کشورها"
        resource="countries"
        fields={[
          { key: "name_fa", label: "نام فارسی", type: "text", required: true },
          { key: "name_en", label: "نام انگلیسی", type: "text", required: true },
          { key: "code", label: "کد ISO", type: "text", required: true },
          activeField,
        ]}
        load={fetchAdminCountries}
        selectedId={country?.id ?? null}
        onSelect={setCountry}
        subtitle={(i) => `${i.name_en as string} · ${i.code as string}`}
      />
      <ResourcePanel
        title={country ? `شهرها/بنادر ${country.name_fa}` : "شهرها و بنادر بین‌المللی"}
        resource="international-cities"
        fields={[
          { key: "name_fa", label: "نام فارسی", type: "text", required: true },
          { key: "name_en", label: "نام انگلیسی", type: "text", required: true },
          cityTypeField,
          { key: "is_major_port", label: "بندر اصلی", type: "bool" },
          activeField,
        ]}
        load={() => fetchAdminInternationalCities(country?.id)}
        deps={[country?.id]}
        fixedPayload={{ country_id: country?.id }}
        subtitle={(i) => `${i.name_en as string} · ${i.city_type as string}`}
        disabledHint={country ? undefined : "ابتدا یک کشور را انتخاب کنید."}
      />
    </div>
  );
}

function PortsSection() {
  const [provinces, setProvinces] = useState<LocationItem[]>([]);
  useEffect(() => { fetchAdminProvinces().then((r) => setProvinces(r.items)).catch(() => setProvinces([])); }, []);

  const provinceOptions = useMemo(
    () => provinces.map((p) => ({ value: String(p.id), label: p.name_fa })),
    [provinces],
  );

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ResourcePanel
        title="بنادر و مبادی ورودی ایران"
        resource="iran-ports"
        fields={[
          { key: "name_fa", label: "نام فارسی", type: "text", required: true },
          { key: "name_en", label: "نام انگلیسی", type: "text", required: true },
          { key: "port_type", label: "نوع", type: "select", options: [
            { value: "sea", label: "دریایی" }, { value: "air", label: "هوایی" }, { value: "land", label: "زمینی" }] },
          { key: "province_id", label: "استان", type: "select", required: true, options: provinceOptions },
          activeField,
        ]}
        load={fetchAdminIranPorts}
        deps={[provinces.length]}
        subtitle={(i) => `${i.name_en as string} · ${i.province_name ? i.province_name : "بدون استان"}`}
      />
      <Card className="h-full">
        <CardHeader className="pb-3"><CardTitle className="text-base">راهنما</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm text-slate-600">
          <p>این بخش بنادر و مبادی ورودی ایران را که در حمل بین‌المللی به‌عنوان نقطهٔ ورود استفاده می‌شوند مدیریت می‌کند.</p>
          <p>برای افزودن بندر ابتدا باید استان مربوط از بخش «داخلی» تعریف شده باشد.</p>
          <p className="text-slate-400">حذف موارد به‌صورت غیرفعال‌سازی انجام می‌شود و رکورد در پایگاه‌داده باقی می‌ماند.</p>
        </CardContent>
      </Card>
    </div>
  );
}

export default function LocationsAdminTab() {
  return (
    <div className="space-y-4">
      <Tabs defaultValue="domestic" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3 rounded-2xl border border-slate-200 bg-white p-1 md:w-auto md:inline-grid">
          <TabsTrigger value="domestic" className="rounded-xl">حمل داخلی</TabsTrigger>
          <TabsTrigger value="international" className="rounded-xl">حمل بین‌المللی</TabsTrigger>
          <TabsTrigger value="ports" className="rounded-xl">بنادر ورودی ایران</TabsTrigger>
        </TabsList>
        <TabsContent value="domestic"><DomesticSection /></TabsContent>
        <TabsContent value="international"><InternationalSection /></TabsContent>
        <TabsContent value="ports"><PortsSection /></TabsContent>
      </Tabs>
    </div>
  );
}
