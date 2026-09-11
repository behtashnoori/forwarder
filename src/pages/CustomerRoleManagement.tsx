import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router";
import PageNav from "@/components/PageNav";
import { fetchCustomerOperationalRoles, fetchCustomers, setCustomerCarrierEligibility, type Customer } from "@/lib/api";

function CustomerRoleManagementContent() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [roles, setRoles] = useState<Record<number, boolean>>({});
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState("");
  const load = async () => {
    setError("");
    try {
      const result = await fetchCustomers({per_page:100, sort_by:"name", sort_order:"asc"});
      setCustomers(result.customers);
      const values = await Promise.all(result.customers.map(async customer => [customer.id, (await fetchCustomerOperationalRoles(customer.id)).roles.carrier_eligible] as const));
      setRoles(Object.fromEntries(values));
    } catch { setError("دریافت اطلاعات مشتریان یا صلاحیت‌های عملیاتی انجام نشد."); }
  };
  useEffect(() => { void load(); }, []);
  const change = async (customerId:number, eligible:boolean) => {
    setBusy(customerId); setError("");
    try { await setCustomerCarrierEligibility(customerId, eligible); await load(); }
    catch { setError("ذخیره صلاحیت عملیاتی انجام نشد."); }
    finally { setBusy(null); }
  };
  return <main className="min-h-screen bg-gray-50 p-6" dir="rtl"><div className="mx-auto max-w-5xl space-y-6"><PageNav backLabel="بازگشت" /><header><h1 className="text-2xl font-bold">مشتریان و صلاحیت‌های عملیاتی</h1><p className="mt-1 text-sm text-slate-600">صلاحیت حمل‌کننده، امکان انتخاب مشتری برای اجرای حمل‌های جدید را تعیین می‌کند.</p></header>{error&&<p role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</p>}<section aria-label="نقش‌ها و صلاحیت‌های عملیاتی" className="rounded-lg border bg-white"><div className="grid grid-cols-[1fr_auto] gap-4 border-b p-4 text-sm font-semibold"><span>مشتری</span><span>کریر / حمل‌کننده</span></div>{customers.map(customer=><div key={customer.id} className="grid grid-cols-[1fr_auto] items-center gap-4 border-b p-4 last:border-0"><span>{customer.company_name || customer.name}</span><label className="flex items-center gap-2"><input aria-label={`کریر / حمل‌کننده برای ${customer.company_name || customer.name}`} type="checkbox" checked={!!roles[customer.id]} disabled={busy===customer.id} onChange={event=>void change(customer.id,event.target.checked)} /><span>{roles[customer.id]?"فعال":"غیرفعال"}</span></label></div>)}{!customers.length&&!error&&<p className="p-4 text-sm text-slate-600">مشتری‌ای برای نمایش وجود ندارد.</p>}</section><Link className="text-sm text-blue-700" to="/admin">بازگشت به مدیریت سازمان</Link></div></main>;
}

export default function CustomerRoleManagement() {
  const authority = (() => { try { return JSON.parse(localStorage.getItem("expert_user") || "{}").authority; } catch { return undefined; } })();
  // Carrier eligibility is tenant-owned. Platform administration has no
  // tenant context, so the data-fetching component must never mount there.
  return authority === "ORGANIZATION_ADMIN" ? <CustomerRoleManagementContent /> : <Navigate to="/admin" replace />;
}
