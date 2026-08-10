import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  listOipAttention,
  listOperationalWorkItems,
  resolveOperationalWorkItem,
  transitionOipSituation,
  type OipProjectionHealth,
  type OipSituation,
  type OperationalWorkItem,
} from "@/lib/api";
import { ProjectionHealthNotice } from "@/components/oip/ProjectionHealthNotice";
import { useI18n } from "@/i18n";

const tone: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-800",
  HIGH: "bg-orange-100 text-orange-800",
  MEDIUM: "bg-amber-100 text-amber-800",
  LOW: "bg-slate-100 text-slate-700",
};

export default function OperationalWorkQueue() {
  const { direction, locale, t } = useI18n();
  const [rows, setRows] = useState<OipSituation[]>([]);
  const [health, setHealth] = useState<OipProjectionHealth>();
  const [legacy, setLegacy] = useState<OperationalWorkItem[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await listOipAttention();
      setRows(response.data);
      setHealth(response.projection_health);
      setLegacy([]);
    } catch {
      try {
        const response = await listOperationalWorkItems();
        setLegacy(response.data);
        setRows([]);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : String(caught));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function acknowledge(row: OipSituation) {
    try {
      await transitionOipSituation(row, "acknowledge");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }
  async function resolveLegacy(row: OperationalWorkItem) {
    try {
      await resolveOperationalWorkItem(row.id, row.version);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 p-4 md:p-8" dir={direction}>
      <div className="mx-auto max-w-6xl space-y-5">
        <header>
          <Link to="/operations/shipments">← {t("operations.shipmentsTitle")}</Link>
          <h1 className="mt-2 text-3xl font-bold">{t("operations.attentionTitle")}</h1>
          <p className="text-slate-600">{t("operations.attentionSubtitle")}</p>
        </header>
        {health && <ProjectionHealthNotice health={health} />}
        {error && (
          <div role="alert" className="rounded bg-red-50 p-3 text-red-700">
            {error}{" "}
            <Button variant="link" onClick={() => void load()}>
              {t("operations.retry")}
            </Button>
          </div>
        )}
        {loading ? (
          <p>{t("operations.attentionLoading")}</p>
        ) : rows.length === 0 && legacy.length === 0 ? (
          <p className="rounded bg-white p-8 text-center">
            {t("operations.attentionEmpty")}
          </p>
        ) : (
          <>
            {rows.map((row) => (
              <Card key={row.public_id}>
                <CardContent className="grid gap-4 p-5 md:grid-cols-[1fr_auto]">
                  <div className="space-y-2">
                    <div className="flex flex-wrap gap-2">
                      <span
                        className={`rounded px-2 py-1 text-xs font-bold ${tone[row.priority]}`}
                      >
                        {row.priority} {t("operations.priority")}
                      </span>
                      <span className="rounded bg-slate-100 px-2 py-1 text-xs">
                        {row.type}
                      </span>
                    </div>
                    <Link
                      className="text-lg font-bold underline"
                      to={`/operations/intelligence/${row.public_id}`}
                    >
                      {row.subject.type}: {row.subject.public_id}
                    </Link>
                    <p>
                      {t("operations.why")}:{" "}
                      {row.priority_explanation.drivers
                        .map((x) => `${x.name} ${x.value ?? t("operations.notSupplied")}`)
                        .join(" · ")}
                    </p>
                    <p>
                      {t("operations.owner")}: {row.owner.state} · {t("operations.since")}{" "}
                      {new Date(row.first_detected_at).toLocaleString(locale)}
                      {row.due_at
                        ? ` · ${t("operations.due")} ${new Date(row.due_at).toLocaleString(locale)}`
                        : ""}
                    </p>
                    <p className="text-xs text-slate-500">
                      {t("operations.policy")} {row.policy.id} {row.policy.version} · {t("operations.calculated")}{" "}
                      {new Date(row.freshness.calculated_at).toLocaleString(
                        locale,
                      )}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {row.status === "OPEN" && (
                      <Button onClick={() => void acknowledge(row)}>
                        {t("operations.acknowledge")}
                      </Button>
                    )}
                    <Link to={`/operations/intelligence/${row.public_id}`}>
                      <Button variant="outline">{t("operations.decisionContext")}</Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}
            {legacy.map((row) => (
              <Card key={`legacy-${row.id}`}>
                <CardContent className="flex items-center justify-between p-5">
                  <div>
                    <Link
                      className="font-bold"
                      to={`/operations/shipments/${row.shipment_public_id}`}
                    >
                      {row.customer}
                    </Link>
                    <p>
                      {row.milestone_type} · {row.reason}
                    </p>
                    <p className="text-xs">
                      {t("operations.legacyWorkItem")}
                    </p>
                  </div>
                  <Button onClick={() => void resolveLegacy(row)}>
                    {t("operations.resolve")}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </>
        )}
      </div>
    </main>
  );
}
