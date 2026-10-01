import {
  AlertTriangle,
  Check,
  CircleDashed,
  Clock3,
  MapPin,
  Route as RouteIcon,
} from "lucide-react";
import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import type { OperationalProjection } from "@/lib/api";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";

const statusLabel: Record<string, string> = {
  DONE: "کامل",
  NOT_APPLICABLE: "نامرتبط",
  READY: "آماده",
  IN_PROGRESS: "در جریان",
  NEEDS_ACTION: "نیازمند اقدام",
  BLOCKED: "مسدود",
  UNKNOWN: "نامشخص",
};

const locationLabel = (value: unknown) => {
  if (typeof value === "string") return value;
  if (value && typeof value === "object") {
    const candidate = value as {
      display_name?: string;
      free_text?: string;
      label?: string;
    };
    return (
      candidate.display_name ||
      candidate.free_text ||
      candidate.label ||
      "موقعیت ثبت‌شده"
    );
  }
  return "موقعیت ثبت نشده";
};

export default function OperationalGuidance({
  projection,
  locale = "fa",
}: {
  projection: OperationalProjection;
  locale?: string;
}) {
  const stage = projection.stage_progress;
  const eta = projection.current_operation.eta;
  const position = projection.current_operation.latest_position;
  return (
    <section aria-labelledby="guided-operation-heading" className="space-y-4">
      <div className="grid gap-3 lg:grid-cols-[1.3fr_1fr]">
        <div className="rounded-2xl border border-blue-200 bg-gradient-to-br from-blue-50 to-white p-4 sm:p-5">
          <p className="text-xs font-bold text-blue-700">
            اکنون کجای کار هستیم؟
          </p>
          <h2
            id="guided-operation-heading"
            className="mt-1 text-xl font-black text-slate-950"
          >
            {stage.current?.display_name_fa ||
              (stage.total
                ? "همه مراحل ثبت‌شده کامل‌اند"
                : "مراحل عملیاتی هنوز پیکربندی نشده‌اند")}
          </h2>
          <div
            className="mt-4 h-2 overflow-hidden rounded-full bg-blue-100"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={stage.total || 1}
            aria-valuenow={stage.completed}
            aria-label="پیشرفت مراحل عملیاتی"
          >
            <div
              className="h-full rounded-full bg-blue-700"
              style={{
                width: `${stage.total ? (stage.completed * 100) / stage.total : 0}%`,
              }}
            />
          </div>
          <p className="mt-2 text-sm text-slate-600">
            {stage.completed} از {stage.total || "—"} مرحله کامل شده است. مرحله
            فرایند با آمادگی کارها یکی نیست.
          </p>
          {!!stage.items.length && (
            <ol
              className="mt-4 grid gap-2 sm:grid-cols-5"
              aria-label="مراحل فرایند"
            >
              {stage.items.map((item, index) => (
                <li
                  key={item.code}
                  className={`rounded-lg border p-2 text-xs ${item.status === "COMPLETED" ? "border-emerald-200 bg-emerald-50 text-emerald-900" : item.code === stage.current?.code ? "border-blue-300 bg-white font-bold text-blue-900" : "border-slate-200 bg-white text-slate-500"}`}
                >
                  <span className="mb-1 block">
                    {item.status === "COMPLETED" ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <CircleDashed className="h-4 w-4" />
                    )}
                  </span>
                  {index + 1}. {item.display_name_fa}
                </li>
              ))}
            </ol>
          )}
        </div>
        <div
          className={`rounded-2xl border p-4 sm:p-5 ${projection.recommended_action ? "border-blue-300 bg-slate-950 text-white" : "border-slate-200 bg-white"}`}
        >
          <p
            className={`text-xs font-bold ${projection.recommended_action ? "text-blue-200" : "text-slate-500"}`}
          >
            بهترین اقدام بعدی
          </p>
          {projection.recommended_action ? (
            <>
              <h2 className="mt-1 text-xl font-black">
                {projection.recommended_action.label}
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-300">
                {projection.recommended_action.reason}
              </p>
              <Button
                asChild
                className="mt-4 min-h-11 bg-white text-slate-950 hover:bg-blue-50"
              >
                <Link to={projection.recommended_action.href}>
                  رفتن به اقدام
                </Link>
              </Button>
            </>
          ) : (
            <>
              <h2 className="mt-1 text-lg font-bold">
                اقدام مجازی پیشنهاد نمی‌شود
              </h2>
              <p className="mt-2 text-sm text-slate-600">
                پرونده بسته است، اختیار اقدام ندارید، یا واقعیت کافی برای
                پیشنهاد امن وجود ندارد.
              </p>
            </>
          )}
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <article className="rounded-xl border bg-white p-4">
          <div className="flex items-center gap-2 text-sm font-bold">
            <MapPin className="h-4 w-4 text-blue-700" />
            آخرین موقعیت
          </div>
          <p className="mt-2 font-semibold">
            {position ? locationLabel(position.label) : "هنوز ثبت نشده"}
          </p>
          {position?.reported_at && (
            <p className="mt-1 text-xs text-slate-500">
              زمان رخداد:{" "}
              {formatDualCalendarInstant(position.reported_at, locale, {
                fallback: "نامعلوم",
              })}
            </p>
          )}
        </article>
        <article className="rounded-xl border bg-white p-4">
          <div className="flex items-center gap-2 text-sm font-bold">
            <Clock3 className="h-4 w-4 text-blue-700" />
            ETA نهایی
          </div>
          {eta.available ? (
            <>
              <p className="mt-2 font-semibold">
                {formatDualCalendarInstant(eta.earliest, locale, {
                  fallback: "نامعلوم",
                })}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                تا{" "}
                {formatDualCalendarInstant(eta.latest, locale, {
                  fallback: "نامعلوم",
                })}
              </p>
            </>
          ) : (
            <>
              <p className="mt-2 font-semibold">در دسترس نیست</p>
              <p className="mt-1 text-xs text-slate-500">
                {eta.message || eta.reason || "مبنای کافی ثبت نشده است"}
              </p>
            </>
          )}
        </article>
        <article className="rounded-xl border bg-white p-4">
          <div className="flex items-center gap-2 text-sm font-bold">
            <RouteIcon className="h-4 w-4 text-blue-700" />
            آمادگی کارها
          </div>
          <p className="mt-2 text-2xl font-black">
            {projection.readiness.percent}٪
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {projection.readiness.completed} از {projection.readiness.total} کار
            · {projection.readiness.blocker_count} مانع
          </p>
        </article>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <section
          className="rounded-xl border bg-white p-4"
          aria-labelledby="task-readiness-heading"
        >
          <h3 id="task-readiness-heading" className="font-bold">
            آمادگی کارها
          </h3>
          <ul className="mt-3 grid gap-2 sm:grid-cols-2">
            {projection.tasks.map((task) => (
              <li
                key={task.key}
                className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 p-2 text-sm"
              >
                <span>{task.label}</span>
                <strong
                  className={
                    task.status === "DONE" || task.status === "READY"
                      ? "text-emerald-700"
                      : task.status === "BLOCKED" ||
                          task.status === "NEEDS_ACTION"
                        ? "text-amber-800"
                        : "text-slate-600"
                  }
                >
                  {statusLabel[task.status] || "وضعیت ثبت‌شده"}
                </strong>
              </li>
            ))}
          </ul>
        </section>
        <section
          className="rounded-xl border bg-white p-4"
          aria-labelledby="attention-items-heading"
        >
          <h3 id="attention-items-heading" className="font-bold">
            موارد نیازمند توجه
          </h3>
          {projection.attention.length ? (
            <ul className="mt-3 space-y-2">
              {projection.attention.slice(0, 4).map((item) => (
                <li
                  key={item.key}
                  className="flex gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm"
                >
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                  <span>
                    <strong>{item.label}</strong>
                    <span className="mt-1 block text-xs text-amber-900">
                      {item.reason}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">
              در واقعیت‌های جاری مورد نیازمند توجهی دیده نشد. این پیام جایگزین
              ثبت واقعیت‌های ناقص نیست.
            </p>
          )}
        </section>
      </div>
      <details className="text-xs text-slate-500">
        <summary className="cursor-pointer">تازگی و منابع این تصویر</summary>
        <p className="mt-2">
          نسخه {projection.meta.projection_version} · محاسبه در{" "}
          {formatDualCalendarInstant(projection.meta.calculated_at, locale, {
            fallback: "نامعلوم",
          })}{" "}
          · بازسازی از منابع جاری و بدون ذخیره حقیقت تکراری.
        </p>
      </details>
    </section>
  );
}
