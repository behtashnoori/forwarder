import type { OipProjectionHealth } from "@/lib/api";
import { useI18n } from "@/i18n";

export function ProjectionHealthNotice({
  health,
}: {
  health: OipProjectionHealth;
}) {
  const { businessLabel } = useI18n();
  const message =
    health.health_state === "FRESH"
      ? "تصویر تحلیلی با منابع معتبر همگام است."
      : health.health_state === "STALE"
        ? "تصویر تحلیلی ممکن است قدیمی باشد؛ واقعیت‌ها و اقدامات عملیاتی همچنان مرجع هستند."
        : health.health_state === "REBUILDING"
          ? "تصویر تحلیلی در حال بازسازی است؛ واقعیت عملیاتی همچنان قابل استفاده است."
          : "قابلیت اتکای تصویر تحلیلی کاهش یافته است؛ واقعیت عملیاتی همچنان قابل استفاده است.";
  const trusted = health.health_state === "FRESH";
  return (
    <div
      role={trusted ? "status" : "alert"}
      data-testid="projection-health"
      className={`rounded border p-3 ${trusted ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-amber-300 bg-amber-50 text-amber-900"}`}
    >
      <b>سلامت تصویر تحلیلی: {businessLabel(health.health_state)}</b>
      <p>{message}</p>
      {health.reason_code && (
        <details className="text-xs">
          <summary>جزئیات فنی</summary>
          <bdi dir="ltr">{health.reason_code}</bdi>
        </details>
      )}
    </div>
  );
}
