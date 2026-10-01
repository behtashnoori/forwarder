import { useCallback, useEffect, useState } from "react";
import OperationalPermission from "@/components/OperationalPermission";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  appendEconomicObservation, confirmCommercialEconomics, correctEconomicObservation,
  createEconomicFx, createEconomicLine, getEconomicProjection, listEconomicLines,
  previewCommercialEconomics, type EconomicLine, type ShipmentEconomicsProjection,
} from "@/lib/api";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import { formatMoney } from "@/lib/formatQuantity";

type Side = "REVENUE" | "COST";
type Stage = "ESTIMATE" | "COMMITMENT" | "ACTUAL";
type CorrectionType = "SUPERSESSION" | "REVERSAL";

const faLabels: Record<string, string> = {
  REVENUE: "درآمد", COST: "هزینه", ESTIMATE: "برآورد", COMMITMENT: "تعهد", ACTUAL: "واقعی",
  COMPLETE: "کامل", INCOMPLETE: "ناقص", UNKNOWN: "نامشخص", AUTHORIZED: "تأییدشده",
  SUPERSEDED: "جایگزین‌شده", REVERSED: "برگشت‌خورده", ACTIVE: "فعال",
  SUPERSESSION: "اصلاح و جایگزینی", REVERSAL: "برگشت", SUPPORTING: "پشتیبان",
  NOT_APPLICABLE: "قابل اعمال نیست", REVENUE_MISSING: "دادهٔ درآمد ثبت نشده است",
  COST_MISSING: "دادهٔ هزینه ثبت نشده است", FX_MISSING: "نرخ تبدیل لازم ثبت نشده است",
  COST_VISIBILITY_RESTRICTED: "نمایش هزینه برای این نقش مجاز نیست",
  MARGIN_VISIBILITY_RESTRICTED: "نمایش حاشیه برای این نقش مجاز نیست",
};

export default function ShipmentEconomicsSection({ shipmentPublicId, sourceType = "accepted_quote" }: {
  shipmentPublicId: string; sourceType?: "direct" | "accepted_quote";
}) {
  const rtl = document.documentElement.dir === "rtl";
  const tr = (en: string, fa: string) => rtl ? fa : en;
  const label = (value: string | null | undefined) => value ? (rtl ? faLabels[value] ?? value : value) : tr("Unknown", "نامشخص");
  const locale = rtl ? "fa-IR" : "en-US";
  const show = (money: { amount: string; currency: string } | null) => money ? formatMoney(money.amount, money.currency, locale) : tr("Unknown", "نامشخص");
  const [projection, setProjection] = useState<ShipmentEconomicsProjection>();
  const [lines, setLines] = useState<EconomicLine[]>([]);
  const [preview, setPreview] = useState<Awaited<ReturnType<typeof previewCommercialEconomics>>["data"]>();
  const [service, setService] = useState("");
  const [authority, setAuthority] = useState("");
  const [error, setError] = useState("");
  const [side, setSide] = useState<Side>("COST");
  const [stage, setStage] = useState<Stage>("ESTIMATE");
  const [lineId, setLineId] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [reason, setReason] = useState("");
  const [fxId, setFxId] = useState("");
  const [evidenceId, setEvidenceId] = useState("");
  const [evidenceVersion, setEvidenceVersion] = useState("1");
  const [selectedObservation, setSelectedObservation] = useState("");
  const [correctionType, setCorrectionType] = useState<CorrectionType>("SUPERSESSION");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [fxFrom, setFxFrom] = useState("EUR");
  const [fxTo, setFxTo] = useState("USD");
  const [fxRate, setFxRate] = useState("");
  const [fxSource, setFxSource] = useState("");

  const load = useCallback(async () => {
    try {
      setError("");
      const [nextProjection, nextLines] = await Promise.all([getEconomicProjection(shipmentPublicId), listEconomicLines(shipmentPublicId)]);
      setProjection(nextProjection.data); setLines(nextLines.data);
      if (sourceType === "accepted_quote") {
        try { setPreview((await previewCommercialEconomics(shipmentPublicId)).data); } catch { setPreview(undefined); }
      } else setPreview(undefined);
    } catch (nextError) { setError(nextError instanceof Error ? nextError.message : String(nextError)); }
  }, [shipmentPublicId, sourceType]);
  useEffect(() => { void load(); }, [load]);

  const evidence = () => evidenceId.trim() ? [{ artifact_public_id: evidenceId.trim(), artifact_version: Number(evidenceVersion), role: "SUPPORTING" }] : [];
  const confirm = async () => {
    try { setError(""); await confirmCommercialEconomics(shipmentPublicId, service.trim(), authority.trim()); await load(); }
    catch (nextError) { setError(nextError instanceof Error ? nextError.message : String(nextError)); }
  };
  const submitFact = async () => {
    try {
      setBusy(true); setError(""); setNotice("");
      const common = { stage, money: { amount: amount.trim(), currency: currency.trim().toUpperCase() }, effective_at: new Date().toISOString(), authority: authority.trim(), reason: reason.trim(), idempotency_key: crypto.randomUUID(), ...(fxId.trim() ? { fx_rate_public_id: fxId.trim() } : {}), evidence: evidence() };
      if (lineId) await appendEconomicObservation(shipmentPublicId, lineId, common);
      else await createEconomicLine(shipmentPublicId, { ...common, side, service_public_id: service.trim() });
      setNotice(tr(`${side} ${stage} recorded.`, `${label(side)} ${label(stage)} ثبت شد.`)); await load();
    } catch (nextError) { setError(nextError instanceof Error ? nextError.message : String(nextError)); }
    finally { setBusy(false); }
  };
  const submitCorrection = async () => {
    const observation = lines.flatMap((line) => line.observations).find((item) => item.public_id === selectedObservation);
    if (!observation) return;
    try {
      setBusy(true); setError(""); setNotice("");
      await correctEconomicObservation(shipmentPublicId, observation.public_id, { correction_type: correctionType, expected_version: observation.version, money: { amount: amount.trim(), currency: currency.trim().toUpperCase() }, effective_at: new Date().toISOString(), authority: authority.trim(), reason: reason.trim(), idempotency_key: crypto.randomUUID(), ...(fxId.trim() ? { fx_rate_public_id: fxId.trim() } : {}), evidence: evidence() });
      setNotice(tr(`${correctionType} recorded without changing history.`, `${label(correctionType)} بدون تغییر سابقه ثبت شد.`)); await load();
    } catch (nextError) { setError(nextError instanceof Error ? nextError.message : String(nextError)); }
    finally { setBusy(false); }
  };
  const submitFx = async () => {
    try {
      setBusy(true); setError("");
      const result = await createEconomicFx({ from_currency: fxFrom.toUpperCase(), to_currency: fxTo.toUpperCase(), rate: fxRate, rate_type: "MANUAL_APPROVED", source: fxSource.trim(), authority: authority.trim(), effective_at: new Date().toISOString() });
      setFxId(result.data.public_id);
      setNotice(tr(`Authorized FX fact ${result.data.public_id} created and selected.`, `واقعیت نرخ تبدیل تأییدشده ${result.data.public_id} ایجاد و انتخاب شد.`));
    } catch (nextError) { setError(nextError instanceof Error ? nextError.message : String(nextError)); }
    finally { setBusy(false); }
  };

  return <section className="space-y-4 rounded-xl border bg-white p-5" aria-label={tr("Shipment Economics", "اقتصاد محموله")}>
    <h3 className="font-semibold">{tr("Shipment Economics", "اقتصاد محموله")}</h3>
    <p className="text-sm text-slate-600">{tr("Missing facts remain UNKNOWN or INCOMPLETE. A recorded amount of 0 is displayed as zero and is never treated as missing.", "داده‌های ثبت‌نشده نامشخص یا ناقص می‌مانند. مبلغ ثبت‌شدهٔ صفر، صفر نمایش داده می‌شود و هرگز دادهٔ مفقود محسوب نمی‌شود.")}</p>
    {error && <p role="alert" className="text-red-700">{error}</p>}{notice && <p role="status" className="text-emerald-700">{notice}</p>}
    <div className="grid gap-3 md:grid-cols-3">{(["ESTIMATE", "COMMITMENT", "ACTUAL"] as const).map((stageKey) => {
      const stageProjection = projection?.stages[stageKey];
      return <article className="rounded-lg border p-3" key={stageKey}>
        <strong>{label(stageKey)}</strong><p>{tr("Revenue", "درآمد")}: {show(stageProjection?.revenue || null)}</p><p>{tr("Cost", "هزینه")}: {show(stageProjection?.cost || null)}</p><p>{tr("Margin", "حاشیه")}: {show(stageProjection?.margin || null)}</p>
        <p className={stageProjection?.completeness === "COMPLETE" ? "text-emerald-700" : "text-amber-700"}>{label(stageProjection?.completeness)}</p>
        {stageProjection?.missing_inputs.map((missing) => <small className="block" key={missing}>{label(missing)}</small>)}
      </article>;
    })}</div>
    <OperationalPermission permission="economics.commitment.create">{preview && !preview.already_materialized && <div className="space-y-2 rounded-lg bg-slate-50 p-3">
      <strong>{tr("Accepted commercial intent", "قصد تجاری پذیرفته‌شده")}: {formatMoney(preview.commercial_intent.amount, preview.commercial_intent.currency, locale)}</strong>
      <p>{tr("Preview only—confirmation explicitly creates committed revenue.", "این فقط پیش‌نمایش است؛ تأیید، درآمد تعهدشده را به‌صراحت ایجاد می‌کند.")}</p>
      <div className="grid gap-2 sm:grid-cols-3"><Input aria-label={tr("Service public identity", "شناسه عمومی خدمت")} placeholder={tr("Governed service public identity", "شناسه عمومی خدمت حاکم‌شده")} value={service} onChange={(event) => setService(event.target.value)} /><Input aria-label={tr("Revenue authority", "مرجع درآمد")} placeholder={tr("Authority", "مرجع")} value={authority} onChange={(event) => setAuthority(event.target.value)} /><Button disabled={!preview.confirmation_allowed || !service.trim() || !authority.trim()} onClick={() => void confirm()}>{tr("Confirm materialization", "تأیید ثبت")}</Button></div>
    </div>}</OperationalPermission>
    <OperationalPermission permission={`economics.${stage.toLowerCase()}.create`}><div className="space-y-3 rounded-lg border p-3">
      <h4 className="font-medium">{tr("Record approved economic fact", "ثبت واقعیت اقتصادی تأییدشده")}</h4>
      <div className="grid gap-2 md:grid-cols-3">
        <select aria-label={tr("Economic side", "سمت اقتصادی")} className="rounded border p-2" value={side} onChange={(event) => { setSide(event.target.value as Side); setLineId(""); }}><option value="REVENUE">{tr("Revenue", "درآمد")}</option><option value="COST">{tr("Cost", "هزینه")}</option></select>
        <select aria-label={tr("Economic stage", "مرحله اقتصادی")} className="rounded border p-2" value={stage} onChange={(event) => setStage(event.target.value as Stage)}><option value="ESTIMATE">{label("ESTIMATE")}</option><option value="COMMITMENT">{label("COMMITMENT")}</option><option value="ACTUAL">{label("ACTUAL")}</option></select>
        <select aria-label={tr("Existing economic line", "ردیف اقتصادی موجود")} className="rounded border p-2" value={lineId} onChange={(event) => setLineId(event.target.value)}><option value="">{tr("Create a new line", "ایجاد ردیف تازه")}</option>{lines.filter((line) => line.side === side).map((line) => <option value={line.public_id} key={line.public_id}>{line.service_title}</option>)}</select>
        <Input aria-label={tr("Service public identity for new line", "شناسه عمومی خدمت برای ردیف تازه")} placeholder={tr("Service public identity", "شناسه عمومی خدمت")} disabled={!!lineId} value={service} onChange={(event) => setService(event.target.value)} />
        <Input aria-label={tr("Original money amount", "مبلغ اصلی")} placeholder={tr("Original amount (0 is valid)", "مبلغ اصلی (صفر معتبر است)")} value={amount} onChange={(event) => setAmount(event.target.value)} />
        <Input aria-label={tr("Original money currency", "ارز مبلغ اصلی")} placeholder={tr("Currency", "ارز")} maxLength={3} value={currency} onChange={(event) => setCurrency(event.target.value)} />
        <Input aria-label={tr("Economic authority", "مرجع اقتصادی")} placeholder={tr("Authority", "مرجع")} value={authority} onChange={(event) => setAuthority(event.target.value)} />
        <Input aria-label={tr("Economic reason", "دلیل اقتصادی")} placeholder={tr("Reason", "دلیل")} value={reason} onChange={(event) => setReason(event.target.value)} />
        <Input aria-label={tr("Applied FX fact identity", "شناسه واقعیت نرخ تبدیل")} placeholder={tr("FX fact public identity (if needed)", "شناسه عمومی نرخ تبدیل (در صورت نیاز)")} value={fxId} onChange={(event) => setFxId(event.target.value)} />
        <Input aria-label={tr("Evidence public identity", "شناسه عمومی مدرک")} placeholder={tr("Evidence public identity (optional)", "شناسه عمومی مدرک (اختیاری)")} value={evidenceId} onChange={(event) => setEvidenceId(event.target.value)} />
        <Input aria-label={tr("Evidence version", "نسخه مدرک")} type="number" min="1" value={evidenceVersion} onChange={(event) => setEvidenceVersion(event.target.value)} />
      </div>
      <Button disabled={busy || !amount.trim() || !currency.trim() || !authority.trim() || !reason.trim() || (!lineId && !service.trim())} onClick={() => void submitFact()}>{tr(`Record ${side.toLowerCase()} ${stage.toLowerCase()}`, `ثبت ${label(side)} ${label(stage)}`)}</Button>
    </div></OperationalPermission>
    <OperationalPermission permission="economics.observation.correct"><div className="space-y-3 rounded-lg border p-3">
      <h4 className="font-medium">{tr("Correction / reversal", "اصلاح / برگشت")}</h4>
      <div className="grid gap-2 md:grid-cols-2"><select aria-label={tr("Observation to correct", "مشاهده برای اصلاح")} className="rounded border p-2" value={selectedObservation} onChange={(event) => setSelectedObservation(event.target.value)}><option value="">{tr("Select an authorized observation", "یک مشاهده تأییدشده را انتخاب کنید")}</option>{lines.flatMap((line) => line.observations).filter((observation) => observation.status === "AUTHORIZED").map((observation) => <option value={observation.public_id} key={observation.public_id}>{label(observation.stage)} · {show(observation.money)}</option>)}</select><select aria-label={tr("Correction type", "نوع اصلاح")} className="rounded border p-2" value={correctionType} onChange={(event) => setCorrectionType(event.target.value as CorrectionType)}><option value="SUPERSESSION">{tr("Correction / supersession", "اصلاح / جایگزینی")}</option><option value="REVERSAL">{tr("Reversal", "برگشت")}</option></select></div>
      <p className="text-sm text-slate-600">{tr("Uses the amount, currency, authority, reason, FX, and evidence fields above. The original observation remains in history.", "از مبلغ، ارز، مرجع، دلیل، نرخ تبدیل و مدرک بالا استفاده می‌شود. مشاهده اصلی در سابقه باقی می‌ماند.")}</p>
      <Button disabled={busy || !selectedObservation || !amount.trim() || !authority.trim() || !reason.trim()} onClick={() => void submitCorrection()}>{tr(`Record ${correctionType.toLowerCase()}`, `ثبت ${label(correctionType)}`)}</Button>
    </div></OperationalPermission>
    <OperationalPermission permission="economics.fx.approve"><div className="space-y-3 rounded-lg border p-3">
      <h4 className="font-medium">{tr("Create authorized FX fact", "ایجاد واقعیت نرخ تبدیل تأییدشده")}</h4>
      <div className="grid gap-2 md:grid-cols-4"><Input aria-label={tr("FX from currency", "ارز مبدأ نرخ تبدیل")} maxLength={3} value={fxFrom} onChange={(event) => setFxFrom(event.target.value)} /><Input aria-label={tr("FX to currency", "ارز مقصد نرخ تبدیل")} maxLength={3} value={fxTo} onChange={(event) => setFxTo(event.target.value)} /><Input aria-label={tr("FX rate", "نرخ تبدیل")} placeholder={tr("Exact rate", "نرخ دقیق")} value={fxRate} onChange={(event) => setFxRate(event.target.value)} /><Input aria-label={tr("FX source", "منبع نرخ تبدیل")} placeholder={tr("Approved source", "منبع تأییدشده")} value={fxSource} onChange={(event) => setFxSource(event.target.value)} /></div>
      <Button disabled={busy || !fxRate || !fxSource.trim() || !authority.trim()} onClick={() => void submitFx()}>{tr("Create and select FX fact", "ایجاد و انتخاب واقعیت نرخ تبدیل")}</Button>
    </div></OperationalPermission>
    <h4 className="font-medium">{tr("Economic Lines / History", "ردیف‌ها / سابقه اقتصادی")}</h4>
    {!lines.length && <p>{tr("No economic truth has been recorded. Missing is not zero.", "هنوز واقعیت اقتصادی ثبت نشده است. دادهٔ مفقود، صفر نیست.")}</p>}
    {lines.map((line) => <details className="rounded-lg border p-3" key={line.public_id}><summary>{label(line.side)} · {line.service_title} (<bdi dir="ltr">{line.service_code}</bdi>) · {label(line.lifecycle)}</summary>{line.observations.map((observation) => <div className="mt-2 text-sm" key={observation.public_id}><p>{label(observation.stage)} · {show(observation.money)} · {label(observation.status)} · {tr("effective", "اثر از")} <time dateTime={observation.effective_at} dir="auto">{formatDualCalendarInstant(observation.effective_at, locale)}</time> · {tr("recorded", "ثبت‌شده در")} <time dateTime={observation.recorded_at} dir="auto">{formatDualCalendarInstant(observation.recorded_at, locale)}</time>{observation.fx_binding && <> · {tr("FX", "نرخ تبدیل")} <bdi dir="ltr">{observation.fx_binding.fx_rate_public_id} @ {observation.fx_binding.rate} {observation.fx_binding.to_currency}</bdi></>}</p>{observation.evidence.map((item) => <p className="text-slate-600" key={item.public_id}>{tr("Evidence", "مدرک")} <bdi dir="ltr">{item.artifact_public_id}</bdi> · {tr("version", "نسخه")} {item.artifact_version} · {label(item.role)}</p>)}</div>)}</details>)}
  </section>;
}
