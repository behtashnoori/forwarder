import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import { formatQuantity } from "@/lib/formatQuantity";
import {
  ApiError, getCargoAllocationTrace, listRouteStageTransportExecutions,
  listShipmentCargoItems, setStageCargoAllocation, transferCargoAllocation,
  type CargoAllocationTrace, type StageCargoAllocation,
} from "@/lib/api";

type Dimension = "PLANNED" | "ACTUAL";
type AllocationDraft = { stageId: string; dimension: Dimension; quantity: string; reason: string };
type TransferDraft = { sourceId: string; targetId: string; quantity: string; context: string; reason: string };
const emptyAllocation = (): AllocationDraft => ({ stageId: "", dimension: "PLANNED", quantity: "", reason: "" });
const emptyTransfer = (): TransferDraft => ({ sourceId: "", targetId: "", quantity: "", context: "", reason: "" });
const time = (value: string) => formatDualCalendarInstant(value, "fa-IR");

function warningText(code: string, difference: string, uom: string) {
  const amount = `${formatQuantity(difference.replace("-", ""))} ${uom}`;
  if (code === "PLAN_UNDER") return `${amount} در برنامه این بخش هنوز تخصیص ندارد.`;
  if (code === "PLAN_OVER") return `${amount} بالاتر از مقدار برنامه‌ریزی‌شده تخصیص داده شده است.`;
  if (code === "ACTUAL_VS_PLAN" || code === "ACTUAL_VS_CARGO_PLAN") return difference.startsWith("-") ? `مقدار واقعی این بخش ${amount} کمتر از برنامه است.` : `مقدار واقعی این بخش ${amount} بیشتر از برنامه است.`;
  if (code === "ACTUAL_VS_KNOWN") return difference.startsWith("-") ? `این بخش ${amount} کمتر از مقدار واقعی شناخته‌شده کالا ثبت کرده است.` : `این بخش ${amount} بیشتر از مقدار واقعی شناخته‌شده کالا ثبت کرده است.`;
  return difference.startsWith("-") ? `${amount} از بخش قبل هنوز در این بخش ثبت نشده است.` : `${amount} بیشتر از بخش قبل در این بخش ثبت شده است.`;
}

function messageFor(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 403) return "فقط کارشناس مسئول این محموله می‌تواند تخصیص یا انتقال را ثبت کند.";
    if (error.status === 404) return "کالا یا اجرای حمل در این محموله پیدا نشد.";
    if (error.status === 409) return "اطلاعات تغییر کرده است؛ تازه‌سازی کنید و دوباره بررسی کنید.";
    if (error.status === 422 || error.status === 400) return "مقدار، واحد و بخش‌های مسیر را بررسی کنید.";
  }
  return "دریافت یا ذخیره تخصیص کالا ممکن نشد.";
}

export default function CargoAllocationTraceSection({ shipmentId, planId }: { shipmentId: string; planId: number }) {
  const [cargoIds, setCargoIds] = useState<string[]>([]);
  const [traces, setTraces] = useState<Record<string, CargoAllocationTrace>>({});
  const [selectedCargo, setSelectedCargo] = useState("");
  const [canManage, setCanManage] = useState(false);
  const [allocation, setAllocation] = useState<AllocationDraft>(emptyAllocation);
  const [transfer, setTransfer] = useState<TransferDraft>(emptyTransfer);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  const retry = useRef<{ signature: string; key: string } | null>(null);

  const load = useCallback(async () => {
    try {
      setError("");
      const [cargo, stages] = await Promise.all([listShipmentCargoItems(shipmentId), listRouteStageTransportExecutions(shipmentId, planId)]);
      const ids = cargo.items.map((item) => item.public_id);
      const all = await Promise.all(ids.map((id) => getCargoAllocationTrace(shipmentId, id)));
      setCargoIds(ids);
      setTraces(Object.fromEntries(ids.map((id, index) => [id, all[index].trace])));
      setSelectedCargo((previous) => ids.includes(previous) ? previous : ids[0] || "");
      setCanManage(stages.data.can_manage);
    } catch (caught) { setError(messageFor(caught)); }
  }, [shipmentId, planId]);
  useEffect(() => { void load(); }, [load]);

  const trace = traces[selectedCargo];
  const currentStages = useMemo(() => trace?.stages.filter((stage) => stage.route_plan_id === planId).flatMap((stage) => stage.executions.map((execution) => ({ ...execution, sequence: stage.sequence_number }))) || [], [trace, planId]);
  const current = currentStages.find((execution) => execution.stage_execution_public_id === allocation.stageId)?.allocations.find((row) => row.dimension === allocation.dimension);
  const actual = (stageId: string): StageCargoAllocation | undefined => currentStages.find((execution) => execution.stage_execution_public_id === stageId)?.allocations.find((row) => row.dimension === "ACTUAL");
  const usableSource = currentStages.filter((execution) => Number(actual(execution.stage_execution_public_id)?.quantity || 0) > 0);
  const stableKey = (signature: string) => {
    if (retry.current?.signature === signature) return retry.current.key;
    const key = crypto.randomUUID();
    retry.current = { signature, key };
    return key;
  };
  const save = async (quantity = allocation.quantity) => {
    if (!selectedCargo || !allocation.stageId || !quantity || Number(quantity) < 0) { setError("بخش مسیر و مقدار را انتخاب کنید."); return; }
    const payload = { dimension: allocation.dimension, quantity, expected_version: current?.version || 0, ...(allocation.reason.trim() ? { reason: allocation.reason.trim() } : {}) };
    const signature = JSON.stringify({ selectedCargo, stageId: allocation.stageId, payload });
    try {
      setPending(true); setError(""); setNotice("");
      await setStageCargoAllocation(shipmentId, selectedCargo, allocation.stageId, payload, stableKey(signature));
      retry.current = null;
      setNotice(quantity === "0" ? "تخصیص جاری پایان یافت و سابقه آن حفظ شد." : "تخصیص ثبت شد؛ اختلاف‌ها فقط هشدار هستند.");
      setAllocation(emptyAllocation());
      await load();
    } catch (caught) { setError(messageFor(caught)); await load(); }
    finally { setPending(false); }
  };
  const move = async () => {
    if (!selectedCargo || !transfer.sourceId || !transfer.targetId || Number(transfer.quantity) <= 0) { setError("مبدأ، مقصد و مقدار انتقال را بررسی کنید."); return; }
    const payload = {
      source_stage_execution_public_id: transfer.sourceId,
      target_stage_execution_public_id: transfer.targetId,
      quantity: transfer.quantity,
      expected_source_version: actual(transfer.sourceId)?.version || 0,
      expected_target_version: actual(transfer.targetId)?.version || 0,
      ...(transfer.context.trim() ? { context: transfer.context.trim() } : {}),
      ...(transfer.reason.trim() ? { reason: transfer.reason.trim() } : {}),
    };
    const signature = JSON.stringify({ selectedCargo, payload });
    try {
      setPending(true); setError(""); setNotice("");
      await transferCargoAllocation(shipmentId, selectedCargo, payload, stableKey(signature));
      retry.current = null;
      setNotice("انتقال ثبت شد؛ مبدأ، مقصد و سابقه با هم به‌روز شدند.");
      setTransfer(emptyTransfer());
      await load();
    } catch (caught) { setError(messageFor(caught)); await load(); }
    finally { setPending(false); }
  };

  return <Card className="border-slate-200 shadow-sm" dir="rtl">
    <CardHeader><CardTitle>تخصیص و مسیر هر کالا</CardTitle><p className="text-sm text-slate-600">برنامه و مقدار واقعی هر بخش جدا ثبت می‌شوند. اختلاف‌ها مانع ثبت واقعیت نیستند.</p></CardHeader>
    <CardContent className="space-y-4">
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-700">{error} <Button variant="link" onClick={() => void load()}>تلاش دوباره</Button></p>}
      {notice && <p role="status" className="rounded-lg bg-emerald-50 p-3 text-emerald-800">{notice}</p>}
      <div className="flex flex-wrap items-end gap-2"><label className="grid gap-1 text-sm">کالا<select aria-label="کالا برای ردگیری" className="min-h-10 rounded border px-2" value={selectedCargo} onChange={(event) => { setSelectedCargo(event.target.value); setAllocation(emptyAllocation()); setTransfer(emptyTransfer()); }}><option value="">انتخاب کالا</option>{cargoIds.map((id) => <option key={id} value={id}>{traces[id]?.cargo.name || id}</option>)}</select></label><Button variant="outline" onClick={() => void load()}>تازه‌سازی</Button></div>
      {!trace && <p className="text-sm text-slate-600">{cargoIds.length ? "کالا را انتخاب کنید." : "هنوز کالایی برای این محموله ثبت نشده است."}</p>}
      {trace && <>
        <div className="grid gap-2 rounded-lg bg-slate-50 p-3 text-sm sm:grid-cols-3"><p>درخواستی: <strong>{trace.cargo.requested_quantity ? formatQuantity(trace.cargo.requested_quantity) : "نامشخص"}</strong></p><p>برنامه کل کالا: <strong>{trace.cargo.planned_quantity ? formatQuantity(trace.cargo.planned_quantity) : "نامشخص"}</strong></p><p>مقدار واقعی شناخته‌شده: <strong>{trace.cargo.actual_quantity ? formatQuantity(trace.cargo.actual_quantity) : "نامشخص"}</strong> {trace.cargo.uom}</p></div>
        {trace.legacy_allocations.length > 0 && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">{trace.legacy_allocations.length} تخصیص قدیمی بدون بخش مسیر و بدون معنای برنامه/واقعی موجود است. سابقه‌ای برای پیش از این ثبت ساخته نشده است.</p>}
        {trace.stages.length === 0 && <p className="text-sm text-slate-600">هنوز اجرای حملی در مسیر این کالا ثبت نشده است.</p>}
        <ol className="space-y-3">{trace.stages.map((stage) => <li key={`${stage.route_plan_id}-${stage.route_leg_id}`} className="rounded-xl border p-3 text-sm"><h3 className="font-semibold">بخش مسیر {stage.sequence_number}</h3><p className="text-slate-600">{stage.origin.display_name || "مبدأ نامشخص"} ← {stage.destination.display_name || "مقصد نامشخص"}</p><div className="mt-2 grid gap-2 rounded bg-slate-50 p-2 sm:grid-cols-2"><p>جمع برنامه: <strong>{stage.planned_recorded ? formatQuantity(stage.planned_total) : "ثبت نشده"}</strong> {trace.cargo.uom}</p><p>جمع واقعی: <strong>{stage.actual_recorded ? formatQuantity(stage.actual_total) : "ثبت نشده"}</strong> {trace.cargo.uom}</p><p>مانده نسبت به برنامه کل کالا: <strong>{stage.planned_remaining === null ? "نامشخص" : formatQuantity(stage.planned_remaining)}</strong> {trace.cargo.uom}</p><p>ثبت‌نشده نسبت به مقدار واقعی شناخته‌شده: <strong>{stage.actual_unrecorded === null ? "نامشخص" : formatQuantity(stage.actual_unrecorded)}</strong> {trace.cargo.uom}</p></div>{stage.warnings.map((warning, index) => <p key={`${warning.code}-${index}`} role="status" className="mt-2 rounded bg-amber-50 p-2 text-amber-900">⚠ {warningText(warning.code, warning.difference, trace.cargo.uom)}</p>)}<div className="mt-2 grid gap-2 md:grid-cols-2">{stage.executions.map((execution) => <article key={execution.stage_execution_public_id} className="rounded border p-2"><strong>{execution.means || "وسیله حمل"} {execution.means_identifier || execution.unit_code}</strong>{execution.equipment.length > 0 && <p className="text-slate-600">{execution.equipment.map((item) => `${item.type}${item.identifier ? ` ${item.identifier}` : ""}`).join(" ← ")}</p>}<p>برنامه: {formatQuantity(execution.allocations.find((row) => row.dimension === "PLANNED")?.quantity || "0")} {trace.cargo.uom}</p><p>واقعی: {formatQuantity(execution.allocations.find((row) => row.dimension === "ACTUAL")?.quantity || "0")} {trace.cargo.uom}</p></article>)}</div></li>)}</ol>
        {canManage && currentStages.length > 0 && <div className="grid gap-3 lg:grid-cols-2"><section className="rounded-lg border p-3 text-sm"><h3 className="font-semibold">ثبت یا اصلاح تخصیص</h3><div className="mt-2 grid gap-2"><select aria-label="اجرای حمل برای تخصیص" className="min-h-10 rounded border px-2" value={allocation.stageId} onChange={(event) => setAllocation({ ...allocation, stageId: event.target.value, quantity: "" })}><option value="">انتخاب اجرای حمل</option>{currentStages.map((stage) => <option key={stage.stage_execution_public_id} value={stage.stage_execution_public_id}>بخش {stage.sequence} · {stage.means_identifier || stage.unit_code}</option>)}</select><select aria-label="نوع تخصیص" className="min-h-10 rounded border px-2" value={allocation.dimension} onChange={(event) => setAllocation({ ...allocation, dimension: event.target.value as Dimension, quantity: "" })}><option value="PLANNED">برنامه</option><option value="ACTUAL">واقعی</option></select>{current && <p>مقدار جاری: {formatQuantity(current.quantity)} {trace.cargo.uom} · نسخه {current.version}</p>}<Input aria-label="مقدار تخصیص مرحله" type="number" min="0.000001" step="any" value={allocation.quantity} onChange={(event) => setAllocation({ ...allocation, quantity: event.target.value })} placeholder="مقدار تازه" /><Input aria-label="دلیل اصلاح تخصیص" value={allocation.reason} onChange={(event) => setAllocation({ ...allocation, reason: event.target.value })} placeholder="دلیل، در صورت وجود" /><div className="flex gap-2"><Button disabled={pending || !allocation.stageId || !allocation.quantity} onClick={() => void save()}>ذخیره تخصیص</Button>{current && <Button variant="outline" disabled={pending} onClick={() => void save("0")}>پایان تخصیص جاری</Button>}</div></div></section>
        <section className="rounded-lg border p-3 text-sm"><h3 className="font-semibold">انتقال کالا</h3><div className="mt-2 grid gap-2"><select aria-label="اجرای مبدأ انتقال" className="min-h-10 rounded border px-2" value={transfer.sourceId} onChange={(event) => setTransfer({ ...transfer, sourceId: event.target.value })}><option value="">اجرای مبدأ</option>{usableSource.map((stage) => <option key={stage.stage_execution_public_id} value={stage.stage_execution_public_id}>بخش {stage.sequence} · {stage.means_identifier || stage.unit_code}</option>)}</select><select aria-label="اجرای مقصد انتقال" className="min-h-10 rounded border px-2" value={transfer.targetId} onChange={(event) => setTransfer({ ...transfer, targetId: event.target.value })}><option value="">اجرای مقصد</option>{currentStages.filter((stage) => stage.stage_execution_public_id !== transfer.sourceId).map((stage) => <option key={stage.stage_execution_public_id} value={stage.stage_execution_public_id}>بخش {stage.sequence} · {stage.means_identifier || stage.unit_code}</option>)}</select><Input aria-label="مقدار انتقال" type="number" min="0.000001" step="any" value={transfer.quantity} onChange={(event) => setTransfer({ ...transfer, quantity: event.target.value })} placeholder="مقدار انتقال" /><Input aria-label="محل یا زمینه انتقال" value={transfer.context} onChange={(event) => setTransfer({ ...transfer, context: event.target.value })} placeholder="محل یا زمینه، در صورت وجود" /><Input aria-label="دلیل انتقال" value={transfer.reason} onChange={(event) => setTransfer({ ...transfer, reason: event.target.value })} placeholder="دلیل، در صورت وجود" /><Button disabled={pending || !transfer.sourceId || !transfer.targetId || !transfer.quantity} onClick={() => void move()}>ثبت انتقال کالا</Button></div></section></div>}
        <details className="rounded border p-3 text-sm"><summary className="cursor-pointer font-semibold">تاریخچه تخصیص و انتقال</summary>{trace.history.length === 0 ? <p className="mt-2 text-slate-600">هنوز تغییری ثبت نشده است.</p> : <ol className="mt-2 space-y-2">{trace.history.map((item) => <li key={item.public_id} className="rounded bg-slate-50 p-2"><strong>{item.action === "PLAN_REVISION" ? "اصلاح برنامه" : item.action === "ACTUAL_CORRECTION" ? "اصلاح مقدار واقعی" : item.action.includes("TRANSFER") || item.action.includes("HANDOFF") ? "انتقال کالا" : item.action === "RELEASE" ? "پایان تخصیص" : "ثبت تخصیص"}</strong> · {formatQuantity(item.before)} ← {formatQuantity(item.after)} {trace.cargo.uom}<p>{item.actor_name} · ثبت: {time(item.recorded_at)} · رخداد: {time(item.occurred_at)}</p>{item.reason && <p>دلیل: {item.reason}</p>}</li>)}</ol>}</details>
      </>}
    </CardContent>
  </Card>;
}
