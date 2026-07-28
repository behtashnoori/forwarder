import { useNavigate } from "react-router";
import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import { ArrowRight, Home, LogOut } from "lucide-react";
import { logoutAndClearExpertSession } from "@/lib/authSession";

interface PageNavProps {
  /** مسیر بازگشت؛ اگر نباشد از history برمی‌گردد */
  backTo?: string;
  /** متن دکمه بازگشت */
  backLabel?: string;
  /** نمایش دکمه خروج (پاک کردن توکن و رفتن به صفحه اصلی) */
  showLogout?: boolean;
  /** مسیر مقصد پس از لغو نشست و پاک‌سازی state محلی */
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

  const handleLogout = async () => {
    await logoutAndClearExpertSession();
    navigate(logoutTo || "/", { replace: true });
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
