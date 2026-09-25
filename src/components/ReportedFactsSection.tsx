import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import { listReportedFacts, recordReportedFact, type ReportDraft, type ReportFact, type ReportList } from "@/lib/reportedFactApi";

const scopes = { SHIPMENT: "پرونده حمل", ROUTE_STAGE: "مرحله مسیر", EXECUTION_UNIT: "اجرای حمل", CARGO: "کالا" };
const kinds = { LOCATION: "گزارش موقعیت", PROGRESS: "گزارش پیشرفت", TRANSPORT_CHANGE: "تغییر حمل", EFFECT: "اثر عملیاتی" };
const sources = { CARRIER_REPORT: "گزارش شرکت حمل", DRIVER_REPORT: "گزارش راننده", INTERNAL_EXPERT: "ثبت کارشناس", OTHER_OPERATIONAL_SOURCE: "منبع عملیاتی دیگر" };
const time = (value: string) => formatDualCalendarInstant(value, "fa-IR");
const localTime = (value: string) => {
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, -1);
};
const message = (error: unknown) => error instanceof ApiError && error.status === 403
  ? "فقط کارشناس مسئول می‌تواند گزارش ثبت یا اصلاح کند."
  : error instanceof ApiError && error.status === 409
    ? "گزارش تغییر کرده است؛ اطلاعات را تازه‌سازی کنید و نسخه جاری را بررسی کنید."
    : "دریافت یا ثبت گزارش ممکن نشد؛ اطلاعات را بررسی و دوباره تلاش کنید.";

function ReportForm({ data, initial, pending, onSubmit, onCancel }: {
  data: ReportList; initial?: ReportFact; pending: boolean;
  onSubmit: (draft: ReportDraft) => Promise<void>; onCancel: () => void;
}) {
  const [draft, setDraft] = useState<ReportDraft>(() => ({
    scope: initial?.scope || "EXECUTION_UNIT", target_public_id: initial?.target_public_id || null,
    kind: initial?.kind || "LOCATION", source: initial?.source || "INTERNAL_EXPERT",
    occurred_at: initial ? localTime(initial.occurred_at) : "",
    location: initial?.location ? { location_text: initial.location } : null,
    internal_note: initial?.internal_note || null, customer_message: initial?.customer_message || null,
    customer_effect: initial?.customer_effect || "CHANGE", impacted_cargo_public_ids: initial?.impacted_cargo_public_ids || [],
    ...(initial ? { corrects_public_id: initial.public_id, reason: null } : {}),
  }));
  const selectClass = "min-h-11 w-full rounded-md border bg-white px-3";
  return <form className="grid gap-3 rounded-xl border bg-slate-50 p-3 sm:grid-cols-2" onSubmit={(event) => {
    event.preventDefault();
    if (!draft.occurred_at) return;
    const occurred = initial && draft.occurred_at === localTime(initial.occurred_at) ? initial.occurred_at : new Date(draft.occurred_at).toISOString();
    void onSubmit({ ...draft, occurred_at: occurred });
  }}>
    <h4 className="font-semibold sm:col-span-2">{initial ? "اصلاح گزارش با حفظ اصل آن" : "ثبت گزارش تازه"}</h4>
    <label>نوع گزارش<select aria-label="نوع گزارش" className={selectClass} value={draft.kind} onChange={e => setDraft({ ...draft, kind: e.target.value as ReportDraft["kind"] })}>{Object.entries(kinds).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
    <label>منبع گزارش<select aria-label="منبع گزارش" className={selectClass} value={draft.source} onChange={e => setDraft({ ...draft, source: e.target.value as ReportDraft["source"] })}>{Object.entries(sources).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
    <label>دامنه گزارش<select aria-label="دامنه گزارش" className={selectClass} value={draft.scope} onChange={e => setDraft({ ...draft, scope: e.target.value as ReportDraft["scope"], target_public_id: null, impacted_cargo_public_ids: [] })}>{Object.entries(scopes).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
    {draft.scope !== "SHIPMENT" && <label>بخش مربوط<select required aria-label="بخش مربوط به گزارش" className={selectClass} value={draft.target_public_id || ""} onChange={e => setDraft({ ...draft, target_public_id: e.target.value, impacted_cargo_public_ids: [] })}><option value="">انتخاب کنید</option>{data.options[draft.scope].map(option => <option key={option.public_id} value={option.public_id}>{option.label}</option>)}</select></label>}
    <label>زمان وقوع<Input required aria-label="زمان وقوع گزارش" type="datetime-local" step="0.001" dir="ltr" value={draft.occurred_at} onChange={e => setDraft({ ...draft, occurred_at: e.target.value })} /><span className="text-xs text-slate-600">زمان محلی شما؛ ثبت دیرهنگام مجاز است.</span></label>
    <label>موقعیت گزارش‌شده{draft.kind === "LOCATION" ? " (الزامی)" : " (اختیاری، داخلی)"}<Input aria-label="موقعیت گزارش‌شده" required={draft.kind === "LOCATION"} maxLength={255} placeholder="برای نمونه: نزدیک مرز" value={draft.location?.location_text || ""} onChange={e => setDraft({ ...draft, location: e.target.value.trim() ? { location_text: e.target.value } : null })} /></label>
    <label className="sm:col-span-2">یادداشت داخلی<textarea aria-label="یادداشت داخلی گزارش" className={`${selectClass} py-2`} maxLength={4000} value={draft.internal_note || ""} onChange={e => setDraft({ ...draft, internal_note: e.target.value || null })} /></label>
    <fieldset className="space-y-2 rounded-lg border bg-white p-3 sm:col-span-2"><legend className="px-1 font-medium">اثر برای مشتری</legend><p className="text-xs text-slate-600">فقط کالاهای متأثر را انتخاب کنید. بدون انتخاب، این گزارش در نمای مشتری نمایش داده نمی‌شود.</p>
      <div className="grid gap-2 sm:grid-cols-2">{data.options.cargo.map(cargo => <label key={cargo.public_id} className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={draft.impacted_cargo_public_ids.includes(cargo.public_id)} onChange={e => setDraft({ ...draft, impacted_cargo_public_ids: e.target.checked ? [...draft.impacted_cargo_public_ids, cargo.public_id] : draft.impacted_cargo_public_ids.filter(id => id !== cargo.public_id) })} />{cargo.label}</label>)}</div>
      <label className="block">نوع اثر<select aria-label="نوع اثر برای مشتری" className={selectClass} value={draft.customer_effect} onChange={e => setDraft({ ...draft, customer_effect: e.target.value as "CHANGE" | "DELAY" })}><option value="CHANGE">تغییر عملیاتی</option><option value="DELAY">تأخیر</option></select></label>
      <label className="block">متن امن برای مشتری<textarea aria-label="متن امن برای مشتری" className={`${selectClass} py-2`} maxLength={1000} value={draft.customer_message || ""} onChange={e => setDraft({ ...draft, customer_message: e.target.value || null })} /></label>
      <p className="text-xs text-slate-600">نام، موقعیت یا علت خصوصی مشتری دیگر را وارد نکنید. اگر متن خالی باشد، پیام ثابت عمومی نمایش داده می‌شود.</p>
    </fieldset>
    {initial && <label className="sm:col-span-2">دلیل اصلاح (اختیاری)<Input aria-label="دلیل اصلاح گزارش" maxLength={500} value={draft.reason || ""} onChange={e => setDraft({ ...draft, reason: e.target.value || null })} /></label>}
    <div className="flex flex-wrap gap-2 sm:col-span-2"><Button type="submit" disabled={pending}>{pending ? "در حال ثبت…" : initial ? "ثبت اصلاح گزارش" : "ثبت گزارش"}</Button><Button type="button" variant="outline" disabled={pending} onClick={onCancel}>انصراف</Button></div>
  </form>;
}

export default function ReportedFactsSection({ shipmentId }: { shipmentId: string }) {
  const [data, setData] = useState<ReportList>();
  const [page, setPage] = useState(1);
  const [form, setForm] = useState<ReportFact | "new" | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const command = useRef<{ body: string; key: string }>();
  const load = useCallback(async () => {
    try { setError(""); setData((await listReportedFacts(shipmentId, page)).data); }
    catch (caught) { setData(undefined); setError(message(caught)); }
  }, [shipmentId, page]);
  useEffect(() => { void load(); }, [load]);
  const submit = async (draft: ReportDraft) => {
    const body = JSON.stringify(draft);
    if (command.current?.body !== body) command.current = { body, key: crypto.randomUUID() };
    try {
      setPending(true); setError(""); setNotice("");
      await recordReportedFact(shipmentId, draft, command.current.key);
      command.current = undefined; setForm(null);
      setNotice(draft.corrects_public_id ? "اصلاح ثبت شد؛ اصل گزارش در سابقه محفوظ است." : "گزارش ثبت شد.");
      await load();
    } catch (caught) { setError(message(caught)); }
    finally { setPending(false); }
  };
  return <section aria-label="گزارش‌های موقعیت و تغییرات حمل" className="space-y-4" dir="rtl">
    <p className="text-sm text-slate-600">این موقعیت‌ها بر اساس گزارش ثبت شده‌اند. موقعیت زنده یا GPS نیستند. گزارش هر بخش حمل جدا نمایش داده می‌شود.</p>
    {error && <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}<Button variant="outline" className="mr-2" onClick={() => void load()}>تازه‌سازی گزارش‌ها</Button></div>}
    {notice && <p role="status" className="rounded-lg bg-green-50 p-3 text-sm">{notice}</p>}
    {!data && !error && <p role="status">در حال دریافت گزارش‌ها…</p>}
    {data && <>
      {!data.can_manage && <p className="text-sm text-slate-600">نمای فقط‌خواندنی؛ ثبت و اصلاح با کارشناس مسئول است.</p>}
      {data.reported_locations.length > 0 && <div className="grid gap-3 sm:grid-cols-2">{data.reported_locations.map(item => <article key={item.public_id} className="rounded-xl border border-blue-100 bg-blue-50 p-3"><h4 className="font-semibold">{item.scope_label}</h4><p>آخرین موقعیت گزارش‌شده: {item.location}</p><p className="text-xs text-slate-600">{item.source_label} · {time(item.occurred_at)}</p></article>)}</div>}
      {data.can_manage && !form && <Button variant="outline" onClick={() => setForm("new")}>گزارش تازه</Button>}
      {data.can_manage && form && <ReportForm key={form === "new" ? "new" : form.public_id} data={data} initial={form === "new" ? undefined : form} pending={pending} onSubmit={submit} onCancel={() => setForm(null)} />}
      <h4 className="font-semibold">سابقه گزارش‌ها</h4>
      {data.items.length === 0 && <p className="rounded-lg border border-dashed p-4 text-sm">هنوز گزارشی ثبت نشده است.</p>}
      {data.items.map(item => <article key={item.public_id} className="space-y-2 rounded-xl border p-3" data-report-id={item.public_id}>
        <div className="flex flex-wrap justify-between gap-2"><h5 className="font-medium">{kinds[item.kind]} · {item.scope_label}</h5><span className="text-xs">{item.status === "SUPERSEDED" ? "اصلاح‌شده؛ محفوظ در سابقه" : item.corrects_public_id ? "نسخه اصلاحی جاری" : "گزارش جاری"}</span></div>
        {item.location && <p>موقعیت گزارش‌شده: {item.location}</p>}
        <p className="text-xs text-slate-600">منبع: {item.source_label} · ثبت‌کننده: {item.actor_label}</p>
        <p className="text-xs text-slate-600">وقوع: {time(item.occurred_at)}<br />ثبت: {time(item.recorded_at)}</p>
        {item.internal_note && <p className="whitespace-pre-wrap text-sm">یادداشت داخلی: {item.internal_note}</p>}
        {item.customer_message && <p className="whitespace-pre-wrap text-sm">متن امن مشتری: {item.customer_message}</p>}
        {item.reason && <p className="text-sm">دلیل اصلاح: {item.reason}</p>}
        {data.can_manage && item.status === "CURRENT" && <Button variant="outline" disabled={pending} onClick={() => setForm(item)}>اصلاح گزارش</Button>}
      </article>)}
      {data.total > 20 && <nav aria-label="صفحه‌های گزارش" className="flex items-center gap-3"><Button variant="outline" disabled={page === 1} onClick={() => setPage(page - 1)}>قبلی</Button><span>صفحه {page}</span><Button variant="outline" disabled={page * 20 >= data.total} onClick={() => setPage(page + 1)}>بعدی</Button></nav>}
    </>}
  </section>;
}
