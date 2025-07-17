import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { apiRequest } from '@/lib/queryClient';
import { 
  Play, 
  Pause, 
  RefreshCw, 
  Settings, 
  FileText, 
  Shield, 
  HelpCircle,
  TestTube,
  History,
  Zap
} from 'lucide-react';

export function QuickActionsPanel() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [isLoading, setIsLoading] = useState<string | null>(null);

  const handleAction = async (action: string, endpoint: string, method: 'GET' | 'POST' = 'POST') => {
    setIsLoading(action);
    try {
      await apiRequest(endpoint, { method });
      toast({
        title: `${action} successful`,
        description: `${action} completed successfully`,
      });
      queryClient.invalidateQueries();
    } catch (error) {
      toast({
        title: `${action} failed`,
        description: `Could not ${action.toLowerCase()}`,
        variant: 'destructive',
      });
    } finally {
      setIsLoading(null);
    }
  };

  const quickActions = [
    {
      id: 'start-router',
      label: 'Start Router',
      icon: <Play className="h-4 w-4" />,
      action: () => handleAction('Start Router', '/api/router/start'),
      variant: 'default' as const,
      description: 'Start signal processing'
    },
    {
      id: 'stop-router',
      label: 'Stop Router',
      icon: <Pause className="h-4 w-4" />,
      action: () => handleAction('Stop Router', '/api/router/stop'),
      variant: 'outline' as const,
      description: 'Stop signal processing'
    },
    {
      id: 'connect-mt5',
      label: 'Connect MT5',
      icon: <RefreshCw className="h-4 w-4" />,
      action: () => handleAction('Connect MT5', '/api/mt5/connect'),
      variant: 'outline' as const,
      description: 'Connect to MT5 platform'
    },
    {
      id: 'test-strategy',
      label: 'Test Strategy',
      icon: <TestTube className="h-4 w-4" />,
      action: () => handleAction('Test Strategy', '/api/strategy/test'),
      variant: 'outline' as const,
      description: 'Run strategy backtest'
    },
    {
      id: 'replay-signal',
      label: 'Replay Signal',
      icon: <History className="h-4 w-4" />,
      action: () => handleAction('Replay Signal', '/api/signal/replay'),
      variant: 'outline' as const,
      description: 'Replay last signal'
    },
    {
      id: 'manual-signal',
      label: 'Manual Signal',
      icon: <Zap className="h-4 w-4" />,
      action: () => handleAction('Manual Signal', '/api/signal/manual'),
      variant: 'outline' as const,
      description: 'Input manual signal'
    }
  ];

  const navigationActions = [
    {
      id: 'logs',
      label: 'View Logs',
      icon: <FileText className="h-4 w-4" />,
      href: '/logs',
      description: 'System logs'
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: <Settings className="h-4 w-4" />,
      href: '/settings',
      description: 'Configuration'
    },
    {
      id: 'license',
      label: 'License',
      icon: <Shield className="h-4 w-4" />,
      href: '/license',
      description: 'License info'
    },
    {
      id: 'help',
      label: 'Help',
      icon: <HelpCircle className="h-4 w-4" />,
      href: '/help',
      description: 'Support & docs'
    }
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Quick Actions</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Primary Actions */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">System Control</h4>
          <div className="grid grid-cols-2 gap-2">
            {quickActions.map((action) => (
              <Button
                key={action.id}
                variant={action.variant}
                size="sm"
                className="h-auto p-3 flex flex-col items-center gap-1"
                onClick={action.action}
                disabled={isLoading === action.id}
              >
                {isLoading === action.id ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  action.icon
                )}
                <span className="text-xs">{action.label}</span>
              </Button>
            ))}
          </div>
        </div>

        {/* Navigation Actions */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Navigation</h4>
          <div className="grid grid-cols-2 gap-2">
            {navigationActions.map((action) => (
              <Button
                key={action.id}
                variant="ghost"
                size="sm"
                className="h-auto p-3 flex flex-col items-center gap-1"
                onClick={() => window.location.href = action.href}
              >
                {action.icon}
                <span className="text-xs">{action.label}</span>
              </Button>
            ))}
          </div>
        </div>

        {/* Emergency Actions */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Emergency</h4>
          <div className="grid grid-cols-1 gap-2">
            <Button
              variant="destructive"
              size="sm"
              className="h-auto p-3 flex items-center gap-2"
              onClick={() => handleAction('Emergency Stop', '/api/emergency/stop')}
            >
              <Pause className="h-4 w-4" />
              <span className="text-xs">Emergency Stop</span>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}