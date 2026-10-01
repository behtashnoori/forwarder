import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import { getShipmentOperationalStages, recordShipmentStageEvent, type ShipmentStagesView } from "@/lib/shipmentStagesApi";

const localNow = () => {
  const date = new Date();
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};

export default function ShipmentOperationalStages({shipmentId}: {shipmentId: string}) {
  const [view, setView] = useState<ShipmentStagesView | null>(null);
  const [occurred, setOccurred] = useState(localNow());
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const command = useRef({signature: "", key: ""});
  const load = useCallback(async () => {
    try { setView((await getShipmentOperationalStages(shipmentId)).data); setError(""); }
    catch { setError("دریافت مراحل عملیاتی ممکن نشد."); }
  }, [shipmentId]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!view || !window.location.hash) return;
    document.getElementById(window.location.hash.slice(1))?.scrollIntoView?.({block: "center"});
  }, [view]);
  const run = async (definition: string, eventType: "STARTED" | "COMPLETED") => {
    if (!view?.configuration) return;
    const payload = {event_type: eventType, occurred_at: new Date(occurred).toISOString(), expected_policy_version_public_id: view.configuration.public_id};
    const signature = JSON.stringify([definition, payload]);
    if (signature !== command.current.signature) command.current = {signature, key: crypto.randomUUID()};
    try { setBusy(definition); setError(""); await recordShipmentStageEvent(shipmentId, definition, payload, command.current.key); setOccurred(localNow()); await load(); }
    catch { setError("ثبت پیشرفت مرحله انجام نشد؛ ترتیب مراحل، زمان رخداد و مجوز کارشناس مسئول را بررسی کنید."); }
    finally { setBusy(""); }
  };
  const actionableIndex = view?.stages.findIndex(stage => stage.status !== "COMPLETED") ?? -1;
  return <section id="shipment-operational-stages" aria-label="مراحل عملیاتی محموله" className="space-y-4 rounded-2xl border bg-white p-4 sm:p-5" dir="rtl">
    <div><p className="text-xs font-semibold text-slate-500">چرخه عملیاتی سازمان</p><h2 className="text-xl font-bold">مراحل عملیاتی محموله</h2><p className="text-sm text-slate-600">این زنجیره به پروژه وابسته نیست. Delivery، تخصیص، موقعیت و ETA هیچ مرحله‌ای را خودکار کامل نمی‌کنند.</p></div>
    {error && <p role="alert" className="text-red-700">{error}</p>}
    {!view && !error && <p role="status">در حال دریافت مراحل…</p>}
    {view && !view.configuration && <p className="rounded bg-amber-50 p-3">مدیر سازمان هنوز پیکربندی فعال مراحل را منتشر نکرده است.</p>}
    {view?.configuration && <>
      <p className="text-sm text-slate-600">نسخه مراحل {view.configuration.version} · {view.pinned ? "برای این محموله تثبیت شده" : "با اولین رخداد برای محموله تثبیت می‌شود"}</p>
      {view.can_record && <label className="block max-w-sm">زمان رخداد (زمان محلی)<Input aria-label="زمان رخداد مرحله" type="datetime-local" value={occurred} onChange={event => setOccurred(event.target.value)}/></label>}
      <ol className="space-y-3">{view.stages.map((stage, index) => <li id={`shipment-operational-stage-${stage.public_id}`} key={stage.public_id} className="scroll-mt-28 rounded-xl border p-3">
        <div className="flex flex-wrap items-center justify-between gap-2"><strong>{stage.sequence}. {stage.display_name_fa}</strong><span>{stage.status === "COMPLETED" ? "کامل‌شده" : stage.status === "STARTED" ? "شروع‌شده" : "شروع‌نشده"} · {stage.required_for_completion ? "الزامی" : "اختیاری"}</span></div>
        {stage.started_at && <p className="text-sm">شروع: {formatDualCalendarInstant(stage.started_at, "fa-IR")}</p>}
        {stage.completed_at && <p className="text-sm">تکمیل: {formatDualCalendarInstant(stage.completed_at, "fa-IR")}</p>}
        {view.can_record && stage.status === "NOT_STARTED" && <Button className="mt-2" disabled={!!busy || !occurred || index !== actionableIndex} onClick={() => void run(stage.public_id, "STARTED")}>شروع مرحله</Button>}
        {view.can_record && stage.status === "STARTED" && <Button className="mt-2" disabled={!!busy || !occurred} onClick={() => void run(stage.public_id, "COMPLETED")}>تکمیل مرحله</Button>}
      </li>)}</ol>
    </>}
  </section>;
}

