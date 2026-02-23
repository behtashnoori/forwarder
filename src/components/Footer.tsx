import { Phone, Mail, MapPin, Clock } from "lucide-react";
import { useSiteSettings } from "@/contexts/SiteSettingsContext";

const Footer = () => {
  const { settings, logoFullUrl } = useSiteSettings();
  return (
    <footer className="bg-card border-t border-border mt-16">
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Company Info */}
          <div className="text-center md:text-right">
            <div className="flex items-center justify-center md:justify-start gap-3 mb-4">
              {logoFullUrl ? (
                <img src={logoFullUrl} alt="" className="w-8 h-8 object-contain rounded-lg" />
              ) : (
                <div className="w-8 h-8 bg-gradient-primary rounded-lg flex items-center justify-center">
                  <div className="w-4 h-4 bg-primary-foreground rounded-sm transform rotate-45"></div>
                </div>
              )}
              <h3 className="text-lg font-bold text-foreground">{settings.company_name}</h3>
            </div>
            <p className="text-muted-foreground text-sm leading-relaxed">
              {settings.footer_description || "ارائه دهنده خدمات حمل و نقل و فورواردری با بیش از ۱۰ سال تجربه در سراسر کشور"}
            </p>
          </div>

          {/* Contact Info */}
          <div className="text-center md:text-right">
            <h4 className="font-semibold text-foreground mb-4">اطلاعات تماس</h4>
            <div className="space-y-3 text-sm">
              {settings.contact_phone && (
                <div className="flex items-center justify-center md:justify-start gap-2 text-muted-foreground">
                  <Phone className="w-4 h-4" />
                  <span>{settings.contact_phone}</span>
                </div>
              )}
              {settings.contact_email && (
                <div className="flex items-center justify-center md:justify-start gap-2 text-muted-foreground">
                  <Mail className="w-4 h-4" />
                  <span>{settings.contact_email}</span>
                </div>
              )}
              {settings.contact_address && (
                <div className="flex items-center justify-center md:justify-start gap-2 text-muted-foreground">
                  <MapPin className="w-4 h-4" />
                  <span>{settings.contact_address}</span>
                </div>
              )}
            </div>
          </div>

          {/* Working Hours */}
          <div className="text-center md:text-right">
            <h4 className="font-semibold text-foreground mb-4">ساعات کاری</h4>
            <div className="space-y-2 text-sm text-muted-foreground">
              {settings.working_hours_weekdays && (
                <div className="flex items-center justify-center md:justify-start gap-2">
                  <Clock className="w-4 h-4" />
                  <span>{settings.working_hours_weekdays}</span>
                </div>
              )}
              {settings.working_hours_thursday && (
                <div className="flex items-center justify-center md:justify-start gap-2">
                  <Clock className="w-4 h-4" />
                  <span>{settings.working_hours_thursday}</span>
                </div>
              )}
              {settings.support_text && (
                <div className="text-secondary font-medium">
                  {settings.support_text}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="border-t border-border mt-8 pt-6 text-center">
          <p className="text-sm text-muted-foreground">
            {settings.copyright_text || "© ۱۴۰۳ فورواردری سریع. تمامی حقوق محفوظ است."}
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;