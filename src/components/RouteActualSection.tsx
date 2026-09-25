import { useEffect, useState } from "react";
import OperationalPermission from "@/components/OperationalPermission";
import {
  RouteLocationPicker,
  routeSelectClass,
  type RouteLocationCatalog,
} from "@/components/RouteAuthoringSection";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  ApiError,
  fetchCountries,
  fetchProvinces,
  listLogisticsPoints,
  recordActualRouteTraversal,
  searchIranDestinations,
  type OperationalLocationRef,
  type RoutePlanDetail,
} from "@/lib/api";
import {
  localDateTimeInputToUtc,
  toLocalDateTimeInputValue,
} from "@/lib/localDateTime";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";

const emptyCatalog: RouteLocationCatalog = {
  provinces: [],
  iran: [],
  facilities: [],
  countries: [],
};

export default function RouteActualSection({
  shipmentId,
  plan,
  reload,
}: {
  shipmentId: string;
  plan: RoutePlanDetail;
  reload: () => Promise<boolean>;
}) {
  const [catalog, setCatalog] = useState<RouteLocationCatalog>(emptyCatalog);
  const [plannedLeg, setPlannedLeg] = useState("");
  const [origin, setOrigin] = useState<OperationalLocationRef | null>(null);
  const [destination, setDestination] = useState<OperationalLocationRef | null>(null);
  const [departure, setDeparture] = useState("");
  const [arrival, setArrival] = useState("");
  const [notes, setNotes] = useState("");
  const [pending, setPending] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!editing) return;
    Promise.all([
      fetchProvinces(),
      searchIranDestinations(),
      listLogisticsPoints({ active: "true", per_page: 100 }),
      fetchCountries(),
    ])
      .then(([provinces, iran, facilities, countries]) =>
        setCatalog({
          provinces,
          iran: iran.data,
          facilities: facilities.items.filter((item) => item.is_active),
          countries,
        }),
      )
      .catch(() => setError("دریافت مکان‌های مجاز ممکن نشد."));
  }, [editing]);

  const searchIran = (query: string) => {
    searchIranDestinations(query)
      .then((response) =>
        setCatalog((current) => ({ ...current, iran: response.data })),
      )
      .catch(() => setError("جست‌وجوی مکان ممکن نشد."));
  };

  const choosePlannedLeg = (value: string) => {
    setPlannedLeg(value);
    const leg = plan.legs.find((item) => item.id === Number(value));
    setOrigin(leg?.origin.canonical_reference || null);
    setDestination(leg?.destination.canonical_reference || null);
  };

  const submit = async () => {
    if (pending) return;
    const departedAt = departure ? localDateTimeInputToUtc(departure) : null;
    const arrivedAt = arrival ? localDateTimeInputToUtc(arrival) : null;
    if (!origin || !destination) {
      setError("مبدأ و مقصد مسیر واقعی را انتخاب کنید.");
      return;
    }
    if ((!departedAt && !arrivedAt) || (departure && !departedAt) || (arrival && !arrivedAt)) {
      setError("دست‌کم یک زمان واقعی معتبر لازم است.");
      return;
    }
    setPending(true);
    setError("");
    setNotice("");
    try {
      await recordActualRouteTraversal(shipmentId, plan.id, {
        planned_route_leg_id: plannedLeg ? Number(plannedLeg) : null,
        origin,
        destination,
        departed_at: departedAt,
        arrived_at: arrivedAt,
        notes: notes || null,
      });
      await reload();
      setPlannedLeg("");
      setOrigin(null);
      setDestination(null);
      setDeparture("");
      setArrival("");
      setNotes("");
      setNotice("واقعیت پیمایش ثبت شد؛ برنامه مسیر بدون تغییر باقی ماند.");
    } catch (caught) {
      setError(
        caught instanceof ApiError && caught.status === 403
          ? "فقط کارشناس مسئول محموله می‌تواند مسیر واقعی را ثبت کند."
          : "ثبت مسیر واقعی ممکن نشد؛ اطلاعات و زمان‌ها را بررسی کنید.",
      );
    } finally {
      setPending(false);
    }
  };

  const now = () => setDeparture(toLocalDateTimeInputValue(new Date()));
  return (
    <Card>
      <CardHeader>
        <CardTitle>مسیر واقعی</CardTitle>
        <p className="text-sm text-slate-600">
          واقعیت پیمایش جدا از برنامه ثبت می‌شود. تفاوت مسیر به‌تنهایی مورد استثنا ایجاد نمی‌کند.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p role="alert" className="rounded bg-red-50 p-3 text-red-700">{error}</p>}
        {notice && <p role="status" className="rounded bg-emerald-50 p-3 text-emerald-800">{notice}</p>}
        {(plan.actual_route || []).length ? (
          <div className="space-y-2">
            {(plan.actual_route || []).map((fact) => (
              <article key={fact.public_id} className="rounded border p-3">
                <div className="flex flex-wrap justify-between gap-2">
                  <strong>پیمایش واقعی {fact.sequence_number}</strong>
                  <span className={fact.is_deviation ? "text-amber-800" : "text-emerald-700"}>
                    {fact.is_deviation ? "متفاوت از برنامه" : "منطبق با بخش برنامه"}
                  </span>
                </div>
                <p>{fact.origin.display_name || "ثبت نشده"} ← {fact.destination.display_name || "ثبت نشده"}</p>
                <p className="text-sm text-slate-600">
                  حرکت {formatDualCalendarInstant(fact.departed_at, "fa", { fallback: "ثبت نشده" })} · رسیدن {formatDualCalendarInstant(fact.arrived_at, "fa", { fallback: "ثبت نشده" })}
                </p>
                {fact.notes && <p className="text-sm">{fact.notes}</p>}
              </article>
            ))}
          </div>
        ) : <p className="text-slate-600">هنوز واقعیت پیمایشی ثبت نشده است.</p>}
        <OperationalPermission permission="route_leg.manage">
          {!editing ? <Button type="button" variant="outline" onClick={() => setEditing(true)}>افزودن پیمایش واقعی</Button> : <div className="space-y-3 rounded border bg-slate-50 p-3">
            <div>
              <label htmlFor="actual-planned-leg">بخش برنامه مرتبط (اختیاری)</label>
              <select id="actual-planned-leg" className={routeSelectClass} value={plannedLeg} onChange={(event) => choosePlannedLeg(event.target.value)}>
                <option value="">بدون بخش برنامه مرتبط / انحراف مستقل</option>
                {plan.legs.map((leg) => <option key={leg.id} value={leg.id}>بخش {leg.sequence_number} · {leg.branch_label || leg.destination.display_name}</option>)}
              </select>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <RouteLocationPicker id="actual-route-origin" label="مبدأ مسیر واقعی" value={origin} onChange={setOrigin} catalog={catalog} searchIran={searchIran} />
              <RouteLocationPicker id="actual-route-destination" label="مقصد مسیر واقعی" value={destination} onChange={setDestination} catalog={catalog} searchIran={searchIran} />
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div><label htmlFor="actual-route-departure">زمان واقعی حرکت</label><Input id="actual-route-departure" type="datetime-local" value={departure} onChange={(event) => setDeparture(event.target.value)} /><Button type="button" variant="outline" className="mt-2" onClick={now}>اکنون</Button></div>
              <div><label htmlFor="actual-route-arrival">زمان واقعی رسیدن (اختیاری)</label><Input id="actual-route-arrival" type="datetime-local" value={arrival} onChange={(event) => setArrival(event.target.value)} /></div>
            </div>
            <div><label htmlFor="actual-route-notes">یادداشت (اختیاری)</label><Input id="actual-route-notes" value={notes} onChange={(event) => setNotes(event.target.value)} /></div>
            <Button type="button" disabled={pending} onClick={() => void submit()}>{pending ? "در حال ثبت…" : "ثبت واقعیت پیمایش"}</Button>
            <Button type="button" variant="outline" disabled={pending} onClick={() => setEditing(false)}>انصراف</Button>
          </div>}
        </OperationalPermission>
      </CardContent>
    </Card>
  );
}
