import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  getOipSituation,
  transitionOipSituation,
  type OipSituationDetail,
} from "@/lib/api";
import { useI18n } from "@/i18n";
import { ProjectionHealthNotice } from "@/components/oip/ProjectionHealthNotice";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";

type DispositionAction = "snooze" | "resolve" | "dismiss";

function localDateTimeValue(date: Date) {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}

export default function OipSituationDetailPage() {
  const { id = "" } = useParams();
  const { direction, locale, businessLabel } = useI18n();
  const [row, setRow] = useState<OipSituationDetail>();
  const [error, setError] = useState("");
  const [pendingAction, setPendingAction] = useState<DispositionAction>();
  const [reason, setReason] = useState("");
  const [snoozeUntil, setSnoozeUntil] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setError("");
      const response = await getOipSituation(id);
      setRow(response.data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  function beginDisposition(action: DispositionAction) {
    setReason("");
    setSnoozeUntil(
      action === "snooze"
        ? localDateTimeValue(new Date(Date.now() + 3600000))
        : "",
    );
    setPendingAction(action);
  }

  function cancelDisposition() {
    setPendingAction(undefined);
    setReason("");
    setSnoozeUntil("");
  }

  async function act(action: string, payload: Record<string, unknown> = {}) {
    if (!row || busy) return;
    try {
      setBusy(true);
      setError("");
      await transitionOipSituation(row, action, payload);
      cancelDisposition();
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  function submitDisposition() {
    if (!pendingAction || !reason.trim()) return;
    if (pendingAction === "snooze") {
      const until = new Date(snoozeUntil);
      if (
        !snoozeUntil ||
        Number.isNaN(until.valueOf()) ||
        until <= new Date()
      ) {
        setError("زمان تعویق باید زمانی معتبر در آینده باشد.");
        return;
      }
      void act("snooze", { reason: reason.trim(), until: until.toISOString() });
      return;
    }
    void act(pendingAction, { reason: reason.trim() });
  }

  if (!row && error)
    return (
      <main role="alert" className="p-8 text-red-700">
        {error}
      </main>
    );
  if (!row) return <main className="p-8">در حال بارگذاری…</main>;
  const canManage = row.decision_context.permissions.can_manage;
  const health = row.projection_health;

  return (
    <main className="min-h-screen bg-slate-50 p-4 md:p-8" dir={direction}>
      <div className="mx-auto max-w-5xl space-y-5">
        <Link to="/operations/work-queue">← بازگشت به صف پیگیری</Link>
        <header>
          <h1 className="text-2xl font-bold">{businessLabel(row.type)}</h1>
          <p>
            موضوع: {businessLabel(row.subject.type)} · وضعیت: {businessLabel(row.status)} ·
            تکرار {row.occurrence_count.toLocaleString("fa-IR")} · نسخه {row.version.toLocaleString("fa-IR")}
          </p>
          <details className="mt-2 text-xs text-slate-500"><summary className="cursor-pointer">شناسه فنی موضوع</summary><bdi>{row.subject.public_id}</bdi></details>
          {row.snoozed_until && (
            <p>
              تعویق تا {formatDualCalendarInstant(row.snoozed_until, locale)}
            </p>
          )}
          {error && (
            <p role="alert" className="mt-3 rounded bg-red-50 p-3 text-red-700">
              {error}
            </p>
          )}
          <div className="mt-3 flex flex-wrap gap-2">
            {row.status === "OPEN" && (
              <Button
                disabled={!canManage || busy}
                onClick={() => void act("acknowledge")}
              >
                ثبت مشاهده
              </Button>
            )}
            <Button
              variant="outline"
              disabled={!canManage || busy}
              onClick={() => void act("claim")}
            >
              پذیرفتن مسئولیت
            </Button>
            <Button
              variant="outline"
              disabled={!canManage || busy}
              onClick={() => void act("start")}
            >
              شروع پیگیری
            </Button>
            <Button
              variant="outline"
              disabled={!canManage || busy}
              onClick={() => beginDisposition("snooze")}
            >
              تعویق
            </Button>
            <Button
              variant="outline"
              disabled={!canManage || busy}
              onClick={() => beginDisposition("resolve")}
            >
              حل‌شده
            </Button>
            <Button
              variant="destructive"
              disabled={!canManage || busy}
              onClick={() => beginDisposition("dismiss")}
            >
              رد مورد
            </Button>
          </div>
        </header>
        <ProjectionHealthNotice health={health} />
        {pendingAction && (
          <Card>
            <CardHeader>
              <CardTitle>
                {pendingAction === "snooze"
                  ? "تعویق مورد"
                  : pendingAction === "resolve" ? "ثبت حل مورد" : "رد مورد"}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <label className="block space-y-1">
                <span className="font-medium">دلیل</span>
                <Input
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  required
                  maxLength={1000}
                  aria-describedby="disposition-help"
                />
              </label>
              {pendingAction === "snooze" && (
                <label className="block space-y-1">
                  <span className="font-medium">تعویق تا</span>
                  <Input
                    type="datetime-local"
                    value={snoozeUntil}
                    min={localDateTimeValue(new Date())}
                    onChange={(event) => setSnoozeUntil(event.target.value)}
                    required
                  />
                </label>
              )}
              <p id="disposition-help" className="text-sm text-slate-600">
                سرور دلیل، زمان، مجوز و نسخه جاری را اعتبارسنجی می‌کند.
              </p>
              <div className="flex gap-2">
                <Button
                  disabled={
                    busy ||
                    !reason.trim() ||
                    (pendingAction === "snooze" && !snoozeUntil)
                  }
                  onClick={submitDisposition}
                >
                  تأیید
                </Button>
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={cancelDisposition}
                >
                  انصراف
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
        <Card>
          <CardHeader>
            <CardTitle>زمینه تصمیم</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p>
              شدت: {businessLabel(row.severity)} · فوریت: {businessLabel(row.urgency)} · اولویت: {businessLabel(row.priority)}
            </p>
            <p>
              موانع فعال: {row.decision_context.active_blockers.map((item) => businessLabel(item)).join("، ") || "موردی ثبت نشده است"}
            </p>
            <p>
              اطلاعات ناقص: {row.decision_context.missing_information.map((item) => businessLabel(item)).join("، ") || "موردی شناسایی نشده است"}
            </p>
            <p>وضعیت عملیاتی: {businessLabel(row.status)}</p>
            <p>
              سلامت تحلیل: {businessLabel(health.health_state)} · نسخه برآورد {health.projection_version.toLocaleString("fa-IR")} · نسخه سیاست {health.policy_version.toLocaleString("fa-IR")}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>پیشنهاد راهنما</CardTitle>
          </CardHeader>
          <CardContent>
            <p>{row.recommendation.suggested_action}</p>
            <details className="mt-2 text-xs text-slate-500"><summary className="cursor-pointer">مرجع فنی اقدام مجاز</summary><bdi>{row.recommendation.allowed_command_reference.method} {row.recommendation.allowed_command_reference.path}</bdi></details>
            <p className="text-xs">هیچ اقدامی خودکار اجرا نمی‌شود.</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>شواهد</CardTitle>
          </CardHeader>
          <CardContent>
            {row.evidence.map((e) => (
              <div className="border-b py-2" key={e.fact_public_id}>
                <b>
                  {businessLabel(e.source_domain)} / {businessLabel(e.source_type)}
                </b>
                <p>
                  منبع ثبت‌شده · نسخه {e.source_version.toLocaleString("fa-IR")} · {businessLabel(e.validity)}
                </p>
                <details className="text-xs text-slate-500"><summary className="cursor-pointer">شناسه‌های فنی شاهد</summary><p><bdi>{e.source_public_id}</bdi> · <bdi>{e.fact_public_id}</bdi> · <bdi>{e.signal_public_id}</bdi></p></details>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>نتیجه و تاریخچه</CardTitle>
          </CardHeader>
          <CardContent>
            {row.timeline.map((e, i) => (
              <p key={`${e.at}-${i}`}>
                {formatDualCalendarInstant(e.at, locale)} · {businessLabel(e.event)} ·{" "}
                {businessLabel(e.from || "not_registered")} → {businessLabel(e.to)}
                {e.reason ? ` · ${e.reason}` : ""}
              </p>
            ))}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
