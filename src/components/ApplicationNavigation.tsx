import { ArrowRight, Home } from "lucide-react";
import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router";
import { Button } from "@/components/ui/button";
import { authenticatedHome, rememberApplicationRoute, safePreviousRoute } from "@/lib/applicationNavigation";

export default function ApplicationNavigation() {
  const location = useLocation();
  const navigate = useNavigate();
  useEffect(() => rememberApplicationRoute(`${location.pathname}${location.search}${location.hash}`), [location.pathname, location.search, location.hash]);
  return <nav dir="rtl" aria-label="ناوبری برنامه" className="sticky top-0 z-50 flex items-center gap-2 border-b bg-white/95 px-3 py-2 backdrop-blur">
    <Button type="button" variant="outline" size="sm" onClick={() => navigate(safePreviousRoute())}><ArrowRight className="ml-2 h-4 w-4"/>بازگشت</Button>
    <Button type="button" variant="outline" size="sm" onClick={() => navigate(authenticatedHome())}><Home className="ml-2 h-4 w-4"/>خانه</Button>
  </nav>;
}
