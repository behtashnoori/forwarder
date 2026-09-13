import { useState } from "react";
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
  const [error, setError] = useState("");
  return <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-end">
    <div className="min-w-0">
      <label className="mb-1 block text-sm" htmlFor={id}>زمان وقوع</label>
      <Input id={id} type="datetime-local" step="1" className="min-w-0 max-w-full" value={value} disabled={pending} onChange={(event) => { setValue(event.target.value); setError(""); }} aria-invalid={!!error} aria-describedby={error ? `${id}-error` : undefined} />
      {error && <p id={`${id}-error`} role="alert" className="text-sm text-red-700">{error}</p>}
    </div>
    <Button className="min-h-11" disabled={pending} onClick={() => {
      const iso = localDateTimeInputToUtc(value);
      if (!iso) { setError("زمان وقوع معتبر نیست؛ تاریخ و ساعت را بررسی کنید."); return; }
      onSubmit(iso);
    }}>{pending ? "در حال ثبت…" : action}</Button>
  </div>;
}
