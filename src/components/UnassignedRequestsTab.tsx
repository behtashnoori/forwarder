import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import {
  assignUnassignedRequest, autoAssignUnassignedRequest, fetchExperts,
  fetchOrganizationHostnames, fetchUnassignedRequests, type ExpertRequest,
  type ExpertUser, type OrganizationHostnameRow,
} from "@/lib/api";

export default function UnassignedRequestsTab() {
  const { toast } = useToast();
  const [rows, setRows] = useState<ExpertRequest[]>([]);
  const [experts, setExperts] = useState<ExpertUser[]>([]);
  const [hostnames, setHostnames] = useState<OrganizationHostnameRow[]>([]);
  const [selection, setSelection] = useState<Record<number, number>>({});
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [queue, expertResult, hostnameResult] = await Promise.all([
        fetchUnassignedRequests(), fetchExperts(), fetchOrganizationHostnames(),
      ]);
      setRows(queue.requests || []);
      setExperts(Array.isArray(expertResult) ? expertResult : expertResult.experts || []);
      setHostnames(hostnameResult.hostnames || []);
    } catch (error) {
      toast({ title: "خطا در دریافت درخواست‌های تخصیص‌نیافته", description: String(error), variant: "destructive" });
    } finally { setLoading(false); }
  }, [toast]);

  useEffect(() => { void load(); }, [load]);

  const runAuto = async (requestId: number) => {
    try {
      const result = await autoAssignUnassignedRequest(requestId);
      toast({ title: result.assigned ? "تخصیص خودکار انجام شد" : "کارشناس واجد شرایط یافت نشد" });
      await load();
    } catch (error) { toast({ title: "تخصیص خودکار ناموفق بود", description: String(error), variant: "destructive" }); }
  };

  const runManual = async (requestId: number) => {
    const expertId = selection[requestId];
    if (!expertId) return;
    try {
      await assignUnassignedRequest(requestId, expertId);
      toast({ title: "درخواست با موفقیت تخصیص یافت" });
      await load();
    } catch (error) { toast({ title: "تخصیص دستی ناموفق بود", description: String(error), variant: "destructive" }); }
  };

  return <div className="space-y-4">
    <Card><CardHeader><CardTitle>هویت سازمان و دامنه‌ها</CardTitle></CardHeader>
      <CardContent className="space-y-1 text-sm">
        {hostnames.length ? hostnames.map((row) => <div key={row.id} dir="ltr">{row.hostname}{row.is_primary ? " (primary)" : ""}</div>) : <p>دامنه‌ای برای نمایش ثبت نشده است.</p>}
      </CardContent></Card>
    <div className="flex items-center justify-between"><h2 className="text-xl font-bold">درخواست‌های تخصیص‌نیافته</h2>
      <Button variant="outline" onClick={() => void load()} disabled={loading}><RefreshCw className="ml-2 h-4 w-4" />بازخوانی</Button></div>
    {!rows.length ? <Card><CardContent className="p-8 text-center text-slate-500">درخواست تخصیص‌نیافته‌ای وجود ندارد.</CardContent></Card> : rows.map((row) =>
      <Card key={row.id}><CardContent className="flex flex-col gap-4 p-5 lg:flex-row lg:items-center lg:justify-between">
        <div><div className="font-bold" dir="ltr">{row.tracking_number}</div><div className="text-sm text-slate-500">{row.customer.name} — {row.customer.phone}</div></div>
        <div className="flex flex-wrap gap-2"><Button variant="outline" onClick={() => void runAuto(row.id)}>تخصیص خودکار</Button>
          <select className="rounded-md border px-3" value={selection[row.id] || ""} onChange={(event) => setSelection((old) => ({ ...old, [row.id]: Number(event.target.value) }))}>
            <option value="">انتخاب کارشناس</option>{experts.filter((expert) => expert.role === "expert" || expert.role === "business_expert").map((expert) => <option key={expert.id} value={expert.id}>{expert.full_name}</option>)}
          </select><Button disabled={!selection[row.id]} onClick={() => void runManual(row.id)}>تخصیص دستی</Button></div>
      </CardContent></Card>)}
  </div>;
}
