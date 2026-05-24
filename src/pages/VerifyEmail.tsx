import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";
import { verifyCustomerEmail } from "@/lib/api";

const VerifyEmail: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState<string>("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("لینک تایید نامعتبر است. توکن در آدرس وجود ندارد.");
      return;
    }

    setStatus("loading");
    verifyCustomerEmail(token)
      .then(({ ok, data }) => {
        if (ok && data.customer_id) {
          setStatus("success");
          setMessage(data.message || "ایمیل شما با موفقیت تایید شد.");
          navigate(`/customer/${data.customer_id}`, { replace: true });
        } else {
          setStatus("error");
          setMessage(data.message || "لینک تایید منقضی یا نامعتبر است.");
        }
      })
      .catch(() => {
        setStatus("error");
        setMessage("خطا در ارتباط با سرور. لطفاً دوباره تلاش کنید.");
      });
  }, [token, navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">
            {status === "loading" && "در حال تایید ایمیل..."}
            {status === "success" && "تایید ایمیل"}
            {status === "error" && "خطا در تایید"}
            {status === "idle" && "تایید ایمیل"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-center">
          {status === "loading" && (
            <div className="flex justify-center">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
            </div>
          )}
          {status === "success" && (
            <>
              <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
              <p className="text-muted-foreground">{message}</p>
              <p className="text-sm text-muted-foreground">در حال انتقال به پنل مشتری...</p>
            </>
          )}
          {status === "error" && (
            <>
              <XCircle className="mx-auto h-12 w-12 text-destructive" />
              <p className="text-muted-foreground">{message}</p>
              <Button asChild variant="outline" className="w-full">
                <Link to="/">بازگشت به صفحه اصلی</Link>
              </Button>
            </>
          )}
          {status === "idle" && !token && (
            <p className="text-muted-foreground">لینک معتبر نیست.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default VerifyEmail;
