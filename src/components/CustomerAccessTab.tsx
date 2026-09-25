import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { formatDualCalendarInstant } from "@/lib/dualCalendar";
import {
  fetchCustomerAccess, grantCustomerAccess, revokeCustomerAccess,
  type CustomerAccessConfiguration,
} from "@/lib/customerEntitlementApi";

const date = (value: string) => formatDualCalendarInstant(value, "fa-IR");
export default function CustomerAccessTab() {
  const [data, setData] = useState<CustomerAccessConfiguration | null>(null);
  const [account, setAccount] = useState("");
  const [customer, setCustomer] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const command = useRef<{ target: string; key: string } | null>(null);
  const load = useCallback(async () => {
    setData(null);
    const result = await fetchCustomerAccess();
    setData(result);
  }, []);
  useEffect(() => { void load().catch(e => setError(e instanceof Error ? e.message : "دسترسی‌ها دریافت نشدند")); }, [load]);

  const save = async (grantId?: string) => {
    setBusy(true); setError(""); setMessage("");
    try {
      if (grantId) await revokeCustomerAccess(grantId);
      else {
        const target = `${account}:${customer}`;
        if (command.current?.target !== target) command.current = { target, key: crypto.randomUUID() };
        await grantCustomerAccess(account, Number(customer), command.current.key);
        command.current = null;
      }
      await load();
      setMessage(grantId ? "دسترسی لغو شد؛ درخواست بعدی مشتری دوباره بررسی می‌شود." : "دسترسی ثبت شد.");
    } catch (e) { setError(e instanceof Error ? e.message : "ثبت تغییر انجام نشد"); }
    finally { setBusy(false); }
  };
  return <Card dir="rtl">
    <CardHeader><CardTitle>دسترسی حساب مشتری</CardTitle></CardHeader>
    <CardContent className="space-y-5">
      <p className="text-sm text-muted-foreground">حساب پورتال را به مشتری یا شرکت مربوط متصل کنید. این دسترسی فقط امکان مشاهده اطلاعات مجاز همان مشتری را فراهم می‌کند.</p>
      {error && <p role="alert" className="text-destructive">{error}</p>}
      {message && <p role="status">{message}</p>}
      {!data ? <div><p>در حال دریافت دسترسی‌ها…</p>{error && <Button variant="outline" onClick={() => void load().catch(e => setError(String(e)))}>تلاش دوباره</Button>}</div> : <>
        <form className="grid gap-4 md:grid-cols-[1fr_1fr_auto]" onSubmit={e => { e.preventDefault(); void save(); }}>
          <div className="space-y-2"><Label htmlFor="access-account">حساب پورتال</Label>
            <select id="access-account" className="h-11 w-full rounded-xl border bg-background px-3" value={account} onChange={e => setAccount(e.target.value)} required disabled={busy}>
              <option value="">انتخاب حساب</option>{data.accounts.map(a => <option key={a.public_id} value={a.public_id}>{a.label}</option>)}
            </select></div>
          <div className="space-y-2"><Label htmlFor="access-customer">مشتری / شرکت</Label>
            <select id="access-customer" className="h-11 w-full rounded-xl border bg-background px-3" value={customer} onChange={e => setCustomer(e.target.value)} required disabled={busy}>
              <option value="">انتخاب مشتری</option>{data.customers.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select></div>
          <Button type="submit" className="self-end h-11" disabled={busy || !account || !customer}>اعطای دسترسی</Button>
        </form>
        {data.grants.length === 0 && <p className="text-muted-foreground">هنوز دسترسی‌ای ثبت نشده است.</p>}
        <div className="divide-y">{data.grants.filter(g => g.status === "ACTIVE").map(g => <div key={g.public_id} className="flex flex-wrap items-center justify-between gap-3 py-4">
          <div><p><bdi>{g.account_label}</bdi> ← {g.customer_label}</p><p className="text-xs text-muted-foreground">اعطا: {date(g.granted_at)}</p></div>
          <Button variant="outline" disabled={busy} onClick={() => void save(g.public_id)}>لغو دسترسی</Button>
        </div>)}</div>
        <details><summary className="cursor-pointer">تاریخچه دسترسی‌ها</summary><ul className="space-y-3 pt-3">{data.grants.map(g => <li key={g.public_id}>
          <bdi>{g.account_label}</bdi> ← {g.customer_label} — {g.status === "ACTIVE" ? "فعال" : "لغو شده"}
          <p className="text-xs text-muted-foreground">اعطا: {date(g.granted_at)}{g.revoked_at && `؛ لغو: ${date(g.revoked_at)}`}</p>
        </li>)}</ul></details>
      </>}
    </CardContent>
  </Card>;
}
