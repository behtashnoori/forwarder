import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { env } from "@/lib/env";
import { RefreshCw, Upload, Trash2, Settings } from "lucide-react";
import { useSiteSettings } from "@/contexts/SiteSettingsContext";
import type { SiteSettingsData } from "@/contexts/SiteSettingsContext";

function buildLogoFullUrl(logoUrl: string | null): string | null {
  if (!logoUrl) return null;
  if (logoUrl.startsWith("http")) return logoUrl;
  const base = env.API_URL || "";
  const path = logoUrl.startsWith("/") ? logoUrl : `/${logoUrl}`;
  return `${base}${path}`;
}

const SiteSettingsTab = () => {
  const { toast } = useToast();
  const { refetch: refetchPublicSettings } = useSiteSettings();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [form, setForm] = useState<SiteSettingsData>({
    company_name: "فورواردری سریع",
    tagline: "ارسال آسان و مطمئن",
    footer_description: "",
    contact_phone: "",
    contact_email: "",
    contact_address: "",
    working_hours_weekdays: "",
    working_hours_thursday: "",
    support_text: "",
    copyright_text: "",
    logo_url: null,
  });

  const loadSettings = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("expert_token");
      const url = `${env.API_URL}/api/admin/site-settings`.replace(/\/+/g, "/");
      const res = await fetch(url, {
        cache: "no-store",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setForm({
          company_name: data.company_name ?? form.company_name,
          tagline: data.tagline ?? form.tagline,
          footer_description: data.footer_description ?? "",
          contact_phone: data.contact_phone ?? "",
          contact_email: data.contact_email ?? "",
          contact_address: data.contact_address ?? "",
          working_hours_weekdays: data.working_hours_weekdays ?? "",
          working_hours_thursday: data.working_hours_thursday ?? "",
          support_text: data.support_text ?? "",
          copyright_text: data.copyright_text ?? "",
          logo_url: data.logo_url ?? null,
        });
      } else {
        const msg = data.error || (res.status === 401 ? "لطفاً دوباره وارد شوید" : "دریافت تنظیمات ناموفق بود");
        toast({ title: "خطا", description: msg, variant: "destructive" });
      }
    } catch (e) {
      toast({ title: "خطا", description: "ارتباط با سرور برقرار نشد", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const token = localStorage.getItem("expert_token");
      const url = `${env.API_URL}/api/admin/site-settings`.replace(/\/+/g, "/");
      const res = await fetch(url, {
        method: "PUT",
        cache: "no-store",
        headers: {
          "Content-Type": "application/json",
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: JSON.stringify(form),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        if (data.settings) {
          setForm({
            company_name: data.settings.company_name ?? form.company_name,
            tagline: data.settings.tagline ?? form.tagline,
            footer_description: data.settings.footer_description ?? "",
            contact_phone: data.settings.contact_phone ?? "",
            contact_email: data.settings.contact_email ?? "",
            contact_address: data.settings.contact_address ?? "",
            working_hours_weekdays: data.settings.working_hours_weekdays ?? "",
            working_hours_thursday: data.settings.working_hours_thursday ?? "",
            support_text: data.settings.support_text ?? "",
            copyright_text: data.settings.copyright_text ?? "",
            logo_url: data.settings.logo_url ?? null,
          });
        }
        toast({ title: "ذخیره شد", description: data.message || "تنظیمات با موفقیت ذخیره شد" });
        refetchPublicSettings();
      } else {
        const msg = data.error || (res.status === 401 ? "لطفاً دوباره وارد شوید" : "ذخیره ناموفق بود");
        toast({ title: "خطا", description: msg, variant: "destructive" });
      }
    } catch (e) {
      toast({ title: "خطا", description: "ارتباط با سرور برقرار نشد", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const allowed = ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"];
    if (!allowed.includes(file.type)) {
      toast({ title: "فرمت نامعتبر", description: "فقط تصاویر png, jpg, gif, webp مجاز هستند", variant: "destructive" });
      return;
    }
    setUploading(true);
    try {
      const token = localStorage.getItem("expert_token");
      const fd = new FormData();
      fd.append("file", file);
      const url = `${env.API_URL}/api/admin/site-settings/logo`.replace(/\/+/g, "/");
      const res = await fetch(url, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: fd,
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setForm((prev) => ({ ...prev, logo_url: data.logo_url ?? null }));
        toast({ title: "آپلود لوگو", description: data.message || "لوگو با موفقیت آپلود شد" });
        refetchPublicSettings();
      } else {
        const msg = data.error || (res.status === 401 ? "لطفاً دوباره وارد شوید" : "آپلود ناموفق بود");
        toast({ title: "خطا", description: msg, variant: "destructive" });
      }
    } catch (e) {
      toast({ title: "خطا", description: "ارتباط با سرور برقرار نشد", variant: "destructive" });
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleRemoveLogo = async () => {
    try {
      const token = localStorage.getItem("expert_token");
      const url = `${env.API_URL}/api/admin/site-settings/logo`.replace(/\/+/g, "/");
      const res = await fetch(url, { method: "DELETE", headers: token ? { Authorization: `Bearer ${token}` } : {} });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setForm((prev) => ({ ...prev, logo_url: null }));
        toast({ title: "حذف لوگو", description: data.message || "لوگو حذف شد" });
        refetchPublicSettings();
      } else {
        toast({ title: "خطا", description: data.error || "حذف ناموفق بود", variant: "destructive" });
      }
    } catch (e) {
      toast({ title: "خطا", description: "ارتباط با سرور برقرار نشد", variant: "destructive" });
    }
  };

  const logoFullUrl = buildLogoFullUrl(form.logo_url);

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            تنظیمات سایت
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="company_name">نام شرکت</Label>
                <Input
                  id="company_name"
                  value={form.company_name}
                  onChange={(e) => setForm((p) => ({ ...p, company_name: e.target.value }))}
                  placeholder="فورواردری سریع"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="tagline">شعار (تگ‌لاین)</Label>
                <Input
                  id="tagline"
                  value={form.tagline}
                  onChange={(e) => setForm((p) => ({ ...p, tagline: e.target.value }))}
                  placeholder="ارسال آسان و مطمئن"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="footer_description">توضیح فوتر (درباره شرکت)</Label>
              <textarea
                id="footer_description"
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={form.footer_description}
                onChange={(e) => setForm((p) => ({ ...p, footer_description: e.target.value }))}
                placeholder="ارائه دهنده خدمات حمل و نقل و فورواردری با بیش از ۱۰ سال تجربه در سراسر کشور"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="contact_phone">تلفن تماس</Label>
                <Input
                  id="contact_phone"
                  value={form.contact_phone}
                  onChange={(e) => setForm((p) => ({ ...p, contact_phone: e.target.value }))}
                  placeholder="۰۲۱-۸۸۷۷۶۶۵۵"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="contact_email">ایمیل</Label>
                <Input
                  id="contact_email"
                  type="email"
                  value={form.contact_email}
                  onChange={(e) => setForm((p) => ({ ...p, contact_email: e.target.value }))}
                  placeholder="info@forwarding.ir"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="contact_address">آدرس</Label>
                <Input
                  id="contact_address"
                  value={form.contact_address}
                  onChange={(e) => setForm((p) => ({ ...p, contact_address: e.target.value }))}
                  placeholder="تهران، میدان آزادی"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="working_hours_weekdays">ساعات کاری (شنبه تا چهارشنبه)</Label>
                <Input
                  id="working_hours_weekdays"
                  value={form.working_hours_weekdays}
                  onChange={(e) => setForm((p) => ({ ...p, working_hours_weekdays: e.target.value }))}
                  placeholder="شنبه تا چهارشنبه: ۸-۱۸"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="working_hours_thursday">ساعات کاری (پنج‌شنبه)</Label>
                <Input
                  id="working_hours_thursday"
                  value={form.working_hours_thursday}
                  onChange={(e) => setForm((p) => ({ ...p, working_hours_thursday: e.target.value }))}
                  placeholder="پنج‌شنبه: ۸-۱۶"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="support_text">متن پشتیبانی</Label>
              <Input
                id="support_text"
                value={form.support_text}
                onChange={(e) => setForm((p) => ({ ...p, support_text: e.target.value }))}
                placeholder="پشتیبانی ۲۴ ساعته"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="copyright_text">متن حق نشر (فوتر)</Label>
              <Input
                id="copyright_text"
                value={form.copyright_text}
                onChange={(e) => setForm((p) => ({ ...p, copyright_text: e.target.value }))}
                placeholder="© ۱۴۰۳ فورواردری سریع. تمامی حقوق محفوظ است."
              />
            </div>

            <div className="border-t pt-6">
              <Label className="block mb-3">لوگوی شرکت</Label>
              <p className="text-sm text-muted-foreground mb-3">
                تصویر با همان سایز نمایش در هدر (۴۰×۴۰) و فوتر (۳۲×۳۲) نشان داده می‌شود.
              </p>
              <div className="flex items-center gap-4 flex-wrap">
                <div className="w-10 h-10 rounded-lg overflow-hidden bg-muted flex items-center justify-center border">
                  {logoFullUrl ? (
                    <img src={logoFullUrl} alt="لوگو" className="w-full h-full object-contain" />
                  ) : (
                    <span className="text-xs text-muted-foreground">بدون لوگو</span>
                  )}
                </div>
                <div className="flex gap-2">
                  <label className="cursor-pointer">
                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/jpg,image/gif,image/webp"
                      className="hidden"
                      onChange={handleLogoUpload}
                      disabled={uploading}
                    />
                    <Button type="button" variant="outline" size="sm" asChild>
                      <span>
                        <Upload className="w-4 h-4 ml-2" />
                        {uploading ? "در حال آپلود..." : "آپلود تصویر"}
                      </span>
                    </Button>
                  </label>
                  {form.logo_url && (
                    <Button type="button" variant="outline" size="sm" className="text-red-600" onClick={handleRemoveLogo}>
                      <Trash2 className="w-4 h-4 ml-2" />
                      حذف لوگو
                    </Button>
                  )}
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-4">
              <Button type="submit" disabled={saving}>
                {saving ? (
                  <>
                    <RefreshCw className="w-4 h-4 ml-2 animate-spin" />
                    در حال ذخیره...
                  </>
                ) : (
                  "ذخیره تنظیمات"
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default SiteSettingsTab;
