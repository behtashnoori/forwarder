import type { OperationalLocationRef, RequestedEndpoints } from "@/lib/api";

function endpointDifference(requested: RequestedEndpoints["origin"], actual?: OperationalLocationRef | null) {
  const ref = requested.reference;
  if (!ref || !actual) return "UNKNOWN";
  if (ref.source_type === actual.source_type) return String(ref.source_id) === String(actual.source_id) ? "SAME" : "DIFFERENT";
  return "PRECISION";
}

export default function RequestedEndpointComparison({ requested, origin, destination }: {
  requested?: RequestedEndpoints | null;
  origin: { label: string; reference?: OperationalLocationRef | null };
  destination: { label: string; reference?: OperationalLocationRef | null };
}) {
  return <section className="space-y-3 rounded border bg-slate-50 p-3 text-sm" aria-label="مقایسه محل درخواستی و برنامه عملیاتی">
    <h3 className="font-semibold">مبدأ و مقصد درخواستی مشتری</h3>
    {requested ? <p>{requested.origin.label} ← {requested.destination.label}</p> : <p>جزئیات محل درخواست در دسترس نیست.</p>}
    <h3 className="font-semibold">مبدأ و مقصد برنامه عملیاتی</h3>
    <p>{origin.label} ← {destination.label}</p>
    {requested && (["origin", "destination"] as const).map(side => {
      const difference = endpointDifference(requested[side], side === "origin" ? origin.reference : destination.reference);
      const label = side === "origin" ? "مبدأ" : "مقصد";
      return difference === "DIFFERENT" ? <p key={side} className="text-amber-900">{label} برنامه عملیاتی با محل درخواستی مشتری متفاوت است.</p> : difference === "PRECISION" ? <p key={side}>{label} درخواست و برنامه با نوع یا دقت مکانی متفاوت ثبت شده‌اند؛ مقایسه دقیق یکسان بودن ممکن نیست.</p> : null;
    })}
    <p className="text-xs text-slate-500">محل درخواست از منبع مرتبط خوانده می‌شود؛ این نمایش، تأیید یا دلیل تاریخی تفاوت نیست.</p>
  </section>;
}
