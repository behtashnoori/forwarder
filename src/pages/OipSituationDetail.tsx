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

type DispositionAction = "snooze" | "resolve" | "dismiss";

function localDateTimeValue(date: Date) {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}

export default function OipSituationDetailPage() {
  const { id = "" } = useParams();
  const { direction, locale } = useI18n();
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
        setError("Snooze until must be a valid future time.");
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
  if (!row) return <main className="p-8">Loading…</main>;
  const canManage = row.decision_context.permissions.can_manage;
  const health = row.projection_health;

  return (
    <main className="min-h-screen bg-slate-50 p-4 md:p-8" dir={direction}>
      <div className="mx-auto max-w-5xl space-y-5">
        <Link to="/operations/work-queue">← Attention queue</Link>
        <header>
          <h1 className="text-2xl font-bold">{row.type}</h1>
          <p>
            {row.subject.type}: {row.subject.public_id} · {row.status} ·
            occurrence {row.occurrence_count} · version {row.version}
          </p>
          {row.snoozed_until && (
            <p>
              Snoozed until {new Date(row.snoozed_until).toLocaleString(locale)}
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
                Acknowledge
              </Button>
            )}
            <Button
              variant="outline"
              disabled={!canManage || busy}
              onClick={() => void act("claim")}
            >
              Claim
            </Button>
            <Button
              variant="outline"
              disabled={!canManage || busy}
              onClick={() => void act("start")}
            >
              Start progress
            </Button>
            <Button
              variant="outline"
              disabled={!canManage || busy}
              onClick={() => beginDisposition("snooze")}
            >
              Snooze
            </Button>
            <Button
              variant="outline"
              disabled={!canManage || busy}
              onClick={() => beginDisposition("resolve")}
            >
              Resolve
            </Button>
            <Button
              variant="destructive"
              disabled={!canManage || busy}
              onClick={() => beginDisposition("dismiss")}
            >
              Dismiss
            </Button>
          </div>
        </header>
        <ProjectionHealthNotice health={health} />
        {pendingAction && (
          <Card>
            <CardHeader>
              <CardTitle>
                {pendingAction === "snooze"
                  ? "Snooze situation"
                  : `${pendingAction[0].toUpperCase()}${pendingAction.slice(1)} situation`}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <label className="block space-y-1">
                <span className="font-medium">Reason</span>
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
                  <span className="font-medium">Snooze until</span>
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
                The server validates the reason, time, permission, and current
                version.
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
                  Confirm
                </Button>
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={cancelDisposition}
                >
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
        <Card>
          <CardHeader>
            <CardTitle>Decision context</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p>
              Severity {row.severity} · urgency {row.urgency} · priority{" "}
              {row.priority}
            </p>
            <p>
              Active blockers: {row.decision_context.active_blockers.join(", ")}
            </p>
            <p>
              Missing information:{" "}
              {row.decision_context.missing_information.join(", ") ||
                "None identified"}
            </p>
            <p>Operational status: {row.status}</p>
            <p>
              Intelligence health: {health.health_state} · projection {health.projection_version} · policy {health.policy_version}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Recommendation (advisory)</CardTitle>
          </CardHeader>
          <CardContent>
            <p>{row.recommendation.suggested_action}</p>
            <p className="text-sm">
              Authorized target:{" "}
              {row.recommendation.allowed_command_reference.method}{" "}
              {row.recommendation.allowed_command_reference.path}
            </p>
            <p className="text-xs">No automatic execution.</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Evidence</CardTitle>
          </CardHeader>
          <CardContent>
            {row.evidence.map((e) => (
              <div className="border-b py-2" key={e.fact_public_id}>
                <b>
                  {e.source_domain} / {e.source_type}
                </b>
                <p>
                  Source {e.source_public_id} · version {e.source_version} ·{" "}
                  {e.validity}
                </p>
                <p className="text-xs">
                  Fact {e.fact_public_id} · Signal {e.signal_public_id}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Outcome and timeline</CardTitle>
          </CardHeader>
          <CardContent>
            {row.timeline.map((e, i) => (
              <p key={`${e.at}-${i}`}>
                {new Date(e.at).toLocaleString(locale)} · {e.event} ·{" "}
                {e.from || "—"} → {e.to}
                {e.reason ? ` · ${e.reason}` : ""}
              </p>
            ))}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
