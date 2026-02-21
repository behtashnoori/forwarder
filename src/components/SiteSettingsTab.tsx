import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { fetchSiteSettings, updateSiteSettings, type SiteSettings } from "@/lib/api";
import { useSiteSettingsUpdater } from "@/contexts/SiteSettingsContext";
import { Save, Loader2 } from "lucide-react";

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
  { key: "btn_expert_login", label: "ورود کارشناس", section: "nav" },
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
