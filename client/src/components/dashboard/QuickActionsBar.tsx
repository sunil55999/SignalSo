import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { 
  Upload, 
  BarChart3, 
  Play, 
  Pause, 
  UserPlus, 
  HelpCircle, 
  Settings,
  Zap,
  Download,
  RefreshCw
} from 'lucide-react';
import { apiRequest } from '@/lib/queryClient';
import { useState } from 'react';

interface QuickActionsBarProps {
  isAutomationRunning?: boolean;
  onImportSignals?: () => void;
  onOpenBacktest?: () => void;
  onOpenProvider?: () => void;
  onOpenSettings?: () => void;
  onOpenHelp?: () => void;
}

export function QuickActionsBar({
  isAutomationRunning = false,
  onImportSignals,
  onOpenBacktest,
  onOpenProvider,
  onOpenSettings,
  onOpenHelp,
}: QuickActionsBarProps) {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState<string | null>(null);

  const handleAction = async (action: string, handler?: () => void) => {
    if (handler) {
      handler();
      return;
    }

    setIsLoading(action);
    try {
      let endpoint = '';
      let method = 'POST';
      let successMessage = '';

      switch (action) {
        case 'automation':
          endpoint = isAutomationRunning ? '/api/automation/pause' : '/api/automation/resume';
          successMessage = isAutomationRunning ? 'Automation paused' : 'Automation resumed';
          break;
        case 'export':
          endpoint = '/api/export/data';
          method = 'GET';
          successMessage = 'Data exported successfully';
          break;
        case 'refresh':
          endpoint = '/api/system/refresh';
          successMessage = 'System refreshed';
          break;
        default:
          throw new Error('Unknown action');
      }

      const response = await apiRequest(endpoint, { method });
      
      if (response.success) {
        toast({
          title: 'Success',
          description: successMessage,
        });
      } else {
        throw new Error(response.message || 'Action failed');
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Action failed',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(null);
    }
  };

  const actions = [
    {
      id: 'import',
      label: 'Import Signals',
      icon: Upload,
      variant: 'default' as const,
      onClick: () => handleAction('import', onImportSignals),
    },
    {
      id: 'backtest',
      label: 'Backtest Strategy',
      icon: BarChart3,
      variant: 'outline' as const,
      onClick: () => handleAction('backtest', onOpenBacktest),
    },
    {
      id: 'automation',
      label: isAutomationRunning ? 'Pause' : 'Resume',
      icon: isAutomationRunning ? Pause : Play,
      variant: isAutomationRunning ? 'destructive' : 'default' as const,
      onClick: () => handleAction('automation'),
    },
    {
      id: 'provider',
      label: 'Add Provider',
      icon: UserPlus,
      variant: 'outline' as const,
      onClick: () => handleAction('provider', onOpenProvider),
    },
    {
      id: 'help',
      label: 'Help',
      icon: HelpCircle,
      variant: 'ghost' as const,
      onClick: () => handleAction('help', onOpenHelp),
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: Settings,
      variant: 'ghost' as const,
      onClick: () => handleAction('settings', onOpenSettings),
    },
  ];

  const secondaryActions = [
    {
      id: 'export',
      label: 'Export Data',
      icon: Download,
      variant: 'ghost' as const,
      onClick: () => handleAction('export'),
    },
    {
      id: 'refresh',
      label: 'Refresh',
      icon: RefreshCw,
      variant: 'ghost' as const,
      onClick: () => handleAction('refresh'),
    },
  ];

  return (
    <Card className="mb-6">
      <CardContent className="p-4">
        <div className="flex flex-col space-y-4">
          {/* System Status */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Zap className="h-5 w-5 text-blue-600" />
              <span className="font-medium">SignalOS Control Center</span>
            </div>
            <div className="flex items-center space-x-2">
              <Badge variant={isAutomationRunning ? 'default' : 'secondary'}>
                {isAutomationRunning ? 'Automation Active' : 'Automation Paused'}
              </Badge>
            </div>
          </div>

          {/* Primary Actions */}
          <div className="flex flex-wrap gap-2">
            {actions.map((action) => (
              <Button
                key={action.id}
                variant={action.variant}
                size="sm"
                onClick={action.onClick}
                disabled={isLoading === action.id}
                className="flex items-center space-x-2"
              >
                <action.icon className="h-4 w-4" />
                <span>{action.label}</span>
                {isLoading === action.id && (
                  <RefreshCw className="h-3 w-3 animate-spin ml-1" />
                )}
              </Button>
            ))}
          </div>

          {/* Secondary Actions */}
          <div className="flex flex-wrap gap-2 pt-2 border-t">
            {secondaryActions.map((action) => (
              <Button
                key={action.id}
                variant={action.variant}
                size="sm"
                onClick={action.onClick}
                disabled={isLoading === action.id}
                className="flex items-center space-x-2"
              >
                <action.icon className="h-4 w-4" />
                <span>{action.label}</span>
                {isLoading === action.id && (
                  <RefreshCw className="h-3 w-3 animate-spin ml-1" />
                )}
              </Button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}