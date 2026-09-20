import { parseLocalDate } from "@/lib/localDate";

export type DualCalendarDateStyle = "short" | "medium" | "long" | "full";

export type DualCalendarInstantOptions = {
  dateStyle?: DualCalendarDateStyle;
  fallback?: string;
  includeTime?: boolean;
  timeStyle?: "short" | "medium" | "long" | "full";
  timeZone?: string;
  timeZoneName?: "short" | "long" | "shortOffset" | "longOffset" | "shortGeneric" | "longGeneric";
};

function formatCalendarDate(
  date: Date,
  locale: string,
  calendar: "gregory" | "persian",
  dateStyle: DualCalendarDateStyle,
  timeZone?: string,
): string {
  return new Intl.DateTimeFormat(locale, {
    calendar,
    dateStyle,
    ...(timeZone ? { timeZone } : {}),
  }).format(date);
}

function joinDualDate(gregorian: string, jalali: string): string {
  return `${gregorian} (${jalali})`;
}

/**
 * Formats an API Local Date as two calendars without ever treating it as an Instant.
 * The UTC calendar container is an implementation detail and cannot shift the civil day.
 */
export function formatDualCalendarDate(
  value: string | null | undefined,
  locale: string,
  fallback = "—",
  dateStyle: DualCalendarDateStyle = "medium",
): string {
  const parts = parseLocalDate(value);
  if (!parts) return fallback;

  try {
    const civilDate = new Date(Date.UTC(parts.year, parts.month - 1, parts.day, 12));
    const gregorian = formatCalendarDate(civilDate, locale, "gregory", dateStyle, "UTC");
    const jalali = formatCalendarDate(civilDate, locale, "persian", dateStyle, "UTC");
    return joinDualDate(gregorian, jalali);
  } catch {
    return fallback;
  }
}

/**
 * Formats both calendars from one parsed Instant and appends the clock once.
 * Omitting timeZone intentionally preserves the surface's existing browser-zone policy.
 */
export function formatDualCalendarInstant(
  value: string | null | undefined,
  locale: string,
  options: DualCalendarInstantOptions = {},
): string {
  const fallback = options.fallback ?? "—";
  if (!value) return fallback;
  const instant = new Date(value);
  if (Number.isNaN(instant.getTime())) return fallback;

  try {
    const dateStyle = options.dateStyle ?? "medium";
    const gregorian = formatCalendarDate(instant, locale, "gregory", dateStyle, options.timeZone);
    const jalali = formatCalendarDate(instant, locale, "persian", dateStyle, options.timeZone);
    const dualDate = joinDualDate(gregorian, jalali);
    if (options.includeTime === false) return dualDate;

    const timeStyle = options.timeStyle ?? "short";
    const timeOptions: Intl.DateTimeFormatOptions = options.timeZoneName
      ? {
          hour: "numeric",
          minute: "2-digit",
          ...(timeStyle === "short" ? {} : { second: "2-digit" as const }),
          timeZoneName: options.timeZoneName,
        }
      : { timeStyle };
    const time = new Intl.DateTimeFormat(locale, {
      ...timeOptions,
      ...(options.timeZone ? { timeZone: options.timeZone } : {}),
    }).format(instant);
    return `${dualDate} · ${time}`;
  } catch {
    return fallback;
  }
}
