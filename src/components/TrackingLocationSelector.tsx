import { useEffect, useState } from "react";
import { fetchTrackingLogisticsPoints, type TrackingLogisticsPoint } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// Selection is retained independently of the current search page. Authorization
// and fresh-selection eligibility are always rechecked by the write service.
export function TrackingLocationSelector({ value, onChange, locale }: {
  value: string;
  onChange: (value: string) => void;
  locale: string;
}) {
  const fa = locale.startsWith("fa");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [retry, setRetry] = useState(0);
  const [items, setItems] = useState<TrackingLogisticsPoint[]>([]);
  const [selected, setSelected] = useState<TrackingLogisticsPoint | null>(null);
  const [nextOffset, setNextOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let current = true;
    const timer = window.setTimeout(() => {
      fetchTrackingLogisticsPoints(query, offset).then(page => {
        if (!current) return;
        setItems(page.items);
        setNextOffset(page.offset + page.limit);
        setHasMore(page.has_more);
        setLoading(false);
      }).catch(() => {
        if (!current) return;
        setItems([]);
        setHasMore(false);
        setError(true);
        setLoading(false);
      });
    }, 250);
    return () => { current = false; window.clearTimeout(timer); };
  }, [query, offset, retry]);

  const begin = () => { setLoading(true); setError(false); setHasMore(false); setItems([]); };
  const options = selected && selected.public_id === value && !items.some(x => x.public_id === value)
    ? [selected, ...items] : items;
  const label = (point: TrackingLogisticsPoint) =>
    `${(fa ? point.fa_name : point.en_name) || point.fa_name || point.en_name || point.immutable_code} · ${point.type.label || point.type.code} · ${point.city ? `${point.city}، ` : ""}${point.country.label || point.country.code}`;

  return <div className="space-y-2">
    <label htmlFor="tracking-location-search" className="text-sm font-medium">{fa ? "مکان لجستیکی" : "Logistics location"}</label>
    <p className="text-xs text-muted-foreground">{fa ? "مکان‌های فعال و مجاز سازمان را با نام فارسی، لاتین یا کد جست‌وجو کنید." : "Search eligible organization locations by Persian name, English name or code."}</p>
    <Input id="tracking-location-search" value={query} maxLength={160} onChange={event => {
      begin(); setOffset(0); setQuery(event.target.value);
    }} placeholder={fa ? "جست‌وجوی مکان" : "Search locations"} />
    <select aria-label={fa ? "انتخاب مکان لجستیکی" : "Select logistics location"}
      className="h-10 w-full min-w-0 rounded-md border bg-background px-3 text-sm"
      value={value} onChange={event => {
        setSelected(options.find(x => x.public_id === event.target.value) || null);
        onChange(event.target.value);
      }}>
      <option value="">{fa ? "محل در فهرست نیست (ورود دستی)" : "Location not listed (manual entry)"}</option>
      {options.map(point => <option key={point.public_id} value={point.public_id}>{label(point)}</option>)}
    </select>
    {loading && <p role="status" className="text-sm">{fa ? "در حال دریافت مکان‌ها…" : "Loading locations…"}</p>}
    {error && <div role="alert" className="text-sm text-destructive">
      <p>{fa ? "دریافت مکان‌ها ناموفق بود یا اجازه دسترسی ندارید. فهرست خالی تأیید نشده است." : "Locations could not be loaded or access was denied. An empty catalog has not been confirmed."}</p>
      <Button type="button" variant="outline" onClick={() => { begin(); setRetry(x => x + 1); }}>{fa ? "تلاش دوباره" : "Retry"}</Button>
    </div>}
    {!loading && !error && items.length === 0 && <p role="status" className="text-sm">{fa ? "مکان فعال و مجازی برای این جست‌وجو پیدا نشد." : "No eligible active locations match this search."}</p>}
    <div className="flex gap-2">
      {offset > 0 && <Button type="button" variant="outline" disabled={loading} onClick={() => { begin(); setOffset(0); }}>{fa ? "صفحه اول" : "First page"}</Button>}
      {hasMore && <Button type="button" variant="outline" disabled={loading} onClick={() => { begin(); setOffset(nextOffset); }}>{fa ? "مکان‌های بیشتر" : "More locations"}</Button>}
    </div>
  </div>;
}
