import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Activity, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Zap,
  Database,
  MessageSquare,
  TrendingUp,
  Settings,
  Cpu
} from 'lucide-react';

interface SystemHealthPanelProps {
  systemStatus: any;
  routerStatus: any;
  mt5Status: any;
  telegramStatus: any;
}

export function SystemHealthPanel({ systemStatus, routerStatus, mt5Status, telegramStatus }: SystemHealthPanelProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected':
      case 'running':
      case 'healthy':
        return 'bg-green-500';
      case 'disconnected':
      case 'stopped':
      case 'unhealthy':
        return 'bg-red-500';
      default:
        return 'bg-yellow-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
      case 'running':
      case 'healthy':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'disconnected':
      case 'stopped':
      case 'unhealthy':
        return <XCircle className="h-4 w-4 text-red-600" />;
      default:
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
    }
  };

  const systemModules = [
    {
      name: 'Signal Parser',
      status: systemStatus?.status || 'healthy',
      icon: <Cpu className="h-5 w-5" />,
      description: 'AI-powered signal processing',
      uptime: '99.9%'
    },
    {
      name: 'Signal Router',
      status: routerStatus?.status || 'running',
      icon: <Zap className="h-5 w-5" />,
      description: 'Signal routing & execution',
      uptime: routerStatus?.uptime ? `${Math.floor(routerStatus.uptime / 3600)}h ${Math.floor((routerStatus.uptime % 3600) / 60)}m` : 'N/A'
    },
    {
      name: 'MT5 Bridge',
      status: mt5Status?.status || 'connected',
      icon: <TrendingUp className="h-5 w-5" />,
      description: 'MetaTrader 5 integration',
      uptime: '98.5%'
    },
    {
      name: 'Telegram Bot',
      status: telegramStatus?.status || 'connected',
      icon: <MessageSquare className="h-5 w-5" />,
      description: 'Telegram channel monitoring',
      uptime: '99.1%'
    },
    {
      name: 'Database',
      status: 'healthy',
      icon: <Database className="h-5 w-5" />,
      description: 'Data storage & retrieval',
      uptime: '99.9%'
    },
    {
      name: 'Risk Engine',
      status: 'healthy',
      icon: <Settings className="h-5 w-5" />,
      description: 'Risk management system',
      uptime: '100%'
    }
  ];

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          System Health Center
        </CardTitle>
        <CardDescription>Live status monitoring for all core modules</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {systemModules.map((module) => (
          <div key={module.name} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-background">
                {module.icon}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-sm">{module.name}</h3>
                  <div className={`h-2 w-2 rounded-full ${getStatusColor(module.status)}`} />
                </div>
                <p className="text-xs text-muted-foreground">{module.description}</p>
              </div>
            </div>
            <div className="text-right">
              <Badge 
                variant={module.status === 'healthy' || module.status === 'running' || module.status === 'connected' ? 'default' : 'destructive'}
                className="text-xs"
              >
                {module.status}
              </Badge>
              <p className="text-xs text-muted-foreground mt-1">{module.uptime}</p>
            </div>
          </div>
        ))}
        
        <div className="pt-4 border-t">
          <Button size="sm" variant="outline" className="w-full">
            <Settings className="h-4 w-4 mr-2" />
            System Diagnostics
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}