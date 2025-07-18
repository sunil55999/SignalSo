import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { apiRequest } from '@/lib/queryClient';
import { 
  Play, 
  Pause, 
  Upload, 
  Download, 
  TestTube,
  RefreshCw,
  Settings,
  Zap,
  Link as LinkIcon,
  Activity,
  CheckCircle
} from 'lucide-react';

export function QuickActionsPanel() {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState<string | null>(null);

  const handleAction = async (actionType: string, endpoint: string, method: 'GET' | 'POST' = 'POST') => {
    setIsLoading(actionType);
    try {
      const response = await apiRequest(endpoint, { method });
      if (response.success !== false) {
        toast({
          title: 'Success',
          description: `${actionType} completed successfully`,
        });
      } else {
        throw new Error(response.message || 'Operation failed');
      }
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || `Failed to ${actionType.toLowerCase()}`,
        variant: 'destructive',
      });
    } finally {
      setIsLoading(null);
    }
  };

  const quickActions = [
    {
      id: 'start-router',
      title: 'Start Router',
      description: 'Begin signal processing',
      icon: <Play className="h-4 w-4" />,
      color: 'bg-green-500 hover:bg-green-600',
      endpoint: '/api/router/start'
    },
    {
      id: 'pause-router',
      title: 'Pause Router',
      description: 'Temporarily stop processing',
      icon: <Pause className="h-4 w-4" />,
      color: 'bg-yellow-500 hover:bg-yellow-600',
      endpoint: '/api/router/stop'
    },
    {
      id: 'connect-mt5',
      title: 'Connect MT5',
      description: 'Establish trading connection',
      icon: <LinkIcon className="h-4 w-4" />,
      color: 'bg-blue-500 hover:bg-blue-600',
      endpoint: '/api/mt5/connect'
    },
    {
      id: 'connect-telegram',
      title: 'Connect Telegram',
      description: 'Authenticate with Telegram',
      icon: <RefreshCw className="h-4 w-4" />,
      color: 'bg-purple-500 hover:bg-purple-600',
      endpoint: '/api/telegram/login'
    }
  ];

  const utilityActions = [
    {
      id: 'import-data',
      title: 'Import Signals',
      description: 'Upload signal data',
      icon: <Upload className="h-4 w-4" />,
      variant: 'outline' as const
    },
    {
      id: 'export-data',
      title: 'Export Data',
      description: 'Download reports',
      icon: <Download className="h-4 w-4" />,
      variant: 'outline' as const
    },
    {
      id: 'test-signal',
      title: 'Test Signal',
      description: 'Parse test signal',
      icon: <TestTube className="h-4 w-4" />,
      variant: 'outline' as const
    },
    {
      id: 'system-settings',
      title: 'Settings',
      description: 'Configure system',
      icon: <Settings className="h-4 w-4" />,
      variant: 'outline' as const
    }
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="h-5 w-5" />
          Quick Actions
        </CardTitle>
        <CardDescription>
          System control and navigation shortcuts
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Primary Actions */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-muted-foreground">System Control</h3>
          {quickActions.map((action) => (
            <Button
              key={action.id}
              className={`w-full justify-start text-white ${action.color}`}
              onClick={() => handleAction(action.title, action.endpoint)}
              disabled={isLoading === action.title}
            >
              {isLoading === action.title ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <span className="mr-2">{action.icon}</span>
              )}
              <div className="text-left">
                <div className="font-medium">{action.title}</div>
                <div className="text-xs opacity-90">{action.description}</div>
              </div>
            </Button>
          ))}
        </div>

        {/* Utility Actions */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-muted-foreground">Tools & Utilities</h3>
          <div className="grid grid-cols-2 gap-2">
            {utilityActions.map((action) => (
              <Button
                key={action.id}
                variant={action.variant}
                size="sm"
                className="flex flex-col items-center gap-1 h-auto py-3"
              >
                {action.icon}
                <span className="text-xs">{action.title}</span>
              </Button>
            ))}
          </div>
        </div>

        {/* Status Indicators */}
        <div className="pt-2 border-t">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">Quick Status</h3>
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span>Router Status</span>
              <Badge variant="outline" className="text-green-600">
                <CheckCircle className="h-3 w-3 mr-1" />
                Running
              </Badge>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span>MT5 Connection</span>
              <Badge variant="outline" className="text-green-600">
                <CheckCircle className="h-3 w-3 mr-1" />
                Connected
              </Badge>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span>Telegram Auth</span>
              <Badge variant="outline" className="text-green-600">
                <CheckCircle className="h-3 w-3 mr-1" />
                Active
              </Badge>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}