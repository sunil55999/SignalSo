import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { 
  Activity, 
  TrendingUp, 
  DollarSign, 
  Users, 
  Play, 
  Pause, 
  Square,
  Zap,
  AlertCircle,
  CheckCircle,
  Clock,
  BarChart3
} from 'lucide-react';

export function Dashboard() {
  const { toast } = useToast();

  // Fetch router status
  const { data: routerStatus } = useQuery({
    queryKey: ['/api/router/status'],
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  // Fetch MT5 status
  const { data: mt5Status } = useQuery({
    queryKey: ['/api/mt5/status'],
    refetchInterval: 5000,
  });

  // Fetch recent logs
  const { data: recentLogs } = useQuery({
    queryKey: ['/api/logs?limit=10'],
    refetchInterval: 10000,
  });

  const handleStartRouter = async () => {
    try {
      const response = await fetch('/api/router/start', { method: 'POST' });
      const result = await response.json();
      
      if (result.success) {
        toast({ title: 'Router started successfully' });
      } else {
        toast({ 
          title: 'Failed to start router', 
          description: result.error,
          variant: 'destructive' 
        });
      }
    } catch (error) {
      toast({ 
        title: 'Error starting router', 
        variant: 'destructive' 
      });
    }
  };

  const handleStopRouter = async () => {
    try {
      const response = await fetch('/api/router/stop', { method: 'POST' });
      const result = await response.json();
      
      if (result.success) {
        toast({ title: 'Router stopped successfully' });
      } else {
        toast({ 
          title: 'Failed to stop router', 
          description: result.error,
          variant: 'destructive' 
        });
      }
    } catch (error) {
      toast({ 
        title: 'Error stopping router', 
        variant: 'destructive' 
      });
    }
  };

  const handleConnectMT5 = async () => {
    try {
      const response = await fetch('/api/mt5/connect', { method: 'POST' });
      const result = await response.json();
      
      if (result.success) {
        toast({ title: 'MT5 connected successfully' });
      } else {
        toast({ 
          title: 'Failed to connect MT5', 
          description: result.error,
          variant: 'destructive' 
        });
      }
    } catch (error) {
      toast({ 
        title: 'Error connecting MT5', 
        variant: 'destructive' 
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-300">
            Monitor your trading automation system
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-green-500 pulse-green" />
          <span className="text-sm text-gray-600 dark:text-gray-400">Live</span>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Router Status</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {routerStatus?.isRunning ? 'Running' : 'Stopped'}
              </p>
            </div>
            <div className={`p-3 rounded-full ${routerStatus?.isRunning ? 'bg-green-100 dark:bg-green-900' : 'bg-red-100 dark:bg-red-900'}`}>
              {routerStatus?.isRunning ? (
                <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
              ) : (
                <AlertCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
              )}
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">MT5 Connection</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {mt5Status?.isConnected ? 'Connected' : 'Disconnected'}
              </p>
            </div>
            <div className={`p-3 rounded-full ${mt5Status?.isConnected ? 'bg-green-100 dark:bg-green-900' : 'bg-red-100 dark:bg-red-900'}`}>
              <Activity className={`h-6 w-6 ${mt5Status?.isConnected ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`} />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Monitored Channels</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {routerStatus?.monitoredChannels?.length || 0}
              </p>
            </div>
            <div className="p-3 rounded-full bg-blue-100 dark:bg-blue-900">
              <Users className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Account Balance</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                ${mt5Status?.accountInfo?.balance?.toFixed(2) || '10,000.00'}
              </p>
            </div>
            <div className="p-3 rounded-full bg-green-100 dark:bg-green-900">
              <DollarSign className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Control Panel */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Control Panel</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <h3 className="font-medium text-gray-700 dark:text-gray-300">Signal Router</h3>
            <div className="flex gap-2">
              <Button 
                onClick={handleStartRouter}
                disabled={routerStatus?.isRunning}
                size="sm"
                className="flex-1"
              >
                <Play className="h-4 w-4 mr-2" />
                Start
              </Button>
              <Button 
                onClick={handleStopRouter}
                disabled={!routerStatus?.isRunning}
                variant="outline"
                size="sm"
                className="flex-1"
              >
                <Pause className="h-4 w-4 mr-2" />
                Stop
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="font-medium text-gray-700 dark:text-gray-300">MT5 Connection</h3>
            <div className="flex gap-2">
              <Button 
                onClick={handleConnectMT5}
                disabled={mt5Status?.isConnected}
                size="sm"
                className="flex-1"
              >
                <Zap className="h-4 w-4 mr-2" />
                Connect
              </Button>
              <Button 
                variant="outline"
                size="sm"
                className="flex-1"
              >
                <Square className="h-4 w-4 mr-2" />
                Disconnect
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="font-medium text-gray-700 dark:text-gray-300">Emergency</h3>
            <Button 
              variant="destructive"
              size="sm"
              className="w-full"
            >
              <AlertCircle className="h-4 w-4 mr-2" />
              Emergency Stop
            </Button>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Recent Logs</h2>
          <div className="space-y-3">
            {recentLogs?.slice(0, 5).map((log: any) => (
              <div key={log.id} className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700">
                <div className={`w-2 h-2 rounded-full ${
                  log.level === 'error' ? 'bg-red-500' : 
                  log.level === 'warning' ? 'bg-yellow-500' : 
                  'bg-green-500'
                }`} />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {log.message}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {log.component} • {new Date(log.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">System Performance</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">CPU Usage</span>
              <span className="text-sm font-medium text-gray-900 dark:text-white">45%</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full" style={{ width: '45%' }} />
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Memory Usage</span>
              <span className="text-sm font-medium text-gray-900 dark:text-white">62%</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div className="bg-green-600 h-2 rounded-full" style={{ width: '62%' }} />
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Signal Processing</span>
              <span className="text-sm font-medium text-gray-900 dark:text-white">85%</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div className="bg-purple-600 h-2 rounded-full" style={{ width: '85%' }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}