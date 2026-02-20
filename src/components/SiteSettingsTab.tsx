import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { env } from "@/lib/env";
import { useSiteSettings } from "@/contexts/SiteSettingsContext";
import type { SiteSettings } from "@/lib/api";
import { RefreshCw, Save } from "lucide-react";

const FIELDS: { key: keyof SiteSettings; label: string; multiline?: boolean }[] = [
  { key: "site_name", label: "نام سایت / برند" },
  { key: "site_tagline", label: "توضیح کوتاه (زیر نام برند)", multiline: true },
  { key: "contact_phone", label: "تلفن تماس" },
  { key: "contact_email", label: "ایمیل" },
  { key: "contact_address", label: "آدرس" },
  { key: "working_hours_week", label: "ساعات کاری (شنبه تا چهارشنبه)" },
  { key: "working_hours_thu", label: "ساعات کاری (پنج‌شنبه)" },
  { key: "support_text", label: "متن پشتیبانی (مثلاً پشتیبانی ۲۴ ساعته)" },
  { key: "copyright_text", label: "متن کپی‌رایت (پایین صفحه)" },
];

const TOGGLE_KEYS: { key: keyof SiteSettings; label: string }[] = [
  { key: "show_contact_section", label: "نمایش بلوک اطلاعات تماس" },
  { key: "show_working_hours_section", label: "نمایش بلوک ساعات کاری" },
  { key: "show_footer", label: "نمایش فوتر سایت" },
];

export default function SiteSettingsTab() {
  const { toast } = useToast();
  const { settings, refetch } = useSiteSettings();
  const [form, setForm] = useState<SiteSettings>({ ...settings });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setForm({ ...settings });
  }, [settings]);

  const loadSettings = async () => {
    const token = localStorage.getItem("expert_token");
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${env.API_URL}/api/admin/site-settings`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setForm((prev) => ({ ...prev, ...data }));
        await refetch();
      }
    } catch {
      toast({ title: "خطا", description: "بارگذاری تنظیمات ناموفق بود", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleChange = (key: string, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleToggle = (key: string, checked: boolean) => {
    setForm((prev) => ({ ...prev, [key]: checked ? "1" : "0" }));
  };

  const handleSave = async () => {
    const token = localStorage.getItem("expert_token");
    if (!token) return;
    setSaving(true);
    try {
      const res = await fetch(`${env.API_URL}/api/admin/site-settings`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(form),
      });
      if (res.ok) {
        const data = await res.json();
        setForm((prev) => ({ ...prev, ...data }));
        await refetch();
        toast({ title: "ذخیره شد", description: "تنظیمات سایت با موفقیت به‌روزرسانی شد." });
      } else {
        const err = await res.json().catch(() => ({}));
        toast({
          title: "خطا",
          description: (err as { error?: string }).error || "ذخیره تنظیمات ناموفق بود",
          variant: "destructive",
        });
      }
    } catch {
      toast({ title: "خطا", description: "ارتباط با سرور برقرار نشد", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>تنظیمات محتوای سایت</CardTitle>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={loadSettings} disabled={loading}>
                <RefreshCw className={`w-4 h-4 ml-2 ${loading ? "animate-spin" : ""}`} />
                بارگذاری
              </Button>
              <Button size="sm" onClick={handleSave} disabled={saving}>
                <Save className="w-4 h-4 ml-2" />
                {saving ? "در حال ذخیره..." : "ذخیره"}
              </Button>
            </div>
          </div>
          <p className="text-sm text-muted-foreground">
            متن‌های نوار بالا، فوتر و اطلاعات تماس را ویرایش کنید یا با غیرفعال کردن گزینه‌ها آن‌ها را مخفی کنید.
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {FIELDS.map(({ key, label, multiline }) => (
            <div key={key} className="space-y-2">
              <Label htmlFor={key}>{label}</Label>
              {multiline ? (
                <textarea
                  id={key}
                  className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={form[key] ?? ""}
                  onChange={(e) => handleChange(key, e.target.value)}
                />
              ) : (
                <Input
                  id={key}
                  value={form[key] ?? ""}
                  onChange={(e) => handleChange(key, e.target.value)}
                />
              )}
            </div>
          ))}

          <div className="border-t pt-6 space-y-4">
            <h4 className="font-medium">فعال / غیرفعال</h4>
            {TOGGLE_KEYS.map(({ key, label }) => (
              <div key={key} className="flex items-center justify-between">
                <Label htmlFor={`switch-${key}`}>{label}</Label>
                <Switch
                  id={`switch-${key}`}
                  checked={(form[key] ?? "1") === "1"}
                  onCheckedChange={(checked) => handleToggle(key, checked)}
                />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
