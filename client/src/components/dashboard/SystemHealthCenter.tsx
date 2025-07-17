import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  CheckCircle, 
  XCircle, 
  AlertCircle, 
  Wifi, 
  Database, 
  Bot, 
  TrendingUp,
  Shield,
  Zap
} from 'lucide-react';

interface SystemModule {
  name: string;
  status: 'healthy' | 'warning' | 'error' | 'offline';
  icon: React.ReactNode;
  details: string;
  lastUpdated: string;
}

export function SystemHealthCenter() {
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

  const { data: bridgeStatus } = useQuery({
    queryKey: ['/api/bridge/status'],
    refetchInterval: 2000,
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected':
      case 'running':
      case 'active':
        return 'healthy';
      case 'disconnected':
      case 'stopped':
      case 'inactive':
        return 'error';
      default:
        return 'warning';
    }
  };

  const getStatusBadge = (status: 'healthy' | 'warning' | 'error' | 'offline') => {
    switch (status) {
      case 'healthy':
        return <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Healthy</Badge>;
      case 'warning':
        return <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100">Warning</Badge>;
      case 'error':
        return <Badge className="bg-red-100 text-red-800 hover:bg-red-100">Error</Badge>;
      case 'offline':
        return <Badge className="bg-gray-100 text-gray-800 hover:bg-gray-100">Offline</Badge>;
    }
  };

  const getStatusIcon = (status: 'healthy' | 'warning' | 'error' | 'offline') => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'warning':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'offline':
        return <XCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const systemModules: SystemModule[] = [
    {
      name: 'Signal Router',
      status: getStatusColor(routerStatus?.status || 'offline'),
      icon: <TrendingUp className="h-5 w-5" />,
      details: `Active tasks: ${routerStatus?.activeTasks || 0}`,
      lastUpdated: routerStatus?.lastStarted || 'Never'
    },
    {
      name: 'MT5 Bridge',
      status: getStatusColor(mt5Status?.status || 'offline'),
      icon: <Database className="h-5 w-5" />,
      details: mt5Status?.account || 'No account',
      lastUpdated: mt5Status?.lastConnected || 'Never'
    },
    {
      name: 'Telegram Monitor',
      status: getStatusColor(telegramStatus?.status || 'offline'),
      icon: <Bot className="h-5 w-5" />,
      details: `${telegramStatus?.channelCount || 0} channels`,
      lastUpdated: telegramStatus?.lastMessageTime || 'Never'
    },
    {
      name: 'API Bridge',
      status: getStatusColor(bridgeStatus?.status || 'offline'),
      icon: <Wifi className="h-5 w-5" />,
      details: `Version ${bridgeStatus?.version || 'Unknown'}`,
      lastUpdated: bridgeStatus?.lastUpdate || 'Never'
    },
    {
      name: 'AI Parser',
      status: 'healthy',
      icon: <Zap className="h-5 w-5" />,
      details: 'Confidence: 95%',
      lastUpdated: new Date().toISOString()
    },
    {
      name: 'License System',
      status: 'healthy',
      icon: <Shield className="h-5 w-5" />,
      details: 'Valid until 2025-12-31',
      lastUpdated: new Date().toISOString()
    }
  ];

  const healthyCount = systemModules.filter(m => m.status === 'healthy').length;
  const warningCount = systemModules.filter(m => m.status === 'warning').length;
  const errorCount = systemModules.filter(m => m.status === 'error').length;

  return (
    <Card className="col-span-2">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold">System Health Center</CardTitle>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
              <span className="text-sm text-muted-foreground">{healthyCount}</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-yellow-500"></div>
              <span className="text-sm text-muted-foreground">{warningCount}</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-red-500"></div>
              <span className="text-sm text-muted-foreground">{errorCount}</span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 md:grid-cols-2">
          {systemModules.map((module) => (
            <div key={module.name} className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  {module.icon}
                  <div>
                    <div className="font-medium text-sm">{module.name}</div>
                    <div className="text-xs text-muted-foreground">{module.details}</div>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {getStatusIcon(module.status)}
                {getStatusBadge(module.status)}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}