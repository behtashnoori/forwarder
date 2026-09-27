import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import CustomerPortalLayout from "@/components/CustomerPortalLayout";
import LocationForm from "@/components/LocationForm";
import RequestTypeChooser, { type RequestShippingType } from "@/components/RequestTypeChooser";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CustomerPortalApiError, fetchCustomerSession } from "@/lib/customerPortalApi";
import { useI18n } from "@/i18n";

export default function CustomerPortalNewRequest() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const [shippingType, setShippingType] = useState<RequestShippingType | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    fetchCustomerSession()
      .then((session) => {
        if (!active) return;
        if (!session.authenticated) {
          navigate("/customer", { replace: true, state: { from: location.pathname } });
          return;
        }
        setReady(true);
      })
      .catch((error) => {
        if (!active) return;
        if (error instanceof CustomerPortalApiError && error.status === 401) {
          navigate("/customer", { replace: true, state: { from: location.pathname } });
          return;
        }
        navigate("/customer", { replace: true, state: { from: location.pathname } });
      });
    return () => { active = false; };
  }, [location.pathname, navigate]);

  return (
    <CustomerPortalLayout privateNav>
      {!ready ? (
        <Card><CardContent className="p-10 text-center">{t("customer.loadingTitle")}</CardContent></Card>
      ) : shippingType ? (
        <div className="mx-auto flex max-w-5xl justify-center">
          <LocationForm shippingType={shippingType} onBack={() => setShippingType(null)} />
        </div>
      ) : (
        <Card className="mx-auto max-w-xl">
          <CardHeader>
            <CardTitle>{t("command.requestTypeTitle")}</CardTitle>
            <p className="text-sm leading-7 text-muted-foreground">{t("command.requestTypeDescription")}</p>
          </CardHeader>
          <CardContent>
            <RequestTypeChooser onSelect={setShippingType} />
          </CardContent>
        </Card>
      )}
    </CustomerPortalLayout>
  );
}
