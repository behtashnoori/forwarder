import { useNavigate } from "react-router-dom";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ArrowRight, Home } from "lucide-react";

interface PageNavProps {
  /** مسیر بازگشت؛ اگر نباشد از history برمی‌گردد */
  backTo?: string;
  /** متن دکمه بازگشت */
  backLabel?: string;
  /** کلاس اضافی برای کانتینر */
  className?: string;
}

const PageNav = ({ backTo, backLabel = "بازگشت", className = "" }: PageNavProps) => {
  const navigate = useNavigate();

  const handleBack = () => {
    if (backTo) navigate(backTo);
    else navigate(-1);
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
    </div>
  );
};

export default PageNav;
