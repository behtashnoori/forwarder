import { useNavigate } from "react-router-dom";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ArrowRight, Home, LogOut } from "lucide-react";

interface PageNavProps {
  /** مسیر بازگشت؛ اگر نباشد از history برمی‌گردد */
  backTo?: string;
  /** متن دکمه بازگشت */
  backLabel?: string;
  /** نمایش دکمه خروج (پاک کردن توکن و رفتن به صفحه اصلی) */
  showLogout?: boolean;
  /** اگر مقدار داشته باشد، با زدن خروج به این مسیر برمی‌گردد (بدون پاک کردن توکن؛ برای بازگشت به پنل کارشناس) */
  logoutTo?: string;
  /** کلاس اضافی برای کانتینر */
  className?: string;
}

const PageNav = ({ backTo, backLabel = "بازگشت", showLogout = false, logoutTo, className = "" }: PageNavProps) => {
  const navigate = useNavigate();

  const handleBack = () => {
    if (backTo) navigate(backTo);
    else navigate(-1);
  };

  const handleLogout = () => {
    if (logoutTo) {
      navigate(logoutTo);
      return;
    }
    localStorage.removeItem("expert_user");
    localStorage.removeItem("expert_token");
    window.location.href = "/";
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <Button variant="outline" size="sm" onClick={handleBack}>
        <ArrowRight className="w-4 h-4 ml-2" />
        {backLabel}
      </Button>
      <Button variant="outline" size="sm" asChild>
        <Link to="/">
          <Home className="w-4 h-4 ml-2" />
          خانه
        </Link>
      </Button>
      {showLogout && (
        <Button variant="outline" size="sm" onClick={handleLogout} className="text-red-600 hover:text-red-700 hover:bg-red-50">
          <LogOut className="w-4 h-4 ml-2" />
          خروج
        </Button>
      )}
    </div>
  );
};

export default PageNav;
