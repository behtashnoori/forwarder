import { forwardRef, useId, type ComponentProps } from "react";
import { Input } from "@/components/ui/input";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import { localDateTimeInputToUtc } from "@/lib/localDateTime";

/** Local wall-clock input; the existing converter owns timezone semantics. */
const LocalizedDateTimeInput = forwardRef<HTMLInputElement, ComponentProps<typeof Input>>(
  ({ value, onChange, ...props }, ref) => {
    const hint = useId();
    const instant = typeof value === "string" ? localDateTimeInputToUtc(value) : null;
    return <div className="min-w-0 space-y-1">
      <Input {...props} ref={ref} type="text" dir="ltr" value={value}
        placeholder="سال-ماه-روز ساعت:دقیقه (میلادی)"
        aria-describedby={[props["aria-describedby"], hint].filter(Boolean).join(" ")}
        onChange={event => {
          event.target.value = event.target.value.replace(/[۰-۹]/g, char => String(char.charCodeAt(0)-1776))
            .replace(/[٠-٩]/g, char => String(char.charCodeAt(0)-1632)).replace(" ","T");
          const raw=event.target.value;
          event.target.setCustomValidity(raw&&!localDateTimeInputToUtc(raw)?"تاریخ و ساعت معتبر را با ترتیب سال-ماه-روز وارد کنید.":"");
          onChange?.(event);
        }}/>
      <p id={hint} className="text-xs leading-6 text-slate-600" dir="rtl">
        {instant ? formatDualCalendarInstant(instant,"fa-IR") : <>زمان محلی دستگاه؛ نمونه میلادی: <bdi dir="ltr">2026-10-01T09:30</bdi></>}
      </p>
    </div>;
  },
);
LocalizedDateTimeInput.displayName="LocalizedDateTimeInput";
export default LocalizedDateTimeInput;
