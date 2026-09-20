import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Link } from "react-router";
import { AlertTriangle, MapPin, RefreshCw, Route, UserRound } from "lucide-react";
import OperationsNav from "@/components/OperationsNav";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useI18n } from "@/i18n";
import { formatBusinessNumber } from "@/lib/formatQuantity";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import {
  classifyControlTowerFailure,
  getControlTowerPage,
  type ControlTowerAttention,
  type ControlTowerFailure,
  type ControlTowerItem,
  type ControlTowerReason,
  type ControlTowerRequestTransport,
} from "./api";

const attentionFilters: Array<{ value?: ControlTowerAttention; label: string }> = [
  { label: "همه موارد" },
  { value: "urgent", label: "فوری" },
  { value: "follow_up", label: "پیگیری" },
  { value: "review", label: "بررسی" },
];

const attentionTone: Record<ControlTowerAttention, string> = {
  urgent: "border-red-200 bg-red-50 text-red-800",
  follow_up: "border-orange-200 bg-orange-50 text-orange-800",
  review: "border-amber-200 bg-amber-50 text-amber-900",
};

const errorMessages: Record<ControlTowerFailure, string> = {
  unauthorized: "نشست شما برای مشاهده برج کنترل معتبر نیست. دوباره وارد سامانه شوید.",
  forbidden: "مجوز مشاهده برج کنترل برای حساب فعلی در دسترس نیست.",
  unavailable: "ارزیابی کامل برج کنترل اکنون در دسترس نیست. برای جلوگیری از نمایش اطلاعات ناقص، هیچ فهرستی نمایش داده نمی‌شود.",
  general: "دریافت اطلاعات برج کنترل کامل نشد. دوباره تلاش کنید.",
};

function sessionContext(): string {
  return `${localStorage.getItem("expert_user") ?? ""}\n${localStorage.getItem("expert_token") ?? ""}`;
}

function subscribeSession(onChange: () => void): () => void {
  window.addEventListener("storage", onChange);
  window.addEventListener("focus", onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener("focus", onChange);
  };
}

function SafeTime({ value, locale }: { value: string; locale: string }) {
  const formatted = formatDualCalendarInstant(value, locale, { fallback: "", timeZoneName: "short" });
  if (!formatted) return null;
  return <time dateTime={value} dir="auto">{formatted}</time>;
}

function ReasonTimes({ reason, locale }: { reason: ControlTowerReason; locale: string }) {
  return <>{reason.time.map(({ label, at }, index) => (
    label && <p key={`${label}-${index}`} className="text-xs text-slate-600">
      {label}: <SafeTime value={at} locale={locale} />
    </p>
  ))}</>;
}

function RequestTransportFacts({ value }: { value: ControlTowerRequestTransport | null }) {
  const { shippingTypeLabel, transportLabel } = useI18n();
  const facts = value ? [
    value.shippingType && { label: "نوع درخواست", value: shippingTypeLabel(value.shippingType) },
    value.transportMethod && { label: "روش حمل ثبت‌شده", value: transportLabel(value.transportMethod) },
    value.internationalTransportMethod && { label: "بخش بین‌المللی", value: transportLabel(value.internationalTransportMethod) },
    value.domesticTransportMethod && { label: "بخش داخلی", value: transportLabel(value.domesticTransportMethod) },
    value.transportMethodPreference && { label: "ترجیح درخواست", value: transportLabel(value.transportMethodPreference) },
  ].filter(Boolean) as Array<{ label: string; value: string }> : [];

  if (!facts.length) return <p className="text-sm text-slate-500">در درخواست ثبت نشده است.</p>;
  return <dl className="space-y-1 text-sm">{facts.map((fact) => (
    <div key={fact.label} className="flex flex-wrap gap-1">
      <dt className="text-slate-500">{fact.label}:</dt><dd>{fact.value}</dd>
    </div>
  ))}</dl>;
}

function AttentionCard({ item }: { item: ControlTowerItem }) {
  const { businessLabel, locale, transportLabel } = useI18n();
  const actualModes = item.actualRouteModes.map(transportLabel);
  return <Card className="min-w-0 border-s-4 bg-white">
    <CardHeader className="space-y-3 pb-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <Badge variant="outline" className={attentionTone[item.attention]}>{item.attentionLabel}</Badge>
          <CardTitle className="min-w-0 break-all text-lg"><span className="font-normal text-slate-500">محموله </span><bdi>{item.shipmentReference}</bdi></CardTitle>
        </div>
        <Badge variant="secondary">{businessLabel(item.operationalStatus)}</Badge>
      </div>
      <div className="grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
        <p className="flex items-center gap-2"><UserRound className="h-4 w-4 shrink-0" />مسئول فعلی: {item.ownerName ?? "ثبت نشده"}</p>
        <p className="flex items-center gap-2"><MapPin className="h-4 w-4 shrink-0" />مکان فعلی: {item.progress.currentLocation ?? "ثبت نشده"}</p>
      </div>
    </CardHeader>
    <CardContent className="space-y-4">
      <section className="grid gap-3 rounded-lg bg-slate-50 p-3 md:grid-cols-2" aria-label="حمل درخواستی و مسیر واقعی">
        <div className="min-w-0">
          <h3 className="mb-2 font-semibold">روش حمل در درخواست</h3>
          <RequestTransportFacts value={item.requestTransport} />
        </div>
        <div className="min-w-0 border-t pt-3 md:border-s md:border-t-0 md:ps-3 md:pt-0">
          <h3 className="mb-2 flex items-center gap-2 font-semibold"><Route className="h-4 w-4" />مسیر اجرایی واقعی</h3>
          <p className="break-words text-sm">{item.routeLabel ?? "مسیر فعال ثبت نشده است."}</p>
          <p className="mt-1 text-sm text-slate-600">{actualModes.length ? actualModes.join(" ← ") : "روش حمل اجرایی ثبت نشده است."}</p>
          {item.transportLabel && <p className="mt-1 text-xs text-slate-500">خلاصه مسیر: {item.transportLabel}</p>}
        </div>
      </section>

      <section className="space-y-2" aria-label="دلیل نیاز به توجه">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="flex items-center gap-2 text-base font-semibold"><AlertTriangle className="h-4 w-4" />{item.primaryReason.title}</h3>
          <span className="text-xs text-slate-500">{formatBusinessNumber(item.workSummary.reasonCount, { locale })} مورد باز</span>
        </div>
        <p className="text-sm leading-6 text-slate-600">{item.primaryReason.explanation}</p>
        <ReasonTimes reason={item.primaryReason} locale={locale} />
      </section>

      {item.additionalReasons.length > 0 && <details className="rounded-lg border p-3">
        <summary className="cursor-pointer text-sm font-medium">سایر موارد نیازمند توجه</summary>
        <ul className="mt-3 space-y-3">{item.additionalReasons.map((reason, index) => <li key={`${reason.semantic}-${index}`} className="text-sm">
          <p className="font-medium">{reason.title}</p>
          <p className="text-slate-600">{reason.explanation}</p>
          <ReasonTimes reason={reason} locale={locale} />
        </li>)}</ul>
      </details>}

      <section className="grid gap-2 rounded-lg border p-3 text-sm sm:grid-cols-2" aria-label="آخرین رهگیری">
        <p>آخرین رخداد: {item.progress.latestEventType ? businessLabel(item.progress.latestEventType) : "ثبت نشده"}</p>
        <p>واحدهای رهگیری: {formatBusinessNumber(item.progress.unitCount, { locale })}</p>
        <p>زمان وقوع آخرین رخداد: {item.progress.latestEventOccurredAt ? <SafeTime value={item.progress.latestEventOccurredAt} locale={locale} /> : "ثبت نشده"}</p>
        <p>زمان ثبت آخرین رخداد: {item.progress.latestEventRecordedAt ? <SafeTime value={item.progress.latestEventRecordedAt} locale={locale} /> : "ثبت نشده"}</p>
      </section>

      <div className="flex justify-end">
        <Button asChild variant="outline" className="w-full sm:w-auto"><Link to={item.destination}>مشاهده جزئیات محموله</Link></Button>
      </div>
    </CardContent>
  </Card>;
}

function LoadingState() {
  return <div role="status" className="space-y-3" aria-label="در حال دریافت برج کنترل">
    <p className="text-sm text-slate-600">در حال دریافت وضعیت محموله‌ها…</p>
    <Skeleton className="h-64 w-full rounded-xl" />
  </div>;
}

function Tower({ context }: { context: string }) {
  const [attention, setAttention] = useState<ControlTowerAttention>();
  const [items, setItems] = useState<ControlTowerItem[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [emptyMessage, setEmptyMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [failure, setFailure] = useState<ControlTowerFailure>();
  const [moreFailed, setMoreFailed] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const generation = useRef(0);
  const pendingMore = useRef(false);

  const retire = useCallback((error: unknown, requestGeneration: number, pagination = false) => {
    if (generation.current !== requestGeneration || sessionContext() !== context) return;
    const kind = classifyControlTowerFailure(error);
    if (pagination && kind === "general") {
      setMoreFailed(true);
      return;
    }
    generation.current += 1;
    pendingMore.current = false;
    setItems([]);
    setCursor(null);
    setEmptyMessage(null);
    setLoadingMore(false);
    setMoreFailed(false);
    setFailure(kind);
    setLoading(false);
  }, [context]);

  useEffect(() => {
    const requestGeneration = ++generation.current;
    setItems([]);
    setCursor(null);
    setFailure(undefined);
    setMoreFailed(false);
    setLoading(true);
    pendingMore.current = false;
    getControlTowerPage(attention).then((page) => {
      if (generation.current !== requestGeneration || sessionContext() !== context) return;
      setItems(page.items);
      setCursor(page.page.nextCursor);
      setEmptyMessage(page.emptyMessage);
      setLoading(false);
    }).catch((error: unknown) => retire(error, requestGeneration));
    return () => { generation.current = requestGeneration + 1; };
  }, [attention, reloadKey, context, retire]);

  function changeFilter(value?: ControlTowerAttention) {
    if (attention === value) return;
    setAttention(value);
  }

  async function loadMore() {
    if (!cursor || pendingMore.current) return;
    const requestGeneration = generation.current;
    const opaqueCursor = cursor;
    pendingMore.current = true;
    setLoadingMore(true);
    setMoreFailed(false);
    try {
      const page = await getControlTowerPage(attention, opaqueCursor);
      if (generation.current !== requestGeneration || sessionContext() !== context) return;
      setItems((current) => [...current, ...page.items.filter((item) => !current.some((old) => old.key === item.key))]);
      setCursor(page.page.nextCursor);
    } catch (error) {
      retire(error, requestGeneration, true);
    } finally {
      if (generation.current === requestGeneration) {
        pendingMore.current = false;
        setLoadingMore(false);
      }
    }
  }

  return <main dir="rtl" lang="fa" className="min-h-screen bg-slate-50 p-3 sm:p-5 md:p-8" aria-busy={loading}>
    <div className="mx-auto max-w-6xl space-y-5">
      <OperationsNav />
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div><h1 className="text-2xl font-bold sm:text-3xl">برج کنترل عملیات</h1><p className="mt-1 text-sm leading-6 text-slate-600">نمای عملیاتی محموله‌های فعال و موارد نیازمند توجه</p></div>
        <Button variant="outline" disabled={loading} onClick={() => setReloadKey((value) => value + 1)}><RefreshCw className="ms-2 h-4 w-4" />به‌روزرسانی</Button>
      </header>
      <div role="group" aria-label="فیلتر سطح توجه" className="flex flex-wrap gap-2">{attentionFilters.map((filter) => <Button
        key={filter.value ?? "all"}
        variant={attention === filter.value ? "default" : "outline"}
        aria-pressed={attention === filter.value}
        onClick={() => changeFilter(filter.value)}
      >{filter.label}</Button>)}</div>

      {loading ? <LoadingState />
        : failure ? <Alert variant={failure === "unavailable" || failure === "general" ? "destructive" : "default"} role="alert"><AlertDescription className="space-y-3"><p>{errorMessages[failure]}</p><Button variant="outline" onClick={() => setReloadKey((value) => value + 1)}>تلاش دوباره</Button></AlertDescription></Alert>
        : items.length === 0 ? <p role="status" className="rounded-xl border bg-white p-6 leading-7">{emptyMessage ?? "در حال حاضر محموله فعالی با این سطح توجه برای شما نمایش داده نمی‌شود."}</p>
        : <section aria-label="محموله‌های نیازمند توجه" className="space-y-4">{items.map((item) => <AttentionCard key={item.key} item={item} />)}</section>}

      {!loading && !failure && cursor && <div className="space-y-2">
        {moreFailed && <p role="alert" className="text-sm text-red-700">دریافت ادامه فهرست کامل نشد؛ موارد نمایش‌داده‌شده حفظ شدند.</p>}
        <Button variant="outline" disabled={loadingMore} onClick={() => void loadMore()}>{loadingMore ? "در حال دریافت…" : moreFailed ? "تلاش دوباره" : "نمایش موارد بیشتر"}</Button>
      </div>}
    </div>
  </main>;
}

export default function ControlTowerOperationalView() {
  const context = useSyncExternalStore(subscribeSession, sessionContext);
  return <Tower key={context} context={context} />;
}
