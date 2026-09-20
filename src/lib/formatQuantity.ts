export type BusinessNumericValue = string | number | bigint | null | undefined;

export type BusinessNumberFormatOptions = {
  locale?: string;
  missing?: string;
  invalid?: string;
  trimTrailingZeros?: boolean;
};

type LocaleNumberProfile = {
  digits: string[];
  group: string;
  decimal: string;
  minus: string;
  plus: string;
  primaryGroupSize: number;
  secondaryGroupSize: number;
};

const localeProfiles = new Map<string, LocaleNumberProfile>();

const localeProfile = (locale: string): LocaleNumberProfile => {
  const cached = localeProfiles.get(locale);
  if (cached) return cached;

  const plain = new Intl.NumberFormat(locale, { useGrouping: false });
  const groupedParts = new Intl.NumberFormat(locale).formatToParts(123456789012345);
  const integerGroups = groupedParts.filter((part) => part.type === "integer").map((part) => part.value.length);
  const signParts = new Intl.NumberFormat(locale, { signDisplay: "always" }).formatToParts(-1);
  const profile = {
    digits: Array.from({ length: 10 }, (_, digit) => plain.format(digit)),
    group: groupedParts.find((part) => part.type === "group")?.value ?? ",",
    decimal: new Intl.NumberFormat(locale).formatToParts(1.1).find((part) => part.type === "decimal")?.value ?? ".",
    minus: signParts.find((part) => part.type === "minusSign")?.value ?? "-",
    plus: new Intl.NumberFormat(locale, { signDisplay: "always" }).formatToParts(1).find((part) => part.type === "plusSign")?.value ?? "+",
    primaryGroupSize: integerGroups.at(-1) ?? 3,
    secondaryGroupSize: integerGroups.at(-2) ?? integerGroups.at(-1) ?? 3,
  };
  localeProfiles.set(locale, profile);
  return profile;
};

const expandExponential = (value: string): string => {
  const match = /^([+-]?)(\d+)(?:\.(\d*))?[eE]([+-]?\d+)$/.exec(value);
  if (!match) return value;
  const [, sign, integer, fraction = "", exponentText] = match;
  const digits = `${integer}${fraction}`;
  const decimalPosition = integer.length + Number(exponentText);
  if (decimalPosition <= 0) return `${sign}0.${"0".repeat(-decimalPosition)}${digits}`;
  if (decimalPosition >= digits.length) return `${sign}${digits}${"0".repeat(decimalPosition - digits.length)}`;
  return `${sign}${digits.slice(0, decimalPosition)}.${digits.slice(decimalPosition)}`;
};

const canonicalDecimal = (value: Exclude<BusinessNumericValue, null | undefined>): string | null => {
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return null;
    return expandExponential(String(value));
  }
  const candidate = String(value).trim();
  if (!/^[+-]?\d+(?:\.\d+)?$/.test(candidate)) return null;
  return candidate;
};

const groupInteger = (integer: string, profile: LocaleNumberProfile): string => {
  const groups: string[] = [];
  let cursor = integer.length;
  let groupSize = profile.primaryGroupSize;
  while (cursor > groupSize) {
    groups.unshift(integer.slice(cursor - groupSize, cursor));
    cursor -= groupSize;
    groupSize = profile.secondaryGroupSize;
  }
  groups.unshift(integer.slice(0, cursor));
  return groups.join(profile.group);
};

/**
 * Display-only formatting for fields already known by their caller to be a
 * business quantity or amount. Never use this for identifiers or references.
 */
export const formatBusinessNumber = (
  value: BusinessNumericValue,
  options: BusinessNumberFormatOptions = {},
): string => {
  const { locale = "en-US", missing = "—", invalid = missing, trimTrailingZeros = false } = options;
  if (value === null || value === undefined || value === "") return missing;
  const canonical = canonicalDecimal(value);
  if (!canonical) return invalid;

  const profile = localeProfile(locale);
  const sign = canonical.startsWith("-") ? profile.minus : canonical.startsWith("+") ? profile.plus : "";
  const unsigned = canonical.replace(/^[+-]/, "");
  const [rawInteger, rawFraction] = unsigned.split(".");
  const integer = rawInteger.replace(/^0+(?=\d)/, "") || "0";
  const fraction = trimTrailingZeros ? rawFraction?.replace(/0+$/, "") : rawFraction;
  const ascii = `${sign}${groupInteger(integer, profile)}${fraction ? `${profile.decimal}${fraction}` : ""}`;
  return ascii.replace(/\d/g, (digit) => profile.digits[Number(digit)]);
};

/** Golden cargo display: trim storage scale, preserve significant decimals. */
export const formatQuantity = (
  value: BusinessNumericValue,
  locale = "en-US",
  missing = "0",
): string => formatBusinessNumber(value, { locale, missing, invalid: "—", trimTrailingZeros: true });

/** Money presentation only; the currency token and fractional digits are unchanged. */
export const formatMoney = (
  value: BusinessNumericValue,
  currency: string | null | undefined,
  locale = "en-US",
  missing = "—",
): string => {
  const amount = formatBusinessNumber(value, { locale, missing });
  return amount === missing ? missing : `${amount}${currency ? ` ${currency}` : ""}`;
};
