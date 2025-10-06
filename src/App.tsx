import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";
import ExpertConsole from "./pages/ExpertConsole";
import RequestDetail from "./pages/RequestDetail";
import CRMDashboard from "./pages/CRMDashboard";
import UserManagement from "./pages/UserManagement";
import CustomerDashboard from "./pages/CustomerDashboard";
import CustomerRequestDetail from "./pages/CustomerRequestDetail";
import PublicTracking from "./pages/PublicTracking";
import ProtectedRoute from "./components/ProtectedRoute";
import ErrorBoundary from "./components/ErrorBoundary";

const queryClient = new QueryClient();

const App = () => (
  <ErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="/expert" element={
              <ProtectedRoute>
                <ErrorBoundary>
                  <ExpertConsole />
                </ErrorBoundary>
              </ProtectedRoute>
            } />
            <Route path="/expert/requests/:id" element={
              <ProtectedRoute>
                <ErrorBoundary>
                  <RequestDetail />
                </ErrorBoundary>
              </ProtectedRoute>
            } />
            <Route path="/crm" element={
              <ProtectedRoute>
                <ErrorBoundary>
                  <CRMDashboard />
                </ErrorBoundary>
              </ProtectedRoute>
            } />
            <Route path="/user-management" element={
              <ProtectedRoute>
                <ErrorBoundary>
                  <UserManagement />
                </ErrorBoundary>
              </ProtectedRoute>
            } />
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
            {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  </ErrorBoundary>
);

export default App;