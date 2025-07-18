import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { SystemHealthPanel } from './SystemHealthPanel';
import { AccountSummaryPanel } from './AccountSummaryPanel';
import { SignalActivityFeed } from './SignalActivityFeed';
import { QuickActionsPanel } from './QuickActionsPanel';
import { NotificationCenter } from './NotificationCenter';

export function MainDashboard() {
  const [activeSection, setActiveSection] = useState<'overview' | 'import' | 'signals' | 'trades' | 'logs' | 'settings'>('overview');

  // Real-time data queries
  const { data: systemStatus } = useQuery({
    queryKey: ['/api/health'],
    refetchInterval: 2000,
  });

  const { data: routerStatus } = useQuery({
    queryKey: ['/api/router/status'],
    refetchInterval: 2000,
  });

  const { data: mt5Status } = useQuery({
    queryKey: ['/api/mt5/status'],
    refetchInterval: 2000,
  });

  const { data: telegramStatus } = useQuery({
    queryKey: ['/api/telegram/status'],
    refetchInterval: 2000,
  });

  const { data: logs } = useQuery({
    queryKey: ['/api/logs'],
    refetchInterval: 5000,
  });

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-slate-50 to-white dark:from-slate-900 dark:to-slate-800">
      {/* Main Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 h-full">
        {/* System Health Panel - Left Column */}
        <div className="lg:col-span-3">
          <SystemHealthPanel 
            systemStatus={systemStatus}
            routerStatus={routerStatus}
            mt5Status={mt5Status}
            telegramStatus={telegramStatus}
          />
        </div>

        {/* Central Content Area */}
        <div className="lg:col-span-6 flex flex-col space-y-6">
          {/* Account Summary */}
          <AccountSummaryPanel mt5Status={mt5Status} />
          
          {/* Signal Activity Feed */}
          <SignalActivityFeed logs={logs} />
        </div>

        {/* Right Column - Quick Actions & Notifications */}
        <div className="lg:col-span-3 flex flex-col space-y-6">
          <QuickActionsPanel />
          <NotificationCenter />
        </div>
      </div>
    </div>
  );
}