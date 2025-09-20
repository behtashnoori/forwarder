import { Button } from "@/components/ui/button";
import { Menu, Phone, Info } from "lucide-react";
import { useState } from "react";
import ExpertLogin from "./ExpertLogin";

const Header = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

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
              <h1 className="text-lg font-bold text-foreground">فورواردری سریع</h1>
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