import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { 
  Bot, 
  Link, 
  MessageCircle, 
  Store, 
  Bell, 
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock
} from 'lucide-react';
import { SystemHealth } from '@shared/schema';

interface SystemHealthIndicatorsProps {
  systemHealth?: SystemHealth;
  isLoading?: boolean;
}

export function SystemHealthIndicators({ systemHealth, isLoading }: SystemHealthIndicatorsProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">System Health</CardTitle>
          <Bot className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex justify-between items-center">
                <div className="h-4 bg-gray-200 rounded animate-pulse w-24"></div>
                <div className="h-6 bg-gray-200 rounded animate-pulse w-16"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
      case 'connected':
      case 'active':
      case 'enabled':
        return <CheckCircle className="h-3 w-3 text-green-600" />;
      case 'offline':
      case 'disconnected':
      case 'inactive':
      case 'disabled':
        return <XCircle className="h-3 w-3 text-red-600" />;
      case 'error':
        return <AlertCircle className="h-3 w-3 text-red-600" />;
      case 'maintenance':
        return <Clock className="h-3 w-3 text-yellow-600" />;
      default:
        return <AlertCircle className="h-3 w-3 text-gray-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
      case 'connected':
      case 'active':
      case 'enabled':
        return 'bg-green-100 text-green-800';
      case 'offline':
      case 'disconnected':
      case 'inactive':
      case 'disabled':
        return 'bg-red-100 text-red-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      case 'maintenance':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatLastActivity = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diff = now.getTime() - date.getTime();
      
      if (diff < 60000) return 'Just now';
      if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
      if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
      return `${Math.floor(diff / 86400000)}d ago`;
    } catch {
      return 'Unknown';
    }
  };

  const services = [
    {
      name: 'AI Parser',
      icon: Bot,
      data: systemHealth?.aiParser,
      tooltip: `Success Rate: ${(systemHealth?.aiParser?.successRate || 0).toFixed(1)}%`,
    },
    {
      name: 'MT5 Bridge',
      icon: Link,
      data: systemHealth?.mt5Bridge,
      tooltip: `Latency: ${systemHealth?.mt5Bridge?.latency || 0}ms`,
    },
    {
      name: 'Telegram Link',
      icon: MessageCircle,
      data: systemHealth?.telegramLink,
      tooltip: `Channels: ${systemHealth?.telegramLink?.channelsConnected || 0}`,
    },
    {
      name: 'Marketplace',
      icon: Store,
      data: systemHealth?.marketplace,
      tooltip: `Last Update: ${formatLastActivity(systemHealth?.marketplace?.lastUpdate || '')}`,
    },
    {
      name: 'Notifications',
      icon: Bell,
      data: systemHealth?.notifications,
      tooltip: `Queue: ${systemHealth?.notifications?.queueSize || 0} items`,
    },
  ];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">System Health</CardTitle>
        <Bot className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <TooltipProvider>
            {services.map((service) => (
              <Tooltip key={service.name}>
                <TooltipTrigger asChild>
                  <div className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
                    <div className="flex items-center space-x-2">
                      <service.icon className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium">{service.name}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(service.data?.status || 'offline')}
                      <Badge 
                        variant="secondary" 
                        className={`text-xs ${getStatusColor(service.data?.status || 'offline')}`}
                      >
                        {service.data?.status || 'Offline'}
                      </Badge>
                    </div>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <div className="text-xs">
                    <p>{service.tooltip}</p>
                    <p className="text-muted-foreground">
                      Last: {formatLastActivity(service.data?.lastActivity || '')}
                    </p>
                    {service.data?.message && (
                      <p className="text-yellow-600 mt-1">{service.data.message}</p>
                    )}
                  </div>
                </TooltipContent>
              </Tooltip>
            ))}
          </TooltipProvider>
        </div>
      </CardContent>
    </Card>
  );
}