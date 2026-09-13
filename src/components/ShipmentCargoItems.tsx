import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatQuantity } from "@/lib/formatQuantity";
import {
  addOperationalTransportTrackingUpdate, createShipmentCargoItem,
  enableOperationalTransportTracking,
  getOperationalTransportTracking, getShipmentCargoOptions, listShipmentCargoItems,
  searchOperationalCustomers, updateShipmentCargoItem,
  type OperationalTransportTracking, type ShipmentCargoItem,
  type OperationalCustomerSelector,
} from "@/lib/api";

type Option = { public_id: string; code: string; name: string; cargo_type_public_id?: string; default_uom_public_id?: string | null; symbol?: string; preferred?: boolean };
const statusLabel: Record<string, string> = { loading: "در حال بارگیری", departed: "حرکت کرده", in_transit: "در مسیر", at_checkpoint: "در نقطه کنترل", delayed: "با تأخیر", arrived_destination: "رسیده به مقصد", delivered: "تحویل شده", cancelled: "لغو شده" };
const label = (status?: string) => statusLabel[status || ""] || status || "ثبت نشده";
const time = (value?: string) => value ? new Date(value).toLocaleString("fa-IR") : "ثبت نشده";
const uniqueCustomers = (customers: OperationalCustomerSelector[]) =>
  Array.from(new Map(customers.map((customer) => [customer.id, customer])).values());

export default function ShipmentCargoItems({ shipmentPublicId, projectPublicId, legacyDescription }: { shipmentPublicId: string; projectPublicId?: string | null; legacyDescription?: string | null }) {
  const [items, setItems] = useState<ShipmentCargoItem[]>([]);
  const [owners, setOwners] = useState<OperationalCustomerSelector[]>([]);
  const [options, setOptions] = useState<{ catalog: Option[]; cargo_types: Option[]; uoms: Option[] }>({ catalog: [], cargo_types: [], uoms: [] });
  const [error, setError] = useState("");
  const [form, setForm] = useState({ line_number: "1", catalog_item_public_id: "", display_name: "", cargo_type_public_id: "", quantity: "", uom_public_id: "", cargo_owner_customer_id: "" });
  const [cargoQuery, setCargoQuery] = useState("");
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [ownerEdits, setOwnerEdits] = useState<Record<string, string>>({});
  const [tracking, setTracking] = useState<OperationalTransportTracking | null>(null);
  const [selectedUnit, setSelectedUnit] = useState("");
  const [trackingForm, setTrackingForm] = useState({ status: "in_transit", location_text: "", customer_message: "", internal_note: "", is_customer_visible: true });
  const load = useCallback(async () => {
    try {
      const [lines, opts, ownerData, trackingData] = await Promise.all([listShipmentCargoItems(shipmentPublicId), getShipmentCargoOptions(projectPublicId || undefined, cargoQuery), searchOperationalCustomers("", 100), getOperationalTransportTracking(shipmentPublicId)]);
      setItems(lines.items); setOptions(opts); setOwners(uniqueCustomers(ownerData.items)); setTracking(trackingData.tracking); setError("");
    } catch { setError("اطلاعات کالا، وسیله حمل یا پیگیری قابل دریافت نیست. اجازه دسترسی یا اتصال را بررسی کنید."); }
  }, [shipmentPublicId, projectPublicId, cargoQuery]);
  useEffect(() => { void load(); }, [load]);
  const latest = useMemo(() => tracking?.units.flatMap((unit) => unit.history.map((event) => ({ unit, event }))).sort((a, b) => Date.parse(b.event.occurred_at) - Date.parse(a.event.occurred_at))[0], [tracking]);
  const choose = (id: string) => {
    const row = options.catalog.find((option) => option.public_id === id);
    setForm({ ...form, catalog_item_public_id: id, cargo_type_public_id: row?.cargo_type_public_id || form.cargo_type_public_id, uom_public_id: row?.default_uom_public_id || form.uom_public_id, display_name: row?.name || form.display_name });
  };
  const create = async () => {
    try {
      await createShipmentCargoItem(shipmentPublicId, { ...form, line_number: Number(form.line_number), quantity: form.quantity, catalog_item_public_id: form.catalog_item_public_id || undefined, cargo_owner_customer_id: form.cargo_owner_customer_id ? Number(form.cargo_owner_customer_id) : undefined });
      setForm({ ...form, line_number: String(Number(form.line_number) + 1), catalog_item_public_id: "", display_name: "", quantity: "" }); await load();
    } catch { setError("شماره ردیف، کالا، مقدار و واحد را بررسی کنید."); }
  };
  return <>
    <Card dir="rtl"><CardHeader><CardTitle>کالا و وسایل حمل</CardTitle></CardHeader><CardContent className="space-y-4">
      {error && <p aria-live="polite" className="rounded bg-red-50 p-3 text-red-700">{error}</p>}
      {legacyDescription && <p className="rounded bg-amber-50 p-3 text-sm"><strong>شرح ثبت‌شده پیشین:</strong> {legacyDescription}</p>}
      <details><summary className="cursor-pointer font-medium">افزودن کالا</summary><div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        <Input aria-label="Cargo line number" type="number" min="1" value={form.line_number} onChange={(event) => setForm({ ...form, line_number: event.target.value })} />
        <Input aria-label="Search cargo catalog" placeholder="جست‌وجوی نام، نام جایگزین، کد، برند یا مدل" value={cargoQuery} onChange={(event) => setCargoQuery(event.target.value)} />
        <select aria-label="Catalog item" className="min-h-11 rounded border px-3" value={form.catalog_item_public_id} onChange={(event) => choose(event.target.value)}><option value="">ورود دستی کالا</option>{options.catalog.some((option) => option.preferred)&&<optgroup label="کالاهای ترجیحی پروژه">{options.catalog.filter((option)=>option.preferred).map((option) => <option key={option.public_id} value={option.public_id}>★ {option.code} — {option.name}</option>)}</optgroup>}<optgroup label="سایر کالاهای سازمان">{options.catalog.filter((option)=>!option.preferred).map((option) => <option key={option.public_id} value={option.public_id}>{option.code} — {option.name}</option>)}</optgroup></select>
        <Input aria-label="Cargo display name" placeholder="نام کالا" value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} />
        <select aria-label="Cargo type" className="min-h-11 rounded border px-3" value={form.cargo_type_public_id} onChange={(event) => setForm({ ...form, cargo_type_public_id: event.target.value })}><option value="">نوع کالا</option>{options.cargo_types.map((option) => <option key={option.public_id} value={option.public_id}>{option.name}</option>)}</select>
         <Input aria-label="Cargo quantity" type="number" min="0.000001" step="any" placeholder="مقدار" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: event.target.value })} />
         <select aria-label="Unit of measure" className="min-h-11 rounded border px-3" value={form.uom_public_id} onChange={(event) => setForm({ ...form, uom_public_id: event.target.value })}><option value="">واحد اندازه‌گیری</option>{options.uoms.map((option) => <option key={option.public_id} value={option.public_id}>{option.name} ({option.symbol})</option>)}</select>
         <select aria-label="Cargo owner" className="min-h-11 rounded border px-3" value={form.cargo_owner_customer_id} onChange={(event) => setForm({ ...form, cargo_owner_customer_id: event.target.value })}><option value="">مالک محموله (پیش‌فرض)</option>{owners.map((owner) => <option key={owner.id} value={owner.id}>{owner.label}</option>)}</select>
         <Button className="min-h-11" onClick={() => void create()}>افزودن کالا</Button>
      </div></details>
      {!items.length ? <p className="text-sm text-slate-600">هنوز کالایی برای این محموله ثبت نشده است.</p> : <div className="grid gap-3 lg:grid-cols-2">{items.map((item) => <article className="rounded border p-3 text-sm" key={item.public_id}>
        <div className="flex flex-wrap justify-between gap-2"><strong>{item.display_name_snapshot}</strong><span>ردیف {item.line_number}</span></div><p className="mt-2">مقدار کل: <strong>{formatQuantity(item.quantity)} {item.uom_symbol_snapshot}</strong></p><p>مالک کالا: <strong>{item.cargo_owner?.label || "نامشخص / ثبت نشده"}</strong></p><p>تخصیص‌یافته: {formatQuantity(item.allocated_quantity)} {item.uom_symbol_snapshot} · باقیمانده: {formatQuantity(item.remaining_quantity ?? item.quantity)} {item.uom_symbol_snapshot}</p>{item.description_snapshot && <p className="mt-2 text-slate-600">{item.description_snapshot}</p>}
        <div className="mt-3 flex flex-wrap items-center gap-2"><Input aria-label={`Edit quantity line ${item.line_number}`} className="w-28" type="number" min="0.000001" step="any" value={edits[item.public_id] ?? item.quantity} onChange={(event) => setEdits({ ...edits, [item.public_id]: event.target.value })} /><select aria-label={`Cargo owner line ${item.line_number}`} className="min-h-10 rounded border px-2" value={ownerEdits[item.public_id] ?? String(item.cargo_owner?.id || "")} onChange={(event) => setOwnerEdits({ ...ownerEdits, [item.public_id]: event.target.value })}><option value="">نامشخص / ثبت نشده</option>{item.cargo_owner && !owners.some((owner) => owner.id === item.cargo_owner?.id) && <option value={item.cargo_owner.id}>{item.cargo_owner.label}</option>}{owners.map((owner) => <option key={owner.id} value={owner.id}>{owner.label}</option>)}</select><Button variant="outline" onClick={async () => { try { await updateShipmentCargoItem(shipmentPublicId, item.public_id, { quantity: edits[item.public_id] ?? item.quantity, cargo_owner_customer_id: ownerEdits[item.public_id] ?? item.cargo_owner?.id ?? null, version: item.version }); await load(); } catch { setError("مقدار یا مالک کالا به‌روزرسانی نشد؛ صفحه را تازه‌سازی کنید."); } }}>ذخیره <span className="sr-only">Save</span></Button></div>
      </article>)}</div>}
    </CardContent></Card>
    <Card dir="rtl"><CardHeader><CardTitle>وضعیت و پیگیری حمل</CardTitle></CardHeader><CardContent className="space-y-4">
      {tracking ? <><div className="grid gap-3 rounded bg-slate-50 p-3 sm:grid-cols-3"><p><span className="text-slate-500">آخرین وضعیت</span><br /><strong>{label(latest?.event.status || tracking.units[0]?.latest_status)}</strong></p><p><span className="text-slate-500">آخرین موقعیت</span><br /><strong>{latest?.event.location.location_name || "ثبت نشده"}</strong></p><p><span className="text-slate-500">زمان آخرین بروزرسانی</span><br />{time(latest?.event.occurred_at)}</p></div><div className="grid gap-2 md:grid-cols-2">{tracking.units.map((unit) => <article className="rounded border p-3" key={`${unit.source}:${unit.id}`}><strong>{unit.unit_code}</strong>{unit.source === "canonical_execution" ? <span className="mr-2 text-emerald-700">· اجرای جاری</span> : <span className="mr-2 text-amber-700">· سابقه حمل</span>}<span> · {label(unit.latest_status)}</span>{unit.carrier && <p className="mt-1 text-sm">کریر: {unit.carrier}</p>}{unit.vehicle_reference && <p className="mt-1 text-sm">شناسه وسیله: {unit.vehicle_reference}</p>}<div className="mt-2 text-sm">{unit.allocated_cargo.map((cargo) => <p key={`${cargo.cargo_name}-${cargo.allocated_quantity}`}>{cargo.cargo_name}: {cargo.allocated_quantity} {cargo.uom_symbol}{cargo.cargo_owner ? ` · مالک کالا: ${cargo.cargo_owner}` : ""}</p>)}</div></article>)}</div>
        {tracking.units.some((unit) => unit.source !== "canonical_execution") && <details><summary className="cursor-pointer font-medium">ثبت بروزرسانی سابقه حمل</summary><div className="mt-3 flex flex-wrap gap-2"><select aria-label="Tracked transport" value={selectedUnit} onChange={(event) => setSelectedUnit(event.target.value)}><option value="">وسیله حمل</option>{tracking.units.filter((unit) => unit.source !== "canonical_execution").map((unit) => <option key={unit.id} value={unit.id}>{unit.unit_code}</option>)}</select><select aria-label="Tracking status" value={trackingForm.status} onChange={(event) => setTrackingForm({ ...trackingForm, status: event.target.value })}>{Object.entries(statusLabel).map(([value, title]) => <option key={value} value={value}>{title}</option>)}</select><Input aria-label="Tracking location" placeholder="موقعیت فعلی" value={trackingForm.location_text} onChange={(event) => setTrackingForm({ ...trackingForm, location_text: event.target.value })} /><Input aria-label="Customer message" placeholder="پیام برای مشتری" value={trackingForm.customer_message} onChange={(event) => setTrackingForm({ ...trackingForm, customer_message: event.target.value })} /><Button onClick={async () => { try { if (!selectedUnit) throw new Error(); const response = await addOperationalTransportTrackingUpdate(shipmentPublicId, Number(selectedUnit), { ...trackingForm, occurred_at: new Date().toISOString() }); setTracking(response.tracking); } catch { setError("بروزرسانی پیگیری ثبت نشد؛ وسیله حمل را انتخاب کنید."); } }}>ثبت بروزرسانی</Button></div></details>}
      </> : <div><p className="text-slate-600">پیگیری حمل هنوز فعال نشده است.</p><Button className="mt-3" onClick={async () => { try { setTracking((await enableOperationalTransportTracking(shipmentPublicId)).tracking); await load(); } catch { setError("فعال‌سازی پیگیری حمل ممکن نشد."); } }}>فعال‌سازی پیگیری حمل</Button></div>}
    </CardContent></Card>
  </>;
}
