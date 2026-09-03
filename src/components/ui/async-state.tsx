import { Button } from "@/components/ui/button";
import type { ReactNode } from "react";

export function LoadingState({ label = "در حال دریافت اطلاعات…" }: { label?: string }) {
  return <p role="status" aria-live="polite" className="rounded border p-4 text-sm text-muted-foreground">{label}</p>;
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <p className="rounded border border-dashed p-4 text-sm text-muted-foreground">{children}</p>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div role="alert" className="flex flex-wrap items-center gap-3 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800"><span>{message}</span>{onRetry && <Button type="button" variant="outline" size="sm" onClick={onRetry}>تلاش مجدد</Button>}</div>;
}
