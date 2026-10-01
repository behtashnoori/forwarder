import type { ReactNode } from "react";
import { CheckCircle2, Circle, Clock3, Target } from "lucide-react";

export type CommercialProgressState =
  "complete" | "current" | "pending" | "not_applicable";

export interface CommercialProgressStep {
  label: string;
  state: CommercialProgressState;
  detail?: string;
}

export interface CommercialProgressFact {
  label: string;
  value: ReactNode;
  ltr?: boolean;
}

interface CommercialProgressProps {
  title: string;
  eyebrow?: string;
  facts: CommercialProgressFact[];
  steps: CommercialProgressStep[];
  nextAction: string;
  nextActionDescription: string;
  action?: ReactNode;
}

const stateLabel: Record<CommercialProgressState, string> = {
  complete: "انجام‌شده",
  current: "در حال پیگیری",
  pending: "در انتظار",
  not_applicable: "در این مسیر لازم نیست",
};

export default function CommercialProgress({
  title,
  eyebrow = "مسیر تجاری درخواست",
  facts,
  steps,
  nextAction,
  nextActionDescription,
  action,
}: CommercialProgressProps) {
  return (
    <section
      aria-label="راهنمای تجاری درخواست"
      className="overflow-hidden rounded-3xl border border-blue-100 bg-white shadow-sm"
    >
      <header className="border-b border-blue-100 bg-blue-50/70 px-5 py-4 sm:px-6">
        <p className="text-xs font-semibold text-blue-700">{eyebrow}</p>
        <h2 className="mt-1 text-xl font-bold text-slate-950">{title}</h2>
      </header>

      <div className="grid gap-0 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
        <div className="space-y-4 p-5 sm:p-6">
          <div className="grid gap-2 sm:grid-cols-2">
            {facts.map((fact) => (
              <div
                key={fact.label}
                className="min-w-0 border-b border-slate-100 pb-2 last:border-b-0 sm:last:border-b"
              >
                <p className="text-xs text-slate-500">{fact.label}</p>
                <div
                  className="mt-1 break-words text-sm font-semibold text-slate-900"
                  dir={fact.ltr ? "ltr" : undefined}
                >
                  {fact.value}
                </div>
              </div>
            ))}
          </div>

          <div
            className="rounded-2xl bg-blue-600 p-4 text-white shadow-sm"
            aria-label="اقدام تجاری بعدی"
          >
            <div className="flex items-start gap-3">
              <Target className="mt-0.5 h-5 w-5 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-xs text-blue-100">اقدام بعدی</p>
                <p className="mt-1 text-lg font-bold">{nextAction}</p>
                <p className="mt-1 text-sm leading-6 text-blue-50">
                  {nextActionDescription}
                </p>
                {action && (
                  <div className="mt-4 flex flex-wrap gap-2">{action}</div>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-slate-100 bg-slate-50/60 p-5 sm:p-6 lg:border-r lg:border-t-0">
          <div className="mb-4">
            <h3 className="font-bold text-slate-950">پیشرفت تجاری</h3>
            <p className="mt-1 text-xs leading-5 text-slate-500">
              این فهرست آمادگی را خلاصه می‌کند؛ مذاکره می‌تواند چند دور تکرار
              شود.
            </p>
          </div>
          <ol className="space-y-3">
            {steps.map((step) => {
              const Icon =
                step.state === "complete"
                  ? CheckCircle2
                  : step.state === "current"
                    ? Clock3
                    : Circle;
              const tone =
                step.state === "complete"
                  ? "text-emerald-700"
                  : step.state === "current"
                    ? "text-blue-700"
                    : "text-slate-400";
              return (
                <li key={step.label} className="flex items-start gap-3">
                  <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${tone}`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-sm font-semibold text-slate-900">
                        {step.label}
                      </span>
                      <span className={`text-xs ${tone}`}>
                        {stateLabel[step.state]}
                      </span>
                    </div>
                    {step.detail && (
                      <p className="mt-1 text-xs leading-5 text-slate-500">
                        {step.detail}
                      </p>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      </div>
    </section>
  );
}
