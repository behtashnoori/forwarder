import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  associateDocumentArtifact, assessDocumentArtifact, getDocumentMaterializationPreview,
  getNextTransitionReadiness, listDocumentReadinessRequirements, listEligibleDocumentArtifacts,
  materializeDocumentRequirements, removeDocumentArtifactAssociation, resolveDocumentApplicability,
  type DocumentReadinessRequirement, type EligibleDocumentArtifact, type TransitionReadiness,
} from "@/lib/api";

type Draft = { artifact?: string; reason?: string };
const statusLabel: Record<DocumentReadinessRequirement["readiness_status"], string> = {
  SATISFIED: "تکمیل شده", MISSING: "کسری", PENDING_REVIEW: "در انتظار بررسی",
  REJECTED: "رد شده", NOT_APPLICABLE: "قابل اعمال نیست", UNRESOLVED: "نیازمند تعیین وضعیت",
};
const levelLabel = { REQUIRED: "الزامی", OPTIONAL: "اختیاری", CONDITIONAL: "مشروط" } as const;
const assessmentLabel: Record<string, string> = {
  ASSOCIATED: "مرتبط شده؛ در انتظار بررسی", REVIEW_STARTED: "در حال بررسی",
  APPROVED: "تأیید شده", REJECTED: "رد شده", VERIFIED: "راستی‌آزمایی شده",
};
const formatDate = (value: string) => new Intl.DateTimeFormat("fa-IR", {
  dateStyle: "medium", timeStyle: "short",
}).format(new Date(value));

export default function DocumentReadinessSection({
  shipmentPublicId, shipmentVersion, shipmentReference, projectReference, readOnly = false,
}: {
  shipmentPublicId: string; shipmentVersion: number; shipmentReference?: string;
  projectReference?: string | null; readOnly?: boolean;
}) {
  const [rows, setRows] = useState<DocumentReadinessRequirement[]>([]);
  const [eligible, setEligible] = useState<Record<string, EligibleDocumentArtifact[]>>({});
  const [preview, setPreview] = useState<Awaited<ReturnType<typeof getDocumentMaterializationPreview>>["data"]>();
  const [next, setNext] = useState<TransitionReadiness>();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});

  const load = useCallback(async () => {
    try {
      setError("");
      const [p, r, n] = await Promise.all([
        getDocumentMaterializationPreview(shipmentPublicId), listDocumentReadinessRequirements(shipmentPublicId),
        getNextTransitionReadiness(shipmentPublicId),
      ]);
      setPreview(p.data); setRows(r.data); setNext(n.data || undefined);
      const options = await Promise.all(r.data.map(async (requirement) => [
        requirement.public_id,
        (await listEligibleDocumentArtifacts(shipmentPublicId, requirement.public_id)).data,
      ] as const));
      setEligible(Object.fromEntries(options));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally { setLoading(false); }
  }, [shipmentPublicId]);
  useEffect(() => { void load(); }, [load]);

  const counts = useMemo(() => ({
    required: rows.filter((r) => r.requirement_level !== "OPTIONAL" && r.readiness_status !== "NOT_APPLICABLE").length,
    complete: rows.filter((r) => r.readiness_status === "SATISFIED").length,
    missing: rows.filter((r) => r.readiness_status === "MISSING" || r.readiness_status === "REJECTED").length,
    pending: rows.filter((r) => r.readiness_status === "PENDING_REVIEW" || r.readiness_status === "UNRESOLVED").length,
  }), [rows]);
  const run = async (action: () => Promise<unknown>) => {
    try { setBusy(true); setError(""); await action(); await load(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : String(caught)); }
    finally { setBusy(false); }
  };
  const patch = (id: string, value: Partial<Draft>) => setDrafts((current) => ({
    ...current, [id]: { ...current[id], ...value },
  }));

  return <section className="space-y-5 rounded border bg-white p-5" aria-label="اسناد محموله" dir="rtl">
    <div>
      <h3 className="text-lg font-semibold">اسناد محموله</h3>
      <p className="mt-1 text-sm text-slate-600">محموله: {shipmentReference || shipmentPublicId}{projectReference ? ` · پروژه: ${projectReference}` : ""}</p>
      <p className="mt-2 rounded bg-slate-50 p-3 text-sm text-slate-700">الزامات اسناد در سطح پروژه تعریف می‌شوند و برای هر محموله به‌صورت مستقل اعمال می‌شوند. فایل‌های بارگذاری‌شده در پرونده درخواست نگهداری می‌شوند و در صورت انطباق می‌توانند به الزامات هر محموله مرتبط شوند. یک فایل پرونده ممکن است سند مرتبط چند محموله باشد؛ مالک فایل همچنان پرونده درخواست است.</p>
    </div>
    {error && <p role="alert" className="rounded bg-red-50 p-3 text-red-700">{error}</p>}
    {loading && <p>در حال دریافت وضعیت اسناد…</p>}
    {!loading && !preview?.initialized && !readOnly && <div className="rounded border p-3">
      <p>{preview?.requirements.length || 0} الزام پیکربندی‌شده برای اعمال روی این محموله آماده است.</p>
      {preview?.findings.map((finding) => <p key={finding.code}>{finding.message}</p>)}
      <Button className="mt-2" disabled={busy || !preview?.confirmation_allowed} onClick={() => void run(() => materializeDocumentRequirements(shipmentPublicId, shipmentVersion))}>اعمال مستقل الزامات برای این محموله</Button>
    </div>}
    {!loading && rows.length > 0 && <div className="grid grid-cols-2 gap-2 sm:grid-cols-4" aria-label="خلاصه وضعیت اسناد">
      <div className="rounded border p-3"><span className="text-sm text-slate-600">الزامی</span><strong className="block text-xl">{counts.required}</strong></div>
      <div className="rounded border p-3"><span className="text-sm text-slate-600">تکمیل</span><strong className="block text-xl text-emerald-700">{counts.complete}</strong></div>
      <div className="rounded border p-3"><span className="text-sm text-slate-600">کسری</span><strong className="block text-xl text-red-700">{counts.missing}</strong></div>
      <div className="rounded border p-3"><span className="text-sm text-slate-600">در انتظار</span><strong className="block text-xl text-amber-700">{counts.pending}</strong></div>
    </div>}
    {!loading && !rows.length && <p className="rounded border border-dashed p-4">برای این محموله الزام سندی اعمال نشده است.</p>}
    {rows.map((requirement) => <RequirementCard key={requirement.public_id} requirement={requirement}
      options={eligible[requirement.public_id] || []} draft={drafts[requirement.public_id] || {}}
      patch={(value) => patch(requirement.public_id, value)} busy={busy} readOnly={readOnly}
      run={run} shipmentPublicId={shipmentPublicId} />)}
    {next && <div className="rounded border p-3"><h4 className="font-medium">وضعیت اسناد برای اقدام بعدی</h4>
      <p>{next.allowed ? "آماده" : "مسدود"} برای {next.target_action}</p>
      {next.blocking_requirements.map((b) => <p className="text-red-700" key={b.requirement_public_id + b.code}>{b.code}: {b.title}</p>)}
      {next.warnings.map((w) => <p className="text-amber-700" key={w.requirement_public_id + w.code}>{w.code}: {w.title}</p>)}
    </div>}
  </section>;
}

function RequirementCard({ requirement, options, draft, patch, busy, readOnly, run, shipmentPublicId }: {
  requirement: DocumentReadinessRequirement; options: EligibleDocumentArtifact[]; draft: Draft;
  patch: (value: Partial<Draft>) => void; busy: boolean; readOnly: boolean;
  run: (action: () => Promise<unknown>) => Promise<void>; shipmentPublicId: string;
}) {
  return <article className="space-y-3 rounded border p-4">
    <div className="flex flex-wrap items-start justify-between gap-2"><div><strong>{requirement.title}</strong>
      <p className="text-sm text-slate-600">نوع سند: {requirement.document_code} · الزام سند: {levelLabel[requirement.requirement_level]}</p></div>
      <span className="rounded-full bg-slate-100 px-3 py-1 text-sm">{statusLabel[requirement.readiness_status]}</span></div>
    <p className="text-sm">سطح بررسی لازم: {requirement.required_assessment_level === "VERIFIED" ? "راستی‌آزمایی" : "تأیید"}</p>
    {requirement.applicability_reason && <p className="text-sm">دلیل تعیین قابلیت اعمال: {requirement.applicability_reason}</p>}
    {requirement.artifact ? <div className="rounded bg-emerald-50 p-3 text-sm"><strong>سند مرتبط:</strong> {requirement.artifact.filename} · نسخه {requirement.artifact.version}
      <p>وضعیت بررسی: {assessmentLabel[requirement.artifact.assessment] || requirement.artifact.assessment}</p>
      <p>زمان ارتباط: {formatDate(requirement.artifact.associated_at)}</p></div>
      : <p className="rounded bg-amber-50 p-3 text-sm">هنوز فایل پرونده‌ای به این الزام محموله مرتبط نشده است.</p>}
    {!readOnly && requirement.applicability_state !== "NOT_APPLICABLE" && <div className="space-y-2">
      <label className="block text-sm font-medium" htmlFor={`artifact-${requirement.public_id}`}>فایل موجود در پرونده</label>
      <div className="flex flex-col gap-2 sm:flex-row"><select id={`artifact-${requirement.public_id}`} className="min-h-10 flex-1 rounded border bg-white px-3" value={draft.artifact || ""} onChange={(event) => patch({ artifact: event.target.value })}>
        <option value="">انتخاب فایل و نسخه</option>{options.map((a) => <option key={a.artifact_public_id} value={a.artifact_public_id}>{a.filename} · نسخه {a.version}</option>)}</select>
        <Button variant="outline" disabled={busy || !draft.artifact} onClick={() => void run(() => associateDocumentArtifact(shipmentPublicId, requirement, draft.artifact!))}>{requirement.artifact ? "جایگزینی سند مرتبط" : "ارتباط با این محموله"}</Button>
        {requirement.artifact && <Button variant="destructive" disabled={busy} onClick={() => void run(() => removeDocumentArtifactAssociation(shipmentPublicId, requirement))}>حذف ارتباط</Button>}</div>
      {!options.length && <p className="text-sm text-slate-600">فایل واجد شرایطی از همین پرونده و همین نوع سند وجود ندارد. فایل را در بخش اسناد پرونده درخواست بارگذاری کنید.</p>}
    </div>}
    {!readOnly && <div className="space-y-2"><Input aria-label={`دلیل برای ${requirement.title}`} placeholder="دلیل (برای رد یا تعیین قابلیت اعمال الزامی است)" value={draft.reason || ""} onChange={(event) => patch({ reason: event.target.value })} />
      <div className="flex flex-wrap gap-2">{requirement.requirement_level === "CONDITIONAL" && requirement.applicability_state === "UNRESOLVED" && <>
        <Button disabled={busy || !draft.reason?.trim()} onClick={() => void run(() => resolveDocumentApplicability(shipmentPublicId, requirement, "APPLICABLE", draft.reason!.trim()))}>قابل اعمال است</Button>
        <Button variant="outline" disabled={busy || !draft.reason?.trim()} onClick={() => void run(() => resolveDocumentApplicability(shipmentPublicId, requirement, "NOT_APPLICABLE", draft.reason!.trim()))}>قابل اعمال نیست</Button></>}
        {requirement.artifact && <><Button variant="outline" disabled={busy} onClick={() => void run(() => assessDocumentArtifact(shipmentPublicId, requirement, "REVIEW_STARTED"))}>شروع بررسی</Button>
          <Button disabled={busy} onClick={() => void run(() => assessDocumentArtifact(shipmentPublicId, requirement, "APPROVED"))}>تأیید</Button>
          <Button variant="destructive" disabled={busy || !draft.reason?.trim()} onClick={() => void run(() => assessDocumentArtifact(shipmentPublicId, requirement, "REJECTED", draft.reason!.trim()))}>رد</Button>
          <Button disabled={busy} onClick={() => void run(() => assessDocumentArtifact(shipmentPublicId, requirement, "VERIFIED"))}>راستی‌آزمایی</Button></>}</div></div>}
  </article>;
}
