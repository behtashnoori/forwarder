import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import OperationsControlTower from "./OperationsControlTower";
import { getDashboard } from "@/lib/api";
import type { DashboardDefinition } from "@/dashboard/types";

const supportedSemantic = "analytics-semantic-v1";
const supportedSchema = "dashboard-definition-v1";
function State({ message, retry }: { message:string; retry?:()=>void }) { return <main dir="rtl" className="min-h-screen bg-slate-50 p-6"><Alert className="mx-auto max-w-xl" role="status"><AlertDescription>{message}{retry && <Button className="mt-3 block" variant="outline" onClick={retry}>تلاش دوباره</Button>}</AlertDescription></Alert></main>; }
export default function PersistedDashboard() {
  const navigate = useNavigate();
  const { public_id = "" } = useParams();
  const query = useQuery({ queryKey:["dashboard", "detail", public_id], queryFn:() => getDashboard(public_id), enabled:Boolean(public_id), retry:false });
  if (!public_id) return <State message="داشبورد مورد نظر پیدا نشد." />;
  if (query.isLoading) return <main dir="rtl" className="min-h-screen bg-slate-50 p-6" aria-busy="true"><div className="mx-auto max-w-7xl space-y-4"><div className="h-8 w-64 animate-pulse rounded bg-muted"/><div className="h-20 animate-pulse rounded bg-muted"/><div className="grid gap-4 md:grid-cols-2"><div className="h-40 animate-pulse rounded bg-muted"/><div className="h-40 animate-pulse rounded bg-muted"/></div></div></main>;
  if (query.isError) return <State message="دریافت داشبورد ممکن نیست یا به آن دسترسی ندارید." retry={() => query.refetch()} />;
  const dashboard = query.data.data;
  if (dashboard.semantic_version !== supportedSemantic) return <State message="این داشبورد به نسخهٔ جدیدتر لایهٔ معنایی نیاز دارد." />;
  if (dashboard.dashboard_schema_version !== supportedSchema) return <State message="این داشبورد به نسخهٔ جدیدتر ساختار نیاز دارد." />;
  if (dashboard.status === "ARCHIVED") return <State message="این داشبورد بایگانی شده است." />;
  return <OperationsControlTower definition={dashboard.definition as DashboardDefinition} displayName={dashboard.name} displayDescription={dashboard.description} sourceContext="نسخهٔ شخصی" allowClone={false} headerAction={<Button variant="outline" onClick={() => navigate(`/dashboards/${dashboard.public_id}/edit`)}>ویرایش داشبورد</Button>} />;
}
