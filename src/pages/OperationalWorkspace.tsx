import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
import { AlertTriangle, Clock3, PackageSearch, Route as RouteIcon } from "lucide-react";
import OperationsNav from "@/components/OperationsNav";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  ApiError,
  getOperationalWorkspace,
  type OperationalWorkspaceShipment,
  type OperationalWorkspaceSnapshot,
} from "@/lib/api";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import { useI18n } from "@/i18n";

const customerName = (shipment: OperationalWorkspaceShipment) =>
  typeof shipment.customer === "string"
    ? shipment.customer
    : shipment.customer?.display_name || "مشتری ثبت نشده";

const routeLabel = (shipment: OperationalWorkspaceShipment, direction: string) => {
  const route = shipment.route_summary;
  if (!route?.origin?.display_name || !route?.destination?.display_name) {
    return "مسیر هنوز قابل نمایش نیست";
  }
  return `${route.origin.display_name} ${direction === "rtl" ? "←" : "→"} ${route.destination.display_name}`;
};

const severityLabel: Record<string, string> = {
  critical: "بحرانی",
  warning: "نیازمند پیگیری",
  info: "اطلاع عملیاتی",
};

const slaTone: Record<string, string> = {
  BREACHED: "bg-red-100 text-red-800",
  WARNING: "bg-amber-100 text-amber-900",
  WITHIN: "bg-emerald-100 text-emerald-900",
  MET: "bg-emerald-100 text-emerald-900",
  PENDING_EVALUATION: "bg-blue-100 text-blue-900",
};

const evaluationStateLabel: Record<string, string> = {
  STALE: "قدیمی",
  REBUILDING: "در حال بازیابی",
  DEGRADED: "دچار خطا",
};

export default function OperationalWorkspace() {
  const { direction, locale, businessLabel } = useI18n();
  const [snapshot, setSnapshot] = useState<OperationalWorkspaceSnapshot>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setSnapshot(await getOperationalWorkspace());
    } catch (caught) {
      setSnapshot(undefined);
      setError(
        caught instanceof ApiError && caught.status === 403
          ? "شما اجازه مشاهده فضای کار عملیاتی را ندارید."
          : "فضای کار عملیاتی در حال حاضر بارگذاری نشد.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const data = snapshot?.data;
  const meta = snapshot?.meta;

  return (
    <main className="min-h-screen bg-slate-50 p-3 sm:p-5 md:p-8" dir={direction}>
      <div className="mx-auto max-w-7xl space-y-6">
        <OperationsNav />
        <header className="space-y-2">
          <p className="text-sm font-semibold text-blue-700">فضای کار کارشناس حمل</p>
          <h1 className="text-2xl font-black text-slate-950 sm:text-3xl">
            امروز چه چیزی نیاز به توجه من دارد؟
          </h1>
          <p className="max-w-3xl text-sm leading-7 text-slate-600 sm:text-base">
            تصویر امروز از محموله‌های فعال، استثناها، اقدام‌ها و SLAهای تعریف‌شده سازمان؛ کاملاً بر پایه واقعیت‌های ثبت‌شده و بدون تصمیم‌گیری خودکار.
          </p>
        </header>

        {error && (
          <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">
            {error}
            <Button variant="link" onClick={() => void load()}>تلاش دوباره</Button>
          </div>
        )}
        {loading && (
          <p role="status" aria-live="polite" className="rounded-xl bg-white p-8 text-center">
            در حال آماده‌سازی فضای کار…
          </p>
        )}

        {!loading && data && meta && (
          <>
            <section aria-label="تصویر امروز" className="grid gap-3 sm:grid-cols-3">
              <Card>
                <CardContent className="flex items-center gap-3 p-5">
                  <PackageSearch className="h-8 w-8 text-blue-700" />
                  <div><p className="text-sm text-slate-500">محموله‌های فعال قابل مشاهده</p><strong className="text-2xl">{meta.active_shipment_count}</strong></div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="flex items-center gap-3 p-5">
                  <AlertTriangle className="h-8 w-8 text-amber-700" />
                  <div><p className="text-sm text-slate-500">پیگیری‌های عملیاتی باز</p><strong className="text-2xl">{meta.attention_available ? meta.open_follow_up_count : "محدود"}</strong></div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="flex items-center gap-3 p-5">
                  <Clock3 className="h-8 w-8 text-emerald-700" />
                  <div><p className="text-sm text-slate-500">به‌روزرسانی‌های اخیر قابل مشاهده</p><strong className="text-2xl">{data.recent_updates.length}</strong></div>
                </CardContent>
              </Card>
            </section>

            {meta.attention_projection && meta.attention_projection.state !== "FRESH" && <div data-testid="attention-freshness-warning" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              آخرین ارزیابی Attention به‌روز نیست ({evaluationStateLabel[meta.attention_projection.state] ?? meta.attention_projection.state}).
              {meta.attention_projection.last_success_at ? <> آخرین ارزیابی موفق: <time dateTime={meta.attention_projection.last_success_at}>{formatDualCalendarInstant(meta.attention_projection.last_success_at, locale, { fallback: meta.attention_projection.last_success_at })}</time>.</> : " هنوز ارزیابی موفقی ثبت نشده است."}
              {" "}نبود هشدار در این وضعیت به‌معنی سلامت عملیات نیست.
            </div>}

            <section aria-labelledby="attention-heading" className="space-y-3">
              <div><h2 id="attention-heading" className="text-xl font-bold">موارد مهم برای پیگیری</h2><p className="text-sm text-slate-600">هر مورد از یک Exception، Action، SLA یا واقعیت عملیاتی قابل ردیابی به دست آمده است.</p></div>
              {!meta.attention_available ? (
                <Card><CardContent className="p-6 text-center text-slate-600">جزئیات پیگیری‌ها با دسترسی فعلی شما قابل نمایش نیست.</CardContent></Card>
              ) : !data.attention_items.length ? (
                <Card><CardContent className="p-6 text-center text-slate-600">در داده‌های فعلی، پیگیری عملیاتی بازی برای محموله‌های فعال قابل مشاهده ثبت نشده است.</CardContent></Card>
              ) : (
                <div className="grid gap-3 lg:grid-cols-2">
                  {data.attention_items.map((item) => (
                    <Link key={item.identity} to={item.source_path} aria-label={`باز کردن منبع پیگیری محموله ${customerName(item.shipment)}`}>
                      <Card className="h-full transition-colors hover:border-amber-300">
                        <CardContent className="space-y-2 p-5">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <strong>{item.label}</strong>
                            <span className="rounded-full bg-amber-100 px-2 py-1 text-xs text-amber-900">{severityLabel[item.severity] || item.severity}</span>
                          </div>
                          <p>{customerName(item.shipment)} · {routeLabel(item.shipment, direction)}</p>
                          {item.why && <p className="text-sm"><b>چرا:</b> {item.why}</p>}
                          <p className="text-sm text-slate-600"><b>اثر زمان:</b> {item.time_effect || formatDualCalendarInstant(item.due_at, locale, { fallback: "موعد مستقلی ثبت نشده" })}</p>
                          {item.next_action && <p className="text-sm text-blue-800"><b>پیگیری بعدی:</b> {item.next_action}</p>}
                          <p className="text-xs text-slate-500">منبع: {item.source.type} · نسخه {item.source.version}{item.freshness?.status ? ` · تازگی: ${item.freshness.status}` : ""}</p>
                        </CardContent>
                      </Card>
                    </Link>
                  ))}
                </div>
              )}
            </section>

            <section aria-labelledby="active-heading" className="space-y-3">
              <div className="flex flex-wrap items-end justify-between gap-2">
                <div><h2 id="active-heading" className="text-xl font-bold">محموله‌های فعال</h2><p className="text-sm text-slate-600">پرونده‌های فعال در دامنه دسترسی جاری شما.</p></div>
                <Button asChild variant="outline"><Link to="/operations/shipments">نمای کامل محموله‌ها</Link></Button>
              </div>
              {!data.active_shipments.length ? (
                <Card><CardContent className="p-8 text-center"><p className="font-semibold">محموله فعالی در دامنه دسترسی شما وجود ندارد.</p><p className="mt-2 text-sm text-slate-500">درخواست‌ها و پرونده‌های تجاری همچنان از بخش درخواست‌های کارشناس در دسترس‌اند.</p></CardContent></Card>
              ) : (
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {data.active_shipments.map((shipment) => (
                    <Link key={shipment.public_id} to={`/operations/shipments/${shipment.public_id}`} aria-label={`مشاهده محموله ${customerName(shipment)}`}>
                      <Card className="h-full transition-colors hover:border-blue-300">
                        <CardContent className="space-y-3 p-5">
                          <div className="flex items-start justify-between gap-3"><strong>{customerName(shipment)}</strong><span className="rounded-full bg-blue-50 px-2 py-1 text-xs text-blue-800">{businessLabel(shipment.status)}</span></div>
                          <p className="break-all text-xs text-slate-500">شناسه: <bdi dir="ltr">{shipment.public_id}</bdi></p>
                          <p className="flex items-center gap-2 text-sm"><RouteIcon className="h-4 w-4 shrink-0" />{routeLabel(shipment, direction)}</p>
                          <p className="text-sm text-slate-600">کارشناس مسئول ثابت: {shipment.responsible_expert?.display_name || "نامعلوم"}</p>
                          <p className="text-sm text-slate-600">زمینه جاری: {shipment.current_milestone ? businessLabel(shipment.current_milestone) : "ثبت نشده"}</p>
                          <p className="text-sm text-slate-600">آخرین به‌روزرسانی: {shipment.latest_update ? `${shipment.latest_update.label} · ${formatDualCalendarInstant(shipment.latest_update.recorded_at, locale, { fallback: "نامعلوم" })}` : "رویدادی ثبت نشده است"}</p>
                          {shipment.sla && <p className={`w-fit rounded-full px-2 py-1 text-xs ${slaTone[shipment.sla.status] || "bg-slate-100 text-slate-700"}`}>{shipment.sla.status_label}</p>}
                        </CardContent>
                      </Card>
                    </Link>
                  ))}
                </div>
              )}
            </section>

            <section aria-labelledby="updates-heading" className="space-y-3">
              <h2 id="updates-heading" className="text-xl font-bold">به‌روزرسانی‌های عملیاتی اخیر</h2>
              {!data.recent_updates.length ? (
                <Card><CardContent className="p-6 text-center text-slate-600">هنوز رویداد عملیاتی قابل نمایشی برای محموله‌های فعال ثبت نشده است.</CardContent></Card>
              ) : (
                <Card><CardContent className="divide-y p-0">{data.recent_updates.map((update) => (
                  <Link className="block p-4 hover:bg-slate-50" key={update.event_public_id} to={`/operations/shipments/${update.shipment_public_id}`}>
                    <strong>{update.label} · {businessLabel(update.milestone_type)}</strong>
                    <p className="text-sm text-slate-600">{typeof update.customer === "string" ? update.customer : update.customer?.display_name || "مشتری ثبت نشده"}</p>
                    <p className="text-xs text-slate-500">رخداد: {formatDualCalendarInstant(update.occurred_at, locale, { fallback: "نامعلوم" })} · ثبت: {formatDualCalendarInstant(update.recorded_at, locale, { fallback: "نامعلوم" })}{update.source ? ` · منبع: ${update.source}` : ""}</p>
                  </Link>
                ))}</CardContent></Card>
              )}
            </section>

            <p className="text-xs text-slate-500">این تصویر در {formatDualCalendarInstant(meta.calculated_at, locale, { fallback: "زمان نامعلوم" })} از داده‌های جاری ساخته شده است. نبود داده به‌معنی سلامت یا رعایت SLA تلقی نمی‌شود.</p>
          </>
        )}
      </div>
    </main>
  );
}
