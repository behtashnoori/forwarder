import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, createExecutionReason, listExecutionReasons, updateExecutionReason, type ExecutionReason } from "@/lib/api";

const safeError = (caught: unknown) => caught instanceof ApiError
  ? caught.status === 403 ? "شما مجوز مدیریت دلایل عملیاتی را ندارید." : caught.status === 409 ? "کد دلیل تکراری است یا اطلاعات تغییر کرده است." : "اطلاعات دلیل را بررسی کنید و دوباره تلاش کنید."
  : "انجام این کار ممکن نشد. دوباره تلاش کنید.";

export default function OperationalReasonsAdminTab() {
  const [kind, setKind] = useState<"delay" | "exception">("delay");
  const [rows, setRows] = useState<ExecutionReason[]>([]);
  const [form, setForm] = useState({ immutable_code: "", fa_name: "", en_name: "", definition: "" });
  const [drafts, setDrafts] = useState<Record<string, { fa_name: string; en_name: string; definition: string }>>({});
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try { setRows((await listExecutionReasons(kind)).data); setError(""); }
    catch (caught) { setError(safeError(caught)); }
  }, [kind]);
  useEffect(() => { void load(); }, [load]);
  const create = async () => {
    try { await createExecutionReason(kind, form); setForm({ immutable_code: "", fa_name: "", en_name: "", definition: "" }); await load(); }
    catch (caught) { setError(safeError(caught)); }
  };
  const save = async (row: ExecutionReason) => {
    try { await updateExecutionReason(kind, row, drafts[row.public_id] || { fa_name: row.fa_name, en_name: row.en_name, definition: row.definition || "" }); await load(); }
    catch (caught) { setError(safeError(caught)); }
  };
  return <div className="space-y-4">
    <div className="flex gap-2"><Button variant={kind === "delay" ? "default" : "outline"} onClick={() => setKind("delay")}>Delay reasons</Button><Button variant={kind === "exception" ? "default" : "outline"} onClick={() => setKind("exception")}>Exception reasons</Button></div>
    {error && <p role="alert">{error}</p>}
    <div className="grid gap-2 md:grid-cols-4"><Input aria-label="Immutable code" placeholder="Immutable code" value={form.immutable_code} onChange={event => setForm({ ...form, immutable_code: event.target.value })}/><Input aria-label="Persian name" placeholder="Persian name" value={form.fa_name} onChange={event => setForm({ ...form, fa_name: event.target.value })}/><Input aria-label="English name" placeholder="English name" value={form.en_name} onChange={event => setForm({ ...form, en_name: event.target.value })}/><Button disabled={!form.immutable_code || !form.fa_name || !form.en_name} onClick={() => void create()}>Create reason</Button></div>
    {!rows.length && <p>No reasons exist. Create the first governed reason above; deployment does not seed this catalog.</p>}
    <div className="grid gap-3 md:grid-cols-2">{rows.map(row => {
      const draft = drafts[row.public_id] || { fa_name: row.fa_name, en_name: row.en_name, definition: row.definition || "" };
      return <article className="min-w-0 space-y-2 rounded border p-3" key={row.public_id}>
        <strong className="break-all">{row.immutable_code}</strong>
        <label className="block">نام فارسی<Input value={draft.fa_name} onChange={event => setDrafts(previous => ({ ...previous, [row.public_id]: { ...draft, fa_name: event.target.value } }))}/></label>
        <label className="block">نام انگلیسی<Input value={draft.en_name} onChange={event => setDrafts(previous => ({ ...previous, [row.public_id]: { ...draft, en_name: event.target.value } }))}/></label>
        <label className="block">تعریف<Input value={draft.definition} onChange={event => setDrafts(previous => ({ ...previous, [row.public_id]: { ...draft, definition: event.target.value } }))}/></label>
        <div className="flex flex-wrap gap-2"><Button disabled={!draft.fa_name.trim() || !draft.en_name.trim()} onClick={() => void save(row)}>ذخیره</Button><Button variant="outline" onClick={() => void updateExecutionReason(kind, row, { is_active: !row.is_active }).then(load).catch(caught => setError(safeError(caught)))}>{row.is_active ? "غیرفعال‌سازی" : "فعال‌سازی"}</Button></div>
      </article>;
    })}</div>
  </div>;
}
