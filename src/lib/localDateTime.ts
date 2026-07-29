const DATE_TIME_LOCAL_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,3})?)?$/;

/** Format an instant as wall-clock fields suitable for a datetime-local input. */
export function toLocalDateTimeInputValue(date: Date): string {
  if (Number.isNaN(date.getTime())) return "";
  const offsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

/** Interpret datetime-local wall-clock fields once, in the browser timezone. */
export function localDateTimeInputToUtc(value: string): string | null {
  if (!DATE_TIME_LOCAL_PATTERN.test(value)) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  const [datePart, timePart] = value.split("T");
  const [year, month, day] = datePart.split("-").map(Number);
  const [hour, minute, second = 0] = timePart.split(":").map(Number);
  if (parsed.getFullYear() !== year || parsed.getMonth() !== month - 1 ||
      parsed.getDate() !== day || parsed.getHours() !== hour ||
      parsed.getMinutes() !== minute || parsed.getSeconds() !== Math.trunc(second)) return null;
  return parsed.toISOString();
}
