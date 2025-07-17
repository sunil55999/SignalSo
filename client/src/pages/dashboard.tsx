import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { 
  Activity, 
  TrendingUp, 
  Users, 
  DollarSign,
  Play,
  Pause,
  CheckCircle,
  XCircle,
  AlertCircle
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
      const response = await fetch('/api/router/start', { method: 'POST' });
      if (response.ok) {
        toast.success({
          title: 'Router started',
          description: 'Signal router has been started successfully',
        });
      }
    } catch (error) {
      toast.error({
        title: 'Failed to start router',
        description: 'Could not start the signal router',
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
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Trading Dashboard</h1>
        <Button onClick={handleStartRouter} className="flex items-center gap-2">
          <Play className="h-4 w-4" />
          Start Signal Router
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Router Status</CardTitle>
            {getStatusIcon(routerStatus?.status || 'unknown')}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{routerStatus?.status || 'Unknown'}</div>
            <p className="text-xs text-muted-foreground">
              Active tasks: {routerStatus?.activeTasks || 0}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">MT5 Connection</CardTitle>
            {getStatusIcon(mt5Status?.status || 'unknown')}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mt5Status?.status || 'Unknown'}</div>
            <p className="text-xs text-muted-foreground">
              Account: {mt5Status?.account || 'N/A'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Telegram</CardTitle>
            {getStatusIcon(telegramStatus?.status || 'unknown')}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{telegramStatus?.status || 'Unknown'}</div>
            <p className="text-xs text-muted-foreground">
              Channels: {telegramStatus?.channelCount || 0}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Balance</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${mt5Status?.balance || 0}</div>
            <p className="text-xs text-muted-foreground">
              Equity: ${mt5Status?.equity || 0}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Latest system logs and events</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {logs?.slice(0, 5).map((log: any) => (
                <div key={log.id} className="flex items-center gap-2 text-sm">
                  <div className={`h-2 w-2 rounded-full ${
                    log.level === 'error' ? 'bg-red-500' : 
                    log.level === 'warning' ? 'bg-yellow-500' : 'bg-green-500'
                  }`} />
                  <span className="text-muted-foreground">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <span>{log.message}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>System Performance</CardTitle>
            <CardDescription>Real-time metrics and status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">CPU Usage</span>
                <span className="text-sm text-muted-foreground">45%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Memory Usage</span>
                <span className="text-sm text-muted-foreground">2.1GB</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Network</span>
                <span className="text-sm text-muted-foreground">Connected</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Uptime</span>
                <span className="text-sm text-muted-foreground">
                  {Math.floor((routerStatus?.uptime || 0) / 60)}h {(routerStatus?.uptime || 0) % 60}m
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}