import { useEffect, useState, type FormEvent } from "react";
import { Copy } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  initiateAdminPortalEnrollment,
  initiateAdminPortalRecovery,
  listAdminPortalAccounts,
  setAdminPortalAccountStatus,
  type AdminPortalAccount,
  type AdminPortalCapability,
  type AdminPortalRecoveryResult,
} from "@/lib/customerPortalApi";

function currentAuthority() {
  try {
    return JSON.parse(localStorage.getItem("expert_user") || "{}").authority || "";
  } catch {
    return "";
  }
}

export default function CustomerPortalAccountSupport() {
  const authority = currentAuthority();
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<AdminPortalAccount[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [capability, setCapability] = useState<AdminPortalCapability | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async (search = query) => {
    setLoading(true);
    setError("");
    try {
      setItems((await listAdminPortalAccounts(search)).items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "دریافت حساب‌ها انجام نشد.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (authority === "ORGANIZATION_ADMIN") void load("");
    // Authority is fixed for this route render; the backend still enforces it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authority]);

  if (authority !== "ORGANIZATION_ADMIN") {
    return (
      <main dir="rtl" className="mx-auto max-w-2xl p-8">
        <Card>
          <CardContent className="p-8 text-center">
            پشتیبانی روزمره حساب مشتری فقط در اختیار مدیر همان سازمان است.
          </CardContent>
        </Card>
      </main>
    );
  }

  const runStatus = async (account: AdminPortalAccount) => {
    setError("");
    setMessage("");
    setCapability(null);
    try {
      await setAdminPortalAccountStatus(
        account.public_id,
        account.account_status === "ACTIVE" ? "DISABLED" : "ACTIVE",
      );
      setMessage("وضعیت حساب به‌روزرسانی شد.");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "عملیات انجام نشد.");
    }
  };

  const issueCapability = async (
    action: () => Promise<AdminPortalCapability>,
  ) => {
    setError("");
    setMessage("");
    setCapability(null);
    try {
      const issued = await action();
      setCapability(issued);
      setMessage(
        "پیوند یک‌بارمصرف صادر شد. سامانه آن را ارسال نمی‌کند؛ آن را اکنون کپی و از کانال مورد تأیید سازمان تحویل دهید.",
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "عملیات انجام نشد.");
    }
  };

  const sendRecoveryEmail = async (
    action: () => Promise<AdminPortalRecoveryResult>,
  ) => {
    setError("");
    setMessage("");
    setCapability(null);
    try {
      const result = await action();
      if (result.delivery_status === "SENT") {
        setMessage("ایمیل بازیابی برای تحویل به سرویس ایمیل سپرده شد.");
      } else if (result.delivery_status === "SUPPRESSED") {
        setMessage("ارسال واقعی ایمیل در این محیط غیرفعال است؛ هیچ پیوند فعالی باقی نماند.");
      } else {
        setError("تحویل ایمیل بازیابی ناموفق بود؛ هیچ پیوند فعالی باقی نماند.");
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "عملیات انجام نشد.");
    }
  };

  const copyCapability = async () => {
    if (!capability) return;
    try {
      await navigator.clipboard.writeText(
        new URL(capability.path, window.location.origin).toString(),
      );
      setMessage("پیوند یک‌بارمصرف کپی شد.");
    } catch {
      setError("کپی خودکار ممکن نبود؛ پیوند را دستی کپی کنید.");
    }
  };

  const search = (event: FormEvent) => {
    event.preventDefault();
    void load(query.trim());
  };

  return (
    <main dir="rtl" className="mx-auto max-w-5xl space-y-5 p-4 sm:p-8">
      <header>
        <h1 className="text-2xl font-bold">پشتیبانی حساب‌های پرتال مشتری</h1>
        <p className="text-sm text-muted-foreground">
          این صفحه از مشتری CRM جداست؛ انتقال مالکیت یا مشاهده/تنظیم رمز عبور در آن ممکن نیست.
        </p>
      </header>

      <form className="flex gap-2" onSubmit={search}>
        <Input
          aria-label="جستجوی حساب پرتال"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="ایمیل یا شناسه عمومی حساب"
        />
        <Button variant="outline">جستجو</Button>
      </form>

      {error && <p role="alert" className="rounded bg-destructive/10 p-3 text-destructive">{error}</p>}
      {message && <p role="status" className="rounded bg-muted p-3">{message}</p>}
      {capability && (
        <Card className="border-amber-300">
          <CardHeader>
            <CardTitle className="text-base">پیوند یک‌بارمصرف — فقط همین بار نمایش داده می‌شود</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input
              readOnly
              dir="ltr"
              aria-label="پیوند یک‌بارمصرف حساب مشتری"
              value={new URL(capability.path, window.location.origin).toString()}
            />
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <Button type="button" variant="outline" onClick={() => void copyCapability()}>
                <Copy className="h-4 w-4" />
                کپی پیوند
              </Button>
              <span>انقضا: <bdi dir="ltr">{capability.expires_at}</bdi></span>
            </div>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <p>در حال دریافت…</p>
      ) : (
        <div className="space-y-3">
          {items.map((account) => (
            <Card key={account.public_id}>
              <CardHeader>
                <CardTitle className="flex flex-wrap justify-between gap-2 text-base">
                  <span>{account.email}</span>
                  <Badge variant={account.account_status === "ACTIVE" ? "default" : "secondary"}>
                    {account.account_status === "ACTIVE" ? "فعال" : "غیرفعال"}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid gap-2 text-sm sm:grid-cols-2">
                  <p>شناسه: <bdi dir="ltr">{account.public_id}</bdi></p>
                  <p>موبایل: <bdi dir="ltr">{account.phone}</bdi></p>
                  <p>تعداد درخواست: {account.request_count ?? "—"}</p>
                  <p>مرجع پیوند: {account.linkage_source || "ثبت‌نشده"}</p>
                  <p>راه‌اندازی حساب: {account.enrollment_state === "ENROLLED" ? "تکمیل‌شده" : "در انتظار"}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" onClick={() => void runStatus(account)}>
                    {account.account_status === "ACTIVE" ? "غیرفعال‌سازی" : "فعال‌سازی"}
                  </Button>
                  <Button
                    variant="outline"
                    disabled={account.account_status !== "ACTIVE" || account.enrollment_state !== "ENROLLED"}
                    onClick={() => void sendRecoveryEmail(() => initiateAdminPortalRecovery(account.public_id))}
                  >
                    ارسال ایمیل بازیابی
                  </Button>
                  <Button
                    variant="outline"
                    disabled={account.account_status !== "ACTIVE" || account.enrollment_state === "ENROLLED"}
                    onClick={() => void issueCapability(() => initiateAdminPortalEnrollment(account.public_id))}
                  >
                    صدور پیوند راه‌اندازی حساب
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
          {!items.length && (
            <Card><CardContent className="p-8 text-center">حسابی یافت نشد.</CardContent></Card>
          )}
        </div>
      )}
    </main>
  );
}
