import { useCallback, useEffect, useRef, useState } from "react";
import { formatMoney } from "@/lib/presentation";
import "./quote-capability-customer.css";

type Call = (body?: unknown, key?: string) => Promise<CustomerView>;
type Fact = { id: string; sequence: number; response: string; response_received_at: string };
type CustomerView = { quote: { amount_exact: string; currency: string; note: string | null; valid_until: string;
  validity_timezone: string; content_revision: number; content_digest: string; response_version: number;
  customer_response: string | null; superseded: boolean }; history: Fact[]; can_respond: boolean };
const labels: Record<string, string> = { accepted: "پذیرفته شد", negotiation_requested: "درخواست مذاکره", declined: "رد شد" };

export default function CustomerPage({ call }: { call: Call }) {
  const [view, setView] = useState<CustomerView | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const pending = useRef<{ body: unknown; key: string; response: string } | null>(null);
  const load = useCallback(async () => {
    try { setView(await call()); }
    catch { setView(null); setMessage("این پیوند در حال حاضر قابل استفاده نیست. پیوند خصوصی معتبر را باز کنید."); }
  }, [call]);
  useEffect(() => { void load(); }, [load]);
  const choose = async (response: string) => {
    if (!view || busy) return;
    if (!pending.current || pending.current.response !== response) {
      pending.current = { key: crypto.randomUUID(), response, body: { response,
        expected_response_version: view.quote.response_version, content_revision: view.quote.content_revision,
        content_digest: view.quote.content_digest, reason: "CUSTOMER_DECISION" } };
    }
    setBusy(true); setMessage("");
    try { await call(pending.current.body, pending.current.key); pending.current = null; setMessage("پاسخ شما ثبت شد."); await load(); }
    catch (error) {
      if (error instanceof Error && error.message === "changed") {
        pending.current = null; setMessage("اطلاعات تغییر کرده است؛ پیشنهاد و پاسخ تازه را بررسی کنید."); await load();
      } else { setMessage("ثبت پاسخ تأیید نشد. برای تلاش دوباره، همان گزینه را انتخاب کنید."); }
    } finally { setBusy(false); }
  };
  return <main className="quote-customer"><header><p>فورواردر</p><h1>پیشنهاد و پاسخ شما</h1></header>
    {message && <p role="status" className="message">{message}</p>}
    {!view && !message && <p>در حال دریافت پیشنهاد…</p>}
    {view && <><section aria-label="پیشنهاد"><div className="amount" dir="ltr">{formatMoney(view.quote.amount_exact, view.quote.currency, "en-US")}</div>
      <p>اعتبار تا روز <span dir="ltr">{view.quote.valid_until}</span></p><p>مبنای اعتبار: <span dir="ltr">{view.quote.validity_timezone}</span></p>
      {view.quote.note && <p className="note">{view.quote.note}</p>}
      {view.quote.superseded && <p>این نسخه جایگزین شده است؛ فقط پیشنهاد و رسید همین نسخه نمایش داده می‌شود.</p>}
      <p>پاسخ فعلی: <strong>{view.quote.customer_response ? labels[view.quote.customer_response] : "هنوز پاسخی ثبت نشده است"}</strong></p>
      {view.can_respond ? <div className="choices"><button disabled={busy} onClick={() => void choose("accepted")}>پذیرش پیشنهاد</button>
        <button disabled={busy} onClick={() => void choose("negotiation_requested")}>درخواست مذاکره</button>
        <button disabled={busy} onClick={() => void choose("declined")}>رد پیشنهاد</button></div> : <p>امکان ثبت پاسخ تازه وجود ندارد؛ رسیدهای ثبت‌شده محفوظ‌اند.</p>}
    </section><section aria-label="رسیدهای پاسخ"><h2>رسیدهای پاسخ</h2>{view.history.length ? <ol>{view.history.map(fact => <li key={fact.id}>
      <strong>{labels[fact.response]}</strong><span> — {new Intl.DateTimeFormat("fa-IR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(fact.response_received_at))}</span>
      <div className="receipt" dir="ltr">{fact.id}</div></li>)}</ol> : <p>هنوز پاسخی ثبت نشده است.</p>}</section></>}
  </main>;
}
