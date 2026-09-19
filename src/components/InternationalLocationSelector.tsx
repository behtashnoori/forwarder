import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  fetchInternationalCityPage,
  type InternationalCity,
} from "@/lib/api";

const PAGE_SIZE = 50;

/** Bounded, server-searched selector for the governed worldwide catalog. */
export function InternationalLocationSelector({
  countryId,
  locale,
  side,
  selected,
  onChange,
  fieldError,
}: {
  countryId: string;
  locale: "fa" | "en";
  side: "origin" | "destination" | "location";
  selected: InternationalCity | null;
  onChange: (city: InternationalCity | null) => void;
  fieldError?: string;
}) {
  const fa = locale === "fa";
  const subject = fa
    ? side === "origin"
      ? "مبدأ"
      : side === "destination"
        ? "مقصد"
        : "مسیر"
    : side;
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [retry, setRetry] = useState(0);
  const [items, setItems] = useState<InternationalCity[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(Boolean(countryId));
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!countryId) {
      setItems([]);
      setHasMore(false);
      setLoading(false);
      setFailed(false);
      return;
    }
    let active = true;
    const timer = window.setTimeout(() => {
      fetchInternationalCityPage(Number(countryId), query, offset)
        .then((page) => {
          if (!active) return;
          setItems(page.items);
          setHasMore(page.has_more);
          setFailed(false);
          setLoading(false);
        })
        .catch(() => {
          if (!active) return;
          setItems([]);
          setHasMore(false);
          setFailed(true);
          setLoading(false);
        });
    }, 250);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [countryId, offset, query, retry]);

  const beginRequest = () => {
    setLoading(Boolean(countryId));
    setFailed(false);
    setHasMore(false);
    setItems([]);
  };
  const options =
    selected && !items.some((item) => item.id === selected.id)
      ? [selected, ...items]
      : items;
  const selectionLabel = fa
    ? `انتخاب مکان ${subject}`
    : `Select ${subject} location`;

  return (
    <div className="min-w-0 space-y-2">
      <Input
        aria-label={fa ? `جست‌وجوی مکان ${subject}` : `Search ${subject} location`}
        placeholder={fa ? "نام، نام منبع یا کد UN/LOCODE" : "Name or UN/LOCODE"}
        value={query}
        maxLength={160}
        disabled={!countryId}
        onChange={(event) => {
          beginRequest();
          setOffset(0);
          setQuery(event.target.value);
        }}
      />
      <p className="text-xs leading-6 text-muted-foreground">
        {fa
          ? "فقط مکان‌های فعال مرجع نمایش داده می‌شوند؛ هر صفحه حداکثر ۵۰ نتیجه دارد. نام فارسیِ برابر با نام منبع، ترجمه تأییدشده نیست."
          : "Only active governed locations are shown, at most 50 per page. A Persian label matching the source name is an untranslated fallback."}
      </p>
      <select
        aria-label={selectionLabel}
        aria-invalid={Boolean(fieldError)}
        className="min-h-11 w-full min-w-0 rounded border bg-background px-3"
        disabled={!countryId || loading}
        value={selected?.id ?? ""}
        onChange={(event) =>
          onChange(
            options.find((item) => String(item.id) === event.target.value) ?? null,
          )
        }
      >
        <option value="">
          {!countryId
            ? fa
              ? "ابتدا کشور را انتخاب کنید"
              : "Select a country first"
            : fa
              ? "انتخاب مکان"
              : "Select location"}
        </option>
        {options.map((city) => (
          <option key={city.id} value={city.id}>
            {(fa ? city.name : city.name_en) || city.name_en || city.name}
            {city.un_locode ? ` · ${city.un_locode}` : ""}
            {fa && city.name_fa_is_fallback ? " · نام منبع" : ""}
          </option>
        ))}
      </select>
      {loading && (
        <p role="status">{fa ? "در حال دریافت مکان‌ها…" : "Loading locations…"}</p>
      )}
      {failed && (
        <div role="alert" className="space-y-2 text-sm text-destructive">
          <p>
            {fa
              ? "دریافت فهرست ناموفق بود؛ خالی بودن فهرست تأیید نشده است."
              : "The list could not be loaded; an empty catalog has not been confirmed."}
          </p>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              beginRequest();
              setRetry((value) => value + 1);
            }}
          >
            {fa ? "تلاش دوباره" : "Retry"}
          </Button>
        </div>
      )}
      {countryId && !loading && !failed && items.length === 0 && (
        <p role="status">
          {fa ? "مکانی برای این جست‌وجو یافت نشد." : "No locations match this search."}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        {offset > 0 && (
          <Button
            type="button"
            variant="outline"
            disabled={loading}
            onClick={() => {
              beginRequest();
              setOffset(Math.max(0, offset - PAGE_SIZE));
            }}
          >
            {fa ? "صفحه قبل" : "Previous page"}
          </Button>
        )}
        {hasMore && (
          <Button
            type="button"
            variant="outline"
            disabled={loading}
            onClick={() => {
              beginRequest();
              setOffset(offset + PAGE_SIZE);
            }}
          >
            {fa ? "مکان‌های بیشتر" : "More locations"}
          </Button>
        )}
      </div>
    </div>
  );
}
