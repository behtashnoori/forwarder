import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import CustomerPortalLayout from "@/components/CustomerPortalLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  downloadCustomerSharedDocument, fetchCustomerSession, fetchCustomerSharedDocuments,
  type CustomerSharedDocument,
} from "@/lib/customerPortalApi";

const contextLabel = {
  SHIPMENT: "پرونده حمل", CARGO: "کالای شما", ROUTE_LEG: "مرحله مسیر", EXECUTION_UNIT: "اجرای حمل", DELIVERY: "تحویل کالای شما",
};

export default function CustomerPortalDocuments() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<CustomerSharedDocument[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    let generation = 0;
    const load = async () => {
      const current = ++generation;
      setLoading(true);
      setRows([]);
      try {
        const session = await fetchCustomerSession();
        if (!session.authenticated) { navigate("/customer", { replace: true }); return; }
        const result = await fetchCustomerSharedDocuments(page);
        if (alive && current === generation) { setRows(result.data); setError(""); }
      } catch (caught) {
        if (alive && current === generation) setError(caught instanceof Error ? caught.message : "اسناد دریافت نشدند");
      } finally { if (alive && current === generation) setLoading(false); }
    };
    void load();
    const refresh = () => { if (document.visibilityState !== "hidden") void load(); };
    window.addEventListener("pageshow", refresh);
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => { alive = false; window.removeEventListener("pageshow", refresh); window.removeEventListener("focus", refresh); document.removeEventListener("visibilitychange", refresh); };
  }, [page, navigate]);

  return <CustomerPortalLayout privateNav><Card dir="rtl">
    <CardHeader><CardTitle>اسناد به‌اشتراک‌گذاشته‌شده با شما</CardTitle>
      <p className="text-sm text-slate-600">نسخه‌های جاریِ مجاز برای کالاهای شما و اسنادی که صریحاً با حساب شما به اشتراک گذاشته شده‌اند نمایش داده می‌شوند.</p>
    </CardHeader>
    <CardContent className="space-y-3">
      {error && <p role="alert" className="rounded bg-red-50 p-3 text-red-700">{error}</p>}
      {loading ? <p role="status">در حال دریافت اسناد…</p> : rows.length === 0 ?
        <p>در این صفحه سندی برای شما به‌اشتراک گذاشته نشده است.</p> :
        rows.map((row) => <article key={row.public_id} className="rounded border p-3">
          <strong dir="auto">{row.filename}</strong>
          <p>مربوط به: {contextLabel[row.context_type]}</p>
          <p>نسخه {row.version}</p>
          <Button variant="outline" onClick={() => {
            void downloadCustomerSharedDocument(row.public_id, row.filename).catch((caught) => {
              setRows([]);
              setError(caught instanceof Error ? caught.message : "سند در دسترس نیست");
            });
          }}>دریافت سند</Button>
        </article>)}
      <div className="flex gap-2">
        <Button variant="outline" disabled={page === 1 || loading} onClick={() => setPage(page - 1)}>صفحه قبل</Button>
        <Button variant="outline" disabled={rows.length < 20 || loading} onClick={() => setPage(page + 1)}>صفحه بعد</Button>
      </div>
    </CardContent>
  </Card></CustomerPortalLayout>;
}
