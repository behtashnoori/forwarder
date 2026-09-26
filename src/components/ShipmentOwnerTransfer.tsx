import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { getOwnerCandidates, getOwnerTransfers, transferOwner, type OwnerTransferView, type TransferPerson } from "@/lib/ownerTransferApi";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import { OWNER_CHANGED_EVENT, useCurrentAuthorityRefresh } from "@/hooks/useCurrentAuthorityRefresh";

const when = (value: string) => formatDualCalendarInstant(value, "fa", {timeZoneName: "short"});

export default function ShipmentOwnerTransfer({shipment}: {shipment: string}) {
  const [view, setView] = useState<OwnerTransferView | null>(null);
  const [page, setPage] = useState(1);
  const [candidates, setCandidates] = useState<TransferPerson[]>([]);
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [candidatePage, setCandidatePage] = useState(1);
  const [moreCandidates, setMoreCandidates] = useState(false);
  const [target, setTarget] = useState<TransferPerson | null>(null);
  const [reason, setReason] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const generation = useRef(0);
  const candidateGeneration = useRef(0);
  const abort = useRef<AbortController | null>(null);
  const command = useRef({signature: "", key: ""});
  const retire = useCallback(() => { generation.current++; candidateGeneration.current++; abort.current?.abort(); }, []);
  const load = useCallback(async () => {
    const current = ++generation.current;
    abort.current?.abort(); abort.current = new AbortController();
    setView(null); setConfirm(false); setCandidates([]); candidateGeneration.current++;
    try {
      const response = await getOwnerTransfers(shipment, page, abort.current.signal);
      if (generation.current === current) setView(response.data);
    } catch {
      if (generation.current === current) setError("دریافت مسئول فعلی ممکن نشد؛ دسترسی و وضعیت پرونده را دوباره بررسی کنید.");
    }
  }, [shipment, page]);
  useEffect(() => { void load(); return retire; }, [load, retire]);
  useCurrentAuthorityRefresh(load, retire);
  useEffect(() => {
    if (!view?.capabilities.TRANSFER_OWNER || !view.available) return;
    const current = ++candidateGeneration.current;
    const controller = new AbortController();
    void getOwnerCandidates(shipment, appliedSearch, candidatePage, controller.signal).then(response => {
      if (candidateGeneration.current === current) { setCandidates(response.data.candidates); setMoreCandidates(response.data.has_more); }
    }).catch(() => { if (candidateGeneration.current === current) { setCandidates([]); setError("دریافت کارشناسان مجاز ممکن نشد."); } });
    return () => { candidateGeneration.current++; controller.abort(); };
  }, [view, shipment, appliedSearch, candidatePage]);

  const submit = async () => {
    if (!view || !target || !reason.trim() || !confirm || busy) return;
    const payload = {expected_owner_id: view.current_owner.id, target_owner_id: target.id, expected_version: view.shipment_version, reason: reason.trim()};
    const signature = JSON.stringify([shipment, payload]);
    if (command.current.signature !== signature) command.current = {signature, key: crypto.randomUUID()};
    const current = generation.current;
    setBusy(true); setError(""); setNotice("");
    try {
      await transferOwner(shipment, payload, command.current.key);
      if (current === generation.current) {
        setReason(""); setTarget(null); setConfirm(false); setNotice("انتقال مسئول ثبت شد. مسئولیت کارهای قبلی حفظ شده است.");
      }
      window.dispatchEvent(new Event(OWNER_CHANGED_EVENT));
    } catch (caught) {
      if (current !== generation.current) return;
      setError(caught instanceof ApiError && caught.status === 409
        ? "مسئول یا اطلاعات پرونده تغییر کرده است. وضعیت تازه را بررسی و دوباره تأیید کنید."
        : "انتقال ثبت نشد؛ مجوز مدیر، کارشناس انتخاب‌شده و وضعیت پرونده را بررسی کنید.");
      await load();
    } finally { setBusy(false); }
  };

  return <section aria-label="مسئول و سابقه انتقال" className="space-y-4 rounded-2xl border bg-white p-4 sm:p-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-xl font-bold">مسئول و سابقه انتقال</h2><Button variant="outline" disabled={busy} onClick={() => {setError(""); void load();}}>بررسی دوباره مسئول</Button></div>
    {error && <p role="alert" className="text-red-700">{error}</p>}
    {notice && <p role="status" className="text-emerald-800">{notice}</p>}
    {!view && !error && <p role="status">در حال دریافت مسئول فعلی…</p>}
    {view && <>
      <p>مسئول فعلی پرونده: <strong>{view.current_owner.display_name}</strong></p>
      <p className="text-sm text-slate-600">مسئول اولیه در سابقه: {view.initial_owner.display_name} · زمان آغاز مسئولیت ثبت نشده است.</p>
      {view.capabilities.TRANSFER_OWNER && (!view.available ? <p className="rounded-xl bg-amber-50 p-3">انتقال مسئول در این محیط آماده نیست.</p> : <div className="space-y-3 rounded-xl border p-4">
        <p>انتقال استثنایی با دلیل مدیر انجام می‌شود. مسئول درخواست، پیشنهاد قیمت و کارهای ثبت‌شده تغییر نمی‌کند.</p>
        <p className="rounded-xl bg-amber-50 p-3">کارهای بازِ مسئول فعلی در این پرونده: {view.old_owner_open_work_count ?? "نامشخص"}. این کارها با انتقال پرونده واگذار نمی‌شوند.</p>
        <form className="flex flex-wrap items-end gap-2" onSubmit={event => {event.preventDefault(); setAppliedSearch(search); setCandidatePage(1);}}>
          <label className="min-w-0 flex-1">جست‌وجوی کارشناس<input value={search} maxLength={100} onChange={event => setSearch(event.target.value)} className="mt-1 min-h-11 w-full rounded-lg border p-2" /></label>
          <Button type="submit" variant="outline" disabled={busy}>جست‌وجو</Button>
        </form>
        <label className="block">کارشناس مسئول جدید<select aria-label="کارشناس مسئول جدید" className="mt-1 min-h-11 w-full rounded-lg border p-2" value={target?.id ?? ""} disabled={busy} onChange={event => {setTarget(candidates.find(person => String(person.id) === event.target.value) ?? null); setConfirm(false);}}>
          <option value="">انتخاب کارشناس</option>{target && !candidates.some(person => person.id === target.id) && <option value={target.id}>{target.display_name}</option>}{candidates.map(person => <option value={person.id} key={person.id}>{person.display_name}</option>)}
        </select></label>
        <div className="flex flex-wrap gap-2"><Button variant="outline" disabled={busy || candidatePage === 1} onClick={() => setCandidatePage(value => value - 1)}>کارشناسان قبلی</Button><Button variant="outline" disabled={busy || !moreCandidates} onClick={() => setCandidatePage(value => value + 1)}>کارشناسان بعدی</Button></div>
        <label className="block">دلیل انتقال (الزامی)<textarea value={reason} disabled={busy} maxLength={1000} onChange={event => {setReason(event.target.value); setConfirm(false);}} className="mt-1 min-h-24 w-full rounded-lg border p-3" /></label>
        {!confirm ? <Button disabled={busy || !target || !reason.trim()} onClick={() => setConfirm(true)}>بررسی انتقال مسئول</Button> : <div role="group" aria-label="تأیید انتقال مسئول" className="space-y-3 rounded-xl bg-amber-50 p-3">
          <p>انتقال از {view.current_owner.display_name} به {target?.display_name} ثبت شود؟ دسترسی وابسته به مالکیت پرونده برای مسئول قبلی پایان می‌یابد. سابقه و مسئولیت کارهای قبلی حفظ می‌شود.</p>
          <p className="whitespace-pre-wrap break-words">دلیل: {reason.trim()}</p><div className="flex flex-wrap gap-2"><Button disabled={busy} onClick={() => void submit()}>تأیید نهایی انتقال</Button><Button variant="outline" disabled={busy} onClick={() => setConfirm(false)}>انصراف</Button></div>
        </div>}
      </div>)}
      <h3 className="font-bold">تاریخچه مسئولیت</h3>
      {!view.transfers.length && <p>انتقالی ثبت نشده است.</p>}
      <ol className="space-y-3">{view.transfers.map(row => <li key={row.public_id} className="space-y-2 rounded-xl border p-3">
        <p className="font-semibold">{row.old_owner.display_name} ← {row.new_owner.display_name}</p><p>ثبت‌کننده: {row.actor.display_name}</p><p className="whitespace-pre-wrap break-words">دلیل: {row.reason}</p>
        <p className="text-sm">زمان انتقال: {when(row.occurred_at)}</p><p className="text-sm">زمان ثبت: {when(row.recorded_at)}</p>
      </li>)}</ol>
      <div className="flex flex-wrap gap-2"><Button variant="outline" disabled={busy || page === 1} onClick={() => setPage(value => value - 1)}>تاریخچه قبلی</Button><span className="p-2">صفحه {page}</span><Button variant="outline" disabled={busy || !view.has_more} onClick={() => setPage(value => value + 1)}>تاریخچه بعدی</Button></div>
    </>}
  </section>;
}
