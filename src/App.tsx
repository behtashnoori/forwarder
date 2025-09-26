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
            {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  </ErrorBoundary>
);

export default App;