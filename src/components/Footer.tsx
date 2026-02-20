import { Phone, Mail, MapPin, Clock } from "lucide-react";
import { useSiteSettings, getSetting, isSettingOn } from "@/contexts/SiteSettingsContext";

const Footer = () => {
  const { settings } = useSiteSettings();
  const showFooter = isSettingOn(settings, "show_footer");
  const showContact = isSettingOn(settings, "show_contact_section");
  const showHours = isSettingOn(settings, "show_working_hours_section");

  if (!showFooter) return null;

  return (
    <footer className="bg-card border-t border-border mt-16">
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Company Info */}
          <div className="text-center md:text-right">
            <div className="flex items-center justify-center md:justify-start gap-3 mb-4">
              <div className="w-8 h-8 bg-gradient-primary rounded-lg flex items-center justify-center">
                <div className="w-4 h-4 bg-primary-foreground rounded-sm transform rotate-45"></div>
              </div>
              <h3 className="text-lg font-bold text-foreground">{getSetting(settings, "site_name")}</h3>
            </div>
            <p className="text-muted-foreground text-sm leading-relaxed">
              {getSetting(settings, "site_tagline")}
            </p>
          </div>

          {/* Contact Info */}
          {showContact && (
            <div className="text-center md:text-right">
              <h4 className="font-semibold text-foreground mb-4">اطلاعات تماس</h4>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-center md:justify-start gap-2 text-muted-foreground">
                  <Phone className="w-4 h-4" />
                  <span>{getSetting(settings, "contact_phone")}</span>
                </div>
                <div className="flex items-center justify-center md:justify-start gap-2 text-muted-foreground">
                  <Mail className="w-4 h-4" />
                  <span>{getSetting(settings, "contact_email")}</span>
                </div>
                <div className="flex items-center justify-center md:justify-start gap-2 text-muted-foreground">
                  <MapPin className="w-4 h-4" />
                  <span>{getSetting(settings, "contact_address")}</span>
                </div>
              </div>
            </div>
          )}

          {/* Working Hours */}
          {showHours && (
            <div className="text-center md:text-right">
              <h4 className="font-semibold text-foreground mb-4">ساعات کاری</h4>
              <div className="space-y-2 text-sm text-muted-foreground">
                <div className="flex items-center justify-center md:justify-start gap-2">
                  <Clock className="w-4 h-4" />
                  <span>{getSetting(settings, "working_hours_week")}</span>
                </div>
                <div className="flex items-center justify-center md:justify-start gap-2">
                  <Clock className="w-4 h-4" />
                  <span>{getSetting(settings, "working_hours_thu")}</span>
                </div>
                <div className="text-secondary font-medium">
                  {getSetting(settings, "support_text")}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Bottom Bar */}
        <div className="border-t border-border mt-8 pt-6 text-center">
          <p className="text-sm text-muted-foreground">
            {getSetting(settings, "copyright_text")}
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;