import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { apiRequest } from '@/lib/queryClient';
import { SystemHealthCenter } from '@/components/dashboard/SystemHealthCenter';
import { TradingMetrics } from '@/components/dashboard/TradingMetrics';
import { EventTimeline } from '@/components/dashboard/EventTimeline';
import { QuickActionsPanel } from '@/components/dashboard/QuickActionsPanel';
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
  Sun
} from 'lucide-react';

export function Dashboard() {
  const { toast } = useToast();
  
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
    try {
      const response = await apiRequest('/api/router/start', { method: 'POST' });
      if (response.success) {
        toast({
          title: 'Router started',
          description: 'Signal router has been started successfully',
        });
      }
    } catch (error) {
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
    <div className="space-y-6">
      {/* Header with Title and Main Actions */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">SignalOS Trading Terminal</h1>
          <p className="text-muted-foreground mt-1">Professional signal automation and trading control</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <BarChart3 className="h-4 w-4 mr-2" />
            Analytics
          </Button>
          <Button variant="outline" size="sm">
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>
          <Button onClick={handleStartRouter} className="flex items-center gap-2">
            <Play className="h-4 w-4" />
            Start Router
          </Button>
        </div>
      </div>

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

      {/* Account & Risk Summary */}
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
    </div>
  );
}