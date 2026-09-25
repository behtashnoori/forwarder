import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, downloadShipmentDocument, uploadShipmentDocument } from "@/lib/api";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import { listDeliveries, recordDelivery, type DeliveryCargo, type DeliveryDraft, type DeliveryFact, type DeliveryList } from "@/lib/deliveryApi";

const time = (value: string) => formatDualCalendarInstant(value, "fa-IR");
const number = (value: string | null) => value === null ? "نامشخص" : Number(value).toLocaleString("fa-IR", { maximumFractionDigits: 6 });
const localTime = (value: string) => {
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, -1);
};
const message = (error: unknown) => error instanceof ApiError && error.status === 403
  ? "فقط کارشناس مسئول می‌تواند تحویل ثبت یا اصلاح کند."
  : error instanceof ApiError && error.status === 409
    ? "اطلاعات تغییر کرده است؛ تازه‌سازی کنید و تحویل جاری را بررسی کنید."
    : error instanceof Error ? error.message : "دریافت یا ثبت تحویل ممکن نشد؛ دوباره تلاش کنید.";

function DeliveryForm({ cargo, initial, pending, onSubmit, onCancel }: {
  cargo: DeliveryCargo; initial?: DeliveryFact; pending: boolean;
  onSubmit: (draft: DeliveryDraft) => Promise<void>; onCancel: () => void;
}) {
  const [quantity, setQuantity] = useState(initial?.quantity || "");
  const [destination, setDestination] = useState(initial?.destination_text || "");
  const [occurred, setOccurred] = useState(initial ? localTime(initial.occurred_at) : "");
  const [reason, setReason] = useState("");
  return <form aria-label={initial ? "اصلاح تحویل" : "ثبت تحویل"} className="rounded-xl border bg-slate-50 p-3" onSubmit={event => {
    event.preventDefault();
    void onSubmit({ cargo_public_id: cargo.public_id, quantity, uom_public_id: cargo.uom_public_id,
      destination_text: destination, occurred_at: initial && occurred === localTime(initial.occurred_at) ? initial.occurred_at : new Date(occurred).toISOString(),
      expected_version: initial?.revision || 0, ...(initial ? { corrects_public_id: initial.public_id, reason: reason || null } : {}) });
  }}>
    <fieldset disabled={pending} className="grid gap-3 sm:grid-cols-2">
      <legend className="mb-3 font-semibold">{initial ? "اصلاح تحویل" : "تحویل تازه"} · {cargo.label} · {cargo.customer_label}</legend>
      <label>مقدار تحویل ({cargo.uom_symbol})<Input aria-label="مقدار تحویل" required type="number" min="0.000001" step="0.000001" max="999999999999.999999" dir="ltr" value={quantity} onChange={e => setQuantity(e.target.value)} /></label>
      <label>مقصد تحویل<Input aria-label="مقصد تحویل" required maxLength={255} value={destination} onChange={e => setDestination(e.target.value)} /></label>
      <label>زمان وقوع تحویل<Input aria-label="زمان وقوع تحویل" required type="datetime-local" step="0.001" dir="ltr" value={occurred} onChange={e => setOccurred(e.target.value)} /><span className="text-xs text-slate-600">زمان محلی شما؛ ثبت دیرهنگام مجاز است.</span></label>
      {initial && <label>دلیل اصلاح (اختیاری)<Input aria-label="دلیل اصلاح تحویل" maxLength={500} value={reason} onChange={e => setReason(e.target.value)} /></label>}
      <p className="text-xs text-slate-600 sm:col-span-2">مقدار واقعی گزارش‌شده را ثبت کنید. اختلاف با مقدار شناخته‌شده مانع ثبت نیست و مقدار کالا را تغییر نمی‌دهد.</p>
      <div className="flex flex-wrap gap-2 sm:col-span-2"><Button type="submit">{pending ? "در حال ثبت…" : initial ? "ثبت اصلاح تحویل" : "ثبت تحویل"}</Button><Button type="button" variant="outline" onClick={onCancel}>انصراف</Button></div>
    </fieldset>
  </form>;
}

function EvidenceForm({ shipmentId, delivery, onSaved }: { shipmentId: string; delivery: DeliveryFact; onSaved: () => Promise<void> }) {
  const [file, setFile] = useState<File>();
  const [visibility, setVisibility] = useState("INTERNAL");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const command = useRef<{ file: File; visibility: string; key: string } | undefined>(undefined);
  return <details className="rounded-lg border p-3"><summary className="cursor-pointer text-sm">افزودن مدرک تحویل</summary>
    <form className="mt-3 space-y-3" onSubmit={async event => {
      event.preventDefault(); if (!file) return;
      if (command.current?.file !== file || command.current.visibility !== visibility) command.current = { file, visibility, key: crypto.randomUUID() };
      const form = new FormData(); form.set("file", file); form.set("title", "مدرک تحویل");
      form.set("context_type", "DELIVERY"); form.set("context_target_public_id", delivery.public_id); form.set("visibility", visibility);
      setPending(true); setError("");
      try { await uploadShipmentDocument(shipmentId, form, command.current.key); command.current = undefined; await onSaved(); }
      catch (caught) { setError(message(caught)); } finally { setPending(false); }
    }}>
      {error && <p role="alert" className="text-red-700">{error}</p>}
      <fieldset disabled={pending} className="space-y-3">
        <Input aria-label="فایل مدرک تحویل" required type="file" accept=".pdf,.png,.jpg,.jpeg,.webp" onChange={e => setFile(e.target.files?.[0])} />
        <label className="block text-sm">دسترسی مدرک<select aria-label="دسترسی مدرک تحویل" className="mt-1 w-full rounded border p-2" value={visibility} onChange={e => setVisibility(e.target.value)}><option value="INTERNAL">فقط داخلی</option><option value="CARGO_OWNER">مشتری صاحب کالا، پس از احراز مجوز هویتی</option></select></label>
        <Button type="submit" variant="outline">{pending ? "در حال بارگذاری…" : "ثبت مدرک تحویل"}</Button>
      </fieldset>
    </form>
  </details>;
}

export default function DeliverySection({ shipmentId }: { shipmentId: string }) {
  const [data, setData] = useState<DeliveryList>();
  const [page, setPage] = useState(1);
  const [form, setForm] = useState<{ cargo: DeliveryCargo; initial?: DeliveryFact } | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const generation = useRef(0);
  const command = useRef<{ body: string; key: string } | undefined>(undefined);
  const load = useCallback(async () => {
    const current = ++generation.current;
    try { setError(""); const result = await listDeliveries(shipmentId, page); if (current === generation.current) setData(result.data); }
    catch (caught) { if (current === generation.current) { setData(undefined); setError(message(caught)); } }
  }, [shipmentId, page]);
  useEffect(() => { setData(undefined); void load(); return () => { generation.current++; }; }, [load]);
  const submit = async (draft: DeliveryDraft) => {
    const body = JSON.stringify(draft);
    if (command.current?.body !== body) command.current = { body, key: crypto.randomUUID() };
    try {
      setPending(true); setError(""); setNotice("");
      await recordDelivery(shipmentId, draft, command.current.key);
      command.current = undefined; setForm(null);
      setNotice(draft.corrects_public_id ? "اصلاح ثبت شد؛ اصل تحویل در سابقه محفوظ است." : "تحویل ثبت شد؛ وضعیت پرونده حمل تغییری نکرد.");
      await load();
    } catch (caught) { setError(message(caught)); } finally { setPending(false); }
  };
  const renderFact = (item: DeliveryFact) => {
    const cargo = data?.cargo.find(c => c.public_id === item.cargo_public_id);
    return <article key={item.public_id} data-delivery-id={item.public_id} className="space-y-2 rounded-xl border p-3">
      <div className="flex flex-wrap justify-between gap-2"><h5 className="font-semibold">{cargo?.label} · {cargo?.customer_label}</h5><span className="text-xs">{item.status === "SUPERSEDED" ? "اصلاح‌شده؛ محفوظ در سابقه" : item.is_correction ? "نسخه اصلاحی جاری" : "تحویل جاری"}</span></div>
      <p>{number(item.quantity)} {item.uom_symbol} · مقصد: {item.destination_text}</p>
      <p className="text-xs text-slate-600">وقوع: {time(item.occurred_at)}<br />ثبت: {time(item.recorded_at)} · {item.actor_label}</p>
      {item.reason && <p className="text-sm">دلیل اصلاح: {item.reason}</p>}
      {item.evidence.length > 0 ? <ul className="space-y-1">{item.evidence.map(doc => <li key={doc.public_id} className="flex flex-wrap items-center gap-2 text-sm"><span className="break-all">{doc.filename} · نسخه {doc.version}</span>{doc.status === "active" ? <Button variant="outline" size="sm" onClick={async () => { try { await downloadShipmentDocument(shipmentId, doc.public_id, doc.filename); } catch (caught) { setError(message(caught)); } }}>دریافت مدرک</Button> : <span>نسخه پیشین؛ محفوظ در سابقه</span>}</li>)}</ul> : <p className="text-xs text-slate-600">مدرک تحویل ثبت نشده است.</p>}
      {data?.can_manage && item.status === "CURRENT" && cargo && <><Button variant="outline" disabled={pending || !cargo.can_record} onClick={() => setForm({ cargo, initial: item })}>اصلاح تحویل</Button><EvidenceForm key={`${item.public_id}-${item.evidence.length}`} shipmentId={shipmentId} delivery={item} onSaved={load} /></>}
    </article>;
  };
  return <section aria-label="تحویل کالاها" className="space-y-4" dir="rtl">
    <p className="text-sm text-slate-600">هر تحویل برای یک کالا ثبت می‌شود. تحویل یک مشتری، کالاهای دیگر یا پرونده حمل را خودکار نمی‌بندد.</p>
    {error && <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}<Button variant="outline" className="mr-2" onClick={() => void load()}>تازه‌سازی تحویل‌ها</Button></div>}
    {notice && <p role="status" className="rounded-lg bg-green-50 p-3 text-sm">{notice}</p>}
    {!data && !error && <p role="status">در حال دریافت تحویل‌ها…</p>}
    {data && <>
      {!data.can_manage && <p className="text-sm text-slate-600">نمای فقط‌خواندنی؛ ثبت و اصلاح با کارشناس مسئول است.</p>}
      {data.cargo.length === 0 && <p>ابتدا کالاهای پرونده حمل را ثبت کنید.</p>}
      <div className="grid gap-3 lg:grid-cols-2">{data.cargo.map(cargo => <article key={cargo.public_id} data-delivery-cargo={cargo.public_id} className="space-y-3 rounded-xl border bg-white p-3">
        <h4 className="font-semibold">{cargo.label} · {cargo.customer_label}</h4>
        <dl className="grid grid-cols-3 gap-2 text-sm"><div><dt className="text-slate-600">واقعی شناخته‌شده</dt><dd>{number(cargo.known_actual)} {cargo.uom_symbol}</dd></div><div><dt className="text-slate-600">تحویل‌شده</dt><dd>{number(cargo.delivered)} {cargo.uom_symbol}</dd></div><div><dt className="text-slate-600">مانده</dt><dd>{number(cargo.remaining)} {cargo.uom_symbol}</dd></div></dl>
        {!cargo.has_delivery && <p className="text-sm text-slate-600">هنوز تحویلی ثبت نشده است.</p>}
        {cargo.known_actual === null && <p className="text-sm text-amber-800">مقدار واقعی نامشخص است؛ مانده قابل محاسبه نیست.</p>}
        {cargo.excess !== null && Number(cargo.excess) > 0 && <p role="alert" className="rounded-lg bg-amber-50 p-3 text-amber-900">{number(cargo.excess)} {cargo.uom_symbol} بیش از مقدار واقعی شناخته‌شده تحویل ثبت شده است. مقدار کالا یا سابقه تحویل را بررسی کنید.</p>}
        {cargo.has_delivery && cargo.remaining !== null && Number(cargo.remaining) > 0 && <p className="text-sm text-amber-800">{number(cargo.remaining)} {cargo.uom_symbol} هنوز تحویل ثبت‌شده ندارد؛ این اختلاف به معنی گم‌شدن یا بسته‌شدن نیست.</p>}
        {data.can_manage && (cargo.can_record ? <Button variant="outline" className="h-auto min-h-10 whitespace-normal text-right" disabled={pending} onClick={() => { setForm({ cargo }); setNotice(""); }}>تحویل تازه برای {cargo.label}</Button> : <p className="text-sm text-amber-800">برای ثبت تحویل، ابتدا مشتری واقعی این کالا را مشخص کنید.</p>)}
      </article>)}</div>
      {data.can_manage && form && <DeliveryForm key={form.initial?.public_id || form.cargo.public_id} cargo={form.cargo} initial={form.initial} pending={pending} onSubmit={submit} onCancel={() => setForm(null)} />}
      <h4 className="font-semibold">تحویل‌های جاری</h4>
      {data.items.length === 0 && <p className="rounded-lg border border-dashed p-4 text-sm">هنوز تحویلی ثبت نشده است.</p>}
      {data.items.filter(item => item.status === "CURRENT").map(renderFact)}
      {data.items.some(item => item.status === "SUPERSEDED") && <details className="rounded-xl border p-3"><summary className="cursor-pointer font-medium">سابقه تحویل‌های اصلاح‌شده</summary><div className="mt-3 space-y-3">{data.items.filter(item => item.status === "SUPERSEDED").map(renderFact)}</div></details>}
      {data.total > 20 && <nav aria-label="صفحه‌های تحویل" className="flex items-center gap-3"><Button variant="outline" disabled={page === 1 || pending} onClick={() => { setForm(null); setPage(page - 1); }}>قبلی</Button><span>صفحه {page}</span><Button variant="outline" disabled={page * 20 >= data.total || pending} onClick={() => { setForm(null); setPage(page + 1); }}>بعدی</Button></nav>}
    </>}
  </section>;
}
