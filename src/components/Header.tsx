import { Button } from "@/components/ui/button";
import { Menu, Phone, Info, BarChart3, Shield } from "lucide-react";
import { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import ExpertLogin from "./ExpertLogin";
import { useSiteSettings, getSetting } from "@/contexts/SiteSettingsContext";

/** فعلاً آیکون CRM در نوار بالا نمایش داده نشود */
const SHOW_CRM_NAV = false;

const Header = () => {
  const { settings } = useSiteSettings();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const location = useLocation();
  const siteName = getSetting(settings, "site_name");

  useEffect(() => {
    const checkAdmin = () => {
      try {
        const expertUser = localStorage.getItem("expert_user");
        if (!expertUser) {
          setIsAdmin(false);
          return;
        }
        const user = JSON.parse(expertUser);
        setIsAdmin(user?.role === "admin");
      } catch {
        setIsAdmin(false);
      }
    };
    checkAdmin();
    window.addEventListener("storage", checkAdmin);
    const interval = setInterval(checkAdmin, 1000);
    return () => {
      window.removeEventListener("storage", checkAdmin);
      clearInterval(interval);
    };
  }, [location.pathname]);

  return (
    <header className="w-full bg-card/80 backdrop-blur-sm border-b border-border sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-primary rounded-lg flex items-center justify-center">
              <div className="w-6 h-6 bg-primary-foreground rounded-sm transform rotate-45"></div>
            </div>
            <div className="text-right">
              <h1 className="text-lg font-bold text-foreground">{siteName || "فورواردری سریع"}</h1>
              <p className="text-xs text-muted-foreground">ارسال آسان و مطمئن</p>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-4">
            <Button variant="ghost" className="text-sm font-medium">
              <Info className="w-4 h-4 ml-2" />
              درباره ما
            </Button>
            <Button variant="ghost" className="text-sm font-medium">
              <Phone className="w-4 h-4 ml-2" />
              تماس با ما
            </Button>
            {SHOW_CRM_NAV && (
              <Button variant="ghost" className="text-sm font-medium" asChild>
                <Link to="/crm">
                  <BarChart3 className="w-4 h-4 ml-2" />
                  CRM
                </Link>
              </Button>
            )}
            {isAdmin && (
              <Button variant="ghost" className="text-sm font-medium" asChild>
                <Link to="/admin">
                  <Shield className="w-4 h-4 ml-2" />
                  پنل ادمین
                </Link>
              </Button>
            )}
            <ExpertLogin />
          </nav>

          {/* Mobile Menu Button */}
          <Button 
            variant="ghost" 
            size="sm"
            className="md:hidden"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            <Menu className="w-5 h-5" />
          </Button>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden py-4 border-t border-border bg-card/95">
            <nav className="flex flex-col gap-2">
              <Button variant="ghost" className="justify-start text-sm font-medium">
                <Info className="w-4 h-4 ml-2" />
                درباره ما
              </Button>
              <Button variant="ghost" className="justify-start text-sm font-medium">
                <Phone className="w-4 h-4 ml-2" />
                تماس با ما
              </Button>
              {SHOW_CRM_NAV && (
                <Button variant="ghost" className="justify-start text-sm font-medium" asChild>
                  <Link to="/crm">
                    <BarChart3 className="w-4 h-4 ml-2" />
                    CRM
                  </Link>
                </Button>
              )}
              {isAdmin && (
                <Button variant="ghost" className="justify-start text-sm font-medium" asChild>
                  <Link to="/admin">
                    <Shield className="w-4 h-4 ml-2" />
                    پنل ادمین
                  </Link>
                </Button>
              )}
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