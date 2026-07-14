import { Button } from "@/components/ui/button";
import { Globe2, Menu, Phone, Info } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import ExpertLogin from "./ExpertLogin";
import { useSiteSettings } from "@/contexts/SiteSettingsContext";
import { useI18n } from "@/i18n";

const Header = () => {
  const settings = useSiteSettings();
  const { direction, language, t, toggleLanguage } = useI18n();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const textAlignClass = direction === "rtl" ? "text-right" : "text-left";
  const iconSpacingClass = direction === "rtl" ? "ml-2" : "mr-2";
  const legacyBrandValues = new Set(["فورواردری سریع", "ارسال آسان و مطمئن"]);
  const localizedSetting = (value: string | undefined, fallback: string) =>
    language === "fa" && value && !legacyBrandValues.has(value.trim()) ? value : fallback;

  return (
    <header className="w-full bg-card/80 backdrop-blur-sm border-b border-border sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 shrink-0 overflow-hidden rounded-full bg-white">
              <img src="/brand-icon.png" alt="" className="h-full w-full scale-[1.4] object-cover" />
            </div>
            <div className={textAlignClass}>
              <h1 className="text-lg font-bold text-foreground">{localizedSetting(settings.site_name, t("brand.name"))}</h1>
              <p className="text-xs text-muted-foreground">{localizedSetting(settings.site_tagline, t("brand.tagline"))}</p>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-4">
            <Button variant="ghost" className="text-sm font-medium" asChild>
              <Link to="/#about">
                <Info className={`w-4 h-4 ${iconSpacingClass}`} />
                {localizedSetting(settings.nav_about, t("nav.about"))}
              </Link>
            </Button>
            <Button variant="ghost" className="text-sm font-medium" asChild>
              <Link to="/#contact">
                <Phone className={`w-4 h-4 ${iconSpacingClass}`} />
                {localizedSetting(settings.nav_contact, t("nav.contact"))}
              </Link>
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="text-xs font-medium"
              onClick={toggleLanguage}
              aria-label={`Switch language from ${t("app.language.current")}`}
            >
              <Globe2 className={`w-4 h-4 ${iconSpacingClass}`} />
              {t("app.language.toggle")}
            </Button>
            <ExpertLogin />
          </nav>

          <Button
            variant="ghost"
            size="sm"
            className="md:hidden"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            <Menu className="w-5 h-5" />
          </Button>
        </div>

        {isMenuOpen && (
          <div className="md:hidden py-4 border-t border-border bg-card/95">
            <nav className="flex flex-col gap-2">
              <Button variant="ghost" className="justify-start text-sm font-medium" asChild>
                <Link to="/#about" onClick={() => setIsMenuOpen(false)}>
                  <Info className={`w-4 h-4 ${iconSpacingClass}`} />
                  {localizedSetting(settings.nav_about, t("nav.about"))}
                </Link>
              </Button>
              <Button variant="ghost" className="justify-start text-sm font-medium" asChild>
                <Link to="/#contact" onClick={() => setIsMenuOpen(false)}>
                  <Phone className={`w-4 h-4 ${iconSpacingClass}`} />
                  {localizedSetting(settings.nav_contact, t("nav.contact"))}
                </Link>
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="mx-3 justify-start text-xs font-medium"
                onClick={() => {
                  toggleLanguage();
                  setIsMenuOpen(false);
                }}
                aria-label={`Switch language from ${t("app.language.current")}`}
              >
                <Globe2 className={`w-4 h-4 ${iconSpacingClass}`} />
                {t("app.language.toggle")}
              </Button>
              <div className="px-3 py-2">
                <ExpertLogin />
              </div>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;
