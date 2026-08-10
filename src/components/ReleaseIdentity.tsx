import { useEffect, useMemo, useState } from "react";
import { getReleaseIdentity, type ReleaseIdentityResponse } from "@/lib/api";
import { env } from "@/lib/env";

export type IdentityState = "MATCH" | "MISMATCH" | "BACKEND_UNAVAILABLE" | "IDENTITY_UNAVAILABLE";

export const compareReleaseIdentity = (frontend: string, response?: ReleaseIdentityResponse, unavailable = false): IdentityState => {
  if (unavailable) return "BACKEND_UNAVAILABLE";
  const backend = response?.data.backend_version || response?.data.application_version;
  if (!backend) return "IDENTITY_UNAVAILABLE";
  return backend === frontend ? "MATCH" : "MISMATCH";
};

export default function ReleaseIdentity({ details = false }: { details?: boolean }) {
  const frontend = env.APP_VERSION || "unknown";
  const [response, setResponse] = useState<ReleaseIdentityResponse>();
  const [unavailable, setUnavailable] = useState(false);
  useEffect(() => {
    let active = true;
    getReleaseIdentity().then(value => active && setResponse(value)).catch(() => active && setUnavailable(true));
    return () => { active = false; };
  }, []);
  const state = useMemo(() => compareReleaseIdentity(frontend, response, unavailable), [frontend, response, unavailable]);
  return <section aria-label="System information" className="min-w-0 text-xs text-slate-500" data-identity-state={state}>
    <p className="font-medium text-slate-600">Forwarder {frontend}</p>
    {details && <dl className="mt-2 grid gap-x-4 gap-y-1 sm:grid-cols-2">
      <div><dt>Frontend Version</dt><dd>{frontend}</dd></div>
      <div><dt>Backend Version</dt><dd>{response?.data.backend_version || "Unavailable"}</dd></div>
      <div><dt>Release Tag</dt><dd>{response?.data.release_tag || "Unavailable"}</dd></div>
      <div><dt>Short Commit</dt><dd>{response?.data.short_commit || "Unavailable"}</dd></div>
      <div><dt>Database Revision</dt><dd className="break-all">{response?.data.database_revision || "Unavailable"}</dd></div>
      <div><dt>Match status</dt><dd>{state}</dd></div>
    </dl>}
  </section>;
}
