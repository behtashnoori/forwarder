import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";
import { verifyCustomerEmail } from "@/lib/api";
import { useI18n } from "@/i18n";

const VerifyEmail: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useI18n();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState<string>("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage(t("verifyEmail.invalidLink"));
      return;
    }

    setStatus("loading");
    verifyCustomerEmail(token)
      .then(({ ok, data }) => {
        if (ok && data.customer_id) {
          setStatus("success");
          setMessage(data.message || t("verifyEmail.successMessage"));
          navigate(`/customer/${data.customer_id}`, { replace: true });
        } else {
          setStatus("error");
          setMessage(data.message || t("verifyEmail.expiredMessage"));
        }
      })
      .catch(() => {
        setStatus("error");
        setMessage(t("verifyEmail.serverError"));
      });
  }, [token, navigate, t]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">
            {status === "loading" && t("verifyEmail.loadingTitle")}
            {status === "success" && t("verifyEmail.successTitle")}
            {status === "error" && t("verifyEmail.errorTitle")}
            {status === "idle" && t("verifyEmail.successTitle")}
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
              <p className="text-sm text-muted-foreground">{t("verifyEmail.redirecting")}</p>
            </>
          )}
          {status === "error" && (
            <>
              <XCircle className="mx-auto h-12 w-12 text-destructive" />
              <p className="text-muted-foreground">{message}</p>
              <Button asChild variant="outline" className="w-full">
                <Link to="/">{t("common.backHome")}</Link>
              </Button>
            </>
          )}
          {status === "idle" && !token && (
            <p className="text-muted-foreground">{t("verifyEmail.invalidIdle")}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default VerifyEmail;
