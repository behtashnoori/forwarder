import { Phone, Mail, MapPin, Clock } from "lucide-react";
import { useSiteSettings } from "@/contexts/SiteSettingsContext";
import { getLogoDisplayUrl } from "@/lib/api";

const Footer = () => {
  const s = useSiteSettings();
  return (
    <footer className="bg-card border-t border-border mt-16">
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Company Info */}
          <div className="text-center md:text-right">
            <div className="flex items-center justify-center md:justify-start gap-3 mb-4">
              {s.logo_url?.trim() ? (
                <img src={getLogoDisplayUrl(s.logo_url)} alt="" className="h-8 w-8 object-contain rounded-lg" />
              ) : (
                <div className="w-8 h-8 bg-gradient-primary rounded-lg flex items-center justify-center">
                  <div className="w-4 h-4 bg-primary-foreground rounded-sm transform rotate-45"></div>
                </div>
              )}
              <h3 className="text-lg font-bold text-foreground">{s.footer_company_name || "فورواردری سریع"}</h3>
            </div>
            <p className="text-muted-foreground text-sm leading-relaxed">
              {s.footer_description || "ارائه دهنده خدمات حمل و نقل و فورواردری با بیش از ۱۰ سال تجربه در سراسر کشور"}
            </p>
          </div>

          {/* Contact Info */}
          <div className="text-center md:text-right">
            <h4 className="font-semibold text-foreground mb-4">{s.footer_contact_title || "اطلاعات تماس"}</h4>
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-center md:justify-start gap-2 text-muted-foreground">
                <Phone className="w-4 h-4" />
                <span>{s.footer_phone || "۰۲۱-۸۸۷۷۶۶۵۵"}</span>
              </div>
              <div className="flex items-center justify-center md:justify-start gap-2 text-muted-foreground">
                <Mail className="w-4 h-4" />
                <span>{s.footer_email || "info@forwarding.ir"}</span>
              </div>
              <div className="flex items-center justify-center md:justify-start gap-2 text-muted-foreground">
                <MapPin className="w-4 h-4" />
                <span>{s.footer_address || "تهران، میدان آزادی"}</span>
              </div>
            </div>
          </div>

          {/* Working Hours */}
          <div className="text-center md:text-right">
            <h4 className="font-semibold text-foreground mb-4">{s.footer_hours_title || "ساعات کاری"}</h4>
            <div className="space-y-2 text-sm text-muted-foreground">
              <div className="flex items-center justify-center md:justify-start gap-2">
                <Clock className="w-4 h-4" />
                <span>{s.footer_working_hours_1 || "شنبه تا چهارشنبه: ۸-۱۸"}</span>
              </div>
              <div className="flex items-center justify-center md:justify-start gap-2">
                <Clock className="w-4 h-4" />
                <span>{s.footer_working_hours_2 || "پنج‌شنبه: ۸-۱۶"}</span>
              </div>
              <div className="text-secondary font-medium">
                {s.footer_support_text || "پشتیبانی ۲۴ ساعته"}
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="border-t border-border mt-8 pt-6 text-center">
          <p className="text-sm text-muted-foreground">
            {s.footer_copyright || "© ۱۴۰۳ فورواردری سریع. تمامی حقوق محفوظ است."}
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;