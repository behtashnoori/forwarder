import { useEffect, useMemo, useState } from "react";
import { getReleaseIdentity, type ReleaseIdentityResponse } from "@/lib/api";
import { env } from "@/lib/env";
import { useI18n } from "@/i18n";

export type IdentityState = "MATCH" | "MISMATCH" | "BACKEND_UNAVAILABLE" | "IDENTITY_UNAVAILABLE";

export const compareReleaseIdentity = (frontend: string, response?: ReleaseIdentityResponse, unavailable = false): IdentityState => {
  if (unavailable) return "BACKEND_UNAVAILABLE";
  const backend = response?.data.backend_version || response?.data.application_version;
  if (!backend) return "IDENTITY_UNAVAILABLE";
  return backend === frontend ? "MATCH" : "MISMATCH";
};

export default function ReleaseIdentity({ details = false }: { details?: boolean }) {
  const { t } = useI18n();
  const frontend = env.APP_VERSION || "unknown";
  const [response, setResponse] = useState<ReleaseIdentityResponse>();
  const [unavailable, setUnavailable] = useState(false);
  useEffect(() => {
    let active = true;
    getReleaseIdentity().then(value => active && setResponse(value)).catch(() => active && setUnavailable(true));
    return () => { active = false; };
  }, []);
  const state = useMemo(() => compareReleaseIdentity(frontend, response, unavailable), [frontend, response, unavailable]);
  const unavailableLabel = t("operations.unavailable");
  return <section aria-label={t("operations.systemInformation")} className="min-w-0 text-xs text-slate-500" data-identity-state={state}>
    <p className="font-medium text-slate-600" dir="ltr">Forwarder {frontend}</p>
    {details && <dl className="mt-2 grid gap-x-4 gap-y-1 sm:grid-cols-2">
      <div><dt>{t("operations.frontendVersion")}</dt><dd dir="ltr">{frontend}</dd></div>
      <div><dt>{t("operations.backendVersion")}</dt><dd dir="ltr">{response?.data.backend_version || unavailableLabel}</dd></div>
      <div><dt>{t("operations.releaseTag")}</dt><dd dir="ltr">{response?.data.release_tag || unavailableLabel}</dd></div>
      <div><dt>{t("operations.shortCommit")}</dt><dd dir="ltr">{response?.data.short_commit || unavailableLabel}</dd></div>
      <div><dt>{t("operations.databaseRevision")}</dt><dd dir="ltr" className="break-all">{response?.data.database_revision || unavailableLabel}</dd></div>
      <div><dt>{t("operations.matchStatus")}</dt><dd dir="ltr">{state}</dd></div>
    </dl>}
  </section>;
}
