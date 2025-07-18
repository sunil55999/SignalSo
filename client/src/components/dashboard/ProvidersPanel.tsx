import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/hooks/use-toast';
import { 
  Users, 
  MessageCircle, 
  TestTube, 
  Settings, 
  TrendingUp, 
  TrendingDown, 
  Clock, 
  Activity,
  CheckCircle,
  XCircle,
  AlertCircle,
  Play,
  Pause,
  Plus
} from 'lucide-react';
import { Provider } from '@shared/schema';
import { apiRequest } from '@/lib/queryClient';
import { useState } from 'react';

interface ProvidersPanelProps {
  providers?: Provider[];
  isLoading?: boolean;
  onAddProvider?: () => void;
  onEditProvider?: (providerId: string) => void;
}

export function ProvidersPanel({ 
  providers = [], 
  isLoading, 
  onAddProvider, 
  onEditProvider 
}: ProvidersPanelProps) {
  const { toast } = useToast();
  const [loadingActions, setLoadingActions] = useState<Set<string>>(new Set());

  const handleProviderAction = async (providerId: string, action: string) => {
    const actionKey = `${providerId}-${action}`;
    setLoadingActions(prev => new Set(prev).add(actionKey));
    
    try {
      let endpoint = '';
      let method = 'POST';
      let successMessage = '';

      switch (action) {
        case 'test':
          endpoint = `/api/providers/${providerId}/test`;
          successMessage = 'Provider test completed';
          break;
        case 'toggle':
          endpoint = `/api/providers/${providerId}/toggle`;
          successMessage = 'Provider status updated';
          break;
        case 'reconnect':
          endpoint = `/api/providers/${providerId}/reconnect`;
          successMessage = 'Provider reconnected';
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
      setLoadingActions(prev => {
        const newSet = new Set(prev);
        newSet.delete(actionKey);
        return newSet;
      });
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'inactive':
        return <XCircle className="h-4 w-4 text-gray-400" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      case 'testing':
        return <TestTube className="h-4 w-4 text-blue-600" />;
      default:
        return <Activity className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      case 'testing':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'telegram':
        return <MessageCircle className="h-4 w-4 text-blue-600" />;
      case 'api':
        return <Settings className="h-4 w-4 text-purple-600" />;
      case 'file':
        return <Activity className="h-4 w-4 text-orange-600" />;
      case 'manual':
        return <Users className="h-4 w-4 text-gray-600" />;
      default:
        return <Activity className="h-4 w-4 text-gray-600" />;
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
      return 'Never';
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Users className="h-5 w-5" />
              <span>Signal Providers</span>
            </div>
            <Button disabled>
              <Plus className="h-4 w-4 mr-2" />
              Add Provider
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="p-4 border rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <div className="h-8 w-8 bg-gray-200 rounded animate-pulse"></div>
                    <div>
                      <div className="h-4 bg-gray-200 rounded animate-pulse w-24 mb-2"></div>
                      <div className="h-3 bg-gray-200 rounded animate-pulse w-32"></div>
                    </div>
                  </div>
                  <div className="h-6 bg-gray-200 rounded animate-pulse w-16"></div>
                </div>
                <div className="grid grid-cols-4 gap-4 text-sm">
                  {[1, 2, 3, 4].map((j) => (
                    <div key={j} className="h-4 bg-gray-200 rounded animate-pulse"></div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Users className="h-5 w-5" />
            <span>Signal Providers</span>
            <Badge variant="outline">{providers.length}</Badge>
          </div>
          <Button onClick={onAddProvider} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            Add Provider
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {providers.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Users className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No providers configured</p>
              <Button onClick={onAddProvider} variant="outline" size="sm" className="mt-2">
                Add Your First Provider
              </Button>
            </div>
          ) : (
            providers.map((provider) => (
              <div key={provider.id} className="p-4 border rounded-lg hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <div className="flex items-center space-x-2">
                      {getTypeIcon(provider.type)}
                      {getStatusIcon(provider.status)}
                    </div>
                    <div>
                      <h4 className="font-medium">{provider.name}</h4>
                      <p className="text-sm text-muted-foreground">
                        {provider.channelName || provider.type} • {formatLastActivity(provider.lastActivity)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge variant="secondary" className={getStatusColor(provider.status)}>
                      {provider.status}
                    </Badge>
                    {provider.connected && (
                      <Badge variant="outline" className="text-green-600">
                        Connected
                      </Badge>
                    )}
                  </div>
                </div>
                
                {/* Performance Metrics */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm mb-3">
                  <div>
                    <span className="text-muted-foreground">Signals</span>
                    <p className="font-medium">{provider.performance.totalSignals}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Parse Rate</span>
                    <p className="font-medium">{provider.performance.successfulParsing}%</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Win Rate</span>
                    <p className={`font-medium flex items-center ${
                      provider.performance.winRate >= 50 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {provider.performance.winRate >= 50 ? (
                        <TrendingUp className="h-3 w-3 mr-1" />
                      ) : (
                        <TrendingDown className="h-3 w-3 mr-1" />
                      )}
                      {provider.performance.winRate}%
                    </p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Profit</span>
                    <p className={`font-medium ${
                      provider.performance.profit >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      ${provider.performance.profit.toFixed(2)}
                    </p>
                  </div>
                </div>
                
                {/* Progress Bar for Performance */}
                <div className="space-y-2 mb-3">
                  <div className="flex justify-between text-xs">
                    <span>Performance Score</span>
                    <span>{Math.round((provider.performance.winRate + provider.performance.successfulParsing) / 2)}%</span>
                  </div>
                  <Progress 
                    value={(provider.performance.winRate + provider.performance.successfulParsing) / 2} 
                    className="h-2"
                  />
                </div>
                
                {/* Actions */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    <span>Latency: {provider.performance.latency}ms</span>
                    <span>•</span>
                    <span>Trades: {provider.performance.executedTrades}</span>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleProviderAction(provider.id, 'test')}
                      disabled={loadingActions.has(`${provider.id}-test`)}
                    >
                      <TestTube className="h-3 w-3 mr-1" />
                      Test
                    </Button>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleProviderAction(provider.id, 'toggle')}
                      disabled={loadingActions.has(`${provider.id}-toggle`)}
                    >
                      {provider.status === 'active' ? (
                        <Pause className="h-3 w-3 mr-1" />
                      ) : (
                        <Play className="h-3 w-3 mr-1" />
                      )}
                      {provider.status === 'active' ? 'Pause' : 'Start'}
                    </Button>
                    
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onEditProvider?.(provider.id)}
                    >
                      <Settings className="h-3 w-3 mr-1" />
                      Edit
                    </Button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}