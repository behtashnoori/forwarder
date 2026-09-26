import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useCurrentAuthorityRefresh } from "@/hooks/useCurrentAuthorityRefresh";
import { useNavigate } from "react-router";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import OperationsNav from "@/components/OperationsNav";
import { cloneSystemDashboard, getAnalyticsSemanticRegistry, getOperationalContext, queryAnalytics, type AnalyticsFilter, type AnalyticsSemanticRegistry } from "@/lib/api";
import { operationsControlTower, operationsControlTowerManifest } from "@/dashboard/control-tower";
import { validateDashboardDefinition } from "@/dashboard/validator";
import { DashboardWidget, type WidgetResult } from "@/dashboard/DashboardWidgets";
import type { WidgetDefinition } from "@/dashboard/types";
import ControlTowerOperationalView from "@/control-tower/ControlTowerOperationalView";

type RuntimeProps = { definition?: import("@/dashboard/types").DashboardDefinition; displayName?: string; displayDescription?: string; sourceContext?: string; allowClone?: boolean; headerAction?:ReactNode };
export default function OperationsControlTower(props: RuntimeProps) {
  if (props.definition === undefined) return <ControlTowerOperationalView />;
  return <SemanticDashboardRuntime {...props} />;
}

function SemanticDashboardRuntime({ definition = operationsControlTower, displayName, displayDescription, sourceContext, allowClone = true, headerAction }: RuntimeProps) {
  const navigate = useNavigate(); const [cloning, setCloning] = useState(false);
  const dashboard = definition;
  const blank = (): Record<string, WidgetResult> => Object.fromEntries(dashboard.widgets.map((widget) => [widget.widget_id, { state:"LOADING" }]));
  const [registry, setRegistry] = useState<AnalyticsSemanticRegistry>(); const [issues, setIssues] = useState<string[]>([]); const [results, setResults] = useState<Record<string, WidgetResult>>(blank); const [filters, setFilters] = useState({ from:"", to:"", customer:"", project:"" }); const [cycle, setCycle] = useState(0); const [lastRefreshed, setLastRefreshed] = useState<string>(); const [allowed, setAllowed] = useState<boolean>(); const [canManageDashboard, setCanManageDashboard] = useState(false); const cycleRef = useRef(0);
  const clone = async () => { if (cloning || !canManageDashboard) return; setCloning(true); try { const {data} = await cloneSystemDashboard(operationsControlTowerManifest.system_dashboard_id); navigate(`/dashboards/${data.public_id}`); } catch { setIssues(["ایجاد نسخه شخصی ناموفق بود. دوباره تلاش کنید."]); } finally { setCloning(false); } };
  const globalFilters = useMemo<AnalyticsFilter[]>(() => [filters.from || filters.to ? { dimension:"TIME", value:{ ...(filters.from ? {from:filters.from}:{}), ...(filters.to ? {to:filters.to}:{}) } } : null, filters.customer ? {dimension:"CUSTOMER",value:filters.customer}:null, filters.project ? {dimension:"PROJECT",value:filters.project}:null].filter(Boolean) as AnalyticsFilter[], [filters]);
  const authorityGeneration = useRef(0);
  const retireAuthority = useCallback(() => {authorityGeneration.current++; cycleRef.current++;}, []);
  const refreshAuthority = useCallback(async () => {
    const current = ++authorityGeneration.current; cycleRef.current++;
    setResults(Object.fromEntries(dashboard.widgets.map(widget => [widget.widget_id, {state: "LOADING"}])));
    try {
      const item = await getOperationalContext();
      if (current !== authorityGeneration.current) return;
      setAllowed(item.data.permissions.includes("operational_shipment.read"));
      setCanManageDashboard(item.data.permissions.includes("personal_dashboard.manage"));
      setCycle(value => value + 1);
    } catch { if (current === authorityGeneration.current) {setAllowed(false); setCanManageDashboard(false);} }
  }, [dashboard]);
  useEffect(() => {void refreshAuthority(); return retireAuthority;}, [refreshAuthority, retireAuthority]);
  useCurrentAuthorityRefresh(refreshAuthority, retireAuthority);
  useEffect(() => { let live = true; getAnalyticsSemanticRegistry().then(({data}) => { if (!live) return; setRegistry(data); setIssues(validateDashboardDefinition(dashboard, data).map((item) => item.message)); }).catch(() => live && setIssues(["دریافت لایه معنایی ممکن نیست."])); return () => { live = false; }; }, [dashboard]);
  useEffect(() => { if (!registry || issues.length || !allowed) return; const current = ++cycleRef.current; setResults(blank()); const queue = [...dashboard.widgets]; const run = async () => { while (queue.length) { const widget = queue.shift()!; const applicable = new Set(dashboard.global_filters.filter((filter) => filter.applicable_widget_ids.includes(widget.widget_id)).map((filter) => filter.dimension_key)); const query = widget.query.query_kind === "ROWSET" ? { query_kind:"ROWSET" as const, semantic_version:widget.query.semantic_version || dashboard.semantic_version, population:widget.query.population, columns:widget.query.columns, filters:[...globalFilters.filter((filter) => applicable.has(filter.dimension)), ...(widget.query.filters || [])], operational_window:widget.query.operational_window, sort:typeof widget.query.sort === "object" ? widget.query.sort : undefined, limit:widget.query.limit } : { metrics:widget.query.metric_keys, dimensions:widget.query.dimension_keys, filters:[...globalFilters.filter((filter) => applicable.has(filter.dimension)), ...(widget.query.filters || [])], time_dimension:widget.query.time_dimension, time_grain:widget.query.time_grain, limit:widget.query.limit }; try { const {data} = await queryAnalytics(query); if (cycleRef.current === current) setResults((old) => ({...old,[widget.widget_id]:{state:data.coverage.some((item) => item.state !== "VALUE") || data.warnings.length ? "PARTIAL_COVERAGE":"VALUE",response:data,receivedAt:new Date().toISOString()}})); } catch (error) { if (cycleRef.current === current) setResults((old) => ({...old,[widget.widget_id]:{state:"ERROR",error:error instanceof Error ? error.message : "Query failed."}})); } } };
    Promise.all(Array.from({length:4}, run)).then(() => current === cycleRef.current && setLastRefreshed(new Date().toISOString())); }, [registry, issues.length, allowed, globalFilters, cycle]);
  useEffect(() => { const timer = window.setInterval(() => { if (!document.hidden) setCycle((value) => value + 1); }, 120000); return () => window.clearInterval(timer); }, []);
  if (allowed === false && allowClone) return <main className="min-h-screen bg-slate-50 p-4"><OperationsNav/><Alert className="mx-auto mt-6 max-w-xl"><AlertDescription>مجوز مشاهده عملیات برای نمایش برج کنترل لازم است.</AlertDescription></Alert></main>;
  return <main dir="rtl" className="min-h-screen bg-slate-50 p-3 sm:p-5 md:p-8" aria-busy={!registry}><div className="mx-auto max-w-7xl space-y-5"><OperationsNav/><header className="flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-2xl font-bold">{displayName || dashboard.name}</h1><p className="text-sm text-muted-foreground">{displayDescription ?? dashboard.description}</p>{sourceContext && <p className="mt-1 text-xs text-muted-foreground">{sourceContext}</p>}{lastRefreshed && <p className="mt-1 text-xs text-muted-foreground">آخرین به‌روزرسانی: {new Date(lastRefreshed).toLocaleString("fa-IR")} · چرخه {cycle}</p>}</div><div className="flex gap-2">{headerAction}{allowClone && canManageDashboard && <Button variant="outline" disabled={cloning} onClick={() => void clone()}>{cloning ? "در حال ایجاد…" : "ایجاد نسخه شخصی"}</Button>}<Button onClick={() => setCycle((value) => value + 1)}><RefreshCw className="ms-2 h-4 w-4" />به‌روزرسانی</Button></div></header>
    <section aria-label="فیلترهای سراسری" className="grid gap-3 rounded-lg border bg-card p-4 sm:grid-cols-2 lg:grid-cols-4"><Input aria-label="شروع بازه زمانی" type="datetime-local" value={filters.from} onChange={(event) => setFilters({...filters,from:event.target.value ? new Date(event.target.value).toISOString():""})}/><Input aria-label="پایان بازه زمانی" type="datetime-local" value={filters.to} onChange={(event) => setFilters({...filters,to:event.target.value ? new Date(event.target.value).toISOString():""})}/><Input aria-label="شناسه مشتری" placeholder="شناسه مشتری، مانند customer:1" value={filters.customer} onChange={(event) => setFilters({...filters,customer:event.target.value})}/><Input aria-label="شناسه پروژه" placeholder="شناسه عمومی پروژه" value={filters.project} onChange={(event) => setFilters({...filters,project:event.target.value})}/></section>
    {allowed === false && !allowClone && <Alert><AlertDescription>فضای داشبورد در دسترس است، اما ابزارک‌های حمل‌ونقل بدون مجوز زندهٔ مشاهده عملیات داده‌ای نمایش نمی‌دهند.</AlertDescription></Alert>}
    {issues.length > 0 && <Alert variant="destructive"><AlertDescription>{issues.join(" ")}</AlertDescription></Alert>}
    {dashboard.sections.map((section) => <section key={section.section_id} aria-labelledby={section.section_id}><h2 id={section.section_id} className="mb-3 text-lg font-semibold">{section.title}</h2><div className="grid grid-cols-1 gap-4 md:grid-cols-4">{section.widget_ids.map((id) => { const widget = dashboard.widgets.find((item) => item.widget_id === id) as WidgetDefinition; const inactive = globalFilters.filter((filter) => !dashboard.global_filters.some((definition) => definition.dimension_key === filter.dimension && definition.applicable_widget_ids.includes(id))).map((filter) => dashboard.global_filters.find((definition) => definition.dimension_key === filter.dimension)?.label || filter.dimension); const span={1:"md:col-span-1",2:"md:col-span-2",3:"md:col-span-3",4:"md:col-span-4"}[widget.layout.col_span]; return <div key={id} className={span}><DashboardWidget widget={widget} result={results[id] || {state:"LOADING"}} notApplicableFilters={inactive} /></div>; })}</div></section>)}</div></main>;
}
