import { useMemo, useState } from "react";
import { Link } from "react-router";
import { AlertCircle, CircleHelp, ExternalLink, RefreshCw } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { drilldownAnalytics, type AnalyticsCoverage, type AnalyticsDrilldownResponse, type AnalyticsResponse } from "@/lib/api";
import type { DashboardSemanticState, WidgetDefinition } from "./types";

export type WidgetResult = { state: DashboardSemanticState; response?: AnalyticsResponse; error?: string; receivedAt?: string };
const number = (value: unknown) => typeof value === "number" ? new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 2 }).format(value) : "—";
const tableValue = (value: unknown) => {
  if (value == null) return "—";
  if (typeof value === "object") {
    const numeric = (value as {value?:unknown}).value;
    if (typeof numeric === "number") return number(numeric);
    const route = value as {origin?:unknown;destination?:unknown;departure?:unknown;arrival?:unknown};
    if (route.origin !== undefined || route.destination !== undefined) return `${String(route.origin ?? "—")} → ${String(route.destination ?? "—")}`;
    if (route.departure !== undefined || route.arrival !== undefined) return `${String(route.departure ?? "—")} — ${String(route.arrival ?? "—")}`;
    return "—";
  }
  return String(value);
};
const coverageVisible = (widget: WidgetDefinition, coverage: AnalyticsCoverage[]) => widget.coverage_policy === "SHOW_ALWAYS" || (widget.coverage_policy === "SHOW_WHEN_PARTIAL" && coverage.some((item) => item.state !== "VALUE" || item.coverage_percent !== 100));
function metricValue(response: AnalyticsResponse, metric: string) {
  const item = response.rows[0]?.[metric] as { value?: number; state?: string } | undefined;
  return item || { value: undefined, state: "NULL_UNKNOWN" };
}
function Coverage({ items, show }: { items: AnalyticsCoverage[]; show: boolean }) {
  if (!show || !items.length) return null;
  return <div className="mt-3 space-y-1 border-t pt-3 text-xs text-muted-foreground">{items.map((item) => <p key={item.coverage_key}>{item.definition}: {item.coverage_percent == null ? "قابل اعمال نیست" : `${number(item.coverage_percent)}٪`} ({number(item.covered_count)} از {number(item.eligible_count)})</p>)}</div>;
}
function WidgetHeader({ widget, result }: { widget: WidgetDefinition; result: WidgetResult }) {
  const response = result.response;
  return <CardHeader className="space-y-1 p-4 pb-2"><div className="flex items-start justify-between gap-2"><div><CardTitle className="text-base">{widget.title}</CardTitle>{widget.description && <CardDescription className="mt-1">{widget.description}</CardDescription>}</div><Tooltip><TooltipTrigger aria-label={`درباره ${widget.title}`}><CircleHelp className="h-4 w-4 text-muted-foreground" /></TooltipTrigger><TooltipContent className="max-w-xs text-xs"><p>نسخه معنایی: {response?.semantic_version || "—"}</p><p>معیار: {widget.query.metric_keys.join(", ")}</p><p>زمان: {widget.query.time_dimension || "پیش‌فرض"} / {widget.query.time_grain || "بدون گروه‌بندی"}</p>{response?.warnings?.length ? <p>هشدار: {response.warnings.join(", ")}</p> : null}</TooltipContent></Tooltip></div></CardHeader>;
}
function StateBody({ result }: { result: WidgetResult }) {
  const labels: Partial<Record<DashboardSemanticState, string>> = { LOADING:"در حال دریافت داده…", EMPTY_ZERO:"داده‌ای برای این بازه وجود ندارد.", UNKNOWN:"مقدار قابل تعیین نیست.", NOT_APPLICABLE:"برای جمعیت فعلی قابل اعمال نیست.", NOT_READY:"این معیار هنوز آماده استفاده نیست.", INCOMPATIBLE_FILTER:"فیلتر فعال با این ویجت سازگار نیست.", ERROR: result.error || "دریافت داده ناموفق بود.", OUT_OF_SCOPE:"دسترسی به این داده مجاز نیست.", STALE_VALUE:"نمایش آخرین مقدار موفق با وضعیت قدیمی." };
  if (result.state === "VALUE" || result.state === "PARTIAL_COVERAGE") return null;
  return <div role={result.state === "ERROR" ? "alert" : "status"} className="flex min-h-24 items-center gap-2 p-4 text-sm text-muted-foreground">{result.state === "LOADING" && <RefreshCw className="h-4 w-4 animate-spin" />}{result.state === "ERROR" && <AlertCircle className="h-4 w-4 text-destructive" />}{labels[result.state]}</div>;
}
function DrilldownLink({ widget, result, segment, onResult }: { widget: WidgetDefinition; result: WidgetResult; segment?: {dimension:string;value:unknown}; onResult: (value:AnalyticsDrilldownResponse) => void }) {
  const [loading, setLoading] = useState(false);
  if (!widget.drilldown.enabled || !result.response || (segment && !widget.drilldown.allow_segment)) return null;
  const metric = widget.query.metric_keys[0];
  const run = async () => {
    setLoading(true);
    try {
      const { data } = await drilldownAnalytics(metric, { ...result.response!.normalized_query, ...(segment ? {segment} : {}) });
      onResult(data);
    } finally { setLoading(false); }
  };
  return <Button variant="link" size="sm" className="px-0" onClick={() => void run()} disabled={loading}>{loading ? "در حال دریافت جزئیات…" : "جزئیات جمعیت"} <ExternalLink className="me-1 h-3 w-3" /></Button>;
}
export function DashboardWidget({ widget, result, notApplicableFilters = [] }: { widget: WidgetDefinition; result: WidgetResult; notApplicableFilters?: string[] }) {
  const response = result.response;
  const metric = widget.query.metric_keys[0];
  const [drilldown, setDrilldown] = useState<AnalyticsDrilldownResponse>();
  const chartData = useMemo(() => (response?.rows || []).map((row) => ({ label: String(row[widget.query.dimension_keys[0]] ?? "ثبت نشده"), value: (row[metric] as { value?: number })?.value ?? null })), [response, widget, metric]);
  const config: ChartConfig = { value: { label: widget.title, color: "hsl(var(--primary))" } };
  return <Card className={`min-w-0 ${widget.layout.col_span >= 2 ? "md:col-span-2" : ""}`}><WidgetHeader widget={widget} result={result} />
    {result.state !== "VALUE" && result.state !== "PARTIAL_COVERAGE" ? <StateBody result={result} /> : <CardContent className="p-4 pt-1">
      {widget.widget_type === "KPI_CARD" ? <div><p className="text-3xl font-bold tabular-nums">{number(metricValue(response!, metric).value)}</p><p className="mt-1 text-xs text-muted-foreground">{response!.columns.find((column) => column.key === metric)?.unit || "تعداد"}</p></div> :
      widget.widget_type === "TABLE" || widget.widget_type === "ATTENTION_LIST" ? <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr>{response!.columns.map((column) => <th key={column.key} className="p-2 text-start">{column.business_name}</th>)}</tr></thead><tbody>{response!.rows.map((row, index) => <tr key={typeof row.shipment_public_id === "string" ? row.shipment_public_id : index} className="border-t">{response!.columns.map((column) => <td key={column.key} className="p-2">{tableValue(row[column.key])}</td>)}</tr>)}</tbody></table></div> :
      <><ChartContainer config={config} className="h-56 w-full"><>{widget.widget_type === "TREND" ? <LineChart data={chartData}><CartesianGrid vertical={false}/><XAxis dataKey="label"/><YAxis/><ChartTooltip content={<ChartTooltipContent />}/><Line type="monotone" dataKey="value" stroke="var(--color-value)" connectNulls={false}/></LineChart> : <BarChart data={chartData}><CartesianGrid vertical={false}/><XAxis dataKey="label"/><YAxis/><ChartTooltip content={<ChartTooltipContent />}/><Bar dataKey="value" fill="var(--color-value)" /></BarChart>}</></ChartContainer><details className="mt-2 text-xs"><summary>نمایش جدولی قابل دسترس</summary><ul>{chartData.map((row) => <li key={row.label}>{row.label}: {row.value == null ? "نامشخص" : <DrilldownLink widget={widget} result={result} segment={{dimension:widget.query.dimension_keys[0],value:row.label}} onResult={setDrilldown}/>}</li>)}</ul></details></>}
      {notApplicableFilters.length > 0 && <p className="mt-3 text-xs text-muted-foreground">این ویجت تحت‌تأثیر فیلتر {notApplicableFilters.join("، ")} نیست.</p>}
      <Coverage items={response!.coverage} show={coverageVisible(widget, response!.coverage)} />
      {response!.warnings.length > 0 && <Alert className="mt-3"><AlertDescription>{response!.warnings.join("، ")}</AlertDescription></Alert>}
      <DrilldownLink widget={widget} result={result} onResult={setDrilldown} />
      {drilldown && <div className="mt-3 border-t pt-3 text-sm"><p className="font-medium">جمعیت معیار</p><ul className="mt-1 space-y-1">{drilldown.items.map((item, index) => <li key={index}>{<ShipmentDetailLink publicId={item.shipment_public_id}/>} {item.route_leg_id ? `· بخش مسیر ${String(item.route_leg_id)}` : ""}</li>)}</ul></div>}
    </CardContent>}</Card>;
}
export function ShipmentDetailLink({ publicId }: { publicId?: unknown }) { return typeof publicId === "string" ? <Link to={`/operations/shipments/${publicId}`}>مشاهده محموله</Link> : null; }
