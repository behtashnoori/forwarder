import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, createExecutionCondition, getOperationalContext, listExecutionConditions, listExecutionReasons, resolveExecutionCondition, type ExecutionCondition, type ExecutionReason } from "@/lib/api";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";

type Kind = "delay" | "exception";
const label = (kind: Kind) => kind === "delay" ? "تأخیر" : "استثنا";
const errorText = (error: unknown) => {
  if (!(error instanceof ApiError)) return "انجام این کار ممکن نشد. دوباره تلاش کنید.";
  if (error.status === 403) return "شما مجوز انجام این کار را ندارید.";
  if (error.status === 409) return "اطلاعات تغییر کرده است. موارد را دوباره بررسی کنید.";
  if (error.status === 404) return "محموله یا دلیل مصوب دیگر در دسترس نیست.";
  if (error.status === 422 || error.status === 400) return "دلیل و زمان واردشده را بررسی کنید.";
  return "انجام این کار ممکن نشد. دوباره تلاش کنید.";
};

export default function OperationalConditionsSection({ shipmentPublicId }: { shipmentPublicId: string }) {
  const [rows, setRows] = useState<Record<Kind, ExecutionCondition[]>>({ delay: [], exception: [] });
  const [reasons, setReasons] = useState<Record<Kind, ExecutionReason[]>>({ delay: [], exception: [] });
  const [selected, setSelected] = useState<Record<Kind, string>>({ delay: "", exception: "" });
  const [times, setTimes] = useState<Record<Kind, string>>({ delay: "", exception: "" });
  const [notes, setNotes] = useState<Record<Kind, string>>({ delay: "", exception: "" });
  const [canManage, setCanManage] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const commandKeys = useRef<Record<Kind, string>>({ delay: crypto.randomUUID(), exception: crypto.randomUUID() });
  const load = useCallback(async () => {
    const [delays, exceptions, delayReasons, exceptionReasons] = await Promise.all([
      listExecutionConditions(shipmentPublicId, "delay"), listExecutionConditions(shipmentPublicId, "exception"),
      listExecutionReasons("delay"), listExecutionReasons("exception"),
    ]);
    setRows({ delay: delays.data, exception: exceptions.data });
    setReasons({ delay: delayReasons.data.filter(row => row.is_active), exception: exceptionReasons.data.filter(row => row.is_active) });
  }, [shipmentPublicId]);
  useEffect(() => {
    void load().catch(caught => setError(errorText(caught)));
    void getOperationalContext().then(result => setCanManage(result.data.permissions.includes("operational_execution.manage"))).catch(() => setCanManage(false));
  }, [load]);
  const run = async (action: () => Promise<unknown>) => {
    setBusy(true); setError("");
    try { await action(); await load(); }
    catch (caught) { setError(errorText(caught)); await load().catch(() => undefined); }
    finally { setBusy(false); }
  };
  const changed = (kind: Kind) => { commandKeys.current[kind] = crypto.randomUUID(); setError(""); };
  const create = (kind: Kind) => {
    const value = times[kind];
    const parsed = new Date(value);
    if (!value || Number.isNaN(parsed.getTime())) { setError("زمان وقوع را وارد کنید."); return; }
    const field = kind === "delay" ? "started_at" : "occurred_at";
    void run(async () => {
      await createExecutionCondition(shipmentPublicId, kind, { reason_public_id: selected[kind], [field]: parsed.toISOString(), note: notes[kind] || null, idempotency_key: commandKeys.current[kind] });
      commandKeys.current[kind] = crypto.randomUUID();
      setSelected(previous => ({ ...previous, [kind]: "" }));
      setTimes(previous => ({ ...previous, [kind]: "" }));
      setNotes(previous => ({ ...previous, [kind]: "" }));
    });
  };
  return <section dir="rtl" className="grid gap-6 lg:grid-cols-2" aria-label="تأخیرها و استثناهای عملیاتی">
    {error && <p className="lg:col-span-2 rounded bg-red-50 p-3 text-red-700" role="alert">{error}</p>}
    {(["delay", "exception"] as const).map(kind => <div key={kind} className="min-w-0 space-y-3 rounded-lg border p-4">
      <h2 className="font-semibold">{kind === "delay" ? "تأخیرهای عملیاتی ثبت‌شده" : "استثناهای عملیاتی ثبت‌شده"}</h2>
      {!rows[kind].length && <p>موردی ثبت نشده است.</p>}
      {rows[kind].map(row => <article key={row.public_id} className="rounded border p-3">
        <strong className="break-words">{row.reason.fa_name}</strong>
        <p>{row.active ? "فعال" : "رفع‌شده"} · شروع: {formatDualCalendarInstant(kind === "delay" ? row.started_at : row.occurred_at, "fa-IR", { fallback: "ثبت نشده" })}</p>
        {row.resolved_at && <p>رفع: {formatDualCalendarInstant(row.resolved_at, "fa-IR")}</p>}
        {row.note && <p className="break-words">{row.note}</p>}
        {row.active && canManage && <Button disabled={busy} onClick={() => void run(() => resolveExecutionCondition(shipmentPublicId, kind, row))}>رفع {label(kind)}</Button>}
      </article>)}
      {canManage && <div className="space-y-2">
        <label className="block">دلیل مصوب {label(kind)}<select className="mt-1 min-h-11 w-full rounded border px-2" value={selected[kind]} onChange={event => { changed(kind); setSelected(previous => ({ ...previous, [kind]: event.target.value })); }}><option value="">انتخاب دلیل</option>{reasons[kind].map(reason => <option key={reason.public_id} value={reason.public_id}>{reason.fa_name}</option>)}</select></label>
        <label className="block">زمان وقوع<Input className="mt-1" type="datetime-local" value={times[kind]} onChange={event => { changed(kind); setTimes(previous => ({ ...previous, [kind]: event.target.value })); }} /></label>
        <label className="block">یادداشت اختیاری<Input className="mt-1" value={notes[kind]} onChange={event => { changed(kind); setNotes(previous => ({ ...previous, [kind]: event.target.value })); }} /></label>
        <Button disabled={busy || !selected[kind] || !times[kind]} onClick={() => create(kind)}>ثبت {label(kind)} عملیاتی</Button>
        {!reasons[kind].length && <p role="status">دلیل مصوب فعالی برای ثبت وجود ندارد.</p>}
      </div>}
    </div>)}
  </section>;
}
