import LocalizedDateTimeInput from "@/components/LocalizedDateTimeInput";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { localDateTimeInputToUtc } from "@/lib/localDateTime";

const localOccurrenceNow = () => {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 19);
};

export default function OccurrenceTimeAction({ id, action, pending, onSubmit }: {
  id: string;
  action: string;
  pending: boolean;
  onSubmit: (occurredAt: string) => void;
}) {
  const [value, setValue] = useState(localOccurrenceNow);
  const previousAction = useRef(action);
  const submitted = useRef(false);
  useEffect(() => {
    if (previousAction.current !== action) { setValue(""); setError(""); previousAction.current = action; }
    submitted.current = false;
  }, [action, pending]);
  const [error, setError] = useState("");
  return <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-end">
    <div className="min-w-0">
      <label className="mb-1 block text-sm" htmlFor={id}>زمان وقوع</label>
      <LocalizedDateTimeInput id={id} type="datetime-local" step="1" dir="ltr" className="min-w-0 max-w-full" value={value} disabled={pending} onChange={(event) => { setValue(event.target.value); setError(""); }} aria-invalid={!!error} aria-describedby={error ? `${id}-error` : `${id}-hint`} />
      <p id={`${id}-hint`} className="mt-1 text-xs text-slate-500">تاریخ و ساعت بر پایهٔ زمان محلی مرورگر است.</p>
      {error && <p id={`${id}-error`} role="alert" className="text-sm text-red-700">{error}</p>}
    </div>
    <Button className="min-h-11" disabled={pending} onClick={() => {
      if (pending || submitted.current) return;
      const iso = localDateTimeInputToUtc(value);
      if (!iso) { setError("زمان وقوع معتبر نیست؛ تاریخ و ساعت را بررسی کنید."); return; }
      submitted.current = true;
      onSubmit(iso);
    }}>{pending ? "در حال ثبت…" : action}</Button>
  </div>;
}
