import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ApiError,
  createOrganizationSlaRule,
  getOrganizationSlaRuleHistory,
  listOrganizationSlaRules,
  updateOrganizationSlaRule,
  type OrganizationSlaProcess,
  type OrganizationSlaRule,
  type OrganizationSlaRulesPayload,
} from "@/lib/api";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";

type Draft = { alias: string; duration: string; warning: string; active: boolean };

const emptyDraft = (): Draft => ({ alias: "", duration: "", warning: "", active: true });
const ruleDraft = (rule: OrganizationSlaRule): Draft => ({
  alias: rule.organization_alias || "",
  duration: String(rule.duration_minutes),
  warning: rule.warning_minutes == null ? "" : String(rule.warning_minutes),
  active: rule.is_active,
});

const errorMessage = (caught: unknown) => {
  if (caught instanceof ApiError && caught.status === 403) return "مدیریت زمان پاسخ فقط برای مدیر همین سازمان مجاز است.";
  if (caught instanceof ApiError && caught.status === 409) return "این تنظیم هم‌زمان تغییر کرده است؛ اطلاعات تازه بارگذاری شد.";
  if (caught instanceof ApiError && caught.status === 422) return "مدت و زمان هشدار را بررسی کنید؛ هشدار باید کمتر از مدت مجاز باشد.";
  return "دریافت یا ذخیره تنظیمات زمان پاسخ ممکن نشد.";
};

export default function OrganizationSlaRulesTab() {
  const [payload, setPayload] = useState<OrganizationSlaRulesPayload>();
  const [selected, setSelected] = useState<OrganizationSlaProcess["process_type"]>("EXCEPTION_RESPONSE");
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [history, setHistory] = useState<Record<string, Array<{ action: string; occurred_at: string }>>>({});
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const response = await listOrganizationSlaRules();
    setPayload(response.data);
    const configured = new Map(response.data.rules.map(rule => [rule.process_type, rule]));
    setDrafts(Object.fromEntries(response.data.catalog.map(process => {
      const rule = configured.get(process.process_type);
      return [process.process_type, rule ? ruleDraft(rule) : emptyDraft()];
    })));
  }, []);

  useEffect(() => { void load().catch(caught => setError(errorMessage(caught))); }, [load]);

  const rules = useMemo(() => new Map(payload?.rules.map(rule => [rule.process_type, rule]) || []), [payload]);
  const process = payload?.catalog.find(item => item.process_type === selected) || payload?.catalog[0];
  const rule = process ? rules.get(process.process_type) : undefined;
  const draft = process ? (drafts[process.process_type] || emptyDraft()) : emptyDraft();

  const change = (patch: Partial<Draft>) => {
    if (!process) return;
    setDrafts(current => ({ ...current, [process.process_type]: { ...draft, ...patch } }));
  };

  const save = async () => {
    if (!process) return;
    const duration = Number(draft.duration);
    const warning = draft.warning.trim() ? Number(draft.warning) : null;
    if (!Number.isInteger(duration) || duration <= 0 || (warning != null && (!Number.isInteger(warning) || warning <= 0 || warning >= duration))) {
      setError("مدت مجاز باید عددی مثبت باشد؛ هشدار نیز باید کمتر از مدت مجاز باشد.");
      return;
    }
    setBusy(process.process_type);
    setError("");
    try {
      const values = {
        organization_alias: draft.alias.trim() || null,
        duration_minutes: duration,
        warning_minutes: warning,
        is_active: draft.active,
      };
      if (rule) await updateOrganizationSlaRule(rule, values);
      else await createOrganizationSlaRule({ process_type: process.process_type, ...values });
      await load();
    } catch (caught) {
      setError(errorMessage(caught));
      await load().catch(() => undefined);
    } finally {
      setBusy("");
    }
  };

  const showHistory = async (current: OrganizationSlaRule) => {
    setBusy(`history-${current.public_id}`);
    setError("");
    try {
      const response = await getOrganizationSlaRuleHistory(current);
      setHistory(value => ({ ...value, [current.public_id]: response.data }));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy("");
    }
  };

  return <section dir="rtl" className="space-y-4" aria-labelledby="sla-rules-title">
    <Card>
      <CardHeader><CardTitle id="sla-rules-title">زمان پاسخ و پیگیری سازمان</CardTitle></CardHeader>
      <CardContent className="space-y-2 text-sm leading-7 text-slate-700">
        <p>فرآیند مورد سنجش را از فهرست تعریف‌شدهٔ سیستم انتخاب کنید و فقط مدت مجاز، هشدار و وضعیت آن را تعیین کنید. نام‌گذاری سازمانی اختیاری است و معنای فرآیند را تغییر نمی‌دهد.</p>
        <p>هر تغییر یک نسخهٔ مؤثر جدید می‌سازد و ارزیابی‌های تاریخی را بازنویسی نمی‌کند.</p>
        {error && <p role="alert" className="rounded bg-red-50 p-3 text-red-700">{error}</p>}
      </CardContent>
    </Card>

    {!payload && !error && <p role="status">در حال دریافت تنظیمات…</p>}
    {payload && <label className="block max-w-xl text-sm font-medium">فرآیند / مرحله مورد سنجش
      <select
        aria-label="فرآیند یا مرحله مورد سنجش"
        className="mt-1 min-h-11 w-full rounded border bg-white px-3"
        value={selected}
        onChange={event => setSelected(event.target.value as OrganizationSlaProcess["process_type"])}
      >
        {payload.catalog.map(item => <option key={item.process_type} value={item.process_type}>{item.label_fa}</option>)}
      </select>
    </label>}

    {process && <Card>
      <CardHeader className="space-y-2">
        <CardTitle className="text-lg">{process.label_fa}</CardTitle>
        <p className="text-sm text-slate-600">{process.domain_context_fa}</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">شروع سنجش</p><p className="mt-1 font-medium">{process.start_label_fa}</p></div>
          <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">پایان سنجش</p><p className="mt-1 font-medium">{process.end_label_fa}</p></div>
        </div>
        <p className={`rounded p-2 text-sm ${rule?.is_active ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-700"}`}>
          {rule ? (rule.is_active ? `فعال · نسخه ${rule.version}` : `غیرفعال · نسخه ${rule.version}`) : "هنوز برای این فرآیند تنظیمی ثبت نشده است"}
        </p>
        <label className="block text-sm">عنوان داخلی سازمان (اختیاری)
          <input className="mt-1 min-h-11 w-full rounded border px-3" value={draft.alias} maxLength={120} onChange={event => change({ alias: event.target.value })} />
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">مدت مجاز (دقیقه)<input aria-label={`مدت ${process.label_fa}`} className="mt-1 min-h-11 w-full rounded border px-3" type="number" min={1} value={draft.duration} onChange={event => change({ duration: event.target.value })} /></label>
          <label className="block text-sm">هشدار چند دقیقه پیش از موعد<input aria-label={`هشدار ${process.label_fa}`} className="mt-1 min-h-11 w-full rounded border px-3" type="number" min={1} value={draft.warning} placeholder="اختیاری" onChange={event => change({ warning: event.target.value })} /></label>
        </div>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={draft.active} onChange={event => change({ active: event.target.checked })} />این تنظیم فعال باشد</label>
        {rule && <p className="text-xs text-slate-500">اثرگذاری نسخهٔ جاری: {formatDualCalendarInstant(rule.effective_from, "fa-IR")}</p>}
        <div className="flex flex-wrap gap-2">
          <Button disabled={!!busy} onClick={() => void save()}>{busy === process.process_type ? "در حال ذخیره…" : rule ? "ذخیره نسخهٔ جدید" : "ثبت تنظیم"}</Button>
          {rule && <Button variant="outline" disabled={!!busy} onClick={() => void showHistory(rule)}>نمایش تاریخچه</Button>}
        </div>
        {rule && history[rule.public_id] && <ol className="space-y-1 rounded bg-slate-50 p-3 text-xs">
          {history[rule.public_id].map((event, index) => <li key={`${event.occurred_at}-${index}`}>{event.action === "organization_sla_rule.created" ? "ایجاد" : "تغییر"} · {formatDualCalendarInstant(event.occurred_at, "fa-IR")}</li>)}
        </ol>}
      </CardContent>
    </Card>}
  </section>;
}
