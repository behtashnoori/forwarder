import { useEffect, useState } from "react";
import OperationalPermission from "@/components/OperationalPermission";
import { InternationalLocationSelector } from "@/components/InternationalLocationSelector";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  ApiError, activateRoutePlan, addRouteCheckpoint, addRouteLeg, createRoutePlan,
  fetchCountries, fetchProvinces, listLogisticsPoints,
  searchIranDestinations, updateRouteCheckpoint, updateRouteLeg, validateRoutePlan,
  type Country, type InternationalCity, type IranDestinationOption, type LogisticsPointView,
  type OperationalLocationRef, type Province, type RouteCheckpoint, type RouteLeg,
  type RoutePlanDetail, type RouteValidationResult,
} from "@/lib/api";
import { localDateTimeInputToUtc, toLocalDateTimeInputValue } from "@/lib/localDateTime";
import { useI18n } from "@/i18n";

const selectClass = "min-h-11 min-w-0 w-full rounded border bg-white px-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2";
const modes = ["road", "rail", "sea", "air", "multimodal_transfer", "customs_handling"];
const checkpointTypes = ["origin_loading", "export_customs", "border_exit", "transit_border_entry", "transit_border_exit", "border_entry", "import_customs", "port_entry", "port_exit", "terminal_arrival", "transshipment", "destination_arrival", "unloading", "final_delivery"];
const checkpointNames: Record<string, string> = { origin_loading: "بارگیری مبدأ", export_customs: "گمرک صادرات", border_exit: "خروج از مرز", transit_border_entry: "ورود به مرز ترانزیت", transit_border_exit: "خروج از مرز ترانزیت", border_entry: "ورود از مرز", import_customs: "گمرک واردات", port_entry: "ورود به بندر", port_exit: "خروج از بندر", terminal_arrival: "رسیدن به پایانه", transshipment: "انتقال بین وسایل حمل", destination_arrival: "رسیدن به مقصد", unloading: "تخلیه", final_delivery: "تحویل نهایی" };
const modeNames: Record<string, string> = { multimodal_transfer: "انتقال چندوجهی", customs_handling: "عملیات گمرکی" };
const validationMessage = (code: string) => ({
  ROUTE_PLAN_INVALID: "برای فعال‌سازی، دست‌کم یک بخش مسیر لازم است.",
  ROUTE_SEQUENCE_GAP: "ترتیب بخش‌های مسیر باید پیوسته باشد.",
  ROUTE_LOCATION_DISCONTINUITY: "مقصد هر بخش باید با مبدأ بخش بعدی یکسان باشد.",
  INVALID_ROUTE_TIMELINE: "زمان‌بندی بخش‌های مسیر یا نقاط کنترل معتبر نیست.",
  CHECKPOINT_SEQUENCE_INVALID: "ترتیب نقاط کنترل را بررسی کنید؛ تحویل نهایی باید آخر باشد.",
  ROUTE_DEPENDENCY_CYCLE: "وابستگی نقاط کنترل معتبر نیست.",
}[code] || "ساختار مسیر نیاز به بررسی دارد.");
const commandError = (error: unknown) => {
  if (!(error instanceof ApiError)) return "انجام این کار ممکن نشد؛ دوباره تلاش کنید.";
  if (error.status === 403) return "شما مجوز انجام این اقدام را ندارید.";
  if (error.code === "ROUTE_SEQUENCE_DUPLICATE") return "این شماره ترتیب قبلاً برای بخش دیگری ثبت شده است.";
  if (error.code === "INVALID_ROUTE_TIMELINE") return "ترتیب زمانی یا مکان‌های بخش مسیر معتبر نیست.";
  if (error.code === "LOCATION_MAPPING_REQUIRED" || error.code === "LOCATION_ANCESTRY_MISMATCH") return "مکان انتخاب‌شده برای این مسیر معتبر نیست.";
  if (error.code === "CROSS_PLAN_REFERENCE_NOT_ALLOWED") return "بخش انتخاب‌شده به این برنامه مسیر تعلق ندارد.";
  if (error.code === "ROUTE_PLAN_NOT_DRAFT" || error.code === "ACTUAL_DATA_IMMUTABLE") return "این بخش از مسیر دیگر قابل ویرایش نیست.";
  if (error.status === 409) return "اطلاعات مسیر تغییر کرده است. نسخه تازه بارگذاری شد؛ دوباره بررسی کنید.";
  if (error.code === "ROUTE_PLAN_INVALID") return "مسیر هنوز آماده فعال‌سازی نیست؛ ابتدا آن را بررسی کنید.";
  return "اطلاعات مسیر را بررسی کنید و دوباره تلاش کنید.";
};

type Catalog = { provinces: Province[]; iran: IranDestinationOption[]; facilities: LogisticsPointView[]; countries: Country[] };
function LocationPicker({ id, label, value, onChange, catalog, searchIran, includeFacilities = true }: {
  id: string; label: string; value: OperationalLocationRef | null;
  onChange: (value: OperationalLocationRef | null) => void; catalog: Catalog; searchIran: (query: string) => void; includeFacilities?: boolean;
}) {
  const [country, setCountry] = useState("");
  const [cities, setCities] = useState<InternationalCity[]>([]);
  const [countryQuery, setCountryQuery] = useState("");
  const [query, setQuery] = useState("");
  const key = value ? `${value.source_type}:${value.source_id}` : "";
  const options = [
    ...catalog.provinces.map((row) => ({ key: `province:${row.id}`, label: row.name, group: "استان" })),
    ...catalog.iran.map((row) => ({ key: `${row.identity.type === "port" ? "iran_port" : row.identity.type === "customs" ? "customs_office" : row.identity.type}:${row.identity.id}`, label: row.label, group: "مکان ایران" })),
    ...cities.map((row) => ({ key: `international_city:${row.id}`, label: row.name, group: "شهر بین‌المللی" })),
    ...(includeFacilities ? catalog.facilities.map((row) => ({ key: `logistics_point:${row.public_id}`, label: row.fa_name, group: "نقطه عملیاتی (موقعیت جغرافیایی وابسته)" })) : []),
  ];
  if (key && !options.some((row) => row.key === key)) options.unshift({ key, label: "مکان انتخاب‌شده", group: "انتخاب فعلی" });
  return <div className="min-w-0 space-y-2">
    <label className="block text-sm font-medium" htmlFor={id}>{label}</label>
    <div className="flex min-w-0 flex-col gap-2 sm:flex-row"><Input aria-label={`${label} جست‌وجوی مکان ایران`} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="جست‌وجوی شهر، بندر یا گمرک" /><Button type="button" variant="outline" aria-label={`${label} جست‌وجو`} onClick={() => searchIran(query)}>جست‌وجو</Button></div>
    <Input aria-label={`${label} جست‌وجوی کشور`} value={countryQuery} onChange={(event) => setCountryQuery(event.target.value)} placeholder="جست‌وجوی کشور / Country" />
    <select className={selectClass} aria-label={`${label} کشور شهر بین‌المللی`} value={country} onChange={(event) => { setCountry(event.target.value); setCities([]); }}><option value="">کشور برای شهر بین‌المللی</option>{catalog.countries.filter((row) => { const needle = countryQuery.trim().toLocaleLowerCase(); return !needle || String(row.id) === country || [row.name, row.name_en, row.code].some((item) => item.toLocaleLowerCase().includes(needle)); }).map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select>
    <InternationalLocationSelector key={`${id}-${country}`} countryId={country} locale="fa" side={id.includes("origin") ? "origin" : id.includes("destination") ? "destination" : "location"} selected={cities.find((city) => key === `international_city:${city.id}`) ?? null} onChange={(city) => { setCities(city ? [city] : []); onChange(city ? { source_type: "international_city", source_id: city.id } : null); }} />
    <select id={id} className={selectClass} value={key} onChange={(event) => { const selected = event.target.value; const split = selected.indexOf(":"); onChange(split < 0 ? null : { source_type: selected.slice(0, split) as OperationalLocationRef["source_type"], source_id: selected.startsWith("logistics_point:") ? selected.slice(split + 1) : Number(selected.slice(split + 1)) }); }}>
      <option value="">انتخاب مکان معتبر</option>
      {options.map((row) => <option key={row.key} value={row.key}>{row.group} · {row.label}</option>)}
    </select>
  </div>;
}

function LegForm({ shipmentId, plan, leg, catalog, searchIran, execute, close, busy }: {
  shipmentId: string; plan: RoutePlanDetail; leg?: RouteLeg; catalog: Catalog; searchIran: (query: string) => void;
  execute: (name: string, action: () => Promise<unknown>) => Promise<boolean>; close: () => void; busy: boolean;
}) {
  const { transportLabel } = useI18n();
  const [sequence, setSequence] = useState(String(leg?.sequence_number ?? plan.legs.length + 1));
  const [origin, setOrigin] = useState<OperationalLocationRef | null>(null);
  const [destination, setDestination] = useState<OperationalLocationRef | null>(null);
  const [mode, setMode] = useState(leg?.transport_mode || "road");
  const [departure, setDeparture] = useState(leg?.planned_departure ? toLocalDateTimeInputValue(new Date(leg.planned_departure)) : "");
  const [arrival, setArrival] = useState(leg?.planned_arrival ? toLocalDateTimeInputValue(new Date(leg.planned_arrival)) : "");
  const [carrier, setCarrier] = useState(leg?.carrier_reference || "");
  const [error, setError] = useState("");
  const submit = async () => {
    const number = Number(sequence);
    if (!Number.isInteger(number) || number < 1) { setError("شماره ترتیب را وارد کنید."); return; }
    if (leg) {
      const payload = { expected_version: leg.version, sequence_number: number, carrier_reference: carrier || null, ...(origin ? { origin } : {}), ...(destination ? { destination } : {}) };
      if (await execute(`leg-${leg.id}`, () => updateRouteLeg(shipmentId, plan.id, leg.id, payload))) close();
    } else {
      const start = localDateTimeInputToUtc(departure), end = localDateTimeInputToUtc(arrival);
      if (!origin || !destination || !start || !end) { setError("مبدأ، مقصد و زمان‌های برنامه‌ریزی‌شده را تکمیل کنید."); return; }
      if (await execute("leg-create", () => addRouteLeg(shipmentId, plan.id, { sequence_number: number, origin, destination, transport_mode: mode, planned_departure: start, planned_arrival: end, carrier_reference: carrier || null }))) close();
    }
  };
  return <div className="space-y-3 rounded border bg-slate-50 p-3">
    <h4 className="font-semibold">{leg ? `ویرایش بخش مسیر ${leg.sequence_number}` : "افزودن بخش مسیر"}</h4>
    <div className="grid min-w-0 gap-3 md:grid-cols-2"><div><label htmlFor={`leg-seq-${leg?.id || "new"}`}>ترتیب بخش مسیر</label><Input id={`leg-seq-${leg?.id || "new"}`} type="number" min="1" value={sequence} onChange={(event) => setSequence(event.target.value)} /></div><div><label htmlFor={`leg-carrier-${leg?.id || "new"}`}>شناسه حمل‌کننده (اختیاری)</label><Input id={`leg-carrier-${leg?.id || "new"}`} value={carrier} onChange={(event) => setCarrier(event.target.value)} /></div></div>
    {leg && <p className="text-sm">مبدأ فعلی: {leg.origin.display_name} · مقصد فعلی: {leg.destination.display_name}</p>}
    <div className="grid min-w-0 gap-3 md:grid-cols-2"><LocationPicker id={`leg-origin-${leg?.id || "new"}`} label={leg ? "مبدأ جدید (اختیاری)" : "مبدأ"} value={origin} onChange={setOrigin} catalog={catalog} searchIran={searchIran} /><LocationPicker id={`leg-destination-${leg?.id || "new"}`} label={leg ? "مقصد جدید (اختیاری)" : "مقصد"} value={destination} onChange={setDestination} catalog={catalog} searchIran={searchIran} /></div>
    {leg ? <p className="text-sm text-slate-600">روش حمل و زمان‌های برنامه‌ریزی‌شده این بخش در فرمان ویرایش فعلی قابل تغییر نیستند. برای تغییر ساختار، از پیش‌نویس مسیر استفاده کنید.</p> : <div className="grid min-w-0 gap-3 md:grid-cols-3"><div><label htmlFor="leg-mode">روش حمل</label><select id="leg-mode" className={selectClass} value={mode} onChange={(event) => setMode(event.target.value)}>{modes.map((item) => <option key={item} value={item}>{modeNames[item] || transportLabel(item)}</option>)}</select></div><div><label htmlFor="leg-departure">حرکت برنامه‌ریزی‌شده</label><Input id="leg-departure" type="datetime-local" value={departure} onChange={(event) => setDeparture(event.target.value)} /></div><div><label htmlFor="leg-arrival">رسیدن برنامه‌ریزی‌شده</label><Input id="leg-arrival" type="datetime-local" value={arrival} onChange={(event) => setArrival(event.target.value)} /></div></div>}
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    <div className="flex flex-wrap gap-2"><Button type="button" disabled={busy} onClick={() => void submit()}>{busy ? "در حال ذخیره…" : "ذخیره بخش مسیر"}</Button><Button type="button" variant="outline" disabled={busy} onClick={close}>انصراف</Button></div>
  </div>;
}

function CheckpointForm({ shipmentId, plan, checkpoint, catalog, searchIran, execute, close, busy }: {
  shipmentId: string; plan: RoutePlanDetail; checkpoint?: RouteCheckpoint; catalog: Catalog; searchIran: (query: string) => void;
  execute: (name: string, action: () => Promise<unknown>) => Promise<boolean>; close: () => void; busy: boolean;
}) {
  const { businessLabel } = useI18n();
  const [sequence, setSequence] = useState(String(checkpoint?.sequence_number ?? plan.checkpoints.length + 1));
  const [kind, setKind] = useState(checkpoint?.checkpoint_type || checkpointTypes[0]);
  const [location, setLocation] = useState<OperationalLocationRef | null>(null);
  const [legId, setLegId] = useState(checkpoint?.route_leg_id ? String(checkpoint.route_leg_id) : "");
  const [arrival, setArrival] = useState(checkpoint?.planned_arrival_at ? toLocalDateTimeInputValue(new Date(checkpoint.planned_arrival_at)) : "");
  const [departure, setDeparture] = useState(checkpoint?.planned_departure_at ? toLocalDateTimeInputValue(new Date(checkpoint.planned_departure_at)) : "");
  const [responsible, setResponsible] = useState(checkpoint?.responsible_party || "");
  const [notes, setNotes] = useState(checkpoint?.notes || "");
  const [error, setError] = useState("");
  const submit = async () => {
    if (checkpoint) {
      if (await execute(`checkpoint-${checkpoint.id}`, () => updateRouteCheckpoint(shipmentId, plan.id, checkpoint.id, { expected_version: checkpoint.version, responsible_party: responsible || null, notes: notes || null }))) close();
      return;
    }
    const number = Number(sequence), start = arrival ? localDateTimeInputToUtc(arrival) : null, end = departure ? localDateTimeInputToUtc(departure) : null;
    if (!Number.isInteger(number) || number < 1 || !location || (!start && !end) || (arrival && !start) || (departure && !end)) { setError("ترتیب، مکان و دست‌کم یک زمان برنامه‌ریزی‌شده معتبر لازم است."); return; }
    if (await execute("checkpoint-create", () => addRouteCheckpoint(shipmentId, plan.id, { sequence_number: number, checkpoint_type: kind, location, route_leg_id: legId ? Number(legId) : null, planned_arrival_at: start, planned_departure_at: end, responsible_party: responsible || null, notes: notes || null }))) close();
  };
  return <div className="space-y-3 rounded border bg-slate-50 p-3">
    <h4 className="font-semibold">{checkpoint ? `ویرایش نقطه کنترل ${checkpoint.sequence_number}` : "افزودن نقطه کنترل"}</h4>
    {checkpoint ? <p className="text-sm text-slate-600">ترتیب، نوع، مکان و زمان‌های نقطه کنترل پس از ثبت در فرمان ویرایش فعلی قابل تغییر نیستند.</p> : <><div className="grid min-w-0 gap-3 md:grid-cols-3"><div><label htmlFor="checkpoint-sequence">ترتیب نقطه کنترل</label><Input id="checkpoint-sequence" type="number" min="1" value={sequence} onChange={(event) => setSequence(event.target.value)} /></div><div><label htmlFor="checkpoint-type">نوع نقطه کنترل</label><select id="checkpoint-type" className={selectClass} value={kind} onChange={(event) => setKind(event.target.value)}>{checkpointTypes.map((item) => <option key={item} value={item}>{checkpointNames[item] || businessLabel(item)}</option>)}</select></div><div><label htmlFor="checkpoint-leg">بخش مسیر مرتبط (اختیاری)</label><select id="checkpoint-leg" className={selectClass} value={legId} onChange={(event) => setLegId(event.target.value)}><option value="">بدون ارتباط مستقیم</option>{plan.legs.map((leg) => <option key={leg.id} value={leg.id}>بخش مسیر {leg.sequence_number}</option>)}</select></div></div><LocationPicker id="checkpoint-location" label="مکان نقطه کنترل" value={location} onChange={setLocation} catalog={catalog} searchIran={searchIran} includeFacilities={false} /><div className="grid min-w-0 gap-3 md:grid-cols-2"><div><label htmlFor="checkpoint-arrival">رسیدن برنامه‌ریزی‌شده</label><Input id="checkpoint-arrival" type="datetime-local" value={arrival} onChange={(event) => setArrival(event.target.value)} /></div><div><label htmlFor="checkpoint-departure">حرکت برنامه‌ریزی‌شده</label><Input id="checkpoint-departure" type="datetime-local" value={departure} onChange={(event) => setDeparture(event.target.value)} /></div></div></>}
    <div className="grid min-w-0 gap-3 md:grid-cols-2"><div><label htmlFor={`checkpoint-responsible-${checkpoint?.id || "new"}`}>مسئول (اختیاری)</label><Input id={`checkpoint-responsible-${checkpoint?.id || "new"}`} value={responsible} onChange={(event) => setResponsible(event.target.value)} /></div><div><label htmlFor={`checkpoint-notes-${checkpoint?.id || "new"}`}>یادداشت (اختیاری)</label><Input id={`checkpoint-notes-${checkpoint?.id || "new"}`} value={notes} onChange={(event) => setNotes(event.target.value)} /></div></div>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    <div className="flex flex-wrap gap-2"><Button type="button" disabled={busy} onClick={() => void submit()}>{busy ? "در حال ذخیره…" : "ذخیره نقطه کنترل"}</Button><Button type="button" variant="outline" disabled={busy} onClick={close}>انصراف</Button></div>
  </div>;
}

export default function RouteAuthoringSection({ shipmentId, draft, hasDraft, reload }: { shipmentId: string; draft?: RoutePlanDetail; hasDraft: boolean; reload: () => Promise<boolean> }) {
  const { businessLabel, transportLabel } = useI18n();
  const draftId = draft?.id;
  const [catalog, setCatalog] = useState<Catalog>({ provinces: [], iran: [], facilities: [], countries: [] });
  const [catalogError, setCatalogError] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState("");
  const [editing, setEditing] = useState("");
  const [validation, setValidation] = useState<RouteValidationResult | null>(null);
  const [needsRefresh, setNeedsRefresh] = useState(false);
  useEffect(() => { setNeedsRefresh(false); }, [draft]);
  useEffect(() => {
    if (!draftId) return;
    Promise.all([fetchProvinces(), searchIranDestinations(), listLogisticsPoints({ active: "true", per_page: 100 }), fetchCountries()])
      .then(([provinces, iran, facilities, countries]) => setCatalog({ provinces, iran: iran.data, facilities: facilities.items.filter((item) => item.is_active), countries }))
      .catch(() => setCatalogError("دریافت مکان‌های مجاز ممکن نشد؛ دوباره صفحه را بارگذاری کنید."));
  }, [draftId]);
  const searchIran = (query: string) => { searchIranDestinations(query).then((response) => setCatalog((current) => ({ ...current, iran: response.data }))).catch(() => setCatalogError("جست‌وجوی مکان ممکن نشد.")); };
  const execute = async (name: string, action: () => Promise<unknown>): Promise<boolean> => {
    if (pending || needsRefresh) return false;
    setPending(name); setError(""); setNotice("");
    try {
      await action();
      setValidation(null);
      if (!(await reload())) {
        setNeedsRefresh(true);
        setError("فرمان ثبت شد اما دریافت وضعیت تازه مسیر ممکن نشد. صفحه را دوباره بارگذاری کنید.");
        return false;
      }
      setNotice("اطلاعات برنامه مسیر به‌روز شد.");
      return true;
    } catch (caught) {
      if (name === "create" || (caught instanceof ApiError && caught.status === 409)) {
        setValidation(null);
        if (!(await reload())) setNeedsRefresh(true);
      }
      setError(commandError(caught));
      return false;
    } finally { setPending(""); }
  };
  const validate = async () => {
    if (!draft || pending || needsRefresh) return;
    setPending("validate"); setError(""); setNotice("");
    try { setValidation((await validateRoutePlan(shipmentId, draft.id)).data); }
    catch (caught) { setError(commandError(caught)); }
    finally { setPending(""); }
  };
  return <Card><CardHeader><CardTitle>برنامه مسیر عملیات</CardTitle></CardHeader><CardContent className="min-w-0 space-y-4">
    {error && <p role="alert" className="rounded bg-red-50 p-3 text-red-700">{error}</p>}
    {notice && <p role="status" className="rounded bg-emerald-50 p-3 text-emerald-800">{notice}</p>}
    {!draft ? hasDraft ? <p role="status">در حال دریافت پیش‌نویس برنامه مسیر…</p> : <><p>هنوز برنامه مسیر فعالی برای این محموله ثبت نشده است. مسیر را به‌صورت پیش‌نویس ایجاد کنید و پس از بررسی فعال کنید.</p><OperationalPermission permission="route_plan.create"><Button disabled={!!pending || needsRefresh} onClick={() => void execute("create", () => createRoutePlan(shipmentId))}>{pending === "create" ? "در حال ایجاد…" : "ایجاد مسیر عملیات"}</Button></OperationalPermission></> : <>
      <p>پیش‌نویس برنامه مسیر · نسخه {draft.revision_number}</p>
      {catalogError && <p role="alert" className="text-red-700">{catalogError}</p>}
      <section className="space-y-2"><h3 className="font-semibold">بخش‌های مسیر</h3>{draft.legs.length ? draft.legs.map((leg) => <div key={leg.id} className="flex min-w-0 flex-col justify-between gap-2 rounded border p-3 sm:flex-row sm:items-center"><span>بخش {leg.sequence_number} · {leg.origin.display_name} → {leg.destination.display_name} · {modeNames[leg.transport_mode] || transportLabel(leg.transport_mode)}</span>{leg.actual_departure || leg.actual_arrival ? <span className="text-sm text-slate-600">دارای رخداد واقعی؛ فقط خواندنی</span> : <OperationalPermission permission="route_leg.manage"><Button variant="outline" disabled={!!pending || needsRefresh} onClick={() => setEditing(`leg-${leg.id}`)}>ویرایش بخش مسیر</Button></OperationalPermission>}</div>) : <p>هنوز بخشی برای مسیر ثبت نشده است.</p>}
        <OperationalPermission permission="route_leg.manage"><Button variant="outline" disabled={!!pending || needsRefresh} onClick={() => setEditing("leg-new")}>افزودن بخش مسیر</Button>{editing.startsWith("leg-") && <LegForm key={editing} shipmentId={shipmentId} plan={draft} leg={draft.legs.find((leg) => editing === `leg-${leg.id}`)} catalog={catalog} searchIran={searchIran} execute={execute} close={() => setEditing("")} busy={!!pending || needsRefresh} />}</OperationalPermission>
      </section>
      <section className="space-y-2"><h3 className="font-semibold">نقاط کنترل</h3>{draft.checkpoints.length ? draft.checkpoints.map((checkpoint) => <div key={checkpoint.id} className="flex min-w-0 flex-col justify-between gap-2 rounded border p-3 sm:flex-row sm:items-center"><span>نقطه کنترل {checkpoint.sequence_number} · {checkpointNames[checkpoint.checkpoint_type] || businessLabel(checkpoint.checkpoint_type)}{checkpoint.route_leg_id ? ` · بخش مرتبط ${draft.legs.find((leg) => leg.id === checkpoint.route_leg_id)?.sequence_number ?? "—"}` : ""}</span>{checkpoint.actual_arrival_at || checkpoint.actual_departure_at ? <span className="text-sm text-slate-600">دارای رخداد واقعی؛ فقط خواندنی</span> : <OperationalPermission permission="checkpoint.report"><Button variant="outline" disabled={!!pending || needsRefresh} onClick={() => setEditing(`checkpoint-${checkpoint.id}`)}>ویرایش نقطه کنترل</Button></OperationalPermission>}</div>) : <p>هنوز نقطه کنترلی ثبت نشده است.</p>}
        <OperationalPermission permission="checkpoint.report"><Button variant="outline" disabled={!!pending || needsRefresh} onClick={() => setEditing("checkpoint-new")}>افزودن نقطه کنترل</Button>{editing.startsWith("checkpoint-") && <CheckpointForm key={editing} shipmentId={shipmentId} plan={draft} checkpoint={draft.checkpoints.find((item) => editing === `checkpoint-${item.id}`)} catalog={catalog} searchIran={searchIran} execute={execute} close={() => setEditing("")} busy={!!pending || needsRefresh} />}</OperationalPermission>
      </section>
      <section className="space-y-2 border-t pt-3"><Button variant="outline" disabled={!!pending || needsRefresh} onClick={() => void validate()}>بررسی و اعتبارسنجی مسیر</Button>{validation && (validation.valid ? <p role="status" className="text-emerald-700">مسیر برای فعال‌سازی معتبر است.</p> : <div role="alert" className="rounded bg-amber-50 p-3 text-amber-900"><p>پیش از فعال‌سازی، موارد زیر را بررسی کنید:</p><ul className="list-inside list-disc">{validation.errors.map((item, index) => <li key={index}>{validationMessage(item.code)}</li>)}</ul></div>)}
        {validation?.valid && <OperationalPermission permission="route_plan.activate"><Button disabled={!!pending || needsRefresh} onClick={() => void execute("activate", () => activateRoutePlan(shipmentId, draft.id, draft.version))}>فعال‌سازی مسیر</Button></OperationalPermission>}
      </section>
    </>}
  </CardContent></Card>;
}
