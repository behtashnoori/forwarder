import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, createExecutionReason, listExecutionReasons, updateExecutionReason, type ExecutionReason } from "@/lib/api";

const safeError = (caught: unknown) => caught instanceof ApiError
  ? caught.status === 403 ? "شما مجوز مدیریت دلایل عملیاتی این سازمان را ندارید." : caught.status === 409 ? "اطلاعات هم‌زمان تغییر کرده است؛ فهرست را دوباره بررسی کنید." : "اطلاعات دلیل را بررسی کنید و دوباره تلاش کنید."
  : "انجام این کار ممکن نشد. دوباره تلاش کنید.";

export default function OperationalReasonsAdminTab() {
  const [kind, setKind] = useState<"delay" | "exception">("delay");
  const [rows, setRows] = useState<ExecutionReason[]>([]);
  const [form, setForm] = useState({ fa_name: "", en_name: "", definition: "", is_active: true });
  const [drafts, setDrafts] = useState<Record<string, { fa_name: string; en_name: string; definition: string }>>({});
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try { setRows((await listExecutionReasons(kind)).data); setError(""); }
    catch (caught) { setError(safeError(caught)); }
  }, [kind]);
  useEffect(() => { void load(); }, [load]);
  const create = async () => {
    try { await createExecutionReason(kind, form); setForm({ fa_name: "", en_name: "", definition: "", is_active: true }); await load(); }
    catch (caught) { setError(safeError(caught)); }
  };
  const save = async (row: ExecutionReason) => {
    try { await updateExecutionReason(kind, row, drafts[row.public_id] || { fa_name: row.fa_name, en_name: row.en_name === row.fa_name ? "" : row.en_name, definition: row.definition || "" }); await load(); }
    catch (caught) { setError(safeError(caught)); }
  };
  return <div className="space-y-4" dir="rtl">
    <Card><CardHeader><CardTitle>دلایل عملیاتی سازمان</CardTitle><p className="text-sm leading-6 text-muted-foreground">دلیل‌هایی را تعریف کنید که کارشناسان هنگام ثبت تأخیر یا مشکل عملیاتی انتخاب می‌کنند. کد داخلی به‌صورت خودکار ساخته می‌شود و غیرفعال‌سازی سابقه‌های قبلی را تغییر نمی‌دهد.</p></CardHeader></Card>
    <div className="flex flex-wrap gap-2"><Button variant={kind === "delay" ? "default" : "outline"} onClick={() => setKind("delay")}>دلایل تأخیر</Button><Button variant={kind === "exception" ? "default" : "outline"} onClick={() => setKind("exception")}>دلایل مشکل عملیاتی</Button></div>
    {error && <p role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-red-800">{error}</p>}
    <Card><CardHeader><CardTitle className="text-base">افزودن دلیل</CardTitle></CardHeader><CardContent className="grid gap-3 md:grid-cols-2">
      <label className="text-sm">عنوان دلیل *<Input aria-label="عنوان دلیل" placeholder="مثلاً تأخیر بارگیری" value={form.fa_name} onChange={event => setForm({ ...form, fa_name: event.target.value })}/></label>
      <label className="text-sm">توضیح<Input aria-label="توضیح دلیل" placeholder="توضیح کوتاه برای انتخاب درست" value={form.definition} onChange={event => setForm({ ...form, definition: event.target.value })}/></label>
      <label className="text-sm">نام انگلیسی (اختیاری)<Input aria-label="نام انگلیسی اختیاری" dir="ltr" value={form.en_name} onChange={event => setForm({ ...form, en_name: event.target.value })}/></label>
      <label className="flex items-center gap-2 self-end pb-2 text-sm"><input type="checkbox" checked={form.is_active} onChange={event => setForm({ ...form, is_active: event.target.checked })}/>فعال باشد</label>
      <Button className="md:col-span-2 md:w-fit" disabled={!form.fa_name.trim()} onClick={() => void create()}>افزودن دلیل</Button>
    </CardContent></Card>
    {!rows.length && <p className="rounded border border-dashed p-4 text-muted-foreground">هنوز دلیلی در این گروه ثبت نشده است. این فهرست برای سازمان‌ها به‌صورت خودکار مقداردهی نمی‌شود.</p>}
    <div className="grid gap-3 md:grid-cols-2">{rows.map(row => {
      const draft = drafts[row.public_id] || { fa_name: row.fa_name, en_name: row.en_name === row.fa_name ? "" : row.en_name, definition: row.definition || "" };
      return <article className="min-w-0 space-y-2 rounded border p-3" key={row.public_id}>
        <div className="flex items-center justify-between gap-2"><strong>{row.fa_name}</strong><span className={row.is_active ? "text-emerald-700" : "text-slate-500"}>{row.is_active ? "فعال" : "غیرفعال"}</span></div>
        <label className="block">عنوان دلیل<Input value={draft.fa_name} onChange={event => setDrafts(previous => ({ ...previous, [row.public_id]: { ...draft, fa_name: event.target.value } }))}/></label>
        <label className="block">نام انگلیسی (اختیاری)<Input dir="ltr" value={draft.en_name} onChange={event => setDrafts(previous => ({ ...previous, [row.public_id]: { ...draft, en_name: event.target.value } }))}/></label>
        <label className="block">توضیح<Input value={draft.definition} onChange={event => setDrafts(previous => ({ ...previous, [row.public_id]: { ...draft, definition: event.target.value } }))}/></label>
        <details className="text-xs text-slate-500"><summary className="cursor-pointer">جزئیات فنی</summary><code dir="ltr" className="mt-2 block break-all">{row.immutable_code}</code></details>
        <div className="flex flex-wrap gap-2"><Button disabled={!draft.fa_name.trim()} onClick={() => void save(row)}>ذخیره تغییرات</Button><Button variant="outline" onClick={() => void updateExecutionReason(kind, row, { is_active: !row.is_active }).then(load).catch(caught => setError(safeError(caught)))}>{row.is_active ? "غیرفعال کردن" : "فعال کردن"}</Button></div>
      </article>;
    })}</div>
  </div>;
}
