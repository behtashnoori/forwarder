import { useEffect, useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import {
  fetchTrackingLocations,
  fetchTrackingLogisticsPoints,
  type TrackingLocationReference,
  type TrackingLogisticsPoint,
} from "@/lib/api";

export type OperationalEventLocation =
  | { kind: "manual"; locationText: string }
  | { kind: "private"; publicId: string }
  | { kind: "reference"; id: number };

type RetainedOption = {
  key: string;
  label: string;
};

const keyFor = (value: OperationalEventLocation) => {
  if (value.kind === "private") return `private:${value.publicId}`;
  if (value.kind === "reference") return `reference:${value.id}`;
  return "manual";
};

const privateLabel = (point: TrackingLogisticsPoint) =>
  `${point.fa_name}${point.en_name ? ` / ${point.en_name}` : ""} — ${
    point.selector_kind === "organization_reference"
      ? "نقطه مرجع شبکه سازمان"
      : "نقطه خصوصی سازمان"
  }`;

const referenceLabel = (point: TrackingLocationReference) =>
  `${point.name_fa}${point.name_en ? ` / ${point.name_en}` : ""} — مکان مرجع`;

export default function OperationalEventLocationSelector({
  value,
  onChange,
}: {
  value: OperationalEventLocation;
  onChange: (value: OperationalEventLocation) => void;
}) {
  const [query, setQuery] = useState("");
  const [privatePoints, setPrivatePoints] = useState<TrackingLogisticsPoint[]>([]);
  const [references, setReferences] = useState<TrackingLocationReference[]>([]);
  const [retained, setRetained] = useState<RetainedOption | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      setLoading(true);
      setFailed(false);
      Promise.all([
        fetchTrackingLogisticsPoints(query),
        fetchTrackingLocations(query),
      ])
        .then(([privateResult, referenceResult]) => {
          if (!active) return;
          setPrivatePoints(privateResult.items);
          setReferences(referenceResult.items);
        })
        .catch(() => {
          if (!active) return;
          setPrivatePoints([]);
          setReferences([]);
          setFailed(true);
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }, 250);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [query]);

  const privateOptions = useMemo(
    () => privatePoints.map((point) => ({
      key: `private:${point.public_id}`,
      label: privateLabel(point),
    })),
    [privatePoints],
  );
  const referenceOptions = useMemo(
    () => references.map((point) => ({
      key: `reference:${point.id}`,
      label: referenceLabel(point),
    })),
    [references],
  );
  const currentKey = keyFor(value);
  const currentIsVisible = [...privateOptions, ...referenceOptions].some(
    (option) => option.key === currentKey,
  );

  const select = (key: string) => {
    if (key === "manual") {
      setRetained(null);
      onChange({
        kind: "manual",
        locationText: value.kind === "manual" ? value.locationText : "",
      });
      return;
    }
    const option = [...privateOptions, ...referenceOptions].find(
      (item) => item.key === key,
    );
    if (option) setRetained(option);
    if (key.startsWith("private:")) {
      onChange({ kind: "private", publicId: key.slice("private:".length) });
      return;
    }
    onChange({ kind: "reference", id: Number(key.slice("reference:".length)) });
  };

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium" htmlFor="operational-location-search">
        مکان رخداد
      </label>
      <Input
        id="operational-location-search"
        aria-label="جست‌وجوی مکان رخداد"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="جست‌وجوی نام، کد یا مکان مرجع"
      />
      <select
        aria-label="انتخاب مکان رخداد"
        className="min-h-11 w-full rounded border bg-white px-3"
        disabled={loading || failed}
        value={currentKey}
        onChange={(event) => select(event.target.value)}
      >
        <option value="manual">ورود دستی مکان</option>
        {retained && !currentIsVisible ? (
          <option value={retained.key}>{retained.label}</option>
        ) : null}
        {privateOptions.length ? (
          <optgroup label="نقاط سازمان">
            {privateOptions.map((option) => (
              <option key={option.key} value={option.key}>{option.label}</option>
            ))}
          </optgroup>
        ) : null}
        {referenceOptions.length ? (
          <optgroup label="مکان‌های مرجع">
            {referenceOptions.map((option) => (
              <option key={option.key} value={option.key}>{option.label}</option>
            ))}
          </optgroup>
        ) : null}
      </select>
      {loading ? <p role="status" className="text-xs text-muted-foreground">در حال دریافت مکان‌های مجاز…</p> : null}
      {failed ? <p role="alert" className="text-xs text-red-700">دریافت مکان‌های مجاز ممکن نشد.</p> : null}
      {value.kind === "manual" ? (
        <Input
          aria-label="مکان دستی رخداد"
          value={value.locationText}
          onChange={(event) => onChange({ kind: "manual", locationText: event.target.value })}
          placeholder="موقعیت فعلی"
        />
      ) : null}
    </div>
  );
}
