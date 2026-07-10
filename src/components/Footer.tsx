import { Phone, Mail, MapPin, Clock } from "lucide-react";
import { useSiteSettings } from "@/contexts/SiteSettingsContext";
import { getLogoDisplayUrl } from "@/lib/api";
import { useI18n } from "@/i18n";

const Footer = () => {
  const s = useSiteSettings();
  const { direction, language, t } = useI18n();
  const textAlignClass = direction === "rtl" ? "md:text-right" : "md:text-left";
  const localizedSetting = (value: string | undefined, fallback: string) =>
    language === "fa" ? value || fallback : fallback;
  return (
    <footer className="bg-card border-t border-border mt-12">
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className={`text-center ${textAlignClass}`}>
            <div className="flex items-center justify-center md:justify-start gap-3 mb-4">
              {s.logo_url?.trim() ? (
                <img src={getLogoDisplayUrl(s.logo_url)} alt="" className="h-8 w-8 object-contain rounded-lg" />
              ) : (
                <div className="w-8 h-8 bg-gradient-primary rounded-lg flex items-center justify-center">
                  <div className="w-4 h-4 bg-primary-foreground rounded-sm transform rotate-45"></div>
                </div>
              )}
              <h3 className="text-lg font-bold text-foreground">{localizedSetting(s.footer_company_name, t("footer.company"))}</h3>
            </div>
            <p className="text-muted-foreground text-sm leading-relaxed">
              {localizedSetting(s.footer_description, t("footer.description"))}
            </p>
          </div>

          <div className={`text-center ${textAlignClass}`}>
            <h4 className="font-semibold text-foreground mb-4">{localizedSetting(s.footer_contact_title, t("footer.contactTitle"))}</h4>
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-center md:justify-start gap-2 text-muted-foreground">
                <Phone className="w-4 h-4" />
                <span>{localizedSetting(s.footer_phone, t("footer.phone"))}</span>
              </div>
              <div className="flex items-center justify-center md:justify-start gap-2 text-muted-foreground">
                <Mail className="w-4 h-4" />
                <span>{s.footer_email || "info@forwarding.ir"}</span>
              </div>
              <div className="flex items-center justify-center md:justify-start gap-2 text-muted-foreground">
                <MapPin className="w-4 h-4" />
                <span>{localizedSetting(s.footer_address, t("footer.address"))}</span>
              </div>
            </div>
          </div>

          <div className={`text-center ${textAlignClass}`}>
            <h4 className="font-semibold text-foreground mb-4">{localizedSetting(s.footer_hours_title, t("footer.hoursTitle"))}</h4>
            <div className="space-y-2 text-sm text-muted-foreground">
              <div className="flex items-center justify-center md:justify-start gap-2">
                <Clock className="w-4 h-4" />
                <span>{localizedSetting(s.footer_working_hours_1, t("footer.hours1"))}</span>
              </div>
              <div className="flex items-center justify-center md:justify-start gap-2">
                <Clock className="w-4 h-4" />
                <span>{localizedSetting(s.footer_working_hours_2, t("footer.hours2"))}</span>
              </div>
              <div className="text-secondary font-medium">
                {localizedSetting(s.footer_support_text, t("footer.support"))}
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-border mt-8 pt-6 text-center">
          <p className="text-sm text-muted-foreground">
            {localizedSetting(s.footer_copyright, t("footer.copyright"))}
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
