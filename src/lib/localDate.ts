export type LocalDateParts = { year: number; month: number; day: number };

const LOCAL_DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;

export function parseLocalDate(value: string | null | undefined): LocalDateParts | null {
  if (!value) return null;
  const match = LOCAL_DATE_PATTERN.exec(value);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const leapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const daysInMonth = [31, leapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1];
  if (!daysInMonth || day < 1 || day > daysInMonth) return null;
  return { year, month, day };
}

export function formatLocalDate(value: string | null | undefined, locale: string, fallback = "—"): string {
  const parts = parseLocalDate(value);
  if (!parts) return fallback;
  // Local calendar fields only; the API value is never parsed or serialized as an instant.
  const calendarValue = new Date(parts.year, parts.month - 1, parts.day, 12);
  return new Intl.DateTimeFormat(locale, {
    year: "numeric", month: "short", day: "numeric",
  }).format(calendarValue);
}

export function isLocalDateBeforeToday(value: string | null | undefined): boolean {
  const parts = parseLocalDate(value);
  if (!parts) return false;
  const today = new Date();
  const comparable = parts.year * 10_000 + parts.month * 100 + parts.day;
  const current = today.getFullYear() * 10_000 + (today.getMonth() + 1) * 100 + today.getDate();
  return comparable < current;
}
