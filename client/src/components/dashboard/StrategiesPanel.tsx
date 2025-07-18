import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/hooks/use-toast';
import { 
  Zap, 
  Play, 
  Pause, 
  Edit, 
  TestTube, 
  TrendingUp, 
  TrendingDown, 
  Target,
  Settings,
  Plus,
  BarChart3,
  Users,
  Shield,
  Activity
} from 'lucide-react';
import { Strategy } from '@shared/schema';
import { apiRequest } from '@/lib/queryClient';
import { useState } from 'react';

interface StrategiesPanelProps {
  strategies?: Strategy[];
  isLoading?: boolean;
  onAddStrategy?: () => void;
  onEditStrategy?: (strategyId: string) => void;
  onBacktestStrategy?: (strategyId: string) => void;
}

export function StrategiesPanel({ 
  strategies = [], 
  isLoading, 
  onAddStrategy, 
  onEditStrategy, 
  onBacktestStrategy 
}: StrategiesPanelProps) {
  const { toast } = useToast();
  const [loadingActions, setLoadingActions] = useState<Set<string>>(new Set());

  const handleStrategyAction = async (strategyId: string, action: string) => {
    const actionKey = `${strategyId}-${action}`;
    setLoadingActions(prev => new Set(prev).add(actionKey));
    
    try {
      let endpoint = '';
      let method = 'POST';
      let successMessage = '';

      switch (action) {
        case 'toggle':
          endpoint = `/api/strategies/${strategyId}/toggle`;
          successMessage = 'Strategy status updated';
          break;
        case 'simulate':
          endpoint = `/api/strategies/${strategyId}/simulate`;
          successMessage = 'Strategy simulation started';
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      case 'testing':
        return 'bg-blue-100 text-blue-800';
      case 'paused':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'signal_copy':
        return <Zap className="h-4 w-4 text-blue-600" />;
      case 'grid':
        return <Activity className="h-4 w-4 text-purple-600" />;
      case 'martingale':
        return <Target className="h-4 w-4 text-red-600" />;
      case 'scalping':
        return <TrendingUp className="h-4 w-4 text-green-600" />;
      case 'swing':
        return <BarChart3 className="h-4 w-4 text-orange-600" />;
      case 'custom':
        return <Settings className="h-4 w-4 text-gray-600" />;
      default:
        return <Activity className="h-4 w-4 text-gray-600" />;
    }
  };

  const formatLastExecuted = (timestamp: string) => {
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
              <Zap className="h-5 w-5" />
              <span>Trading Strategies</span>
            </div>
            <Button disabled>
              <Plus className="h-4 w-4 mr-2" />
              Add Strategy
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
                      <div className="h-4 bg-gray-200 rounded animate-pulse w-32 mb-2"></div>
                      <div className="h-3 bg-gray-200 rounded animate-pulse w-24"></div>
                    </div>
                  </div>
                  <div className="h-6 bg-gray-200 rounded animate-pulse w-16"></div>
                </div>
                <div className="grid grid-cols-4 gap-4">
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
            <Zap className="h-5 w-5" />
            <span>Trading Strategies</span>
            <Badge variant="outline">{strategies.length}</Badge>
          </div>
          <Button onClick={onAddStrategy} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            Add Strategy
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {strategies.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Zap className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No strategies configured</p>
              <Button onClick={onAddStrategy} variant="outline" size="sm" className="mt-2">
                Create Your First Strategy
              </Button>
            </div>
          ) : (
            strategies.map((strategy) => (
              <div key={strategy.id} className="p-4 border rounded-lg hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    {getTypeIcon(strategy.type)}
                    <div>
                      <h4 className="font-medium">{strategy.name}</h4>
                      <p className="text-sm text-muted-foreground">{strategy.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge variant="secondary" className={getStatusColor(strategy.status)}>
                      {strategy.status}
                    </Badge>
                    <Badge variant="outline" className="text-blue-600">
                      {strategy.type.replace('_', ' ')}
                    </Badge>
                  </div>
                </div>
                
                {/* Strategy Rules Summary */}
                <div className="mb-3">
                  <div className="flex items-center space-x-2 mb-2">
                    <Settings className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">Rules: {strategy.rules.length}</span>
                    <Users className="h-4 w-4 text-muted-foreground ml-4" />
                    <span className="text-sm font-medium">Providers: {strategy.providers.length}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {strategy.rules.slice(0, 2).map((rule, index) => (
                      <span key={rule.id}>
                        {rule.condition} → {rule.action}
                        {index < Math.min(strategy.rules.length - 1, 1) && ' • '}
                      </span>
                    ))}
                    {strategy.rules.length > 2 && ' • +' + (strategy.rules.length - 2) + ' more'}
                  </div>
                </div>
                
                {/* Performance Metrics */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm mb-3">
                  <div>
                    <span className="text-muted-foreground">Total Trades</span>
                    <p className="font-medium">{strategy.performance.totalTrades}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Win Rate</span>
                    <p className={`font-medium flex items-center ${
                      strategy.performance.winRate >= 50 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {strategy.performance.winRate >= 50 ? (
                        <TrendingUp className="h-3 w-3 mr-1" />
                      ) : (
                        <TrendingDown className="h-3 w-3 mr-1" />
                      )}
                      {strategy.performance.winRate}%
                    </p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Profit</span>
                    <p className={`font-medium ${
                      strategy.performance.profit >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      ${strategy.performance.profit.toFixed(2)}
                    </p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Drawdown</span>
                    <p className="font-medium text-red-600">
                      {strategy.performance.drawdown.toFixed(2)}%
                    </p>
                  </div>
                </div>
                
                {/* Risk Management */}
                <div className="mb-3 p-3 bg-gray-50 rounded">
                  <div className="flex items-center space-x-2 mb-2">
                    <Shield className="h-4 w-4 text-blue-600" />
                    <span className="text-sm font-medium">Risk Management</span>
                  </div>
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 text-xs">
                    <div>
                      <span className="text-muted-foreground">Max Lot:</span>
                      <span className="ml-1 font-medium">{strategy.riskManagement.maxLotSize}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Risk/Trade:</span>
                      <span className="ml-1 font-medium">{strategy.riskManagement.maxRiskPerTrade}%</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Daily Loss:</span>
                      <span className="ml-1 font-medium">{strategy.riskManagement.maxDailyLoss}%</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">SL Points:</span>
                      <span className="ml-1 font-medium">{strategy.riskManagement.stopLossPoints}</span>
                    </div>
                  </div>
                </div>
                
                {/* Progress Bar for Win Rate */}
                <div className="space-y-2 mb-3">
                  <div className="flex justify-between text-xs">
                    <span>Win Rate Performance</span>
                    <span>{strategy.performance.winRate}%</span>
                  </div>
                  <Progress value={strategy.performance.winRate} className="h-2" />
                </div>
                
                {/* Actions */}
                <div className="flex items-center justify-between">
                  <div className="text-xs text-muted-foreground">
                    Last executed: {formatLastExecuted(strategy.performance.lastExecuted)}
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleStrategyAction(strategy.id, 'simulate')}
                      disabled={loadingActions.has(`${strategy.id}-simulate`)}
                    >
                      <TestTube className="h-3 w-3 mr-1" />
                      Simulate
                    </Button>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onBacktestStrategy?.(strategy.id)}
                    >
                      <BarChart3 className="h-3 w-3 mr-1" />
                      Backtest
                    </Button>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleStrategyAction(strategy.id, 'toggle')}
                      disabled={loadingActions.has(`${strategy.id}-toggle`)}
                    >
                      {strategy.status === 'active' ? (
                        <Pause className="h-3 w-3 mr-1" />
                      ) : (
                        <Play className="h-3 w-3 mr-1" />
                      )}
                      {strategy.status === 'active' ? 'Pause' : 'Start'}
                    </Button>
                    
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onEditStrategy?.(strategy.id)}
                    >
                      <Edit className="h-3 w-3 mr-1" />
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