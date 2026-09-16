export const PRODUCT_DISPLAY_TIME_ZONE = "Asia/Tehran";

const PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
const ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩";

export function normalizeNumericInput(value: string): string {
  return value
    .replace(/[۰-۹]/g, (digit) => String(PERSIAN_DIGITS.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String(ARABIC_DIGITS.indexOf(digit)))
    .replace(/٬/g, ",")
    .replace(/٫/g, ".");
}

/** Parses a human-entered quantity without guessing ambiguous separators. */
export function parseQuantityInput(value: string): { canonical: string } | null {
  const normalized = normalizeNumericInput(value).trim();
  if (!normalized) return null;
  if (!/^(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?$/.test(normalized)) return null;
  return { canonical: normalized.replace(/,/g, "") };
}

export function formatQuantity(value: number | string | null | undefined, locale: string, fallback = "—"): string {
  if (value === null || value === undefined || value === "") return fallback;
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 20 }).format(numeric);
}

export function formatMoney(value: number | string | null | undefined, currency: string | null | undefined, locale: string, fallback = "—"): string {
  if (typeof value === "string" && /^-?(?:0|[1-9]\d*)(?:\.\d+)?$/.test(value)) {
    const [integer, fraction] = value.split(".");
    const parts = new Intl.NumberFormat(locale, { minimumFractionDigits: 1 }).formatToParts(0);
    const decimal = parts.find(part => part.type === "decimal")?.value || ".";
    const digits = new Intl.NumberFormat(locale, { useGrouping: false });
    const amount = new Intl.NumberFormat(locale).format(BigInt(integer)) + (fraction !== undefined
      ? decimal + fraction.replace(/\d/g, digit => digits.format(Number(digit))) : "");
    return `${amount} ${currency || ""}`.trim();
  }
  const amount = formatQuantity(value, locale, fallback);
  return amount === fallback ? fallback : `${amount} ${currency || ""}`.trim();
}

function parseInstant(value: string | null | undefined): Date | null {
  if (!value || !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value)) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatInstant(value: string | null | undefined, locale: string, options: Intl.DateTimeFormatOptions = {}, fallback = "—"): string {
  const instant = parseInstant(value);
  if (!instant) return fallback;
  const hasExplicitFields = Object.keys(options).length > 0;
  return new Intl.DateTimeFormat(locale, {
    ...(hasExplicitFields ? options : { dateStyle: "medium", timeStyle: "short" }),
    timeZone: PRODUCT_DISPLAY_TIME_ZONE,
  }).format(instant);
}

/** Persian and Gregorian renderings of the same explicit instant and display timezone. */
export function formatDualCalendarInstant(value: string | null | undefined, fallback = "—"): { primary: string; secondary: string } {
  return {
    primary: formatInstant(value, "fa-IR-u-ca-persian", undefined, fallback),
    secondary: formatInstant(value, "en-GB-u-ca-gregory", undefined, fallback),
  };
}
