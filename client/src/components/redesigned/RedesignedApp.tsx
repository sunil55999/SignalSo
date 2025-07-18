import { useState } from 'react';
import { ThemeProvider } from '@/components/theme-provider';
import { Toaster } from '@/components/ui/toaster';
import { RedesignedHeader } from './RedesignedHeader';
import { RedesignedSidebar } from './RedesignedSidebar';
import { MainDashboard } from './MainDashboard';
import { ImportExportHub } from './ImportExportHub';
import { SignalProviderManagement } from './SignalProviderManagement';
import { StrategyBuilder } from './StrategyBuilder';
import { ActiveTradesPanel } from './ActiveTradesPanel';
import { LoginPage } from '@/pages/auth/login';
import { ComprehensiveLogsCenter } from './ComprehensiveLogsCenter';
import { SettingsPanel } from '@/pages/settings/panel';
import { useAuthStore } from '@/store/auth';
import { useEffect } from 'react';

export function RedesignedApp() {
  const { isAuthenticated, checkAuth } = useAuthStore();
  const [activeSection, setActiveSection] = useState('dashboard');

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // For development/demo purposes, we'll show the redesigned interface
  // In production, uncomment the authentication check below
  /*
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
  */

  const renderContent = () => {
    switch (activeSection) {
      case 'dashboard':
        return <MainDashboard />;
      case 'import':
        return <ImportExportHub />;
      case 'providers':
        return <SignalProviderManagement />;
      case 'strategies':
        return <StrategyBuilder />;
      case 'backtest':
        return <StrategyBuilder />;
      case 'trades':
        return <ActiveTradesPanel />;
      case 'logs':
        return <ComprehensiveLogsCenter />;
      case 'settings':
        return <SettingsPanel />;
      default:
        return <MainDashboard />;
    }
  };

  return (
    <ThemeProvider defaultTheme="light">
      <div className="min-h-screen bg-background">
        <div className="flex h-screen">
          {/* Header */}
          <div className="fixed top-0 left-0 right-0 z-50">
            <RedesignedHeader />
          </div>

          {/* Sidebar */}
          <div className="fixed left-0 top-16 bottom-0 z-40">
            <RedesignedSidebar 
              activeSection={activeSection} 
              onSectionChange={setActiveSection} 
            />
          </div>

          {/* Main Content */}
          <div className="flex-1 ml-64 mt-16">
            <main className="p-6 overflow-auto h-full">
              {renderContent()}
            </main>
          </div>
        </div>
        
        <Toaster />
      </div>
    </ThemeProvider>
  );
}