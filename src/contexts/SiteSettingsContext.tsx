import React, { createContext, useContext, useEffect, useState } from "react";
import {
  fetchSiteSettings,
  DEFAULT_SITE_SETTINGS,
  type SiteSettings,
} from "@/lib/api";

type SiteSettingsContextValue = {
  settings: SiteSettings;
  loading: boolean;
  error: boolean;
  refetch: () => Promise<void>;
};

const mergedDefaults = (data: SiteSettings | null): SiteSettings =>
  data ? { ...DEFAULT_SITE_SETTINGS, ...data } : DEFAULT_SITE_SETTINGS;

const SiteSettingsContext = createContext<SiteSettingsContextValue>({
  settings: DEFAULT_SITE_SETTINGS,
  loading: false,
  error: false,
  refetch: async () => {},
});

export function SiteSettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<SiteSettings>(DEFAULT_SITE_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const refetch = async () => {
    setLoading(true);
    setError(false);
    try {
      const data = await fetchSiteSettings();
      setSettings(mergedDefaults(data));
    } catch {
      setSettings(DEFAULT_SITE_SETTINGS);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refetch();
  }, []);

  return (
    <SiteSettingsContext.Provider value={{ settings, loading, error, refetch }}>
      {children}
    </SiteSettingsContext.Provider>
  );
}

export function useSiteSettings(): SiteSettingsContextValue {
  const ctx = useContext(SiteSettingsContext);
  if (!ctx) {
    return {
      settings: DEFAULT_SITE_SETTINGS,
      loading: false,
      error: false,
      refetch: async () => {},
    };
  }
  return ctx;
}

export function getSetting(settings: SiteSettings, key: string): string {
  return settings[key] ?? DEFAULT_SITE_SETTINGS[key] ?? "";
}

export function isSettingOn(settings: SiteSettings, key: string): boolean {
  const v = settings[key];
  return v === "1" || v === "true" || v === "yes";
}
