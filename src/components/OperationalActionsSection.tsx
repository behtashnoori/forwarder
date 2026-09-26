import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  ApiError,
  createOperationalAction,
  getOperationalActionHistory,
  getOperationalContext,
  listExecutionConditions,
  listOperationalActions,
  recordOperationalActionFollowUp,
  resolveOperationalAction,
  type ExecutionCondition,
  type OperationalAction,
} from "@/lib/api";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";

const message = (caught: unknown) => {
  if (caught instanceof ApiError && caught.status === 403) return "دسترسی لازم برای مشاهده یا تغییر اقدام‌ها وجود ندارد.";
  if (caught instanceof ApiError && caught.status === 409) return "این اقدام هم‌زمان تغییر کرده است؛ اطلاعات تازه شد.";
  if (caught instanceof ApiError && caught.status === 422) return "عنوان، موعد یا نتیجه اقدام را بررسی کنید.";
  return "عملیات اقدام قابل انجام نبود.";
};

export default function OperationalActionsSection({ shipmentPublicId, closed = false }: { shipmentPublicId: string; closed?: boolean }) {
  const [actions, setActions] = useState<OperationalAction[]>([]);
  const [exceptions, setExceptions] = useState<ExecutionCondition[]>([]);
  const [canRead, setCanRead] = useState(false);
  const [canManage, setCanManage] = useState(false);
  const [what, setWhat] = useState("");
  const [expected, setExpected] = useState("");
  const [due, setDue] = useState("");
  const [contextType, setContextType] = useState<"SHIPMENT" | "EXCEPTION" | "PROCESS">("SHIPMENT");
  const [exceptionId, setExceptionId] = useState("");
  const [processType, setProcessType] = useState<"EXCEPTION_RESPONSE" | "ACTION_FOLLOW_UP">("ACTION_FOLLOW_UP");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [results, setResults] = useState<Record<string, string>>({});
  const [history, setHistory] = useState<Record<string, Array<{ action: string; occurred_at: string }>>>({});
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const response = await listOperationalActions(shipmentPublicId);
    setActions(response.data);
    try {
      const conditions = await listExecutionConditions(shipmentPublicId, "exception");
      setExceptions(conditions.data);
    } catch {
      setExceptions([]);
    }
  }, [shipmentPublicId]);

  useEffect(() => {
    void getOperationalContext().then(context => {
      const permissions = context.data.permissions;
      const readable = permissions.includes("work_item.read");
      setCanRead(readable);
      setCanManage(permissions.includes("work_item.manage"));
      if (readable) void load().catch(caught => setError(message(caught)));
    }).catch(() => setCanRead(false));
  }, [load]);

  useEffect(() => {
    if (!canRead) return undefined;
    const refreshExceptions = (event: Event) => {
      const changedShipment = (event as CustomEvent<{ shipmentPublicId?: string }>).detail?.shipmentPublicId;
      if (!changedShipment || changedShipment === shipmentPublicId) {
        void load().catch(caught => setError(message(caught)));
      }
    };
    window.addEventListener("operational-exceptions-changed", refreshExceptions);
    return () => window.removeEventListener("operational-exceptions-changed", refreshExceptions);
  }, [canRead, load, shipmentPublicId]);

  const run = async (key: string, operation: () => Promise<unknown>) => {
    setBusy(key);
    setError("");
    try {
      await operation();
      await load();
    } catch (caught) {
      setError(message(caught));
      await load().catch(() => undefined);
    } finally {
      setBusy("");
    }
  };

  const create = () => {
    const parsed = new Date(due);
    if (!what.trim() || !due || Number.isNaN(parsed.getTime())) {
      setError("عنوان اقدام و موعد معتبر لازم است.");
      return;
    }
    if (contextType === "EXCEPTION" && !exceptionId) {
      setError("استثنای مرتبط را انتخاب کنید.");
      return;
    }
    void run("create", async () => {
      await createOperationalAction(shipmentPublicId, {
        what: what.trim(),
        expected_result: expected.trim() || null,
        due_at: parsed.toISOString(),
        context_type: contextType,
        ...(contextType === "EXCEPTION" ? { exception_public_id: exceptionId } : {}),
        ...(contextType === "PROCESS" ? { process_type: processType } : {}),
      });
      setWhat(""); setExpected(""); setDue(""); setContextType("SHIPMENT"); setExceptionId("");
    });
  };

  const showHistory = async (action: OperationalAction) => {
    setBusy(`history-${action.public_id}`);
    setError("");
    try {
      const response = await getOperationalActionHistory(shipmentPublicId, action);
      setHistory(current => ({ ...current, [action.public_id]: response.data }));
    } catch (caught) {
      setError(message(caught));
    } finally {
      setBusy("");
    }
  };

  if (!canRead) return null;
  return <section dir="rtl" className="space-y-3" aria-labelledby="operational-actions-title">
    <div>
      <h2 id="operational-actions-title" className="text-xl font-bold">اقدام‌ها و پیگیری‌ها</h2>
      <p className="text-sm text-slate-600">اقدام، پیگیری سبک در زمینه همین محموله است؛ مالک داخلی آن همان کارشناس مسئول ثابت محموله می‌ماند.</p>
    </div>
    {error && <p role="alert" className="rounded bg-red-50 p-3 text-red-700">{error}</p>}
    {!actions.length && <p className="rounded border bg-white p-4">هنوز اقدامی برای این محموله ثبت نشده است.</p>}
    <div className="grid gap-3 lg:grid-cols-2">
      {actions.map(action => <article key={action.public_id} className="space-y-2 rounded border bg-white p-4">
        <div className="flex flex-wrap justify-between gap-2"><strong>{action.what}</strong><span className={`rounded-full px-2 py-1 text-xs ${action.status === "open" ? "bg-amber-100 text-amber-900" : "bg-emerald-100 text-emerald-900"}`}>{action.status === "open" ? "باز" : "رفع‌شده"}</span></div>
        {action.expected_result && <p>نتیجه مورد انتظار: {action.expected_result}</p>}
        <p className="text-sm">مسئول داخلی: {action.responsible.display_name || "کارشناس مسئول محموله"} · موعد: {formatDualCalendarInstant(action.due_at, "fa-IR")}</p>
        <p className="text-xs text-slate-500">زمینه: {action.context.type === "SHIPMENT" ? "محموله" : action.context.type === "EXCEPTION" ? "استثنای عملیاتی" : "فرایند تحت قاعده"}</p>
        {action.latest_follow_up && <p className="rounded bg-slate-50 p-2 text-sm">آخرین پیگیری: {action.latest_follow_up}</p>}
        {action.result && <p className="rounded bg-emerald-50 p-2 text-sm">نتیجه نهایی: {action.result}</p>}
        {canManage && action.status === "open" && <div className="space-y-2 border-t pt-3">
          <div className="flex flex-col gap-2 sm:flex-row"><input aria-label={`یادداشت پیگیری ${action.what}`} className="min-h-11 flex-1 rounded border px-3" value={notes[action.public_id] || ""} placeholder="آخرین پیگیری" onChange={event => setNotes(current => ({ ...current, [action.public_id]: event.target.value }))} /><Button variant="outline" disabled={!!busy || !notes[action.public_id]?.trim()} onClick={() => void run(`note-${action.public_id}`, () => recordOperationalActionFollowUp(shipmentPublicId, action, notes[action.public_id]))}>ثبت پیگیری</Button></div>
          <div className="flex flex-col gap-2 sm:flex-row"><input aria-label={`نتیجه اقدام ${action.what}`} className="min-h-11 flex-1 rounded border px-3" value={results[action.public_id] || ""} placeholder="نتیجه نهایی (الزامی)" onChange={event => setResults(current => ({ ...current, [action.public_id]: event.target.value }))} /><Button disabled={!!busy || !results[action.public_id]?.trim()} onClick={() => void run(`resolve-${action.public_id}`, () => resolveOperationalAction(shipmentPublicId, action, results[action.public_id]))}>ثبت نتیجه و بستن</Button></div>
        </div>}
        <Button variant="ghost" disabled={!!busy} onClick={() => void showHistory(action)}>تاریخچه اقدام</Button>
        {history[action.public_id] && <ol className="space-y-1 text-xs text-slate-500">{history[action.public_id].map((event, index) => <li key={`${event.occurred_at}-${index}`}>{event.action.replace("operational_action.", "")} · {formatDualCalendarInstant(event.occurred_at, "fa-IR")}</li>)}</ol>}
      </article>)}
    </div>
    {canManage && !closed && <div className="space-y-3 rounded border bg-white p-4">
      <h3 className="font-semibold">اقدام جدید</h3>
      <label className="block text-sm">چه کاری لازم است؟<input className="mt-1 min-h-11 w-full rounded border px-3" value={what} maxLength={1000} onChange={event => setWhat(event.target.value)} /></label>
      <label className="block text-sm">نتیجه مورد انتظار<input className="mt-1 min-h-11 w-full rounded border px-3" value={expected} maxLength={2000} onChange={event => setExpected(event.target.value)} /></label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm">موعد<input className="mt-1 min-h-11 w-full rounded border px-3" type="datetime-local" value={due} onChange={event => setDue(event.target.value)} /></label>
        <label className="block text-sm">زمینه<select className="mt-1 min-h-11 w-full rounded border px-3" value={contextType} onChange={event => setContextType(event.target.value as typeof contextType)}><option value="SHIPMENT">محموله</option><option value="EXCEPTION">استثنا</option><option value="PROCESS">فرایند</option></select></label>
      </div>
      {contextType === "EXCEPTION" && <label className="block text-sm">استثنای مرتبط<select className="mt-1 min-h-11 w-full rounded border px-3" value={exceptionId} onChange={event => setExceptionId(event.target.value)}><option value="">انتخاب استثنا</option>{exceptions.map(exception => <option key={exception.public_id} value={exception.public_id}>{exception.reason.fa_name} · {exception.active ? "باز" : "رفع‌شده"}</option>)}</select></label>}
      {contextType === "PROCESS" && <label className="block text-sm">فرایند<select className="mt-1 min-h-11 w-full rounded border px-3" value={processType} onChange={event => setProcessType(event.target.value as typeof processType)}><option value="ACTION_FOLLOW_UP">پیگیری اقدام عملیاتی</option><option value="EXCEPTION_RESPONSE">رسیدگی به استثنای عملیاتی</option></select></label>}
      <Button disabled={!!busy} onClick={create}>{busy === "create" ? "در حال ثبت…" : "ثبت اقدام"}</Button>
    </div>}
  </section>;
}
