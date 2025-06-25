import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/hooks/use-auth";
import Dashboard from "@/pages/dashboard";
import SignalsPage from "@/pages/signals-page";
import TradesPage from "@/pages/trades-page";
import ProvidersPage from "@/pages/providers-page";
import ProvidersConfigPage from "@/pages/providers-config";
import StrategyPage from "@/pages/strategy-page";
import CopilotPage from "@/pages/copilot-page";
import RiskPage from "@/pages/risk-page";
import SettingsPage from "@/pages/settings-page";
import Analytics from "@/pages/Analytics";
import AdminPage from "@/pages/admin-page";
import AuthPage from "@/pages/auth-page";
import ProviderCompare from "@/pages/ProviderCompare";
import NotFound from "@/pages/not-found";
import { ProtectedRoute } from "./lib/protected-route";

function Router() {
  return (
    <Switch>
      <ProtectedRoute path="/" component={Dashboard} />
      <ProtectedRoute path="/signals" component={SignalsPage} />
      <ProtectedRoute path="/trades" component={TradesPage} />
      <ProtectedRoute path="/providers" component={ProvidersPage} />
      <ProtectedRoute path="/providers/config" component={ProvidersConfigPage} />
      <Route path="/provider-compare" component={ProviderCompare} />
      <ProtectedRoute path="/strategy" component={StrategyPage} />
      <ProtectedRoute path="/copilot" component={CopilotPage} />
      <ProtectedRoute path="/risk" component={RiskPage} />
      <ProtectedRoute path="/settings" component={SettingsPage} />
      <ProtectedRoute path="/analytics" component={Analytics} />
      <ProtectedRoute path="/admin" component={AdminPage} />
      <Route path="/auth" component={AuthPage} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
