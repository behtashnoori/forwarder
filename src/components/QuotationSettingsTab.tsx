import { useEffect, useState } from "react";
import { request } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function QuotationSettingsTab() {
  const [zone, setZone] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  useEffect(() => { void request<{timezone: string | null}>("/api/admin/quotation-settings")
    .then(result => setZone(result.timezone || "")).catch(() => setMessage("تنظیمات دریافت نشد."))
    .finally(() => setLoading(false)); }, []);
  const save = async () => {
    setBusy(true); setMessage("");
    try { await request("/api/admin/quotation-settings", { method: "PATCH", body: JSON.stringify({ timezone: zone.trim() || null }) }); setMessage("تنظیمات ثبت شد."); }
    catch { setMessage("ثبت انجام نشد؛ شناسه معتبر منطقه زمانی و دسترسی مدیر سازمان را بررسی کنید."); }
    finally { setBusy(false); }
  };
  return <section className="space-y-4 rounded-xl border bg-white p-6"><h2 className="text-lg font-bold">اعتبار پیشنهادهای سازمان</h2>
    <p>این مبنا فقط برای پیشنهادهای جدید اعمال می‌شود. اعتبار پیشنهادهای منتشرشده تغییر نمی‌کند.</p>
    <Label htmlFor="quotation-zone">منطقه زمانی اعتبار پیشنهاد (IANA)</Label>
    <Input id="quotation-zone" dir="ltr" disabled={loading || busy} value={zone} onChange={event => setZone(event.target.value)} placeholder="مانند Asia/Tehran" />
    {!zone && <p>تا تنظیم منطقه زمانی، انتشار پیشنهاد جدید امکان‌پذیر نیست.</p>}
    <Button disabled={busy || loading} onClick={() => void save()}>ثبت منطقه زمانی</Button>{message && <p role="status">{message}</p>}
  </section>;
}
