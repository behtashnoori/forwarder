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

type Draft = {
  name: string;
  duration: string;
  warning: string;
  active: boolean;
};

const emptyDraft = (process: OrganizationSlaProcess): Draft => ({
  name: process.label_fa,
  duration: "",
  warning: "",
  active: true,
});

const ruleDraft = (rule: OrganizationSlaRule): Draft => ({
  name: rule.name,
  duration: String(rule.duration_minutes),
  warning: rule.warning_minutes == null ? "" : String(rule.warning_minutes),
  active: rule.is_active,
});

const errorMessage = (caught: unknown) => {
  if (caught instanceof ApiError && caught.status === 403) return "مدیریت SLA فقط برای ادمین همین سازمان مجاز است.";
  if (caught instanceof ApiError && caught.status === 409) return "این قاعده هم‌زمان تغییر کرده است؛ اطلاعات تازه بارگذاری شد.";
  if (caught instanceof ApiError && caught.status === 422) return "مدت و زمان هشدار را بررسی کنید؛ هشدار باید کمتر از مدت SLA باشد.";
  return "دریافت یا ذخیره قواعد SLA ممکن نشد.";
};

export default function OrganizationSlaRulesTab() {
  const [payload, setPayload] = useState<OrganizationSlaRulesPayload>();
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
      return [process.process_type, rule ? ruleDraft(rule) : emptyDraft(process)];
    })));
  }, []);

  useEffect(() => {
    void load().catch(caught => setError(errorMessage(caught)));
  }, [load]);

  const rules = useMemo(
    () => new Map(payload?.rules.map(rule => [rule.process_type, rule]) || []),
    [payload],
  );

  const change = (processType: string, patch: Partial<Draft>) => {
    setDrafts(current => ({
      ...current,
      [processType]: { ...current[processType], ...patch },
    }));
  };

  const save = async (process: OrganizationSlaProcess) => {
    const draft = drafts[process.process_type];
    const duration = Number(draft?.duration);
    const warning = draft?.warning.trim() ? Number(draft.warning) : null;
    if (!draft?.name.trim() || !Number.isInteger(duration) || duration <= 0 || (warning != null && (!Number.isInteger(warning) || warning <= 0 || warning >= duration))) {
      setError("نام و مدت معتبر وارد کنید؛ هشدار باید عددی مثبت و کمتر از مدت SLA باشد.");
      return;
    }
    setBusy(process.process_type);
    setError("");
    try {
      const current = rules.get(process.process_type);
      const values = {
        name: draft.name.trim(),
        duration_minutes: duration,
        warning_minutes: warning,
        is_active: draft.active,
      };
      if (current) await updateOrganizationSlaRule(current, values);
      else await createOrganizationSlaRule({ process_type: process.process_type, ...values });
      await load();
    } catch (caught) {
      setError(errorMessage(caught));
      await load().catch(() => undefined);
    } finally {
      setBusy("");
    }
  };

  const showHistory = async (rule: OrganizationSlaRule) => {
    setBusy(`history-${rule.public_id}`);
    setError("");
    try {
      const response = await getOrganizationSlaRuleHistory(rule);
      setHistory(current => ({ ...current, [rule.public_id]: response.data }));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy("");
    }
  };

  return <section dir="rtl" className="space-y-4" aria-labelledby="sla-rules-title">
    <Card>
      <CardHeader><CardTitle id="sla-rules-title">قواعد SLA سازمان</CardTitle></CardHeader>
      <CardContent className="space-y-2 text-sm text-slate-700">
        <p>هر قاعده فقط برای رویدادهایی اعمال می‌شود که پس از فعال‌شدن همان نسخه آغاز شوند. تغییر قاعده، تاریخچه تعهدهای قبلی را بازنویسی نمی‌کند.</p>
        <p>زمان‌ها بر حسب دقیقه واقعی و UTC سنجیده می‌شوند. اگر قاعده‌ای ثبت نشده باشد، سیستم صریحاً «SLA تعریف نشده» نشان می‌دهد.</p>
        {error && <p role="alert" className="rounded bg-red-50 p-3 text-red-700">{error}</p>}
      </CardContent>
    </Card>
    {!payload && !error && <p role="status">در حال دریافت قواعد…</p>}
    <div className="grid gap-4 xl:grid-cols-2">
      {payload?.catalog.map(process => {
        const rule = rules.get(process.process_type);
        const draft = drafts[process.process_type] || emptyDraft(process);
        return <Card key={process.process_type}>
          <CardHeader>
            <CardTitle className="text-lg">{process.label_fa}</CardTitle>
            <p className="text-xs text-slate-500">شروع: {process.start_reference} · پایان: {process.completion_reference}</p>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className={`rounded p-2 text-sm ${rule?.is_active ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-700"}`}>
              {rule ? (rule.is_active ? `فعال · نسخه ${rule.version}` : `غیرفعال · نسخه ${rule.version}`) : "SLA تعریف نشده"}
            </p>
            <label className="block text-sm">نام قاعده<input className="mt-1 min-h-11 w-full rounded border px-3" value={draft.name} maxLength={120} onChange={event => change(process.process_type, { name: event.target.value })} /></label>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-sm">مدت پاسخ (دقیقه)<input aria-label={`مدت ${process.label_fa}`} className="mt-1 min-h-11 w-full rounded border px-3" type="number" min={1} value={draft.duration} onChange={event => change(process.process_type, { duration: event.target.value })} /></label>
              <label className="block text-sm">هشدار چند دقیقه پیش از موعد<input aria-label={`هشدار ${process.label_fa}`} className="mt-1 min-h-11 w-full rounded border px-3" type="number" min={1} value={draft.warning} placeholder="اختیاری" onChange={event => change(process.process_type, { warning: event.target.value })} /></label>
            </div>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={draft.active} onChange={event => change(process.process_type, { active: event.target.checked })} />قاعده فعال باشد</label>
            {rule && <p className="text-xs text-slate-500">اثرگذاری نسخه جاری: {formatDualCalendarInstant(rule.effective_from, "fa-IR")}</p>}
            <div className="flex flex-wrap gap-2">
              <Button disabled={!!busy} onClick={() => void save(process)}>{busy === process.process_type ? "در حال ذخیره…" : rule ? "ذخیره نسخه جدید" : "ایجاد قاعده"}</Button>
              {rule && <Button variant="outline" disabled={!!busy} onClick={() => void showHistory(rule)}>نمایش تاریخچه</Button>}
            </div>
            {rule && history[rule.public_id] && <ol className="space-y-1 rounded bg-slate-50 p-3 text-xs">
              {history[rule.public_id].map((event, index) => <li key={`${event.occurred_at}-${index}`}>{event.action === "organization_sla_rule.created" ? "ایجاد" : "تغییر"} · {formatDualCalendarInstant(event.occurred_at, "fa-IR")}</li>)}
            </ol>}
          </CardContent>
        </Card>;
      })}
    </div>
  </section>;
}
