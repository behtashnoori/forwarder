import { useEffect, type ReactNode } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Routes, Route } from "react-router";
import Index from "./pages/Index";
import InformationPage from "./pages/InformationPage";
import NotFound from "./pages/NotFound";
import ExpertConsole from "./pages/ExpertConsole";
import RequestDetail from "./pages/RequestDetail";
import CRMDashboard from "./pages/CRMDashboard";
import CustomerRoleManagement from "./pages/CustomerRoleManagement";
import CustomerManagement from "./pages/CustomerManagement";
import UserManagement from "./pages/UserManagement";
import CustomerPortalAccess from "./pages/CustomerPortalAccess";
import CustomerPortalRequests from "./pages/CustomerPortalRequests";
import CustomerPortalRequestDetail from "./pages/CustomerPortalRequestDetail";
import CustomerPortalProfile from "./pages/CustomerPortalProfile";
import CustomerPortalChangePassword from "./pages/CustomerPortalChangePassword";
import CustomerPortalForgotPassword from "./pages/CustomerPortalForgotPassword";
import CustomerPortalTokenPassword from "./pages/CustomerPortalTokenPassword";
import CustomerPortalAccountSupport from "./pages/CustomerPortalAccountSupport";
import PublicTracking from "./pages/PublicTracking";
import ExecutionUnits from "./pages/ExecutionUnits";
import ProjectTracking from "./pages/ProjectTracking";
import VerifyEmail from "./pages/VerifyEmail";
import ProtectedRoute from "./components/ProtectedRoute";
import OperationalShipments from "./pages/OperationalShipments";
import OperationalShipmentDetail from "./pages/OperationalShipmentDetail";
import OperationalWorkspace from "./pages/OperationalWorkspace";
import OperationalWorkQueue from "./pages/OperationalWorkQueue";
import OperationsControlTower from "./pages/OperationsControlTower";
import PersistedDashboard from "./pages/PersistedDashboard";
import DashboardBuilder from "./pages/DashboardBuilder";
import DashboardIndex from "./pages/DashboardIndex";
import NewOperation from "./pages/NewOperation";
import OipSituationDetail from "./pages/OipSituationDetail";
import AdminRoute from "./components/AdminRoute";
import ErrorBoundary from "./components/ErrorBoundary";
import AdminPanel from "./pages/AdminPanel";
import RouteScrollManager from "./components/RouteScrollManager";
import { env } from "./lib/env";
import { SiteSettingsProvider } from "./contexts/SiteSettingsContext";
import { I18nProvider, useI18n } from "./i18n";

const queryClient = new QueryClient();
const CRM_ALLOWED_ROLES = ["admin", "crm_manager", "supervisor", "business_expert"];

function OperationalRoute({ children }: { children: ReactNode }) {
  const expertUser = localStorage.getItem("expert_user");
  try {
    if (expertUser && JSON.parse(expertUser).authority === "PLATFORM_ADMIN") {
      return <main className="p-6" dir="rtl">این سطح عملیاتی به یک سازمان مشخص نیاز دارد.</main>;
    }
  } catch {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

function DevHealthCheck() {
  useEffect(() => {
    if (!import.meta.env.DEV) return;
    const base = env.API_URL || "";
    const healthUrl = `${base}/api/health`;
    console.warn("Health check URL:", healthUrl);
    fetch(healthUrl)
      .then(async (r) => {
        const data = await r.json().catch(() => ({}));
        if (r.ok && data?.status === "ok") {
          console.log("✅ Backend health OK:", data.port != null ? `port ${data.port}` : data);
          return;
        }
        const msg =
          data?.message ||
          data?.error ||
          (data?.database === "not_ready" ? "Database not ready" : "Backend health check failed");
        console.warn("⚠️ Backend health check failed:", msg);
      })
      .catch((err) => {
        console.warn("⚠️ Backend health check failed (is backend running on PORT from .env?):", err);
      });
  }, []);
  return null;
}

function PersianOnlyRoute({ children }: { children: ReactNode }) {
  const { language, setLanguage } = useI18n();

  useEffect(() => {
    if (language !== "fa") {
      setLanguage("fa");
    }
  }, [language, setLanguage]);

  if (language !== "fa") {
    return null;
  }

  return <>{children}</>;
}

const App = () => (
  <ErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <DevHealthCheck />
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <RouteScrollManager />
          <I18nProvider>
            <SiteSettingsProvider>
              <Routes>
                <Route path="/" element={<Index />} />
                <Route path="/about" element={<InformationPage kind="about" />} />
                <Route path="/contact" element={<InformationPage kind="contact" />} />
                <Route path="/expert" element={
                  <ProtectedRoute>
                    <PersianOnlyRoute>
                      <ErrorBoundary>
                        <ExpertConsole />
                      </ErrorBoundary>
                    </PersianOnlyRoute>
                  </ProtectedRoute>
                } />
                <Route path="/expert/requests/:id" element={
                  <ProtectedRoute>
                    <PersianOnlyRoute>
                      <ErrorBoundary>
                        <RequestDetail />
                      </ErrorBoundary>
                    </PersianOnlyRoute>
                  </ProtectedRoute>
                } />
                <Route path="/crm" element={
                  <ProtectedRoute allowedRoles={CRM_ALLOWED_ROLES}>
                    <PersianOnlyRoute>
                      <ErrorBoundary>
                        <CRMDashboard />
                      </ErrorBoundary>
                    </PersianOnlyRoute>
                  </ProtectedRoute>
                } />
                <Route path="/admin" element={
                  <AdminRoute>
                    <PersianOnlyRoute>
                      <ErrorBoundary>
                        <AdminPanel />
                      </ErrorBoundary>
                    </PersianOnlyRoute>
                  </AdminRoute>
                } />
                <Route path="/admin/customers" element={<AdminRoute><PersianOnlyRoute><ErrorBoundary><CustomerRoleManagement /></ErrorBoundary></PersianOnlyRoute></AdminRoute>} />
                <Route path="/admin/customer-portal-accounts" element={<AdminRoute><PersianOnlyRoute><ErrorBoundary><CustomerPortalAccountSupport /></ErrorBoundary></PersianOnlyRoute></AdminRoute>} />
                <Route path="/customers" element={<ProtectedRoute><PersianOnlyRoute><ErrorBoundary><CustomerManagement /></ErrorBoundary></PersianOnlyRoute></ProtectedRoute>} />
                <Route path="/user-management" element={
                  <AdminRoute>
                    <PersianOnlyRoute>
                      <ErrorBoundary>
                        <AdminPanel />
                      </ErrorBoundary>
                    </PersianOnlyRoute>
                  </AdminRoute>
                } />
                <Route path="/operations" element={<ProtectedRoute><OperationalRoute><OperationalWorkspace /></OperationalRoute></ProtectedRoute>} />
                <Route path="/operations/shipments" element={<ProtectedRoute><OperationalRoute><OperationalShipments /></OperationalRoute></ProtectedRoute>} />
                <Route path="/operations/shipments/new" element={<ProtectedRoute><OperationalRoute><NewOperation /></OperationalRoute></ProtectedRoute>} />
                <Route path="/operations/shipments/:id" element={<ProtectedRoute><OperationalRoute><OperationalShipmentDetail /></OperationalRoute></ProtectedRoute>} />
                <Route path="/operations/work-queue" element={<ProtectedRoute><OperationalRoute><OperationalWorkQueue /></OperationalRoute></ProtectedRoute>} />
                <Route path="/operations/control-tower" element={<ProtectedRoute><OperationalRoute><OperationsControlTower /></OperationalRoute></ProtectedRoute>} />
                <Route path="/dashboards" element={<ProtectedRoute><DashboardIndex /></ProtectedRoute>} />
                <Route path="/dashboards/:public_id" element={<ProtectedRoute><PersistedDashboard /></ProtectedRoute>} />
                <Route path="/dashboards/:public_id/edit" element={<ProtectedRoute><DashboardBuilder /></ProtectedRoute>} />
                <Route path="/operations/intelligence/:id" element={<ProtectedRoute><OperationalRoute><OipSituationDetail /></OperationalRoute></ProtectedRoute>} />
                <Route path="/operations/projects/:projectId/units" element={<ProtectedRoute><OperationalRoute><ExecutionUnits /></OperationalRoute></ProtectedRoute>} />
                <Route path="/customer" element={<ErrorBoundary><CustomerPortalAccess /></ErrorBoundary>} />
                <Route path="/customer/forgot-password" element={<ErrorBoundary><CustomerPortalForgotPassword /></ErrorBoundary>} />
                <Route path="/customer/reset-password" element={<ErrorBoundary><CustomerPortalTokenPassword mode="reset" /></ErrorBoundary>} />
                <Route path="/customer/enroll" element={<ErrorBoundary><CustomerPortalTokenPassword mode="enrollment" /></ErrorBoundary>} />
                <Route path="/customer/requests" element={<ErrorBoundary><CustomerPortalRequests /></ErrorBoundary>} />
                <Route path="/customer/requests/:requestId" element={<ErrorBoundary><CustomerPortalRequestDetail /></ErrorBoundary>} />
                <Route path="/customer/profile" element={<ErrorBoundary><CustomerPortalProfile /></ErrorBoundary>} />
                <Route path="/customer/change-password" element={<ErrorBoundary><CustomerPortalChangePassword /></ErrorBoundary>} />
                <Route path="/customer/:customerId" element={<Navigate to="/customer/requests" replace />} />
                <Route path="/request/:requestId" element={<Navigate to="/customer/requests" replace />} />
                <Route path="/customer/track/:requestId" element={
                  <ErrorBoundary>
                    <PublicTracking />
                  </ErrorBoundary>
                } />
                <Route path="/project/track/:trackingCode" element={<ErrorBoundary><ProjectTracking /></ErrorBoundary>} />
                <Route path="/verify-email" element={
                  <ErrorBoundary>
                    <VerifyEmail />
                  </ErrorBoundary>
                } />
                {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
                <Route path="*" element={<NotFound />} />
              </Routes>
            </SiteSettingsProvider>
          </I18nProvider>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  </ErrorBoundary>
);

export default App;
