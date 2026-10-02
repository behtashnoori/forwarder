import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { request, listShipmentCargoItems } from "@/lib/api";
import { customerRequest } from "@/lib/customerPortalApi";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";

type Estimate = { available: boolean; target: string | null; earliest: string | null; latest: string | null; message: string | null };
export type EtaSnapshot = {
  public_id: string; sequence: number; ruleset: string; calculated_at: string;
  next: Estimate; final: Estimate; as_of: string | null; recorded_at: string | null;
  basis_label: string | null; unquantified_effect: boolean; planned_distance: string | null;
  authorization_revision?: string;
};
type RouteContext = { route_completed: boolean; actual_cargo_known: boolean; coverage_ambiguous: boolean; conflicting_positions?: boolean; legs: Array<{leg_id: number; destination: string; planned_distance_km: string | null; reference_version: number | null}> };
type Current = {snapshot: EtaSnapshot | null; context: RouteContext | null; stale: boolean; authorization_revision?: string};
function KnownRoute({value}: {value: RouteContext}) {
  return <aside className="space-y-2 rounded border bg-blue-50 p-3 text-sm" aria-label="واقعیت مسیر و مبنای انتخاب‌شده">
    {value.route_completed && <p className="font-semibold">رسیدن در مسیر ثبت شده و مسیر تکمیل شده است؛ این وضعیت، برآورد آینده رسیدن کالا نیست.</p>}
    {value.legs.map((leg, index) => <p key={leg.leg_id}>بخش {(index + 1).toLocaleString("fa-IR")} · {leg.destination}: {leg.planned_distance_km == null ? "مبنای فاصله انتخاب نشده" : `مبنای این بخش: ${Number(leg.planned_distance_km).toLocaleString("fa-IR")} کیلومتر · نسخه مرجع ${leg.reference_version}`}</p>)}
    {!value.actual_cargo_known && <p>مقدار واقعی کالا ثبت نشده است؛ مقدار تخصیص جایگزین آن نیست.</p>}
    {value.coverage_ambiguous && <p>پوشش اجرای کل کالا برای برآورد روشن نیست.</p>}
    {value.conflicting_positions && <p>در یک زمان وقوع، موقعیت‌های متفاوت ثبت شده‌اند؛ پیشرفت کالا قابل تعیین نیست.</p>}
  </aside>;
}
type History = { items: EtaSnapshot[]; page: number; has_next: boolean; authorization_revision?: string };
const time = (value: string | null) => formatDualCalendarInstant(value, "fa-IR", { timeStyle: "short" });
function age(value: string, calculatedAt: string) {
  const minutes = Math.floor((Date.parse(calculatedAt) - Date.parse(value)) / 60_000);
  if (!Number.isFinite(minutes) || minutes < 0) return "زمان داده نیازمند بررسی است";
  return `${minutes.toLocaleString("fa-IR")} دقیقه تا زمان محاسبه`;
}

function Range({ title, value }: { title: string; value: Estimate }) {
  return <div className="space-y-1 rounded-lg bg-slate-50 p-3">
    <h4 className="font-semibold">{title}{value.target ? ` · ${value.target}` : ""}</h4>
    {value.available ? <p>بین {time(value.earliest)} تا {time(value.latest)}</p> : <>
      <p>زمان تقریبی رسیدن قابل محاسبه نیست</p><p className="text-sm text-slate-600">{value.message}</p>
    </>}
  </div>;
}

function Result({ value, historical = false }: { value: EtaSnapshot; historical?: boolean }) {
  return <article className="space-y-3 text-sm">
    {historical && <p className="font-semibold">برآورد قبلی {value.sequence.toLocaleString("fa-IR")} · {time(value.calculated_at)}</p>}
    <Range title="نقطه مهم بعدی" value={value.next} />
    <Range title="مقصد نهایی این کالا" value={value.final} />
    {value.as_of && <div className="space-y-1 text-slate-600">
      <p>مبنای برآورد: {value.basis_label} و بازه‌های زمان مرجع سازمان</p>
      <p>زمان داده عملیاتی: {time(value.as_of)}</p>
      <p>زمان ثبت گزارش: {time(value.recorded_at)}</p>
      <p>عمر داده: {age(value.as_of, value.calculated_at)}</p>
    </div>}
    <p className="text-slate-600">فاصله مبنای گزارش پیشرفت: {value.planned_distance == null ? "در این برآورد در دسترس نیست" : `${Number(value.planned_distance).toLocaleString("fa-IR", {maximumFractionDigits:3})} کیلومتر`}</p>
    <p className="text-xs text-slate-600">زمان محاسبه: {time(value.calculated_at)}</p>
    {value.unquantified_effect && <p className="rounded-lg bg-amber-50 p-3 text-amber-900">مدت اثر عملیاتی ثبت‌شده مشخص نیست و به برآورد اضافه نشده است.</p>}
  </article>;
}

/** Viewing/refreshing is read-only. Calculation is a separate explicit command. */
export default function CargoEta({ shipmentId, cargoId, customer = false }: { shipmentId: string; cargoId: string; customer?: boolean }) {
  const path = `${customer ? "/api/customer/shipments" : "/api/operational-shipments"}/${encodeURIComponent(shipmentId)}/cargo/${encodeURIComponent(cargoId)}/eta`;
  const [refresh, setRefresh] = useState(0);
  const command = useRef<string | null>(null);
  const previous = useRef<{path: string; id?: string}>({path});
  const [page, setPage] = useState(0);
  const [state, setState] = useState<{ path: string; current?: EtaSnapshot; context?: RouteContext | null; stale?: boolean; notice?: string; history?: History; loading: boolean; error: string }>({ path, loading: true, error: "" });
  useEffect(() => {
    let alive = true;
    let generation = 0;
    let controller: AbortController | undefined;
    const clear = () => {
      generation += 1; controller?.abort();
      setState({ path, loading: true, error: "" });
    };
    const load = async () => {
      clear();
      if (document.visibilityState === "hidden") return;
      const current = generation;
      controller = new AbortController();
      const read = customer ? customerRequest : request;
      try {
        for (let attempt = 0; attempt < 2; attempt += 1) {
          const materialize = command.current === path;
          command.current = null;
          const computed = materialize ? await read<EtaSnapshot>(`${path}/ensure`, {method: "POST", body: "{}", cache: "no-store", signal: controller.signal}) : undefined;
          const value = await read<Current>(`${path}/current`, {cache: "no-store", signal: controller.signal});
          const history = page ? await read<History>(`${path}/history?page=${page}`, { cache: "no-store", signal: controller.signal }) : undefined;
          if (!alive || current !== generation) return;
          if (customer) {
            const auth = await customerRequest<{ authorization_revision: string }>("/api/customer/shipments/authorization", { cache: "no-store", signal: controller.signal });
            if (!alive || current !== generation) return;
            if (!value.authorization_revision || value.authorization_revision !== auth.authorization_revision || history && history.authorization_revision !== auth.authorization_revision) continue;
          }
          const notice = computed ? (previous.current.path === path && previous.current.id === computed.public_id ? "اطلاعات مؤثر تغییر نکرده؛ همان برآورد ذخیره‌شده بازگردانده شد." : "برآورد محاسبه و ذخیره شد.") : "آخرین نتیجه ذخیره‌شده خوانده شد؛ محاسبه جدید انجام نشد.";
          previous.current = {path, id: value.snapshot?.public_id};
          setState({ path, current: value.snapshot || undefined, context: value.context, stale: value.stale, notice, history, loading: false, error: "" });
          return;
        }
        throw new Error("دسترسی تغییر کرده است؛ دوباره بخوانید.");
      } catch (error) {
        if (alive && current === generation) setState({ path, loading: false, error: error instanceof Error ? error.message : "دریافت برآورد ممکن نشد." });
      }
    };
    const reload = () => { void load(); };
    const visibility = () => { if (document.visibilityState === "hidden") clear(); else reload(); };
    void load();
    window.addEventListener("focus", reload); window.addEventListener("pageshow", reload);
    window.addEventListener("pagehide", clear); document.addEventListener("visibilitychange", visibility);
    return () => {
      alive = false; generation += 1; controller?.abort();
      window.removeEventListener("focus", reload); window.removeEventListener("pageshow", reload);
      window.removeEventListener("pagehide", clear); document.removeEventListener("visibilitychange", visibility);
    };
  }, [path, customer, page, refresh]);
  const active = state.path === path;
  return <section aria-label="زمان تقریبی رسیدن کالا" className="min-w-0 space-y-3 break-words rounded-xl border p-3" dir="rtl">
    <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-bold">زمان تقریبی رسیدن</h3><div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" disabled={state.loading} onClick={() => setRefresh(value => value + 1)}>خواندن آخرین نتیجه</Button><Button size="sm" disabled={state.loading} onClick={() => {command.current = path; setRefresh(value => value + 1);}}>محاسبه و ذخیره برآورد</Button></div></div>
    <p className="text-xs text-slate-600">برآورد عملیاتی است؛ تعهد زمانی یا موقعیت لحظه‌ای نیست.</p>
    <p className="text-xs text-slate-600">زمان رسیدن است؛ مدت عملیات پس از رسیدن به مقصد نهایی در آن حساب نمی‌شود.</p>
    {active && !state.loading && state.context && <KnownRoute value={state.context} />}
    {active && !state.loading && state.notice && <p role="status" className="text-xs text-slate-600">{state.notice}</p>}
    {active && !state.loading && state.stale && <p className="text-sm text-amber-800">نتیجه ذخیره‌شده با مبنای فعلی متفاوت است؛ برای نتیجه تازه «محاسبه و ذخیره برآورد» را انتخاب کنید.</p>}
    {active && !state.loading && !state.error && !state.current && <p>هنوز برآوردی ذخیره نشده است.</p>}
    {!active || state.loading ? <p role="status">در حال دریافت برآورد…</p> : state.error ? <p role="alert">{state.error}</p> : state.current && <div className="space-y-3"><p className="font-semibold">آخرین برآورد ذخیره‌شده</p><Result value={state.current} /></div>}
    <Button size="sm" variant="ghost" onClick={() => setPage(value => value ? 0 : 1)}>{page ? "بستن تاریخچه برآورد" : "برآوردهای قبلی"}</Button>
    {active && !state.loading && state.history && <div className="space-y-4 border-t pt-3">
      {state.history.items.map(value => <Result key={value.public_id} value={value} historical />)}
      {!state.history.items.length && <p>برآورد قبلی ثبت نشده است.</p>}
      <nav aria-label="صفحه‌بندی برآوردها" className="flex flex-wrap gap-2"><Button size="sm" disabled={page <= 1} onClick={() => setPage(value => value - 1)}>صفحه قبل</Button><Button size="sm" disabled={!state.history.has_next} onClick={() => setPage(value => value + 1)}>صفحه بعد</Button></nav>
    </div>}
  </section>;
}

export function ShipmentEta({ shipmentId }: { shipmentId: string }) {
  const [cargo, setCargo] = useState<{ public_id: string; display_name_snapshot: string }[]>([]);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    let alive = true;
    setCargo([]); setSelected(""); setError("");
    void listShipmentCargoItems(shipmentId).then(result => {
      if (alive) { setCargo(result.items); setSelected(result.items[0]?.public_id || ""); }
    }).catch(error => { if (alive) setError(error instanceof Error ? error.message : "دریافت کالاها ممکن نشد."); });
    return () => { alive = false; };
  }, [shipmentId]);
  return <div className="space-y-3 p-3">
    {error ? <p role="alert">{error}</p> : cargo.length ? <>
      <label className="block text-sm font-medium">کالا برای نمایش برآورد<select aria-label="کالا برای نمایش برآورد" className="mt-2 block min-h-11 w-full rounded-md border bg-white p-2" value={selected} onChange={event => setSelected(event.target.value)}>{cargo.map(item => <option key={item.public_id} value={item.public_id}>{item.display_name_snapshot}</option>)}</select></label>
      {selected && <CargoEta shipmentId={shipmentId} cargoId={selected} />}
    </> : <p>کالایی برای نمایش برآورد در دسترس نیست.</p>}
  </div>;
}

export function CargoEtaPanel(props: { shipmentId: string; cargoId: string; customer?: boolean }) {
  const [open, setOpen] = useState(false);
  return <details className="rounded-xl border bg-white" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary className="cursor-pointer p-3 font-semibold">زمان تقریبی رسیدن کالا</summary>
    {open && <CargoEta {...props} />}
  </details>;
}
