import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatQuantity } from "@/lib/formatQuantity";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import {
  addOperationalTransportTrackingUpdate, createShipmentCargoItem,
  createCanonicalCargoAllocation, createCanonicalShipmentTransportUnit,
  deleteCanonicalCargoAllocation, getCanonicalCargoAllocations,
  getCanonicalShipmentTransportUnits,
  getShipmentCargoHistory,
  enableOperationalTransportTracking,
  getOperationalTransportTracking, getShipmentCargoLineageOptions,
  getShipmentCargoOptions, listShipmentCargoItems, updateShipmentCargoItem,
  updateCanonicalCargoAllocation,
  ApiError,
  type CanonicalCargoAllocation, type CanonicalShipmentTransportUnit,
  type OperationalTransportTracking, type ShipmentCargoItem,
  type OperationalCustomerSelector, type ShipmentCargoLineageOption,
  type ShipmentCargoHistoryEntry,
} from "@/lib/api";

type Option = { public_id: string; code: string; name: string; cargo_type_public_id?: string; default_uom_public_id?: string | null; symbol?: string; preferred?: boolean; selectable?: boolean; measurement_dimension?: "COUNT" | "WEIGHT" | "VOLUME" | "LENGTH" | "OTHER_GOVERNED" };
type CargoEdit = {
  cargo_owner_customer_id: string;
  source_request_public_id: string;
  source_request_cargo_item_public_id: string;
  requested_quantity: string;
  planned_quantity: string;
  actual_quantity: string;
  packaging_type_public_id: string;
  hs_code: string;
  description: string;
  gross_weight: string;
  gross_weight_uom_public_id: string;
  volume: string;
  volume_uom_public_id: string;
  destination_description: string;
  reason: string;
};
const statusLabel: Record<string, string> = { loading: "در حال بارگیری", departed: "حرکت کرده", in_transit: "در مسیر", at_checkpoint: "در نقطه کنترل", delayed: "با تأخیر", arrived_destination: "رسیده به مقصد", delivered: "تحویل شده", cancelled: "لغو شده" };
const missingReferenceGuidance = "این نوع در تعاریف سازمان موجود نیست. برای ادامه، مدیر سازمان باید آن را تعریف یا فعال کند.";
const label = (status?: string) => statusLabel[status || ""] || status || "ثبت نشده";
const time = (value?: string) => formatDualCalendarInstant(value, "fa-IR", { fallback: "ثبت نشده" });
const quantityText = (value: string | null) => value === null ? "نامشخص" : formatQuantity(value);
const incompleteLabel: Record<string, string> = { HS_CODE: "HS", PACKAGING_TYPE: "نوع بسته‌بندی", WEIGHT: "وزن", VOLUME: "حجم" };

export default function ShipmentCargoItems({ shipmentPublicId, projectPublicId, legacyDescription, stageScoped = false }: { shipmentPublicId: string; projectPublicId?: string | null; legacyDescription?: string | null; stageScoped?: boolean }) {
  const [items, setItems] = useState<ShipmentCargoItem[]>([]);
  const [owners, setOwners] = useState<OperationalCustomerSelector[]>([]);
  const [requests, setRequests] = useState<ShipmentCargoLineageOption[]>([]);
  const [options, setOptions] = useState<{ catalog: Option[]; cargo_types: Option[]; uoms: Option[]; packaging_types: Option[] }>({ catalog: [], cargo_types: [], uoms: [], packaging_types: [] });
  const [error, setError] = useState("");
  const [form, setForm] = useState({ line_number: "1", catalog_item_public_id: "", display_name: "", cargo_type_public_id: "", requested_quantity: "", planned_quantity: "", actual_quantity: "", uom_public_id: "", cargo_owner_customer_id: "", source_request_public_id: "", source_request_cargo_item_public_id: "", packaging_type_public_id: "", hs_code: "", description: "", gross_weight: "", gross_weight_uom_public_id: "", volume: "", volume_uom_public_id: "", destination_description: "" });
  const [cargoQuery, setCargoQuery] = useState("");
  const [edits, setEdits] = useState<Record<string, CargoEdit>>({});
  const [historyByCargo, setHistoryByCargo] = useState<Record<string, ShipmentCargoHistoryEntry[]>>({});
  const [tracking, setTracking] = useState<OperationalTransportTracking | null>(null);
  const [units, setUnits] = useState<CanonicalShipmentTransportUnit[]>([]);
  const [allocations, setAllocations] = useState<CanonicalCargoAllocation[]>([]);
  const [unitForm, setUnitForm] = useState({ display_name: "", vehicle_reference: "" });
  const [allocationForm, setAllocationForm] = useState({ unit: "", cargo: "", quantity: "" });
  const [allocationEdits, setAllocationEdits] = useState<Record<string, string>>({});
  const [selectedUnit, setSelectedUnit] = useState("");
  const [trackingForm, setTrackingForm] = useState({ status: "in_transit", location_text: "", customer_message: "", internal_note: "", is_customer_visible: true });
  const load = useCallback(async () => {
    try {
      const [lines, opts, lineage, trackingData, unitData, allocationData] = await Promise.all([listShipmentCargoItems(shipmentPublicId), getShipmentCargoOptions(projectPublicId || undefined, cargoQuery), getShipmentCargoLineageOptions(shipmentPublicId), getOperationalTransportTracking(shipmentPublicId), getCanonicalShipmentTransportUnits(shipmentPublicId), getCanonicalCargoAllocations(shipmentPublicId)]);
      setItems(lines.items); setOptions({ catalog: opts.catalog.filter((option) => option.selectable !== false), cargo_types: opts.cargo_types.filter((option) => option.selectable !== false), uoms: opts.uoms.filter((option) => option.selectable !== false), packaging_types: (opts.packaging_types || []).filter((option) => option.selectable !== false) }); setOwners(lineage.customers); setRequests(lineage.requests); setTracking(trackingData.tracking); setError("");
      setUnits(unitData.units); setAllocations(allocationData.allocations);
    } catch { setError("اطلاعات کالا، وسیله حمل یا پیگیری قابل دریافت نیست. اجازه دسترسی یا اتصال را بررسی کنید."); }
  }, [shipmentPublicId, projectPublicId, cargoQuery]);
  useEffect(() => { void load(); }, [load]);
  const latest = useMemo(() => tracking?.units.flatMap((unit) => unit.history.map((event) => ({ unit, event }))).sort((a, b) => Date.parse(b.event.occurred_at) - Date.parse(a.event.occurred_at))[0], [tracking]);
  const choose = (id: string) => {
    const row = options.catalog.find((option) => option.public_id === id);
    setForm({ ...form, catalog_item_public_id: id, cargo_type_public_id: row?.cargo_type_public_id || form.cargo_type_public_id, uom_public_id: row?.default_uom_public_id || form.uom_public_id, display_name: row?.name || form.display_name });
  };
  const chooseRequest = (id: string) => {
    const row = requests.find((item) => item.public_id === id);
    setForm({ ...form, source_request_public_id: id, source_request_cargo_item_public_id: "", requested_quantity: "", cargo_owner_customer_id: row?.customer_id ? String(row.customer_id) : form.cargo_owner_customer_id });
  };
  const chooseRequestCargo = (id: string) => {
    const requestRow = requests.find((item) => item.public_id === form.source_request_public_id);
    const cargo = requestRow?.cargo_items.find((item) => item.public_id === id);
    setForm({ ...form, source_request_cargo_item_public_id: id, requested_quantity: cargo?.quantity || "", cargo_type_public_id: cargo?.cargo_type_public_id || form.cargo_type_public_id, uom_public_id: cargo?.uom_public_id || form.uom_public_id, display_name: cargo?.description || form.display_name, description: cargo?.description || form.description });
  };
  const initialEdit = (item: ShipmentCargoItem): CargoEdit => ({
    cargo_owner_customer_id: String(item.cargo_owner?.id || ""),
    source_request_public_id: item.source_lineage.request_public_id || "",
    source_request_cargo_item_public_id: item.source_lineage.request_cargo_item_public_id || "",
    requested_quantity: item.quantities.requested || "",
    planned_quantity: item.quantities.planned || "",
    actual_quantity: item.quantities.actual || "",
    packaging_type_public_id: item.packaging?.public_id || "",
    hs_code: item.hs_code_snapshot || "",
    description: item.description_snapshot || "",
    gross_weight: item.gross_weight?.value || "",
    gross_weight_uom_public_id: item.gross_weight?.uom_public_id || "",
    volume: item.volume?.value || "",
    volume_uom_public_id: item.volume?.uom_public_id || "",
    destination_description: item.destination_description || "",
    reason: "",
  });
  const editFor = (item: ShipmentCargoItem) => edits[item.public_id] || initialEdit(item);
  const changeEdit = (item: ShipmentCargoItem, patch: Partial<CargoEdit>) => setEdits((current) => ({ ...current, [item.public_id]: { ...(current[item.public_id] || initialEdit(item)), ...patch } }));
  const referenceUnavailable = options.cargo_types.length === 0 || options.uoms.length === 0 || (Boolean(form.cargo_type_public_id) && !options.cargo_types.some((option) => option.public_id === form.cargo_type_public_id)) || (Boolean(form.uom_public_id) && !options.uoms.some((option) => option.public_id === form.uom_public_id));
  const remainingFor = (cargoId: string, exceptId?: string) => {
    const cargo = items.find((item) => item.public_id === cargoId);
    const allocated = allocations.filter((item) => item.cargo_item_public_id === cargoId && item.public_id !== exceptId).reduce((sum, item) => sum + Number(item.allocated_quantity), 0);
    return Number(cargo?.quantities.planned || cargo?.quantity || 0) - allocated;
  };
  const addUnit = async () => {
    try { await createCanonicalShipmentTransportUnit(shipmentPublicId, { unit_type: "truck", ...unitForm }); setUnitForm({ display_name: "", vehicle_reference: "" }); await load(); }
    catch (caught) { setError(caught instanceof ApiError && caught.status === 403 ? "شما مجوز افزودن وسیله حمل برای این محموله را ندارید." : "افزودن وسیله حمل انجام نشد."); }
  };
  const addAllocation = async () => {
    const quantity = Number(allocationForm.quantity);
    if (!(quantity > 0)) { setError("مقدار تخصیص باید بیشتر از صفر باشد."); return; }
    try { await createCanonicalCargoAllocation(shipmentPublicId, { execution_unit_public_id: allocationForm.unit, cargo_item_public_id: allocationForm.cargo, allocated_quantity: allocationForm.quantity }); setAllocationForm({ unit: "", cargo: "", quantity: "" }); await load(); }
    catch { setError("تخصیص کالا ثبت نشد؛ مقدار و اجازه دسترسی را بررسی کنید."); }
  };
  const create = async () => {
    try {
      await createShipmentCargoItem(shipmentPublicId, { ...form, line_number: Number(form.line_number), quantity: form.planned_quantity, planned_quantity: form.planned_quantity, requested_quantity: form.requested_quantity || undefined, actual_quantity: form.actual_quantity || undefined, catalog_item_public_id: form.catalog_item_public_id || undefined, cargo_owner_customer_id: form.cargo_owner_customer_id ? Number(form.cargo_owner_customer_id) : undefined, source_request_public_id: form.source_request_public_id || undefined, source_request_cargo_item_public_id: form.source_request_cargo_item_public_id || undefined, packaging_type_public_id: form.packaging_type_public_id || undefined, gross_weight: form.gross_weight || undefined, gross_weight_uom_public_id: form.gross_weight_uom_public_id || undefined, volume: form.volume || undefined, volume_uom_public_id: form.volume_uom_public_id || undefined });
      setForm({ ...form, line_number: String(Number(form.line_number) + 1), catalog_item_public_id: "", display_name: "", requested_quantity: "", planned_quantity: "", actual_quantity: "", source_request_public_id: "", source_request_cargo_item_public_id: "", packaging_type_public_id: "", hs_code: "", description: "", gross_weight: "", gross_weight_uom_public_id: "", volume: "", volume_uom_public_id: "", destination_description: "" }); await load();
    } catch (caught) { setError(caught instanceof ApiError && caught.code === "ORGANIZATION_REFERENCE_NOT_ACTIVE" ? missingReferenceGuidance : "مشتری، منبع درخواست، شماره ردیف، مقادیر و واحدها را بررسی کنید."); }
  };
  const saveCargo = async (item: ShipmentCargoItem) => {
    const edit = editFor(item);
    try {
      await updateShipmentCargoItem(shipmentPublicId, item.public_id, {
        cargo_owner_customer_id: Number(edit.cargo_owner_customer_id),
        source_request_public_id: edit.source_request_public_id || null,
        source_request_cargo_item_public_id: edit.source_request_cargo_item_public_id || null,
        requested_quantity: edit.requested_quantity || null,
        planned_quantity: edit.planned_quantity,
        actual_quantity: edit.actual_quantity || null,
        packaging_type_public_id: edit.packaging_type_public_id || null,
        hs_code: edit.hs_code || null,
        description: edit.description || null,
        gross_weight: edit.gross_weight || null,
        gross_weight_uom_public_id: edit.gross_weight ? edit.gross_weight_uom_public_id || null : null,
        volume: edit.volume || null,
        volume_uom_public_id: edit.volume ? edit.volume_uom_public_id || null : null,
        destination_description: edit.destination_description || null,
        reason: edit.reason || null,
        version: item.version,
      });
      setEdits((current) => { const next = { ...current }; delete next[item.public_id]; return next; });
      await load();
      if (historyByCargo[item.public_id]) await showCargoHistory(item);
    } catch { setError("اطلاعات کالا به‌روزرسانی نشد؛ مقادیر، منبع درخواست و نسخه جاری را بررسی کنید."); }
  };
  const showCargoHistory = async (item: ShipmentCargoItem) => {
    try { const response = await getShipmentCargoHistory(shipmentPublicId, item.public_id); setHistoryByCargo((current) => ({ ...current, [item.public_id]: response.history })); }
    catch { setError("تاریخچه اصلاح کالا قابل دریافت نیست."); }
  };
  const selectedCreateRequest = requests.find((item) => item.public_id === form.source_request_public_id);
  const weightUoms = options.uoms.filter((option) => option.measurement_dimension === "WEIGHT");
  const volumeUoms = options.uoms.filter((option) => option.measurement_dimension === "VOLUME");
  return <>
    <Card dir="rtl"><CardHeader><CardTitle>کالا، مشتری و درخواست منبع</CardTitle></CardHeader><CardContent className="space-y-4">
      {error && <p aria-live="polite" className="rounded bg-red-50 p-3 text-red-700">{error}</p>}
      {legacyDescription && <p className="rounded bg-amber-50 p-3 text-sm"><strong>شرح ثبت‌شده پیشین:</strong> {legacyDescription}</p>}
      <details><summary className="cursor-pointer font-medium">افزودن ردیف کالا</summary><div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {referenceUnavailable && <p className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 sm:col-span-2 lg:col-span-3">{missingReferenceGuidance}</p>}
        <Input aria-label="Cargo line number" type="number" min="1" value={form.line_number} onChange={(event) => setForm({ ...form, line_number: event.target.value })} />
        <Input aria-label="Search cargo catalog" placeholder="جست‌وجوی نام، نام جایگزین، کد، برند یا مدل" value={cargoQuery} onChange={(event) => setCargoQuery(event.target.value)} />
        <select aria-label="Catalog item" className="min-h-11 rounded border px-3" value={form.catalog_item_public_id} onChange={(event) => choose(event.target.value)}><option value="">بدون کالای استاندارد؛ شرح فقط برای این محموله</option>{options.catalog.some((option) => option.preferred)&&<optgroup label="کالاهای ترجیحی پروژه">{options.catalog.filter((option)=>option.preferred).map((option) => <option key={option.public_id} value={option.public_id}>★ {option.code} — {option.name}</option>)}</optgroup>}<optgroup label="سایر کالاهای سازمان">{options.catalog.filter((option)=>!option.preferred).map((option) => <option key={option.public_id} value={option.public_id}>{option.code} — {option.name}</option>)}</optgroup></select>
        <Input aria-label="Cargo display name" placeholder="شرح نمایشی این قلم؛ فقط برای این محموله" value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} />
        <select aria-label="Cargo type" className="min-h-11 rounded border px-3" value={form.cargo_type_public_id} onChange={(event) => setForm({ ...form, cargo_type_public_id: event.target.value })}><option value="">نوع کالا</option>{options.cargo_types.map((option) => <option key={option.public_id} value={option.public_id}>{option.name}</option>)}</select>
        <select aria-label="Cargo customer" className="min-h-11 rounded border px-3" value={form.cargo_owner_customer_id} onChange={(event) => setForm({ ...form, cargo_owner_customer_id: event.target.value })}><option value="">مشتری کالا (الزامی)</option>{owners.map((owner) => <option key={owner.id} value={owner.id}>{owner.label}</option>)}</select>
        <select aria-label="Source request" className="min-h-11 rounded border px-3" value={form.source_request_public_id} onChange={(event) => chooseRequest(event.target.value)}><option value="">ثبت مستقیم؛ بدون درخواست منبع</option>{requests.map((request) => <option key={request.public_id} value={request.public_id}>{request.label} — {request.customer_label || "بدون مشتری صریح"}</option>)}</select>
        <select aria-label="Source request cargo" className="min-h-11 rounded border px-3" disabled={!selectedCreateRequest} value={form.source_request_cargo_item_public_id} onChange={(event) => chooseRequestCargo(event.target.value)}><option value="">قلم درخواست منبع (اختیاری)</option>{selectedCreateRequest?.cargo_items.map((cargo) => <option key={cargo.public_id} value={cargo.public_id}>{cargo.description || "قلم درخواست"}{cargo.quantity ? ` — ${cargo.quantity} ${cargo.uom_symbol || ""}` : ""}</option>)}</select>
        <Input aria-label="Requested quantity" type="number" min="0.000001" step="any" placeholder="مقدار درخواستی؛ فقط با درخواست منبع" disabled={!form.source_request_public_id} value={form.requested_quantity} onChange={(event) => setForm({ ...form, requested_quantity: event.target.value })} />
        <Input aria-label="Planned quantity" type="number" min="0.000001" step="any" placeholder="مقدار برنامه‌ریزی‌شده (الزامی)" value={form.planned_quantity} onChange={(event) => setForm({ ...form, planned_quantity: event.target.value })} />
        <Input aria-label="Actual quantity" type="number" min="0.000001" step="any" placeholder="مقدار واقعی؛ در صورت معلوم بودن" value={form.actual_quantity} onChange={(event) => setForm({ ...form, actual_quantity: event.target.value })} />
        <select aria-label="Unit of measure" className="min-h-11 rounded border px-3" value={form.uom_public_id} onChange={(event) => setForm({ ...form, uom_public_id: event.target.value })}><option value="">واحد اندازه‌گیری</option>{options.uoms.map((option) => <option key={option.public_id} value={option.public_id}>{option.name} ({option.symbol})</option>)}</select>
        <select aria-label="Packaging type" className="min-h-11 rounded border px-3" value={form.packaging_type_public_id} onChange={(event) => setForm({ ...form, packaging_type_public_id: event.target.value })}><option value="">نوع بسته‌بندی؛ بعداً هم قابل تکمیل است</option>{options.packaging_types.map((option) => <option key={option.public_id} value={option.public_id}>{option.name}</option>)}</select>
        <Input aria-label="HS code" placeholder="کد HS؛ نبودن آن مانع ثبت نیست" value={form.hs_code} onChange={(event) => setForm({ ...form, hs_code: event.target.value })} />
        <Input aria-label="Cargo description" placeholder="شرح تکمیلی" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
        <Input aria-label="Cargo destination description" placeholder="مقصد این قلم؛ در صورت تفاوت" value={form.destination_description} onChange={(event) => setForm({ ...form, destination_description: event.target.value })} />
        <Input aria-label="Gross weight" type="number" min="0.000001" step="any" placeholder="وزن ناخالص" value={form.gross_weight} onChange={(event) => setForm({ ...form, gross_weight: event.target.value })} />
        <select aria-label="Gross weight unit" className="min-h-11 rounded border px-3" value={form.gross_weight_uom_public_id} onChange={(event) => setForm({ ...form, gross_weight_uom_public_id: event.target.value })}><option value="">واحد وزن</option>{weightUoms.map((option) => <option key={option.public_id} value={option.public_id}>{option.name} ({option.symbol})</option>)}</select>
        <Input aria-label="Cargo volume" type="number" min="0.000001" step="any" placeholder="حجم" value={form.volume} onChange={(event) => setForm({ ...form, volume: event.target.value })} />
        <select aria-label="Cargo volume unit" className="min-h-11 rounded border px-3" value={form.volume_uom_public_id} onChange={(event) => setForm({ ...form, volume_uom_public_id: event.target.value })}><option value="">واحد حجم</option>{volumeUoms.map((option) => <option key={option.public_id} value={option.public_id}>{option.name} ({option.symbol})</option>)}</select>
        <p className="text-xs text-slate-600 sm:col-span-2 lg:col-span-3">در این مرحله تبدیل واحد انجام نمی‌شود. مقدار درخواستی، برنامه‌ریزی‌شده و واقعی مستقل نگه داشته می‌شوند.</p>
        <Button className="min-h-11" disabled={referenceUnavailable || !form.cargo_owner_customer_id || !form.cargo_type_public_id || !form.uom_public_id || !form.planned_quantity || (Boolean(form.gross_weight) !== Boolean(form.gross_weight_uom_public_id)) || (Boolean(form.volume) !== Boolean(form.volume_uom_public_id))} onClick={() => void create()}>افزودن کالا</Button>
      </div></details>
      {!items.length ? <p className="text-sm text-slate-600">هنوز کالایی برای این محموله ثبت نشده است.</p> : <div className="grid gap-3 lg:grid-cols-2">{items.map((item) => <article className="rounded border p-3 text-sm" key={item.public_id}>
        <div className="flex flex-wrap justify-between gap-2"><strong>{item.display_name_snapshot}</strong><span>ردیف {item.line_number}</span></div>
        <p className="mt-2">نوع ثبت‌شده: <strong>{item.cargo_type_fa_snapshot}</strong></p><p>مشتری کالا: <strong>{item.cargo_owner?.label || "نامشخص / داده پیشین"}</strong></p>
        <p>منبع: <strong>{item.source_lineage.kind === "REQUEST" ? `درخواست ${item.source_lineage.request_reference || ""}` : item.source_lineage.kind === "DIRECT" ? "ثبت مستقیم" : "نامشخص / داده پیشین"}</strong></p>
        <div className="my-2 grid grid-cols-3 gap-2 rounded bg-slate-50 p-2 text-center"><p><span className="text-slate-500">درخواستی</span><br /><strong>{quantityText(item.quantities.requested)}</strong></p><p><span className="text-slate-500">برنامه‌ریزی‌شده</span><br /><strong>{quantityText(item.quantities.planned)}</strong></p><p><span className="text-slate-500">واقعی</span><br /><strong>{quantityText(item.quantities.actual)}</strong></p><p className="col-span-3 text-xs">واحد: {item.uom_symbol_snapshot}</p></div>
        {item.quantities.legacy_meaning === "UNKNOWN" && <p className="rounded bg-amber-50 p-2 text-amber-900">معنای مقدار این داده پیشین مشخص نیست و به مقدار برنامه‌ریزی‌شده تبدیل نشده است.</p>}
        <p>بسته‌بندی: {item.packaging?.fa_name || "نامشخص"} · HS: {item.hs_code_snapshot || "نامشخص"}</p><p>وزن ناخالص: {item.gross_weight ? `${formatQuantity(item.gross_weight.value)} ${item.gross_weight.uom_symbol}` : "نامشخص"} · حجم: {item.volume ? `${formatQuantity(item.volume.value)} ${item.volume.uom_symbol}` : "نامشخص"}</p>{item.destination_description && <p>مقصد قلم: {item.destination_description}</p>}{!stageScoped && <p>تخصیص قدیمی بدون بخش مسیر: {formatQuantity(item.allocated_quantity)} {item.uom_symbol_snapshot} · مانده نسبت به مقدار کالا: {formatQuantity(item.remaining_quantity ?? item.quantity)} {item.uom_symbol_snapshot}</p>}{item.description_snapshot && <p className="mt-2 text-slate-600">{item.description_snapshot}</p>}
        {item.incomplete_fields.length > 0 && <p className="mt-2 text-xs text-amber-800">اطلاعات قابل تکمیل: {item.incomplete_fields.map((field) => incompleteLabel[field] || field).join("، ")}</p>}
        <details className="mt-3"><summary className="cursor-pointer font-medium">تکمیل یا اصلاح اطلاعات</summary><div className="mt-2 grid gap-2 sm:grid-cols-2">
          <select aria-label={`Edit cargo customer line ${item.line_number}`} className="min-h-10 rounded border px-2" value={editFor(item).cargo_owner_customer_id} onChange={(event) => changeEdit(item, { cargo_owner_customer_id: event.target.value })}>{item.cargo_owner && !owners.some((owner) => owner.id === item.cargo_owner?.id) && <option value={item.cargo_owner.id}>{item.cargo_owner.label}</option>}{owners.map((owner) => <option key={owner.id} value={owner.id}>{owner.label}</option>)}</select>
          <select aria-label={`Edit source request line ${item.line_number}`} className="min-h-10 rounded border px-2" value={editFor(item).source_request_public_id} onChange={(event) => changeEdit(item, { source_request_public_id: event.target.value, source_request_cargo_item_public_id: "", requested_quantity: "", ...(requests.find((request) => request.public_id === event.target.value)?.customer_id ? { cargo_owner_customer_id: String(requests.find((request) => request.public_id === event.target.value)?.customer_id) } : {}) })}><option value="">ثبت مستقیم</option>{requests.map((request) => <option key={request.public_id} value={request.public_id}>{request.label}</option>)}</select>
          <select aria-label={`Edit source request cargo line ${item.line_number}`} className="min-h-10 rounded border px-2" disabled={!editFor(item).source_request_public_id} value={editFor(item).source_request_cargo_item_public_id} onChange={(event) => { const cargo = requests.find((request) => request.public_id === editFor(item).source_request_public_id)?.cargo_items.find((candidate) => candidate.public_id === event.target.value); changeEdit(item, { source_request_cargo_item_public_id: event.target.value, requested_quantity: cargo?.quantity || "" }); }}><option value="">قلم درخواست منبع</option>{requests.find((request) => request.public_id === editFor(item).source_request_public_id)?.cargo_items.map((cargo) => <option key={cargo.public_id} value={cargo.public_id}>{cargo.description || "قلم درخواست"}</option>)}</select>
          <Input aria-label={`Edit requested quantity line ${item.line_number}`} type="number" min="0.000001" step="any" placeholder="درخواستی" disabled={!editFor(item).source_request_public_id} value={editFor(item).requested_quantity} onChange={(event) => changeEdit(item, { requested_quantity: event.target.value })} />
          <Input aria-label={`Edit planned quantity line ${item.line_number}`} type="number" min="0.000001" step="any" placeholder="برنامه‌ریزی‌شده" value={editFor(item).planned_quantity} onChange={(event) => changeEdit(item, { planned_quantity: event.target.value })} />
          <Input aria-label={`Edit actual quantity line ${item.line_number}`} type="number" min="0.000001" step="any" placeholder="واقعی" value={editFor(item).actual_quantity} onChange={(event) => changeEdit(item, { actual_quantity: event.target.value })} />
          <Input aria-label={`Edit cargo reason line ${item.line_number}`} placeholder="دلیل اصلاح برنامه یا مقدار واقعی، در صورت وجود" value={editFor(item).reason} onChange={(event) => changeEdit(item, { reason: event.target.value })} />
          <select aria-label={`Edit packaging line ${item.line_number}`} className="min-h-10 rounded border px-2" value={editFor(item).packaging_type_public_id} onChange={(event) => changeEdit(item, { packaging_type_public_id: event.target.value })}><option value="">بسته‌بندی نامشخص</option>{options.packaging_types.map((option) => <option key={option.public_id} value={option.public_id}>{option.name}</option>)}</select>
          <Input aria-label={`Edit HS line ${item.line_number}`} placeholder="کد HS" value={editFor(item).hs_code} onChange={(event) => changeEdit(item, { hs_code: event.target.value })} />
          <Input aria-label={`Edit description line ${item.line_number}`} placeholder="شرح تکمیلی" value={editFor(item).description} onChange={(event) => changeEdit(item, { description: event.target.value })} />
          <Input aria-label={`Edit destination line ${item.line_number}`} placeholder="مقصد قلم" value={editFor(item).destination_description} onChange={(event) => changeEdit(item, { destination_description: event.target.value })} />
          <Input aria-label={`Edit gross weight line ${item.line_number}`} type="number" min="0.000001" step="any" placeholder="وزن ناخالص" value={editFor(item).gross_weight} onChange={(event) => changeEdit(item, { gross_weight: event.target.value })} />
          <select aria-label={`Edit gross weight unit line ${item.line_number}`} className="min-h-10 rounded border px-2" value={editFor(item).gross_weight_uom_public_id} onChange={(event) => changeEdit(item, { gross_weight_uom_public_id: event.target.value })}><option value="">واحد وزن</option>{weightUoms.map((option) => <option key={option.public_id} value={option.public_id}>{option.name}</option>)}</select>
          <Input aria-label={`Edit volume line ${item.line_number}`} type="number" min="0.000001" step="any" placeholder="حجم" value={editFor(item).volume} onChange={(event) => changeEdit(item, { volume: event.target.value })} />
          <select aria-label={`Edit volume unit line ${item.line_number}`} className="min-h-10 rounded border px-2" value={editFor(item).volume_uom_public_id} onChange={(event) => changeEdit(item, { volume_uom_public_id: event.target.value })}><option value="">واحد حجم</option>{volumeUoms.map((option) => <option key={option.public_id} value={option.public_id}>{option.name}</option>)}</select>
          <Button variant="outline" disabled={!editFor(item).cargo_owner_customer_id || !editFor(item).planned_quantity || (Boolean(editFor(item).gross_weight) !== Boolean(editFor(item).gross_weight_uom_public_id)) || (Boolean(editFor(item).volume) !== Boolean(editFor(item).volume_uom_public_id))} onClick={() => void saveCargo(item)}>ذخیره اطلاعات کالا</Button>
        </div></details>
        <div className="mt-2"><Button variant="link" onClick={() => void showCargoHistory(item)}>تاریخچه برنامه و مقدار واقعی</Button>{historyByCargo[item.public_id] && <ol className="space-y-2">{historyByCargo[item.public_id].filter((entry) => entry.changed_fields.some((field) => ["planned_quantity", "actual_quantity"].includes(field))).map((entry, index) => <li key={`${entry.version}-${index}`} className="rounded bg-slate-50 p-2 text-xs"><p>{entry.changed_fields.filter((field) => ["planned_quantity", "actual_quantity"].includes(field)).map((field) => `${field === "planned_quantity" ? "برنامه" : "مقدار واقعی"}: ${entry.changes?.[field]?.before ?? "نامشخص"} ← ${entry.changes?.[field]?.after ?? "نامشخص"}`).join(" · ")}</p><p>{entry.actor_name} · {time(entry.recorded_at)}{entry.reason ? ` · دلیل: ${entry.reason}` : ""}</p></li>)}</ol>}</div>
      </article>)}</div>}
    </CardContent></Card>
    {stageScoped ? allocations.length > 0 && <Card dir="rtl"><CardHeader><CardTitle>تخصیص‌های قدیمی بدون بخش مسیر</CardTitle></CardHeader><CardContent><p className="text-sm text-amber-900">برای این ردیف‌های پیشین، برنامه یا واقعیت و بخش مسیر قابل اثبات نیست. تخصیص تازه را در بخش «تخصیص و مسیر هر کالا» ثبت کنید.</p><ul className="mt-2 space-y-1 text-sm">{allocations.map((item) => <li key={item.public_id}>{item.cargo_name}: {formatQuantity(item.allocated_quantity)} {item.uom_symbol}</li>)}</ul></CardContent></Card> : <Card dir="rtl"><CardHeader><CardTitle>وسایل حمل و تخصیص کالا</CardTitle></CardHeader><CardContent className="space-y-4">
      <p className="text-sm text-muted-foreground">تخصیص بار مستقل از پیگیری موقعیت وسیله حمل است.</p>
      <details><summary className="cursor-pointer font-medium">افزودن وسیله حمل</summary><div className="mt-3 flex flex-wrap gap-2"><Input aria-label="نام وسیله حمل" placeholder="نام کامیون" value={unitForm.display_name} onChange={(event) => setUnitForm({ ...unitForm, display_name: event.target.value })} /><Input aria-label="شناسه وسیله حمل" placeholder="پلاک یا شناسه کامیون" value={unitForm.vehicle_reference} onChange={(event) => setUnitForm({ ...unitForm, vehicle_reference: event.target.value })} /><Button onClick={() => void addUnit()}>افزودن کامیون</Button></div></details>
      {units.length === 0 ? <p className="text-sm text-muted-foreground">هنوز وسیله حملی ثبت نشده است.</p> : <div className="grid gap-2 md:grid-cols-2">{units.map((unit) => <article className="rounded border p-3" key={unit.public_id}><strong>{unit.display_name || "کامیون"}</strong><p className="text-sm" dir="ltr">{unit.vehicle_reference || unit.unit_code}</p><div className="mt-2 text-sm">{allocations.filter((allocation) => allocation.execution_unit_public_id === unit.public_id).map((allocation) => <p key={allocation.public_id}>{allocation.cargo_name}: {formatQuantity(allocation.allocated_quantity)} {allocation.uom_symbol}</p>) || "—"}</div></article>)}</div>}
      <div className="grid gap-2 rounded border p-3 sm:grid-cols-4"><select aria-label="وسیله حمل برای تخصیص" className="min-h-11 min-w-0 w-full rounded border px-3" value={allocationForm.unit} onChange={(event) => setAllocationForm({ ...allocationForm, unit: event.target.value })}><option value="">وسیله حمل</option>{units.map((unit) => <option key={unit.public_id} value={unit.public_id}>{unit.display_name || "کامیون"} · {unit.unit_code}</option>)}</select><select aria-label="کالا برای تخصیص" className="min-h-11 min-w-0 w-full rounded border px-3" value={allocationForm.cargo} onChange={(event) => setAllocationForm({ ...allocationForm, cargo: event.target.value })}><option value="">کالا</option>{items.map((item) => <option key={item.public_id} value={item.public_id}>{item.display_name_snapshot} · باقی‌مانده {formatQuantity(remainingFor(item.public_id))} {item.uom_symbol_snapshot}</option>)}</select><Input aria-label="مقدار تخصیص" className="min-w-0 w-full" type="number" min="0.000001" step="any" placeholder="مقدار تخصیص" value={allocationForm.quantity} onChange={(event) => setAllocationForm({ ...allocationForm, quantity: event.target.value })} /><Button className="min-w-0 w-full" disabled={!allocationForm.unit || !allocationForm.cargo || !allocationForm.quantity} onClick={() => void addAllocation()}>تخصیص کالا</Button></div>
      <div className="space-y-2">{items.map((item) => <article className="rounded bg-slate-50 p-3 text-sm" key={`summary-${item.public_id}`}><strong>{item.display_name_snapshot}</strong><p>کل: {formatQuantity(item.quantity)} {item.uom_symbol_snapshot} · تخصیص‌یافته: {formatQuantity(item.allocated_quantity)} · اختلاف با کل: {formatQuantity(item.remaining_quantity ?? item.quantity)}</p>{allocations.filter((allocation) => allocation.cargo_item_public_id === item.public_id).map((allocation) => <div className="mt-2 flex flex-wrap items-center gap-2" key={allocation.public_id}><span>{units.find((unit) => unit.public_id === allocation.execution_unit_public_id)?.display_name || "کامیون"}</span><Input aria-label={`ویرایش تخصیص ${item.display_name_snapshot}`} className="w-28" type="number" min="0.000001" step="any" value={allocationEdits[allocation.public_id] ?? allocation.allocated_quantity} onChange={(event) => setAllocationEdits({ ...allocationEdits, [allocation.public_id]: event.target.value })} /><Button variant="outline" onClick={async () => { const quantity = Number(allocationEdits[allocation.public_id] ?? allocation.allocated_quantity); if (!(quantity > 0)) { setError("مقدار تخصیص باید مثبت باشد."); return; } try { await updateCanonicalCargoAllocation(shipmentPublicId, allocation.public_id, { allocated_quantity: String(quantity) }); await load(); } catch { setError("ویرایش تخصیص انجام نشد."); } }}>ویرایش</Button><Button variant="ghost" onClick={async () => { try { await deleteCanonicalCargoAllocation(shipmentPublicId, allocation.public_id); await load(); } catch { setError("پایان تخصیص انجام نشد."); } }}>پایان تخصیص</Button></div>)}</article>)}</div>
    </CardContent></Card>}
    <Card dir="rtl"><CardHeader><CardTitle>وضعیت و پیگیری حمل</CardTitle></CardHeader><CardContent className="space-y-4">
      {tracking ? <><div className="grid gap-3 rounded bg-slate-50 p-3 sm:grid-cols-3"><p><span className="text-slate-500">آخرین وضعیت</span><br /><strong>{label(latest?.event.status || tracking.units[0]?.latest_status)}</strong></p><p><span className="text-slate-500">آخرین موقعیت</span><br /><strong>{latest?.event.location.location_name || "ثبت نشده"}</strong></p><p><span className="text-slate-500">زمان آخرین بروزرسانی</span><br />{time(latest?.event.occurred_at)}</p></div><div className="grid gap-2 md:grid-cols-2">{tracking.units.map((unit) => <article className="rounded border p-3" key={`${unit.source}:${unit.id}`}><strong>{unit.unit_code}</strong>{unit.source === "canonical_execution" ? <span className="mr-2 text-emerald-700">· اجرای جاری</span> : <span className="mr-2 text-amber-700">· سابقه حمل</span>}<span> · {label(unit.latest_status)}</span>{unit.carrier && <p className="mt-1 text-sm">کریر: {unit.carrier}</p>}{unit.vehicle_reference && <p className="mt-1 text-sm">شناسه وسیله: {unit.vehicle_reference}</p>}<div className="mt-2 text-sm">{unit.allocated_cargo.map((cargo) => <p key={`${cargo.cargo_name}-${cargo.allocated_quantity}`}>{cargo.cargo_name}: {formatQuantity(cargo.allocated_quantity)} {cargo.uom_symbol}{cargo.cargo_owner ? ` · مالک کالا: ${cargo.cargo_owner}` : ""}</p>)}</div></article>)}</div>
        {tracking.units.some((unit) => unit.source !== "canonical_execution") && <details><summary className="cursor-pointer font-medium">ثبت بروزرسانی سابقه حمل</summary><div className="mt-3 flex flex-wrap gap-2"><select aria-label="Tracked transport" value={selectedUnit} onChange={(event) => setSelectedUnit(event.target.value)}><option value="">وسیله حمل</option>{tracking.units.filter((unit) => unit.source !== "canonical_execution").map((unit) => <option key={unit.id} value={unit.id}>{unit.unit_code}</option>)}</select><select aria-label="Tracking status" value={trackingForm.status} onChange={(event) => setTrackingForm({ ...trackingForm, status: event.target.value })}>{Object.entries(statusLabel).map(([value, title]) => <option key={value} value={value}>{title}</option>)}</select><Input aria-label="Tracking location" placeholder="موقعیت فعلی" value={trackingForm.location_text} onChange={(event) => setTrackingForm({ ...trackingForm, location_text: event.target.value })} /><Input aria-label="Customer message" placeholder="پیام برای مشتری" value={trackingForm.customer_message} onChange={(event) => setTrackingForm({ ...trackingForm, customer_message: event.target.value })} /><Button onClick={async () => { try { if (!selectedUnit) throw new Error(); const response = await addOperationalTransportTrackingUpdate(shipmentPublicId, Number(selectedUnit), { ...trackingForm, occurred_at: new Date().toISOString() }); setTracking(response.tracking); } catch { setError("بروزرسانی پیگیری ثبت نشد؛ وسیله حمل را انتخاب کنید."); } }}>ثبت بروزرسانی</Button></div></details>}
      </> : <div><p className="text-slate-600">پیگیری حمل هنوز فعال نشده است.</p><Button className="mt-3" onClick={async () => { try { setTracking((await enableOperationalTransportTracking(shipmentPublicId)).tracking); await load(); } catch { setError("فعال‌سازی پیگیری حمل ممکن نشد."); } }}>فعال‌سازی پیگیری حمل</Button></div>}
    </CardContent></Card>
  </>;
}
