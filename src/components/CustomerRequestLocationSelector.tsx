import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  fetchInternationalCityPage,
  fetchPublicCanonicalCitiesByCountry,
  type CanonicalCity,
  type CustomerRequestLocationWrite,
  type InternationalCity,
} from "@/lib/api";

const PAGE_SIZE = 50;

export interface CustomerRequestLocationSelection {
  write: CustomerRequestLocationWrite;
  label: string;
  referenceType: "city" | "airport" | "port" | "declared";
}

export function CustomerRequestLocationSelector({
  countryId,
  countryCode,
  locale,
  side,
  value,
  onChange,
}: {
  countryId: string;
  countryCode?: string;
  locale: "fa" | "en";
  side: "origin" | "destination";
  value: CustomerRequestLocationSelection | null;
  onChange: (value: CustomerRequestLocationSelection | null) => void;
}) {
  const fa = locale === "fa";
  const subject = fa ? (side === "origin" ? "مبدأ" : "مقصد") : side;
  const [mode, setMode] = useState<"city" | "physical" | "declared">("city");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [cities, setCities] = useState<CanonicalCity[]>([]);
  const [points, setPoints] = useState<InternationalCity[]>([]);
  const [declared, setDeclared] = useState("");
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    setMode("city");
    setQuery("");
    setOffset(0);
    setDeclared("");
    setCities([]);
    setPoints([]);
    setFailed(false);
  }, [countryId]);

  useEffect(() => {
    if (!countryId || !countryCode || mode === "declared") {
      setLoading(false);
      setFailed(false);
      setHasMore(false);
      return;
    }
    let active = true;
    setLoading(true);
    setFailed(false);
    const timer = window.setTimeout(() => {
      const operation = mode === "city"
        ? fetchPublicCanonicalCitiesByCountry(countryCode, query, offset, PAGE_SIZE)
        : Promise.all([
            fetchInternationalCityPage(Number(countryId), query, offset, "airport", true),
            fetchInternationalCityPage(Number(countryId), query, offset, "port", true),
          ]);
      Promise.resolve(operation).then((response) => {
        if (!active) return;
        if (Array.isArray(response)) {
          const unique = Array.from(new Map(response.flatMap((page) => page.items).map((row) => [row.id, row])).values());
          setPoints(unique);
          setCities([]);
          setHasMore(response.some((page) => page.has_more));
        } else {
          setCities(response.items);
          setPoints([]);
          setHasMore(Boolean(response.has_more));
        }
        setLoading(false);
      }).catch(() => {
        if (!active) return;
        setCities([]);
        setPoints([]);
        setHasMore(false);
        setFailed(true);
        setLoading(false);
      });
    }, 200);
    return () => { active = false; window.clearTimeout(timer); };
  }, [countryId, countryCode, mode, query, offset, retry]);

  const switchMode = (next: "city" | "physical" | "declared") => {
    setMode(next);
    setQuery("");
    setOffset(0);
    setFailed(false);
    onChange(null);
  };
  const noResults = mode === "city" ? cities.length === 0 : points.length === 0;

  return (
    <div className="space-y-3 rounded-lg border bg-muted/20 p-3" data-testid={`${side}-customer-location`}>
      <div className="flex flex-wrap gap-2" role="group" aria-label={fa ? `نوع محل ${subject}` : `${subject} place type`}>
        <Button type="button" size="sm" variant={mode === "city" ? "default" : "outline"} onClick={() => switchMode("city")}>{fa ? "شهر شناخته‌شده" : "Known city"}</Button>
        <Button type="button" size="sm" variant={mode === "physical" ? "default" : "outline"} onClick={() => switchMode("physical")}>{fa ? "فرودگاه یا بندر" : "Airport or port"}</Button>
        <Button type="button" size="sm" variant={mode === "declared" ? "default" : "outline"} onClick={() => switchMode("declared")}>{fa ? "محل موردنظر در فهرست نیست" : "Place is not listed"}</Button>
      </div>
      {!countryId ? (
        <><p className="text-sm text-muted-foreground">{fa ? "ابتدا کشور را انتخاب کنید." : "Select a country first."}</p><select disabled aria-label={fa ? `انتخاب محل ${subject}` : `Select ${subject} place`} className="min-h-11 w-full rounded border bg-background px-3"><option>{fa ? "ابتدا کشور را انتخاب کنید" : "Select a country first"}</option></select></>
      ) : mode === "declared" ? (
        <div className="space-y-2">
          <Input
            aria-label={fa ? `نام شهر یا محل موردنظر ${subject}` : `Requested ${subject} place`}
            placeholder={fa ? "نام شهر یا محل موردنظر را بنویسید" : "Enter the requested city or place"}
            value={declared}
            maxLength={100}
            onChange={(event) => {
              const description = event.target.value;
              setDeclared(description);
              onChange(description.trim() ? { write: { kind: "declared", description }, label: description.trim(), referenceType: "declared" } : null);
            }}
          />
          <p className="rounded bg-amber-50 p-2 text-xs leading-6 text-amber-900">{fa ? "محل اعلام‌شده مشتری؛ نیازمند بررسی کارشناس" : "Customer-declared place; Expert review required"}</p>
        </div>
      ) : (
        <>
          <Input
            aria-label={fa ? `جست‌وجوی ${mode === "city" ? "شهر" : "فرودگاه یا بندر"} ${subject}` : `Search ${subject}`}
            placeholder={fa ? "نام فارسی، نام انگلیسی یا نام جایگزین" : "Persian, English or alternate name"}
            value={query}
            maxLength={160}
            onChange={(event) => { setQuery(event.target.value); setOffset(0); onChange(null); }}
          />
          <select
            className="min-h-11 w-full rounded border bg-background px-3"
            aria-label={fa ? `انتخاب ${mode === "city" ? "شهر" : "نقطه مرجع"} ${subject}` : `Select ${subject}`}
            disabled={loading || failed}
            value={value?.write.kind !== "declared" ? value?.write.source_id ?? "" : ""}
            onChange={(event) => {
              const id = Number(event.target.value);
              if (!id) return onChange(null);
              if (mode === "city") {
                const city = cities.find((row) => row.source_id === id);
                if (city) onChange({ write: { kind: "canonical_city", source_id: city.source_id }, label: `${city.name_fa}${city.province?.name_fa ? `، ${city.province.name_fa}` : ""}`, referenceType: "city" });
              } else {
                const point = points.find((row) => row.id === id);
                if (point) onChange({ write: { kind: "physical_reference", source_id: point.id }, label: point.name, referenceType: point.city_type as "airport" | "port" });
              }
            }}
          >
            <option value="">{fa ? "انتخاب کنید" : "Select"}</option>
            {mode === "city" ? cities.map((city) => <option key={city.source_id} value={city.source_id}>{city.name_fa}{city.name_en ? ` · ${city.name_en}` : ""}{city.province?.name_fa ? ` · ${city.province.name_fa}` : ""}</option>) : points.map((point) => <option key={point.id} value={point.id}>{point.name} · {point.city_type === "airport" ? "فرودگاه" : "بندر"}{point.un_locode ? ` · ${point.un_locode}` : ""}</option>)}
          </select>
          {loading && <p role="status" className="text-sm">{fa ? "در حال دریافت فهرست…" : "Loading…"}</p>}
          {failed && <div role="alert" className="space-y-2 text-sm text-destructive"><p>{fa ? "دریافت فهرست ناموفق بود؛ نبود نتیجه تأیید نشده است." : "The list failed to load; no result has not been confirmed."}</p><Button type="button" variant="outline" size="sm" onClick={() => setRetry((value) => value + 1)}>{fa ? "تلاش دوباره" : "Retry"}</Button></div>}
          {!loading && !failed && noResults && <p role="status" className="text-sm text-muted-foreground">{query.trim() ? (fa ? "نتیجه‌ای برای این جست‌وجو یافت نشد." : "No matching result.") : (fa ? "داده مرجع عمیق‌تری در این بخش موجود نیست؛ می‌توانید محل را اعلام کنید." : "No deeper reference data is available; you can declare the place.")}</p>}
          <div className="flex gap-2">{offset > 0 && <Button type="button" variant="outline" size="sm" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>{fa ? "صفحه قبل" : "Previous"}</Button>}{hasMore && <Button type="button" variant="outline" size="sm" onClick={() => setOffset(offset + PAGE_SIZE)}>{fa ? "نتایج بیشتر" : "More"}</Button>}</div>
          <p className="text-xs leading-6 text-muted-foreground">{mode === "city" ? (fa ? "این انتخاب یک شهر مرجع است." : "This is a canonical city reference.") : (fa ? "فرودگاه و بندر جدا از شهر ثبت می‌شوند." : "Airports and ports are recorded separately from cities.")}</p>
        </>
      )}
    </div>
  );
}
