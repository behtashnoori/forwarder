import { forwardRef, useId, useState, type ChangeEvent, type ComponentProps } from "react";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import { localDateTimeInputToUtc } from "@/lib/localDateTime";

type CalendarMode = "jalali" | "gregorian";
type DateParts = { year: number; month: number; day: number };
type PickerProps = Omit<ComponentProps<"input">, "type"> & {
  includeTime?: boolean;
  type?: ComponentProps<"input">["type"];
};

const pad = (value: number) => String(value).padStart(2, "0");
const div = (a: number, b: number) => Math.trunc(a / b);

export const gregorianToJalali = (gy: number, gm: number, gd: number): DateParts => {
  const monthDays = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
  let jy: number;
  if (gy > 1600) { jy = 979; gy -= 1600; } else { jy = 0; gy -= 621; }
  const gy2 = gm > 2 ? gy + 1 : gy;
  let days = 365 * gy + div(gy2 + 3, 4) - div(gy2 + 99, 100) + div(gy2 + 399, 400)
    - 80 + gd + monthDays[gm - 1];
  jy += 33 * div(days, 12053); days %= 12053;
  jy += 4 * div(days, 1461); days %= 1461;
  if (days > 365) { jy += div(days - 1, 365); days = (days - 1) % 365; }
  return { year: jy, month: days < 186 ? 1 + div(days, 31) : 7 + div(days - 186, 30),
    day: 1 + (days < 186 ? days % 31 : (days - 186) % 30) };
};

export const jalaliToGregorian = (jy: number, jm: number, jd: number): DateParts => {
  jy += 1595;
  let days = -355668 + 365 * jy + div(jy, 33) * 8 + div((jy % 33) + 3, 4)
    + jd + (jm < 7 ? (jm - 1) * 31 : (jm - 7) * 30 + 186);
  let gy = 400 * div(days, 146097); days %= 146097;
  if (days > 36524) { gy += 100 * div(--days, 36524); days %= 36524; if (days >= 365) days++; }
  gy += 4 * div(days, 1461); days %= 1461;
  if (days > 365) { gy += div(days - 1, 365); days = (days - 1) % 365; }
  let gd = days + 1;
  const leap = (gy % 4 === 0 && gy % 100 !== 0) || gy % 400 === 0;
  const lengths = [0, 31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  let gm = 1;
  while (gm <= 12 && gd > lengths[gm]) { gd -= lengths[gm]; gm++; }
  return { year: gy, month: gm, day: gd };
};

const jalaliMonthNames = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور","مهر","آبان","آذر","دی","بهمن","اسفند"];
const gregorianMonthNames = ["ژانویه","فوریه","مارس","آوریل","مه","ژوئن","ژوئیه","اوت","سپتامبر","اکتبر","نوامبر","دسامبر"];
const parseValue = (value: string) => {
  const match = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2}))?)?$/.exec(value);
  if (!match) return null;
  const parts = { year:Number(match[1]), month:Number(match[2]), day:Number(match[3]),
    hour:Number(match[4] ?? 0), minute:Number(match[5] ?? 0), second:Number(match[6] ?? 0) };
  const test = new Date(parts.year, parts.month - 1, parts.day);
  return test.getFullYear() === parts.year && test.getMonth() === parts.month - 1
    && test.getDate() === parts.day && parts.hour < 24 && parts.minute < 60 && parts.second < 60 ? parts : null;
};
const jalaliMonthLength = (year:number, month:number) => {
  if (month <= 6) return 31;
  if (month <= 11) return 30;
  const start=jalaliToGregorian(year,1,1), next=jalaliToGregorian(year+1,1,1);
  return (Date.UTC(next.year,next.month-1,next.day)-Date.UTC(start.year,start.month-1,start.day))/86400000===366?30:29;
};

const LocalizedDateTimeInput = forwardRef<HTMLInputElement, PickerProps>(
  ({ value, onChange, includeTime = true, id, "aria-label": ariaLabel, required, disabled, ...props }, ref) => {
    const hint = useId();
    const [mode,setMode]=useState<CalendarMode>("jalali");
    const [open,setOpen]=useState(false);
    const raw=typeof value==="string"?value:"";
    const parsed=parseValue(raw);
    const today=new Date();
    const base={year:parsed?.year??today.getFullYear(),month:parsed?.month??today.getMonth()+1,
      day:parsed?.day??today.getDate(),hour:parsed?.hour??0,minute:parsed?.minute??0};
    const displayed=mode==="jalali"?gregorianToJalali(base.year,base.month,base.day):base;
    const dayLimit=mode==="jalali"?jalaliMonthLength(displayed.year,displayed.month)
      :new Date(displayed.year,displayed.month,0).getDate();
    const nowDisplayed=mode==="jalali"?gregorianToJalali(today.getFullYear(),today.getMonth()+1,today.getDate())
      :{year:today.getFullYear(),month:today.getMonth()+1,day:today.getDate()};
    const years=Array.from({length:41},(_,index)=>nowDisplayed.year-10+index);
    if(!years.includes(displayed.year)) years.push(displayed.year);
    years.sort((a,b)=>a-b);
    const emit=(next:DateParts,hour=base.hour,minute=base.minute)=>{
      const gregorian=mode==="jalali"?jalaliToGregorian(next.year,next.month,next.day):next;
      const nextValue=`${gregorian.year}-${pad(gregorian.month)}-${pad(gregorian.day)}${includeTime?`T${pad(hour)}:${pad(minute)}`:""}`;
      const target={value:nextValue} as HTMLInputElement;
      onChange?.({target,currentTarget:target} as ChangeEvent<HTMLInputElement>);
    };
    const setPart=(part:keyof DateParts,next:number)=>{
      const candidate={...displayed,[part]:next};
      const limit=mode==="jalali"?jalaliMonthLength(candidate.year,candidate.month)
        :new Date(candidate.year,candidate.month,0).getDate();
      emit({...candidate,day:Math.min(candidate.day,limit)});
    };
    const instant=includeTime&&parsed?localDateTimeInputToUtc(raw):null;
    const equivalent=mode==="jalali"
      ? `معادل میلادی: ${base.year}/${pad(base.month)}/${pad(base.day)}`
      : (()=>{const j=gregorianToJalali(base.year,base.month,base.day);return `معادل شمسی: ${j.year}/${pad(j.month)}/${pad(j.day)}`;})();
    return <div className="min-w-0 space-y-2">
      <input {...props} ref={ref} id={id} type="text" value={raw} onChange={onChange} aria-label={ariaLabel}
        placeholder={props.placeholder ?? (includeTime?"سال-ماه-روز ساعت:دقیقه (میلادی)":"سال-ماه-روز")}
        aria-describedby={[props["aria-describedby"],hint].filter(Boolean).join(" ")}
        required={required} disabled={disabled} tabIndex={-1} className="sr-only"/>
      <button type="button" disabled={disabled} onClick={()=>setOpen(value=>!value)}
        className="min-h-10 w-full rounded-md border bg-white px-3 text-right text-sm">
        {parsed?`${mode==="jalali"?gregorianToJalali(base.year,base.month,base.day).year:base.year}/${pad(mode==="jalali"?gregorianToJalali(base.year,base.month,base.day).month:base.month)}/${pad(mode==="jalali"?gregorianToJalali(base.year,base.month,base.day).day:base.day)}${includeTime?` · ${pad(base.hour)}:${pad(base.minute)}`:""}`:"انتخاب تاریخ"} · {mode==="jalali"?"شمسی":"میلادی"}
      </button>
      {open&&<><div className="inline-flex rounded-lg border bg-slate-50 p-1" aria-label="نوع تقویم">
        <button type="button" disabled={disabled} aria-pressed={mode==="jalali"} onClick={()=>setMode("jalali")}
          className={`rounded-md px-3 py-1 text-sm ${mode==="jalali"?"bg-white font-semibold shadow-sm":"text-slate-600"}`}>شمسی</button>
        <button type="button" disabled={disabled} aria-pressed={mode==="gregorian"} onClick={()=>setMode("gregorian")}
          className={`rounded-md px-3 py-1 text-sm ${mode==="gregorian"?"bg-white font-semibold shadow-sm":"text-slate-600"}`}>میلادی</button>
      </div>
      <div className={`grid gap-2 ${includeTime?"grid-cols-2 sm:grid-cols-5":"grid-cols-3"}`} dir="rtl">
        <label className="text-xs">سال<select aria-label={`${ariaLabel||"تاریخ"} سال`} disabled={disabled}
          className="mt-1 min-h-10 w-full rounded-md border bg-white px-2" value={displayed.year}
          onChange={event=>setPart("year",Number(event.target.value))}>{years.map(year=><option key={year} value={year}>{year.toLocaleString("fa-IR",{useGrouping:false})}</option>)}</select></label>
        <label className="text-xs">ماه<select aria-label={`${ariaLabel||"تاریخ"} ماه`} disabled={disabled}
          className="mt-1 min-h-10 w-full rounded-md border bg-white px-2" value={displayed.month}
          onChange={event=>setPart("month",Number(event.target.value))}>{(mode==="jalali"?jalaliMonthNames:gregorianMonthNames).map((name,index)=><option key={name} value={index+1}>{name}</option>)}</select></label>
        <label className="text-xs">روز<select aria-label={`${ariaLabel||"تاریخ"} روز`} disabled={disabled}
          className="mt-1 min-h-10 w-full rounded-md border bg-white px-2" value={Math.min(displayed.day,dayLimit)}
          onChange={event=>setPart("day",Number(event.target.value))}>{Array.from({length:dayLimit},(_,index)=>index+1).map(day=><option key={day} value={day}>{day.toLocaleString("fa-IR")}</option>)}</select></label>
        {includeTime&&<><label className="text-xs">ساعت<select aria-label={`${ariaLabel||"زمان"} ساعت`} disabled={disabled}
          className="mt-1 min-h-10 w-full rounded-md border bg-white px-2" value={base.hour}
          onChange={event=>emit(displayed,Number(event.target.value),base.minute)}>{Array.from({length:24},(_,hour)=>hour).map(hour=><option key={hour} value={hour}>{pad(hour)}</option>)}</select></label>
        <label className="text-xs">دقیقه<select aria-label={`${ariaLabel||"زمان"} دقیقه`} disabled={disabled}
          className="mt-1 min-h-10 w-full rounded-md border bg-white px-2" value={base.minute}
          onChange={event=>emit(displayed,base.hour,Number(event.target.value))}>{Array.from({length:60},(_,minute)=>minute).map(minute=><option key={minute} value={minute}>{pad(minute)}</option>)}</select></label></>}
      </div>
      </>}
      <p id={hint} className="text-xs leading-6 text-slate-600" dir="rtl">
        {parsed?<>{equivalent}{instant?<> · {formatDualCalendarInstant(instant,"fa-IR")}</>:null}</>:"با انتخاب هر بخش، یک تاریخ واحد در هر دو تقویم ثبت می‌شود."}
      </p>
    </div>;
  },
);
LocalizedDateTimeInput.displayName="LocalizedDateTimeInput";
export const LocalizedDateInput=forwardRef<HTMLInputElement,Omit<PickerProps,"includeTime">>((props,ref)=>
  <LocalizedDateTimeInput {...props} ref={ref} includeTime={false}/>);
LocalizedDateInput.displayName="LocalizedDateInput";
export default LocalizedDateTimeInput;
