import React, { createContext, useContext, useEffect, useState } from "react";
import { env } from "@/lib/env";

export interface SiteSettingsData {
  company_name: string;
  tagline: string;
  footer_description: string;
  contact_phone: string;
  contact_email: string;
  contact_address: string;
  working_hours_weekdays: string;
  working_hours_thursday: string;
  support_text: string;
  copyright_text: string;
  logo_url: string | null;
}

const defaultSettings: SiteSettingsData = {
  company_name: "فورواردری سریع",
  tagline: "ارسال آسان و مطمئن",
  footer_description: "ارائه دهنده خدمات حمل و نقل و فورواردری با بیش از ۱۰ سال تجربه در سراسر کشور",
  contact_phone: "۰۲۱-۸۸۷۷۶۶۵۵",
  contact_email: "info@forwarding.ir",
  contact_address: "تهران، میدان آزادی",
  working_hours_weekdays: "شنبه تا چهارشنبه: ۸-۱۸",
  working_hours_thursday: "پنج‌شنبه: ۸-۱۶",
  support_text: "پشتیبانی ۲۴ ساعته",
  copyright_text: "© ۱۴۰۳ فورواردری سریع. تمامی حقوق محفوظ است.",
  logo_url: null,
};

type SiteSettingsContextValue = {
  settings: SiteSettingsData;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  /** Full URL for logo image (API base + path when logo_url is relative) */
  logoFullUrl: string | null;
};

const SiteSettingsContext = createContext<SiteSettingsContextValue>({
  settings: defaultSettings,
  loading: true,
  error: null,
  refetch: async () => {},
  logoFullUrl: null,
});

export function useSiteSettings() {
  const ctx = useContext(SiteSettingsContext);
  return ctx;
}

function buildLogoFullUrl(logoUrl: string | null): string | null {
  if (!logoUrl) return null;
  if (logoUrl.startsWith("http")) return logoUrl;
  const base = env.API_URL || "";
  const path = logoUrl.startsWith("/") ? logoUrl : `/${logoUrl}`;
  return `${base}${path}`;
}

export function SiteSettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<SiteSettingsData>(defaultSettings);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSettings = async () => {
    try {
      setError(null);
      const res = await fetch(`${env.API_URL}/api/site-settings`);
      const data = await res.json();
      if (res.ok) {
        setSettings({
          company_name: data.company_name ?? defaultSettings.company_name,
          tagline: data.tagline ?? defaultSettings.tagline,
          footer_description: data.footer_description ?? defaultSettings.footer_description,
          contact_phone: data.contact_phone ?? defaultSettings.contact_phone,
          contact_email: data.contact_email ?? defaultSettings.contact_email,
          contact_address: data.contact_address ?? defaultSettings.contact_address,
          working_hours_weekdays: data.working_hours_weekdays ?? defaultSettings.working_hours_weekdays,
          working_hours_thursday: data.working_hours_thursday ?? defaultSettings.working_hours_thursday,
          support_text: data.support_text ?? defaultSettings.support_text,
          copyright_text: data.copyright_text ?? defaultSettings.copyright_text,
          logo_url: data.logo_url ?? null,
        });
      } else {
        setSettings(defaultSettings);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "خطا در دریافت تنظیمات");
      setSettings(defaultSettings);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const value: SiteSettingsContextValue = {
    settings,
    loading,
    error,
    refetch: fetchSettings,
    logoFullUrl: buildLogoFullUrl(settings.logo_url),
  };

  return (
    <SiteSettingsContext.Provider value={value}>
      {children}
    </SiteSettingsContext.Provider>
  );
}
