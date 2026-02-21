import { Truck, Clock, Shield, Star } from "lucide-react";
import heroBackground from "@/assets/hero-bg.jpg";
import { useSiteSettings } from "@/contexts/SiteSettingsContext";

const Hero = () => {
  const s = useSiteSettings();
  return (
    <section className="relative min-h-[60vh] flex items-center justify-center overflow-hidden">
      {/* Background Image with Overlay */}
      <div 
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: `url(${heroBackground})` }}
      >
        <div className="absolute inset-0 bg-gradient-to-r from-primary/90 to-primary-dark/80"></div>
      </div>

      {/* Content */}
      <div className="relative z-10 container mx-auto px-4 text-center text-primary-foreground">
        <div className="max-w-3xl mx-auto">
            <h1 className="text-4xl md:text-5xl font-bold mb-6 leading-tight">
            {s.hero_title_1 || "ارسال سریع و مطمئن"}
            <br />
            <span className="text-secondary-light">{s.hero_title_2 || "با انواع روش‌های حمل"}</span>
          </h1>
          
          <p className="text-lg md:text-xl mb-8 opacity-90 leading-relaxed">
            {s.hero_subtitle || "با سرویس فورواردری ما، بسته‌های خود را از طریق جاده، ریل، دریا یا ترکیبی از این روش‌ها ارسال کنید"}
          </p>

          {/* Features */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6 mt-12">
            <div className="flex flex-col items-center gap-2 p-4 bg-white/10 backdrop-blur-sm rounded-lg border border-white/20">
              <Truck className="w-6 h-6 text-secondary-light" />
              <span className="text-sm font-medium">{s.hero_feature_1 || "ارسال فوری"}</span>
            </div>
            
            <div className="flex flex-col items-center gap-2 p-4 bg-white/10 backdrop-blur-sm rounded-lg border border-white/20">
              <Clock className="w-6 h-6 text-secondary-light" />
              <span className="text-sm font-medium">{s.hero_feature_2 || "۲۴ ساعته"}</span>
            </div>
            
            <div className="flex flex-col items-center gap-2 p-4 bg-white/10 backdrop-blur-sm rounded-lg border border-white/20">
              <Shield className="w-6 h-6 text-secondary-light" />
              <span className="text-sm font-medium">{s.hero_feature_3 || "بیمه شده"}</span>
            </div>
            
            <div className="flex flex-col items-center gap-2 p-4 bg-white/10 backdrop-blur-sm rounded-lg border border-white/20">
              <Star className="w-6 h-6 text-secondary-light" />
              <span className="text-sm font-medium">{s.hero_feature_4 || "کیفیت بالا"}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Decorative Elements */}
      <div className="absolute bottom-0 left-0 w-full h-24 bg-gradient-to-t from-background to-transparent"></div>
    </section>
  );
};

export default Hero;