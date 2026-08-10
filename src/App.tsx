import { useEffect, type ReactNode } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router";
import Index from "./pages/Index";
import InformationPage from "./pages/InformationPage";
import NotFound from "./pages/NotFound";
import ExpertConsole from "./pages/ExpertConsole";
import RequestDetail from "./pages/RequestDetail";
import CRMDashboard from "./pages/CRMDashboard";
import UserManagement from "./pages/UserManagement";
import CustomerDashboard from "./pages/CustomerDashboard";
import CustomerRequestDetail from "./pages/CustomerRequestDetail";
import PublicTracking from "./pages/PublicTracking";
import ExecutionUnits from "./pages/ExecutionUnits";
import ProjectTracking from "./pages/ProjectTracking";
import VerifyEmail from "./pages/VerifyEmail";
import ProtectedRoute from "./components/ProtectedRoute";
import OperationalShipments from "./pages/OperationalShipments";
import OperationalShipmentDetail from "./pages/OperationalShipmentDetail";
import OperationalWorkQueue from "./pages/OperationalWorkQueue";
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
                <Route path="/user-management" element={
                  <AdminRoute>
                    <PersianOnlyRoute>
                      <ErrorBoundary>
                        <AdminPanel />
                      </ErrorBoundary>
                    </PersianOnlyRoute>
                  </AdminRoute>
                } />
                <Route path="/operations/shipments" element={<ProtectedRoute><OperationalShipments /></ProtectedRoute>} />
                <Route path="/operations/shipments/new" element={<ProtectedRoute><NewOperation /></ProtectedRoute>} />
                <Route path="/operations/shipments/:id" element={<ProtectedRoute><OperationalShipmentDetail /></ProtectedRoute>} />
                <Route path="/operations/work-queue" element={<ProtectedRoute><OperationalWorkQueue /></ProtectedRoute>} />
                <Route path="/operations/intelligence/:id" element={<ProtectedRoute><OipSituationDetail /></ProtectedRoute>} />
                <Route path="/operations/projects/:projectId/units" element={<ProtectedRoute><ExecutionUnits /></ProtectedRoute>} />
                <Route path="/customer/:customerId" element={
                  <ErrorBoundary>
                    <CustomerDashboard />
                  </ErrorBoundary>
                } />
                <Route path="/request/:requestId" element={
                  <ErrorBoundary>
                    <CustomerRequestDetail />
                  </ErrorBoundary>
                } />
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
