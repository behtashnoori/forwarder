/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Language = "fa" | "en";
type Direction = "rtl" | "ltr";

const STORAGE_KEY = "forwarder.language";

const translations = {
  fa: {
    "app.language.toggle": "English",
    "app.language.current": "فارسی",
    "brand.name": "فورواردر",
    "brand.tagline": "ثبت و پیگیری درخواست حمل",
    "nav.about": "درباره ما",
    "nav.contact": "تماس با ما",
    "home.title": "سرویس مدیریت درخواست حمل فورواردر",
    "home.description":
      "درخواست حمل خود را ثبت کنید؛ تیم فورواردر بررسی، هماهنگی و پیگیری وضعیت درخواست را انجام می‌دهد. وضعیت درخواست نیز با شماره پیگیری قابل مشاهده است.",
    "shipping.domestic.title": "ثبت درخواست حمل داخلی",
    "shipping.domestic.description":
      "درخواست حمل داخل کشور را ثبت کنید تا تیم فورواردر پیگیری و هماهنگی مسیر را انجام دهد.",
    "shipping.domestic.detail": "مناسب برای مبدا و مقصد در استان‌های ایران",
    "shipping.international.title": "ثبت درخواست حمل بین‌المللی",
    "shipping.international.description":
      "درخواست حمل بین ایران و کشورهای دیگر را ثبت کنید تا مراحل بررسی و هماهنگی آغاز شود.",
    "shipping.international.detail": "مناسب برای مسیرهای واردات، صادرات و حمل خارجی",
    "shipping.submit": "ثبت درخواست حمل",
    "tracking.title": "پیگیری وضعیت درخواست حمل",
    "tracking.description": "شماره پیگیری درخواست را وارد کنید تا وضعیت ثبت و پیگیری آن را ببینید.",
    "tracking.ariaLabel": "شماره پیگیری",
    "tracking.placeholder": "مثال: SR-XXXXXX یا SR000001",
    "tracking.search": "جستجو",
    "contact.title": "تماس و هماهنگی با فورواردر",
    "contact.description":
      "پس از ثبت درخواست، تیم فورواردر اطلاعات شما را بررسی می‌کند و برای هماهنگی جزئیات حمل با شما تماس می‌گیرد.",
    "hero.title1": "ارسال سریع و مطمئن",
    "hero.title2": "با انواع روش‌های حمل",
    "hero.subtitle":
      "با سرویس فورواردر، بسته‌های خود را از طریق جاده، ریل، دریا یا ترکیبی از این روش‌ها ارسال کنید.",
    "hero.feature.fast": "ارسال فوری",
    "hero.feature.hours": "۲۴ ساعته",
    "hero.feature.insured": "بیمه شده",
    "hero.feature.quality": "کیفیت بالا",
    "footer.company": "فورواردر",
    "footer.description":
      "سرویس ثبت، مدیریت و پیگیری درخواست حمل؛ تیم فورواردر پس از ثبت درخواست، هماهنگی و پیگیری مراحل حمل را انجام می‌دهد.",
    "footer.contactTitle": "اطلاعات تماس",
    "footer.phone": "شماره تماس فورواردر",
    "footer.address": "دفتر هماهنگی فورواردر",
    "footer.hoursTitle": "ساعات پاسخ‌گویی",
    "footer.hours1": "شنبه تا چهارشنبه: ۸ تا ۱۸",
    "footer.hours2": "پنج‌شنبه: ۸ تا ۱۶",
    "footer.support": "پاسخ‌گویی و هماهنگی توسط تیم فورواردر",
    "footer.copyright": "© ۱۴۰۳ فورواردر. تمام حقوق محفوظ است.",
  },
  en: {
    "app.language.toggle": "فارسی",
    "app.language.current": "English",
    "brand.name": "Forwarder",
    "brand.tagline": "Register and track freight requests",
    "nav.about": "About",
    "nav.contact": "Contact",
    "home.title": "Forwarder Freight Request Management",
    "home.description":
      "Register your freight request and the Forwarder team will review, coordinate, and track its status. You can also check progress with your tracking number.",
    "shipping.domestic.title": "Create a domestic freight request",
    "shipping.domestic.description":
      "Register an in-country freight request so the Forwarder team can coordinate and follow up on the route.",
    "shipping.domestic.detail": "Best for origins and destinations inside Iran",
    "shipping.international.title": "Create an international freight request",
    "shipping.international.description":
      "Register a freight request between Iran and other countries so review and coordination can begin.",
    "shipping.international.detail": "Best for import, export, and cross-border freight routes",
    "shipping.submit": "Create freight request",
    "tracking.title": "Track freight request status",
    "tracking.description": "Enter your tracking number to view the registration and follow-up status.",
    "tracking.ariaLabel": "Tracking number",
    "tracking.placeholder": "Example: SR-XXXXXX or SR000001",
    "tracking.search": "Search",
    "contact.title": "Contact and coordination with Forwarder",
    "contact.description":
      "After you submit a request, the Forwarder team reviews your information and contacts you to coordinate shipment details.",
    "hero.title1": "Fast and reliable shipping",
    "hero.title2": "Across multiple freight methods",
    "hero.subtitle":
      "Use Forwarder to ship by road, rail, sea, or a combination of available freight methods.",
    "hero.feature.fast": "Fast dispatch",
    "hero.feature.hours": "24-hour support",
    "hero.feature.insured": "Insured",
    "hero.feature.quality": "High quality",
    "footer.company": "Forwarder",
    "footer.description":
      "A service for registering, managing, and tracking freight requests. The Forwarder team coordinates and follows up after each request is submitted.",
    "footer.contactTitle": "Contact information",
    "footer.phone": "Forwarder phone number",
    "footer.address": "Forwarder coordination office",
    "footer.hoursTitle": "Support hours",
    "footer.hours1": "Saturday to Wednesday: 8:00 to 18:00",
    "footer.hours2": "Thursday: 8:00 to 16:00",
    "footer.support": "Response and coordination by the Forwarder team",
    "footer.copyright": "© 2024 Forwarder. All rights reserved.",
  },
} as const;

export type TranslationKey = keyof typeof translations.fa;

type I18nContextValue = {
  language: Language;
  direction: Direction;
  setLanguage: (language: Language) => void;
  toggleLanguage: () => void;
  t: (key: TranslationKey) => string;
};

const I18nContext = createContext<I18nContextValue | undefined>(undefined);

const getInitialLanguage = (): Language => {
  if (typeof window === "undefined") return "fa";
  return window.localStorage.getItem(STORAGE_KEY) === "en" ? "en" : "fa";
};

export const I18nProvider = ({ children }: { children: ReactNode }) => {
  const [language, setLanguageState] = useState<Language>(getInitialLanguage);
  const direction: Direction = language === "fa" ? "rtl" : "ltr";

  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = direction;
    window.localStorage.setItem(STORAGE_KEY, language);
  }, [direction, language]);

  const value = useMemo<I18nContextValue>(
    () => ({
      language,
      direction,
      setLanguage: setLanguageState,
      toggleLanguage: () => setLanguageState((current) => (current === "fa" ? "en" : "fa")),
      t: (key) => translations[language][key],
    }),
    [direction, language],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
};

export const useI18n = () => {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return context;
};
