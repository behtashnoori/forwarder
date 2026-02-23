import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { fetchSiteSettings, updateSiteSettings, uploadLogo, getLogoDisplayUrl, type SiteSettings } from "@/lib/api";
import { useSiteSettingsUpdater } from "@/contexts/SiteSettingsContext";
import { Save, Loader2, Upload, Trash2 } from "lucide-react";

const SECTION_TITLES: Record<string, string> = {
  general: "عمومی (نام سایت، لوگو، عنوان صفحه)",
  nav: "منو و دکمه‌ها",
  footer: "فوتر",
  hero: "بخش هیرو (صفحه اصلی)",
  index: "صفحه اصلی - تب‌ها و متن‌ها",
};

const FIELDS: { key: keyof SiteSettings; label: string; placeholder?: string; section: string; multiline?: boolean }[] = [
  { key: "site_name", label: "نام سایت", section: "general" },
  { key: "site_tagline", label: "شعار سایت", placeholder: "ارسال آسان و مطمئن", section: "general" },
  { key: "logo_url", label: "آدرس لوگو (URL)", placeholder: "خالی = لوگوی پیش‌فرض", section: "general" },
  { key: "favicon_url", label: "آدرس فاویکون (URL)", placeholder: "خالی = پیش‌فرض", section: "general" },
  { key: "page_title", label: "عنوان صفحه (title)", section: "general" },
  { key: "meta_description", label: "توضیحات متا (SEO)", section: "general", multiline: true },
  { key: "meta_author", label: "نویسنده متا", section: "general" },
  { key: "meta_keywords", label: "کلمات کلیدی متا", section: "general" },
  { key: "nav_about", label: "درباره ما", section: "nav" },
  { key: "nav_contact", label: "تماس با ما", section: "nav" },
  { key: "nav_crm", label: "CRM", section: "nav" },
  { key: "nav_admin", label: "پنل ادمین", section: "nav" },
  { key: "btn_expert_login", label: "ورود", section: "nav" },
  { key: "footer_company_name", label: "نام شرکت (فوتر)", section: "footer" },
  { key: "footer_description", label: "توضیح شرکت (فوتر)", section: "footer", multiline: true },
  { key: "footer_contact_title", label: "عنوان بخش تماس", section: "footer" },
  { key: "footer_phone", label: "تلفن", section: "footer" },
  { key: "footer_email", label: "ایمیل", section: "footer" },
  { key: "footer_address", label: "آدرس", section: "footer" },
  { key: "footer_hours_title", label: "عنوان ساعات کاری", section: "footer" },
  { key: "footer_working_hours_1", label: "ساعات کاری ۱", section: "footer" },
  { key: "footer_working_hours_2", label: "ساعات کاری ۲", section: "footer" },
  { key: "footer_support_text", label: "متن پشتیبانی", section: "footer" },
  { key: "footer_copyright", label: "متن کپی‌رایت (پایین فوتر)", section: "footer" },
  { key: "hero_title_1", label: "عنوان هیرو (خط اول)", section: "hero" },
  { key: "hero_title_2", label: "عنوان هیرو (خط دوم)", section: "hero" },
  { key: "hero_subtitle", label: "زیرعنوان هیرو", section: "hero", multiline: true },
  { key: "hero_feature_1", label: "ویژگی ۱", section: "hero" },
  { key: "hero_feature_2", label: "ویژگی ۲", section: "hero" },
  { key: "hero_feature_3", label: "ویژگی ۳", section: "hero" },
  { key: "hero_feature_4", label: "ویژگی ۴", section: "hero" },
  { key: "index_services_title", label: "عنوان بخش خدمات", section: "index" },
  { key: "index_services_subtitle", label: "زیرعنوان بخش خدمات", section: "index", multiline: true },
  { key: "index_tab_request", label: "تب درخواست ارسال", section: "index" },
  { key: "index_tab_track", label: "تب پیگیری درخواست", section: "index" },
  { key: "index_track_title", label: "عنوان کارت پیگیری", section: "index" },
  { key: "index_track_label", label: "برچسب شماره پیگیری", section: "index" },
  { key: "index_shipping_type_title", label: "عنوان انتخاب نوع ارسال", section: "index" },
];

export default function SiteSettingsTab() {
  const [form, setForm] = useState<SiteSettings>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const { toast } = useToast();
  const setGlobalSettings = useSiteSettingsUpdater();

  useEffect(() => {
    fetchSiteSettings()
      .then((data) => setForm(data))
      .catch(() => toast({ title: "خطا", description: "بارگذاری تنظیمات ناموفق بود", variant: "destructive" }))
      .finally(() => setLoading(false));
  }, [toast]);

  const handleChange = (key: string, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingLogo(true);
    e.target.value = "";
    try {
      const { url } = await uploadLogo(file);
      setForm((prev) => {
        const next = { ...prev, logo_url: url };
        setGlobalSettings(next);
        return next;
      });
      toast({ title: "لوگو آپلود شد", description: "آدرس لوگو به‌روز شد. برای ذخیرهٔ نهایی «ذخیره تنظیمات» را بزنید." });
    } catch (err) {
      toast({ title: "خطا", description: err instanceof Error ? err.message : "آپلود لوگو ناموفق بود", variant: "destructive" });
    } finally {
      setUploadingLogo(false);
    }
  };

  const handleRemoveLogo = () => {
    setForm((prev) => {
      const next = { ...prev, logo_url: "" };
      setGlobalSettings(next);
      return next;
    });
    toast({ title: "لوگو حذف شد", description: "برای اعمال در سایت «ذخیره تنظیمات» را بزنید." });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await updateSiteSettings(form);
      setForm(updated);
      setGlobalSettings(updated);
      toast({ title: "ذخیره شد", description: "تنظیمات سایت با موفقیت به‌روزرسانی شد." });
    } catch {
      toast({ title: "خطا", description: "ذخیره تنظیمات ناموفق بود.", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  const sections = Array.from(new Set(FIELDS.map((f) => f.section)));

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {sections.map((section) => (
        <Card key={section}>
          <CardHeader>
            <CardTitle>{SECTION_TITLES[section] || section}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {section === "general" && (
              <div className="space-y-2">
                <Label>آپلود لوگو (ایکون / نام سایت)</Label>
                <div className="flex flex-wrap items-center gap-4">
                  {form.logo_url?.trim() ? (
                    <div className="relative flex items-center gap-2">
                      <img
                        src={getLogoDisplayUrl(form.logo_url)}
                        alt="لوگو"
                        className="h-16 w-auto max-w-[200px] object-contain rounded border bg-muted/30"
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={handleRemoveLogo}
                        className="text-destructive hover:text-destructive hover:bg-destructive/10"
                        title="حذف لوگو"
                      >
                        <Trash2 className="w-4 h-4 ml-1" />
                        حذف لوگو
                      </Button>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">فعلاً لوگویی انتخاب نشده؛ با دکمهٔ زیر آپلود کنید.</p>
                  )}
                  <div className="flex items-center gap-2">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <Input
                        type="file"
                        accept="image/png,image/jpeg,image/jpg,image/gif,image/webp,image/svg+xml"
                        onChange={handleLogoUpload}
                        disabled={uploadingLogo}
                        className="max-w-xs"
                      />
                      {uploadingLogo ? <Loader2 className="w-4 h-4 animate-spin text-gray-500" /> : <Upload className="w-4 h-4" />}
                      <span className="text-sm">انتخاب و آپلود</span>
                    </label>
                  </div>
                </div>
                <p className="text-xs text-gray-500">فرمت‌های مجاز: PNG, JPG, GIF, WebP, SVG. حداکثر ۵ مگابایت.</p>
              </div>
            )}
            {FIELDS.filter((f) => f.section === section).map((field) => (
              <div key={field.key} className="space-y-2">
                <Label htmlFor={field.key}>{field.label}</Label>
                {field.multiline ? (
                  <Textarea
                    id={field.key}
                    value={form[field.key] ?? ""}
                    onChange={(e) => handleChange(field.key, e.target.value)}
                    placeholder={field.placeholder}
                    rows={2}
                    className="resize-none"
                  />
                ) : (
                  <Input
                    id={field.key}
                    value={form[field.key] ?? ""}
                    onChange={(e) => handleChange(field.key, e.target.value)}
                    placeholder={field.placeholder}
                  />
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      ))}
      <div className="flex justify-end">
        <Button type="submit" disabled={saving}>
          {saving ? <Loader2 className="w-4 h-4 ml-2 animate-spin" /> : <Save className="w-4 h-4 ml-2" />}
          {saving ? "در حال ذخیره..." : "ذخیره تنظیمات"}
        </Button>
      </div>
    </form>
  );
}
