import React, { createContext, useContext, useEffect, useState } from "react";
import { fetchSiteSettings } from "@/lib/api";

export type SiteSettings = Record<string, string>;

const defaultSettings: SiteSettings = {
  site_name: "فورواردری سریع",
  site_tagline: "ارسال آسان و مطمئن",
  logo_url: "",
  favicon_url: "",
  page_title: "فورواردری سریع - ارسال آسان و مطمئن در سراسر کشور",
  meta_description: "سرویس حرفه‌ای فورواردری و ارسال مرسوله در سراسر ایران. ارسال سریع، مطمئن و با بیمه کامل.",
  meta_author: "فورواردری سریع",
  meta_keywords: "فورواردری, ارسال مرسوله, حمل و نقل, ارسال سریع, ایران",
  footer_company_name: "فورواردری سریع",
  footer_description: "ارائه دهنده خدمات حمل و نقل و فورواردری با بیش از ۱۰ سال تجربه در سراسر کشور",
  footer_phone: "۰۲۱-۸۸۷۷۶۶۵۵",
  footer_email: "info@forwarding.ir",
  footer_address: "تهران، میدان آزادی",
  footer_working_hours_1: "شنبه تا چهارشنبه: ۸-۱۸",
  footer_working_hours_2: "پنج‌شنبه: ۸-۱۶",
  footer_support_text: "پشتیبانی ۲۴ ساعته",
  footer_copyright: "© ۱۴۰۳ فورواردری سریع. تمامی حقوق محفوظ است.",
  footer_contact_title: "اطلاعات تماس",
  footer_hours_title: "ساعات کاری",
  nav_about: "درباره ما",
  nav_contact: "تماس با ما",
  nav_crm: "CRM",
  nav_admin: "پنل ادمین",
  btn_expert_login: "ورود",
  hero_title_1: "ارسال سریع و مطمئن",
  hero_title_2: "با انواع روش‌های حمل",
  hero_subtitle: "با سرویس فورواردری ما، بسته‌های خود را از طریق جاده، ریل، دریا یا ترکیبی از این روش‌ها ارسال کنید",
  hero_feature_1: "ارسال فوری",
  hero_feature_2: "۲۴ ساعته",
  hero_feature_3: "بیمه شده",
  hero_feature_4: "کیفیت بالا",
  index_services_title: "خدمات فورواردر",
  index_services_subtitle: "درخواست ارسال مرسوله یا پیگیری درخواست‌های قبلی",
  index_tab_request: "درخواست ارسال",
  index_tab_track: "پیگیری درخواست",
  index_track_title: "پیگیری درخواست",
  index_track_label: "شماره پیگیری",
  index_shipping_type_title: "نوع ارسال خود را انتخاب کنید",
};

const SiteSettingsContext = createContext<{
  settings: SiteSettings;
  setSettings: (s: SiteSettings) => void;
}>({
  settings: defaultSettings,
  setSettings: () => {},
});

export function SiteSettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<SiteSettings>(defaultSettings);

  useEffect(() => {
    fetchSiteSettings()
      .then((data) => setSettings((prev) => ({ ...prev, ...data })))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (settings.page_title) {
      document.title = settings.page_title;
    }
    const favicon = settings.favicon_url?.trim();
    if (favicon) {
      let link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
      if (!link) {
        link = document.createElement("link");
        link.rel = "icon";
        document.head.appendChild(link);
      }
      link.href = favicon;
    }
  }, [settings.page_title, settings.favicon_url]);

  return (
    <SiteSettingsContext.Provider value={{ settings, setSettings }}>
      {children}
    </SiteSettingsContext.Provider>
  );
}

export function useSiteSettings() {
  return useContext(SiteSettingsContext).settings;
}

export function useSiteSettingsUpdater() {
  return useContext(SiteSettingsContext).setSettings;
}
