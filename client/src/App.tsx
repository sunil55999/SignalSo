import { Router, Route, Switch } from 'wouter';
import { Toaster } from '@/components/ui/toaster';
import { ThemeProvider } from '@/components/theme-provider';
import { Navbar } from '@/components/layout/navbar';
import { Sidebar } from '@/components/layout/sidebar';

// Pages
import { Dashboard } from '@/pages/dashboard';
import { LoginPage } from '@/pages/auth/login';
import { ChannelSetup } from '@/pages/channels/setup';
import { SignalValidator } from '@/pages/signals/validator';
import { LogsView } from '@/pages/logs/view';
import { SettingsPanel } from '@/pages/settings/panel';
import { StrategyBacktest } from '@/pages/strategy/backtest';

import { useAuthStore } from '@/store/auth';
import { useEffect } from 'react';

function App() {
  const { isAuthenticated, checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  if (!isAuthenticated) {
    return (
      <ThemeProvider defaultTheme="light">
        <div className="min-h-screen bg-background">
          <LoginPage />
          <Toaster />
        </div>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider defaultTheme="light">
      <div className="min-h-screen bg-background">
        <div className="flex h-screen">
          {/* Sidebar */}
          <Sidebar />
          
          {/* Main content area */}
          <div className="flex-1 flex flex-col">
            {/* Top navbar */}
            <Navbar />
            
            {/* Page content */}
            <main className="flex-1 overflow-auto p-6">
              <Router>
                <Switch>
                  <Route path="/" component={Dashboard} />
                  <Route path="/channels/setup" component={ChannelSetup} />
                  <Route path="/signals/validator" component={SignalValidator} />
                  <Route path="/logs" component={LogsView} />
                  <Route path="/settings" component={SettingsPanel} />
                  <Route path="/strategy/backtest" component={StrategyBacktest} />
                  <Route>
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center">
                        <h1 className="text-2xl font-bold mb-4">Page Not Found</h1>
                        <p className="text-muted-foreground">The page you're looking for doesn't exist.</p>
                      </div>
                    </div>
                  </Route>
                </Switch>
              </Router>
            </main>
          </div>
        </div>
        
        <Toaster />
      </div>
    </ThemeProvider>
  );
}

export default App;