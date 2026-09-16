import { useEffect, useState } from "react";
import { fetchInternationalCityPage, type InternationalCity } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// Parent keys this component by country, so pages cannot cross country changes.
// Selection belongs to the form and survives searching and page navigation.
export function InternationalLocationSelector({ countryId, locale, side, selected, onChange }: {
  countryId: string; locale: string; side: "origin" | "destination";
  selected: InternationalCity | null; onChange: (city: InternationalCity | null) => void;
}) {
  const fa = locale === "fa";
  const subject = fa ? (side === "origin" ? "مبدأ" : "مقصد") : side;
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [retry, setRetry] = useState(0);
  const [items, setItems] = useState<InternationalCity[]>([]);
  const [more, setMore] = useState(false);
  const [loading, setLoading] = useState(Boolean(countryId));
  const [error, setError] = useState(false);
  useEffect(() => {
    if (!countryId) return;
    let active = true;
    const timer = window.setTimeout(() => {
      fetchInternationalCityPage(Number(countryId), query, offset).then(page => {
        if (!active) return;
        setItems(page.items); setMore(page.has_more); setLoading(false);
      }).catch(() => {
        if (!active) return;
        setError(true); setLoading(false); setMore(false); setItems([]);
      });
    }, 250);
    return () => { active = false; window.clearTimeout(timer); };
  }, [countryId, query, offset, retry]);
  const begin = () => { setLoading(Boolean(countryId)); setError(false); setMore(false); setItems([]); };
  const options = selected && !items.some(x => x.id === selected.id) ? [selected, ...items] : items;
  return <div className="space-y-2">
    <Input aria-label={fa ? `جست‌وجوی مکان ${subject}` : `Search ${subject} location`}
      placeholder={fa ? "نام یا کد مکان / UNLOCODE" : "Location name or UN/LOCODE"}
      value={query} maxLength={160} disabled={!countryId} onChange={event => {
        begin(); setOffset(0); setQuery(event.target.value);
      }} />
    <p className="text-xs text-muted-foreground">{fa ? "مکان‌های فعال مرجع جهانی؛ هر صفحه ۵۰ نتیجه. برای یافتن مکان، نام لاتین، نام فارسیِ موجود یا کد را جست‌وجو کنید. وجود مکان تضمین ارائه خدمت نیست." : "Active worldwide reference locations; 50 results per page. Search by source name, available Persian name or code. Listing does not guarantee service availability."}</p>
    <select aria-label={fa ? `انتخاب مکان ${subject}` : `Select ${subject} location`}
      className="h-10 w-full min-w-0 rounded-md border bg-background px-3 text-sm"
      disabled={!countryId || loading} value={selected?.id || ""}
      onChange={event => onChange(options.find(x => String(x.id) === event.target.value) || null)}>
      <option value="">{!countryId ? (fa ? "ابتدا کشور را انتخاب کنید" : "Select a country first") : (fa ? "انتخاب مکان" : "Select location")}</option>
      {options.map(city => <option key={city.id} value={city.id}>
        {(fa ? city.name : city.name_en) || city.name_en || city.name} {city.un_locode ? `· ${city.un_locode}` : ""}
      </option>)}
    </select>
    {loading && <p role="status">{fa ? "در حال دریافت مکان‌ها…" : "Loading locations…"}</p>}
    {error && <div role="alert" className="text-sm text-destructive">
      <p>{fa ? "دریافت فهرست ناموفق بود؛ خالی بودن فهرست تأیید نشده است." : "The list could not be loaded; an empty catalog has not been confirmed."}</p>
      <Button type="button" variant="outline" onClick={() => { begin(); setRetry(x => x + 1); }}>{fa ? "تلاش دوباره" : "Retry"}</Button>
    </div>}
    {countryId && !loading && !error && items.length === 0 && <p role="status">{fa ? "مکانی برای این جست‌وجو یافت نشد." : "No locations match this search."}</p>}
    <div className="flex flex-wrap gap-2">
      {offset > 0 && <Button type="button" variant="outline" disabled={loading} onClick={() => { begin(); setOffset(Math.max(0, offset - 50)); }}>{fa ? "صفحه قبل" : "Previous page"}</Button>}
      {more && <Button type="button" variant="outline" disabled={loading} onClick={() => { begin(); setOffset(offset + 50); }}>{fa ? "مکان‌های بیشتر" : "More locations"}</Button>}
    </div>
  </div>;
}
