import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { routeSelectClass } from "@/components/RouteAuthoringSection";
import {
  fetchInternationalCityPage,
  listLogisticsPoints,
  searchIranDestinations,
  type AdminCountry,
  type AdminProvince,
  type OperationalLocationRef,
} from "@/lib/api";

export type RouteReferenceEndpointRef = OperationalLocationRef & { country_id: number };

type EndpointOption = {
  key: string;
  label: string;
  reference: RouteReferenceEndpointRef;
};

const referenceKey = (value: RouteReferenceEndpointRef | null) =>
  value ? `${value.source_type}:${value.source_id}` : "";

const internationalTypeLabel = (value: string) => ({
  city: "شهر",
  port: "بندر",
  airport: "فرودگاه",
}[value] || "مکان");

const normalized = (value: string) => value.trim().toLocaleLowerCase("fa-IR");

function ordered(options: EndpointOption[]) {
  const unique = new Map(options.map((option) => [option.key, option]));
  return [...unique.values()].sort((left, right) =>
    left.label.localeCompare(right.label, "fa") || left.key.localeCompare(right.key),
  );
}
export function RouteReferenceLocationPicker({
  id,
  label,
  value,
  onChange,
  countries,
  provinces,
}: {
  id: string;
  label: string;
  value: RouteReferenceEndpointRef | null;
  onChange: (value: RouteReferenceEndpointRef | null) => void;
  countries: AdminCountry[];
  provinces: AdminProvince[];
}) {
  const [countryId, setCountryId] = useState("");
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<EndpointOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);
  const requestSequence = useRef(0);

  const load = useCallback(async (term: string) => {
    const country = countries.find((item) => String(item.id) === countryId);
    if (!country) {
      setOptions([]);
      return;
    }
    const sequence = ++requestSequence.current;
    setLoading(true);
    setError("");
    setSearched(true);
    try {
      const facilitiesPromise = listLogisticsPoints({
        active: "true",
        country: country.code,
        q: term,
        per_page: 100,
      });
      let next: EndpointOption[] = [];
      if (country.code === "IR") {
        const [cities, ports, customs, internationalLocations, facilities] = await Promise.all([
          searchIranDestinations(term, 50, "city"),
          searchIranDestinations(term, 50, "port"),
          searchIranDestinations(term, 50, "customs"),
          searchIranDestinations(term, 50, "international_city"),
          facilitiesPromise,
        ]);
        const needle = normalized(term);
        next.push(...provinces
          .filter((item) => item.is_active && (
            item.country_id === country.id || item.country_id === null
          ))
          .filter((item) => !needle || normalized(item.name_fa).includes(needle))
          .map((item) => ({
            key: `province:${item.id}`,
            label: `استان — ${item.name_fa}`,
            reference: { country_id: country.id, source_type: "province" as const, source_id: item.id },
          })));
        for (const item of [...cities.data, ...ports.data, ...customs.data, ...internationalLocations.data]) {
          const sourceType = item.identity.type === "port"
            ? "iran_port"
            : item.identity.type === "customs"
              ? "customs_office"
              : item.identity.type === "international_city"
                ? "international_city"
                : "city";
          next.push({
            key: `${sourceType}:${item.identity.id}`,
            label: `${item.type_label} — ${item.display_name}`,
            reference: { country_id: country.id, source_type: sourceType, source_id: item.identity.id },
          });
        }
        next.push(...facilities.items.map((item) => ({
          key: `logistics_point:${item.public_id}`,
          label: `${item.point_type.fa_name} — ${item.fa_name}`,
          reference: { country_id: country.id, source_type: "logistics_point" as const, source_id: item.public_id },
        })));
      } else {
        const [locations, facilities] = await Promise.all([
          fetchInternationalCityPage(country.id, term, 0, undefined, true),
          facilitiesPromise,
        ]);
        next = locations.items.map((item) => ({
          key: `international_city:${item.id}`,
          label: `${internationalTypeLabel(item.city_type)} — ${item.name}`,
          reference: { country_id: country.id, source_type: "international_city", source_id: item.id },
        }));
        next.push(...facilities.items.map((item) => ({
          key: `logistics_point:${item.public_id}`,
          label: `${item.point_type.fa_name} — ${item.fa_name}`,
          reference: { country_id: country.id, source_type: "logistics_point" as const, source_id: item.public_id },
        })));
      }
      if (sequence === requestSequence.current) {
        setOptions((current) => {
          const selected = current.find((item) => item.key === referenceKey(value));
          return ordered(selected ? [selected, ...next] : next);
        });
      }
    } catch {
      if (sequence === requestSequence.current) {
        setOptions([]);
        setError("دریافت مکان‌های معتبر این کشور ممکن نشد؛ اتصال را بررسی و دوباره جست‌وجو کنید.");
      }
    } finally {
      if (sequence === requestSequence.current) setLoading(false);
    }
  }, [countries, countryId, provinces, value]);

  useEffect(() => {
    if (!countryId) return;
    void load("");
  }, [countryId, load]);

  return <fieldset className="min-w-0 space-y-2 rounded-xl border p-3">
    <legend className="px-1 text-sm font-medium">{label}</legend>
    <select
      aria-label={`${label} کشور`}
      className={routeSelectClass}
      value={countryId}
      onChange={(event) => {
        requestSequence.current += 1;
        setCountryId(event.target.value);
        setQuery("");
        setOptions([]);
        setError("");
        setSearched(false);
        onChange(null);
      }}
    >
      <option value="">انتخاب کشور</option>
      {countries.map((country) => <option key={country.id} value={country.id}>
        {country.name_fa || country.name_en} · {country.code}
      </option>)}
    </select>
    <div className="flex min-w-0 flex-col gap-2 sm:flex-row">
      <Input
        aria-label={`${label} جست‌وجوی مکان`}
        disabled={!countryId}
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="جست‌وجوی شهر، استان، بندر، فرودگاه یا نقطه لجستیکی"
      />
      <Button type="button" variant="outline" disabled={!countryId || loading} onClick={() => void load(query)}>
        {loading ? "در حال دریافت…" : "جست‌وجو"}
      </Button>
    </div>
    <select
      id={id}
      aria-label={`${label} مکان`}
      className={routeSelectClass}
      disabled={!countryId || loading}
      value={referenceKey(value)}
      onChange={(event) => onChange(options.find((item) => item.key === event.target.value)?.reference ?? null)}
    >
      <option value="">انتخاب مکان معتبر</option>
      {options.map((option) => <option key={option.key} value={option.key}>{option.label}</option>)}
    </select>
    {loading && <p role="status" className="text-sm text-slate-600">در حال جست‌وجوی مکان‌های معتبر…</p>}
    {searched && !loading && !error && options.length === 0 && (
      <p role="status" className="text-sm text-slate-600">مکان معتبر منطبق با این جست‌وجو یافت نشد.</p>
    )}
    {value && <p className="text-sm text-emerald-800">
      مکان انتخاب‌شده: {options.find((option) => option.key === referenceKey(value))?.label ?? "مکان معتبر"}
    </p>}
    <p className="text-xs leading-6 text-slate-600">
      نام نمایشی از رکورد انتخاب‌شده ساخته می‌شود؛ هویت مبدأ یا مقصد با شناسهٔ مکان ثبت می‌شود، نه متن آزاد.
    </p>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
  </fieldset>;
}
