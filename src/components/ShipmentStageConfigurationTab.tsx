import LocalizedDateTimeInput from "@/components/LocalizedDateTimeInput";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import { localDateTimeInputToUtc } from "@/lib/localDateTime";
import {
  getShipmentStageConfiguration,
  saveShipmentStageConfiguration,
  type ShipmentStageConfiguration,
  type ShipmentStageDraft,
} from "@/lib/shipmentStagesApi";

const localInput = (date: Date) => new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);

export default function ShipmentStageConfigurationTab() {
  const [data, setData] = useState<ShipmentStageConfiguration | null>(null);
  const [draft, setDraft] = useState<ShipmentStageDraft[]>([]);
  const [effective, setEffective] = useState("");
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const command = useRef({signature: "", key: ""});
  const load = useCallback(async () => {
    try { setData((await getShipmentStageConfiguration()).data); setError(""); }
    catch { setError("دریافت پیکربندی مراحل ممکن نشد؛ مجوز مدیر سازمان را بررسی کنید."); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  const begin = () => {
    if (!data) return;
    const source = data.versions[0]?.stages || data.canonical_stages.map((stage, index) => ({
      public_id: "", configuration_public_id: "", ...stage, sequence: index + 1, active: true, required_for_completion: true,
    }));
    setDraft(source.map(stage => ({code: stage.code, display_name_fa: stage.display_name_fa, sequence: stage.sequence,
      active: stage.active, required_for_completion: stage.required_for_completion})));
    const offset = data.versions.length ? 5 * 60 * 1000 : 0;
    setEffective(localInput(new Date(Date.now() + offset))); setEditing(true); setError("");
  };
  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= draft.length) return;
    const next = [...draft]; [next[index], next[target]] = [next[target], next[index]];
    setDraft(next.map((stage, position) => ({...stage, sequence: position + 1})));
  };
  const save = async () => {
    const at = localDateTimeInputToUtc(effective);
    if (!data || !at) { setError("زمان شروع اعتبار معتبر نیست."); return; }
    const payload = {expected_version: data.versions[0]?.version || 0, effective_from: at, stages: draft};
    const signature = JSON.stringify(payload);
    if (signature !== command.current.signature) command.current = {signature, key: crypto.randomUUID()};
    try { setBusy(true); setError(""); await saveShipmentStageConfiguration(payload, command.current.key); setEditing(false); await load(); }
    catch { setError("ثبت پیکربندی انجام نشد؛ ترتیب، فعال‌بودن و زمان اعتبار را بررسی کنید."); }
    finally { setBusy(false); }
  };
  return <section aria-label="پیکربندی مراحل عملیاتی محموله" className="space-y-4 rounded-2xl border bg-white p-4 sm:p-6" dir="rtl">
    <h2 className="text-xl font-bold">مراحل عملیاتی محموله</h2>
    <p className="text-sm text-slate-600">این مراحل متعلق به سازمان‌اند و برای محموله‌های بدون پروژه نیز کار می‌کنند. تعریف‌های پروژه و Delivery مستقل می‌مانند.</p>
    {error && <p role="alert" className="text-red-700">{error}</p>}
    {!data ? <Button variant="outline" onClick={() => void load()}>دریافت مراحل</Button> : <>
      {!data.versions.length && <p className="rounded bg-amber-50 p-3">هنوز نسخه فعالی برای مراحل محموله تعریف نشده است.</p>}
      {!editing && <Button onClick={begin}>تعریف نسخه تازه مراحل</Button>}
      {editing && <div className="space-y-3 rounded-xl border p-4">
        <label className="block">شروع اعتبار (زمان محلی)<LocalizedDateTimeInput type="datetime-local" value={effective} onChange={event => setEffective(event.target.value)} /></label>
        {draft.map((stage, index) => <article key={stage.code} className="grid gap-3 rounded-xl bg-slate-50 p-3 md:grid-cols-[1fr_auto_auto]">
          <label>نام فارسی<Input value={stage.display_name_fa} maxLength={160} onChange={event => setDraft(old => old.map((row, position) => position === index ? {...row, display_name_fa: event.target.value} : row))}/><small dir="ltr">{stage.code}</small></label>
          <div className="space-y-2"><label className="flex gap-2"><input type="checkbox" checked={stage.active} onChange={event => setDraft(old => old.map((row, position) => position === index ? {...row, active: event.target.checked, required_for_completion: event.target.checked ? row.required_for_completion : false} : row))}/>فعال</label><label className="flex gap-2"><input type="checkbox" disabled={!stage.active} checked={stage.required_for_completion} onChange={event => setDraft(old => old.map((row, position) => position === index ? {...row, required_for_completion: event.target.checked} : row))}/>الزامی برای تکمیل</label></div>
          <div className="flex gap-2"><Button type="button" variant="outline" disabled={index === 0} onClick={() => move(index, -1)}>↑</Button><Button type="button" variant="outline" disabled={index === draft.length - 1} onClick={() => move(index, 1)}>↓</Button></div>
        </article>)}
        <div className="flex gap-2"><Button disabled={busy} onClick={() => void save()}>انتشار نسخه مراحل</Button><Button variant="outline" disabled={busy} onClick={() => setEditing(false)}>انصراف</Button></div>
      </div>}
      {data.versions.map(version => <details key={version.public_id} className="rounded-xl border p-4"><summary className="cursor-pointer font-semibold">نسخه {version.version} · از {formatDualCalendarInstant(version.effective_from, "fa-IR")}</summary><ol className="mt-3 space-y-2">{version.stages.map(stage => <li key={stage.public_id}>{stage.sequence}. {stage.display_name_fa} · {stage.active ? "فعال" : "غیرفعال"} · {stage.required_for_completion ? "الزامی" : "اختیاری"}</li>)}</ol></details>)}
    </>}
  </section>;
}

