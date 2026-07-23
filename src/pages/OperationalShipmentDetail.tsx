import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import OperationalPermission from "@/components/OperationalPermission";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  correctOperationalMilestone,
  getOperationalShipment,
  recordOperationalEvent,
  verifyOperationalMilestone,
  type OperationalShipmentSummary,
} from "@/lib/api";
import { useI18n } from "@/i18n";
export default function OperationalShipmentDetail() {
  const { id } = useParams();
  const { t, direction, locale } = useI18n();
  const [data, setData] = useState<OperationalShipmentSummary>();
  const [error, setError] = useState("");
  const [reasons, setReasons] = useState<Record<number, string>>({});
  const [pending, setPending] = useState(false);
  const load = () =>
    getOperationalShipment(Number(id))
      .then((r) => setData(r.data))
      .catch((e) => setError(e.message));
  useEffect(() => { void load(); }, [id]);
  const run = async (fn: () => Promise<unknown>) => {
    if (pending) return;
    try {
      setPending(true);
      setError("");
      await fn();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPending(false);
    }
  };
  if (!data && !error) return <p className="p-8">{t("operations.loading")}</p>;
  return (
    <main className="min-h-screen bg-slate-50 p-4 md:p-8" dir={direction}>
      <div className="mx-auto max-w-5xl space-y-5">
        <Link to="/operations/shipments">← {t("operations.back")}</Link>
        {error && (
          <div role="alert" className="rounded bg-red-50 p-3 text-red-700">
            {error}
            <Button variant="link" onClick={load}>
              {t("operations.retry")}
            </Button>
          </div>
        )}
        {data && (
          <>
            <header>
              <h1 className="text-2xl font-bold">
                {t("operations.shipmentDetail")} #{data.id}
              </h1>
              <p>
                {data.customer || "—"} · Quote #{data.source.accepted_quote_id}{" "}
                · Request #{data.source.shipment_request_id} · {data.status}
              </p>
            </header>
            <Card>
              <CardHeader>
                <CardTitle>{t("operations.route")}</CardTitle>
              </CardHeader>
              <CardContent>
                <p>
                  {data.route_leg.origin.display_name} →{" "}
                  {data.route_leg.destination.display_name}
                </p>
                <p>{data.route_leg.transport_mode}</p>
              </CardContent>
            </Card>
            <div className="grid gap-4 md:grid-cols-2">
              {data.milestones.map((m) => (
                <Card key={m.id}>
                  <CardHeader>
                    <CardTitle>{m.type}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p>{new Date(m.planned_at).toLocaleString(locale)}</p>
                    <p>
                      {m.verification_state} · v{m.version}
                    </p>
                    <div className="flex gap-2">
                      <OperationalPermission permission="milestone_event.create">
                        <Button
                          disabled={pending}
                          onClick={() =>
                            run(() =>
                              recordOperationalEvent(
                                Number(id),
                                m.id,
                                new Date().toISOString(),
                                crypto.randomUUID(),
                              ),
                            )
                          }
                        >
                          {t("operations.report")}
                        </Button>
                      </OperationalPermission>
                      <OperationalPermission permission="milestone.verify">
                        <Button
                          disabled={pending}
                          variant="outline"
                          onClick={() =>
                            run(() =>
                              verifyOperationalMilestone(
                                Number(id),
                                m.id,
                                m.version,
                              ),
                            )
                          }
                        >
                          {t("operations.verify")}
                        </Button>
                      </OperationalPermission>
                    </div>
                    <OperationalPermission permission="milestone.correct">
                      <label htmlFor={`reason-${m.id}`}>
                        {t("operations.correctionReason")}
                      </label>
                      <Input
                        id={`reason-${m.id}`}
                        value={reasons[m.id] || ""}
                        onChange={(e) =>
                          setReasons({ ...reasons, [m.id]: e.target.value })
                        }
                      />
                      <Button
                        disabled={pending}
                        variant="secondary"
                        onClick={() =>
                          reasons[m.id]?.trim()
                            ? run(() =>
                                correctOperationalMilestone(
                                  Number(id),
                                  m.id,
                                  new Date().toISOString(),
                                  reasons[m.id],
                                  m.version,
                                  crypto.randomUUID(),
                                ),
                              )
                            : setError(t("operations.correctionRequired"))
                        }
                      >
                        {t("operations.correct")}
                      </Button>
                    </OperationalPermission>
                  </CardContent>
                </Card>
              ))}
            </div>
            <Card>
              <CardHeader>
                <CardTitle>{t("operations.eventHistory")}</CardTitle>
              </CardHeader>
              <CardContent>
                {data.recent_events.map((e) => (
                  <div key={e.id}>
                    {e.event_type} ·{" "}
                    {new Date(e.occurred_at).toLocaleString(locale)}{" "}
                    {e.reason && `· ${e.reason}`}
                  </div>
                ))}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>{t("operations.workQueue")}</CardTitle>
              </CardHeader>
              <CardContent>
                {data.open_work_items.map((w) => (
                  <div key={w.id}>
                    #{w.id} · {w.type} · {w.status}
                  </div>
                ))}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Audit</CardTitle>
              </CardHeader>
              <CardContent>
                {data.audit_summary.map((a) => (
                  <div key={a.id}>
                    {a.action} ·{" "}
                    {new Date(a.recorded_at).toLocaleString(locale)}
                  </div>
                ))}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </main>
  );
}
