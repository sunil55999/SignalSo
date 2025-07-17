import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { apiRequest } from '@/lib/queryClient';
import { SystemHealthCenter } from '@/components/dashboard/SystemHealthCenter';
import { TradingMetrics } from '@/components/dashboard/TradingMetrics';
import { EventTimeline } from '@/components/dashboard/EventTimeline';
import { QuickActionsPanel } from '@/components/dashboard/QuickActionsPanel';
import { GlobalImportPanel } from '@/components/GlobalImportPanel';
import { OnboardingWizard } from '@/components/OnboardingWizard';
import { ImportExportPanel } from '@/components/ImportExportPanel';
import { ActivityCenter } from '@/components/ActivityCenter';
import { EnhancedManagementPanel } from '@/components/EnhancedManagementPanel';
import { FeedbackSystem, useFeedbackSystem } from '@/components/FeedbackSystem';
import { 
  Activity, 
  TrendingUp, 
  Users, 
  DollarSign,
  Play,
  Pause,
  CheckCircle,
  XCircle,
  AlertCircle,
  BarChart3,
  Settings,
  Moon,
  Sun,
  Plus,
  Upload,
  FileText,
  Zap
} from 'lucide-react';

export function Dashboard() {
  const { toast } = useToast();
  const [showImportPanel, setShowImportPanel] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [currentView, setCurrentView] = useState<'dashboard' | 'import' | 'activity' | 'manage'>('dashboard');
  const { items: feedbackItems, addFeedback, updateFeedback, removeFeedback } = useFeedbackSystem();
  
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

  const handleStartRouter = async () => {
    const feedbackId = addFeedback({
      type: 'connection',
      action: 'Starting Router',
      status: 'loading',
      message: 'Starting signal router...'
    });

    try {
      const response = await apiRequest('/api/router/start', { method: 'POST' });
      if (response.success) {
        updateFeedback(feedbackId, {
          status: 'success',
          message: 'Signal router started successfully'
        });
        
        toast({
          title: 'Router started',
          description: 'Signal router has been started successfully',
        });
        
        setTimeout(() => removeFeedback(feedbackId), 3000);
      }
    } catch (error) {
      updateFeedback(feedbackId, {
        status: 'error',
        message: 'Failed to start router'
      });
      
      toast({
        title: 'Failed to start router',
        description: 'Could not start the signal router',
        variant: 'destructive',
      });
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
      case 'running':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'disconnected':
      case 'stopped':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
    }
  };

  return (
    <div className="space-y-6 p-4">
      {/* Header with Title and Main Actions */}
      <div className="flex flex-col space-y-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">SignalOS Trading Terminal</h1>
          <p className="text-muted-foreground mt-1">Professional signal automation and trading control</p>
        </div>
        
        {/* Core Navigation - Primary Functions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="cursor-pointer transition-all hover:shadow-lg border-2 hover:border-blue-500" onClick={() => setCurrentView('manage')}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Settings className="h-8 w-8 text-blue-600" />
                  <div>
                    <h3 className="font-semibold text-lg">Manage</h3>
                    <p className="text-sm text-muted-foreground">Signals, Strategies & Providers</p>
                  </div>
                </div>
                {currentView === 'manage' && <CheckCircle className="h-6 w-6 text-green-500" />}
              </div>
            </CardContent>
          </Card>
          
          <Card className="cursor-pointer transition-all hover:shadow-lg border-2 hover:border-green-500" onClick={() => setCurrentView('import')}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Upload className="h-8 w-8 text-green-600" />
                  <div>
                    <h3 className="font-semibold text-lg">Import</h3>
                    <p className="text-sm text-muted-foreground">Add signals & data</p>
                  </div>
                </div>
                {currentView === 'import' && <CheckCircle className="h-6 w-6 text-green-500" />}
              </div>
            </CardContent>
          </Card>
          
          <Card className="cursor-pointer transition-all hover:shadow-lg border-2 hover:border-purple-500" onClick={() => setCurrentView('activity')}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Activity className="h-8 w-8 text-purple-600" />
                  <div>
                    <h3 className="font-semibold text-lg">Activity</h3>
                    <p className="text-sm text-muted-foreground">View logs & history</p>
                  </div>
                </div>
                {currentView === 'activity' && <CheckCircle className="h-6 w-6 text-green-500" />}
              </div>
            </CardContent>
          </Card>
        </div>
        
        {/* Quick Actions & Tools */}
        <div className="flex flex-wrap items-center gap-2 bg-white dark:bg-gray-800 p-3 rounded-lg border">
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setShowImportPanel(true)}
          >
            <Plus className="h-4 w-4 mr-2" />
            Quick Actions
          </Button>
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setShowOnboarding(true)}
          >
            <Zap className="h-4 w-4 mr-2" />
            Setup Wizard
          </Button>
          <Button onClick={handleStartRouter} className="flex items-center gap-2">
            <Play className="h-4 w-4" />
            Start Router
          </Button>
        </div>
      </div>

      {/* View Switching */}
      {currentView === 'dashboard' && (
        <>
          {/* Trading Metrics - Key Performance Indicators */}
          <TradingMetrics />

          {/* Main Dashboard Grid */}
          <div className="grid gap-6 lg:grid-cols-3">
            {/* System Health Center - 2 columns */}
            <div className="lg:col-span-2">
              <SystemHealthCenter />
            </div>

            {/* Quick Actions Panel - 1 column */}
            <div className="lg:col-span-1">
              <QuickActionsPanel />
            </div>
          </div>

          {/* Event Timeline - Full width */}
          <EventTimeline />
        </>
      )}

      {/* Import/Export View */}
      {currentView === 'import' && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-4">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => setCurrentView('dashboard')}
            >
              ← Back to Dashboard
            </Button>
          </div>
          <ImportExportPanel />
        </div>
      )}

      {/* Activity Center View */}
      {currentView === 'activity' && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-4">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => setCurrentView('dashboard')}
            >
              ← Back to Dashboard
            </Button>
          </div>
          <ActivityCenter />
        </div>
      )}

      {/* Enhanced Management Panel View */}
      {currentView === 'manage' && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-4">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => setCurrentView('dashboard')}
            >
              ← Back to Dashboard
            </Button>
          </div>
          <EnhancedManagementPanel />
        </div>
      )}

      {/* Account & Risk Summary - Only show on dashboard view */}
      {currentView === 'dashboard' && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20 border-green-200 dark:border-green-800">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-green-800 dark:text-green-200">Account Balance</CardTitle>
              <DollarSign className="h-4 w-4 text-green-600 dark:text-green-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-900 dark:text-green-100">
                ${mt5Status?.balance?.toLocaleString() || '0'}
              </div>
              <p className="text-xs text-green-700 dark:text-green-300">
                Equity: ${mt5Status?.equity?.toLocaleString() || '0'}
              </p>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border-blue-200 dark:border-blue-800">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-blue-800 dark:text-blue-200">Daily PnL</CardTitle>
              <TrendingUp className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-900 dark:text-blue-100">+$1,247</div>
              <p className="text-xs text-blue-700 dark:text-blue-300">
                Today's performance
              </p>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20 border-purple-200 dark:border-purple-800">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-purple-800 dark:text-purple-200">Active Signals</CardTitle>
              <Activity className="h-4 w-4 text-purple-600 dark:text-purple-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-purple-900 dark:text-purple-100">{routerStatus?.activeTasks || 0}</div>
              <p className="text-xs text-purple-700 dark:text-purple-300">
                Processing now
              </p>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-900/20 dark:to-orange-800/20 border-orange-200 dark:border-orange-800">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-orange-800 dark:text-orange-200">Channels</CardTitle>
              <Users className="h-4 w-4 text-orange-600 dark:text-orange-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-900 dark:text-orange-100">{telegramStatus?.channelCount || 0}</div>
              <p className="text-xs text-orange-700 dark:text-orange-300">
                Telegram sources
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Global Modals */}
      <GlobalImportPanel 
        isOpen={showImportPanel} 
        onClose={() => setShowImportPanel(false)} 
      />
      
      {showOnboarding && (
        <OnboardingWizard 
          onComplete={() => setShowOnboarding(false)} 
        />
      )}

      {/* Global Feedback System */}
      <FeedbackSystem 
        items={feedbackItems} 
        onRetry={(id) => {
          console.log('Retry action:', id);
        }}
        onDismiss={removeFeedback}
      />
    </div>
  );
}