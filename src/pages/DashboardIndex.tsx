import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router";
import { LayoutDashboard, Plus } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cloneSystemDashboard, getOperationalContext, listDashboards } from "@/lib/api";
import { operationsControlTowerManifest } from "@/dashboard/control-tower";

export default function DashboardIndex() {
  const navigate = useNavigate();
  const client = useQueryClient();
  const context = useQuery({queryKey:["operational-context"], queryFn:getOperationalContext, retry:false});
  const dashboards = useQuery({queryKey:["dashboard","list"], queryFn:listDashboards, retry:false});
  const permissions = context.data?.data.permissions || [];
  const canManage = permissions.includes("personal_dashboard.manage");
  const create = useMutation({
    mutationFn:() => cloneSystemDashboard(operationsControlTowerManifest.system_dashboard_id),
    onSuccess:({data}) => { void client.invalidateQueries({queryKey:["dashboard","list"]}); navigate(`/dashboards/${data.public_id}/edit`); },
  });
  if (context.isLoading || dashboards.isLoading) return <main dir="rtl" className="min-h-screen bg-slate-50 p-6" aria-busy="true"><div className="mx-auto max-w-5xl space-y-4"><div className="h-10 w-56 animate-pulse rounded bg-muted"/><div className="h-40 animate-pulse rounded bg-muted"/></div></main>;
  if (context.isError || dashboards.isError) return <main dir="rtl" className="min-h-screen bg-slate-50 p-6"><Alert className="mx-auto max-w-2xl" variant="destructive"><AlertDescription>دریافت داشبوردهای شخصی ممکن نیست یا مجوز لازم را ندارید.</AlertDescription></Alert></main>;
  const rows = dashboards.data?.data || [];
  return <main dir="rtl" className="min-h-screen bg-slate-50 p-4 sm:p-8"><div className="mx-auto max-w-5xl space-y-6">
    <header className="flex flex-wrap items-center justify-between gap-3"><div><h1 className="text-2xl font-bold">داشبوردهای من</h1><p className="text-muted-foreground">فضای شخصی تحلیل و پیگیری شما</p></div>{canManage && <Button onClick={() => create.mutate()} disabled={create.isPending}><Plus className="ml-2 h-4 w-4"/>{create.isPending ? "در حال ایجاد…" : "ایجاد داشبورد شخصی"}</Button>}</header>
    {create.isError && <Alert variant="destructive"><AlertDescription>ایجاد داشبورد ناموفق بود. دوباره تلاش کنید.</AlertDescription></Alert>}
    {!rows.length ? <Card><CardContent className="flex flex-col items-center gap-3 py-14 text-center"><LayoutDashboard className="h-12 w-12 text-muted-foreground"/><CardTitle>هنوز داشبورد شخصی ندارید</CardTitle><CardDescription>{canManage ? "برای شروع، نخستین داشبورد خود را ایجاد کنید." : "برای ایجاد داشبورد با مدیر سازمان تماس بگیرید."}</CardDescription></CardContent></Card> : <section className="grid gap-4 sm:grid-cols-2">{rows.map(row => <Card key={row.public_id}><CardHeader><CardTitle>{row.name}</CardTitle><CardDescription>{row.description || "داشبورد شخصی"}</CardDescription></CardHeader><CardContent className="flex gap-2"><Button asChild><Link to={`/dashboards/${row.public_id}`}>باز کردن</Link></Button>{canManage && <Button variant="outline" asChild><Link to={`/dashboards/${row.public_id}/edit`}>ویرایش</Link></Button>}</CardContent></Card>)}</section>}
  </div></main>;
}
