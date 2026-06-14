import { Button } from "@/components/ui/button";
import { Menu, Phone, Info } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import ExpertLogin from "./ExpertLogin";
import { useSiteSettings } from "@/contexts/SiteSettingsContext";
import { getLogoDisplayUrl } from "@/lib/api";

const Header = () => {
  const settings = useSiteSettings();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <header className="w-full bg-card/80 backdrop-blur-sm border-b border-border sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            {settings.logo_url?.trim() ? (
              <img src={getLogoDisplayUrl(settings.logo_url)} alt="" className="h-10 w-10 object-contain rounded-lg" />
            ) : (
              <div className="w-10 h-10 bg-gradient-primary rounded-lg flex items-center justify-center">
                <div className="w-6 h-6 bg-primary-foreground rounded-sm transform rotate-45"></div>
              </div>
            )}
            <div className="text-right">
              <h1 className="text-lg font-bold text-foreground">{settings.site_name || "فورواردر"}</h1>
              <p className="text-xs text-muted-foreground">{settings.site_tagline || "ثبت و پیگیری درخواست حمل"}</p>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-4">
            <Button variant="ghost" className="text-sm font-medium" asChild>
              <Link to="/#about">
                <Info className="w-4 h-4 ml-2" />
                {settings.nav_about || "درباره ما"}
              </Link>
            </Button>
            <Button variant="ghost" className="text-sm font-medium" asChild>
              <Link to="/#contact">
                <Phone className="w-4 h-4 ml-2" />
                {settings.nav_contact || "تماس با ما"}
              </Link>
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
                  <Info className="w-4 h-4 ml-2" />
                  {settings.nav_about || "درباره ما"}
                </Link>
              </Button>
              <Button variant="ghost" className="justify-start text-sm font-medium" asChild>
                <Link to="/#contact" onClick={() => setIsMenuOpen(false)}>
                  <Phone className="w-4 h-4 ml-2" />
                  {settings.nav_contact || "تماس با ما"}
                </Link>
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
