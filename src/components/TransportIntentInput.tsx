import { Button } from "@/components/ui/button";
import type { TransportIntent, TransportIntentOption } from "@/lib/api";

export function TransportIntentInput({ value, onChange, options, classification, onClassificationChange }: {
  value: TransportIntent | null; onChange: (value: TransportIntent | null) => void;
  options: TransportIntentOption[]; classification: string; onClassificationChange: (value: string) => void;
}) {
  const steps = value?.steps ?? [];
  return <fieldset className="space-y-3 min-w-0">
    <legend className="text-sm font-medium">توالی خواسته حمل</legend>
    <p className="text-xs text-muted-foreground">این انتخاب خواسته اولیه شماست و تأیید مسیر اجرایی یا امکان حمل نیست.</p>
    <label className="block text-sm">نوع حمل
      <select aria-label="نوع حمل" className="block w-full rounded border bg-background p-2" value={classification} onChange={e => onClassificationChange(e.target.value)}>
        <option value="single-mode">تک‌روش</option><option value="combined">ترکیبی</option>
      </select>
    </label>
    <ol className="space-y-2">
      {steps.map((step, index) => <li key={index} className="flex flex-wrap gap-2 items-center">
        <span>{index + 1}.</span>
        <select aria-label={`روش مرحله ${index + 1}`} className="min-w-0 flex-1 rounded border bg-background p-2" value={step.mode} onChange={e => onChange({ version: 1, steps: steps.map((item, i) => i === index ? { mode: e.target.value } : item) })}>
          {!options.some(item => item.mode === step.mode) && <option value={step.mode}>{step.mode} (غیرفعال)</option>}
          {options.map(item => <option key={item.mode} value={item.mode}>{item.label}</option>)}
        </select>
        <Button type="button" variant="outline" size="sm" aria-label={`حذف مرحله ${index + 1}`} onClick={() => onChange({ version: 1, steps: steps.filter((_, i) => i !== index) })}>حذف</Button>
      </li>)}
    </ol>
    <Button type="button" variant="outline" disabled={!options.length} onClick={() => onChange({ version: 1, steps: [...steps, { mode: options[0].mode }] })}>افزودن مرحله حمل</Button>
    {!options.length && <p role="status">روش حمل فعالی برای انتخاب موجود نیست.</p>}
  </fieldset>;
}
