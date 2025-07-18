import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  TrendingUp, 
  TrendingDown, 
  Target, 
  Activity, 
  Zap, 
  Clock,
  DollarSign,
  Percent
} from 'lucide-react';
import { TradingMetrics } from '@shared/schema';

interface PerformanceMetricsTilesProps {
  metrics?: TradingMetrics;
  isLoading?: boolean;
}

export function PerformanceMetricsTiles({ metrics, isLoading }: PerformanceMetricsTilesProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="h-4 bg-gray-200 rounded animate-pulse w-20"></div>
              <div className="h-4 w-4 bg-gray-200 rounded animate-pulse"></div>
            </CardHeader>
            <CardContent>
              <div className="h-8 bg-gray-200 rounded animate-pulse w-16 mb-2"></div>
              <div className="h-3 bg-gray-200 rounded animate-pulse w-24"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  const formatLatency = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const tiles = [
    {
      title: "Today's P&L",
      value: formatCurrency(metrics?.todaysPnL || 0),
      icon: DollarSign,
      trend: (metrics?.todaysPnL || 0) >= 0 ? 'up' : 'down',
      color: (metrics?.todaysPnL || 0) >= 0 ? 'text-green-600' : 'text-red-600',
      bgColor: (metrics?.todaysPnL || 0) >= 0 ? 'bg-green-50' : 'bg-red-50',
      description: `${(metrics?.todaysPnL || 0) >= 0 ? '+' : ''}${formatCurrency(metrics?.todaysPnL || 0)}`,
    },
    {
      title: "Win Rate",
      value: formatPercentage(metrics?.winRate || 0),
      icon: Target,
      trend: (metrics?.winRate || 0) >= 60 ? 'up' : (metrics?.winRate || 0) >= 40 ? 'neutral' : 'down',
      color: (metrics?.winRate || 0) >= 60 ? 'text-green-600' : (metrics?.winRate || 0) >= 40 ? 'text-yellow-600' : 'text-red-600',
      bgColor: (metrics?.winRate || 0) >= 60 ? 'bg-green-50' : (metrics?.winRate || 0) >= 40 ? 'bg-yellow-50' : 'bg-red-50',
      description: `${metrics?.tradesExecuted || 0} trades`,
      progress: metrics?.winRate || 0,
    },
    {
      title: "Trades Executed",
      value: (metrics?.tradesExecuted || 0).toString(),
      icon: Activity,
      trend: 'neutral',
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      description: `${metrics?.totalTrades || 0} total`,
    },
    {
      title: "Parsing Success",
      value: formatPercentage(metrics?.parsingSuccessRate || 0),
      icon: Percent,
      trend: (metrics?.parsingSuccessRate || 0) >= 90 ? 'up' : (metrics?.parsingSuccessRate || 0) >= 75 ? 'neutral' : 'down',
      color: (metrics?.parsingSuccessRate || 0) >= 90 ? 'text-green-600' : (metrics?.parsingSuccessRate || 0) >= 75 ? 'text-yellow-600' : 'text-red-600',
      bgColor: (metrics?.parsingSuccessRate || 0) >= 90 ? 'bg-green-50' : (metrics?.parsingSuccessRate || 0) >= 75 ? 'bg-yellow-50' : 'bg-red-50',
      description: 'Signal processing',
      progress: metrics?.parsingSuccessRate || 0,
    },
    {
      title: "Execution Speed",
      value: formatLatency(metrics?.executionSpeed || 0),
      icon: Zap,
      trend: (metrics?.executionSpeed || 0) <= 500 ? 'up' : (metrics?.executionSpeed || 0) <= 1000 ? 'neutral' : 'down',
      color: (metrics?.executionSpeed || 0) <= 500 ? 'text-green-600' : (metrics?.executionSpeed || 0) <= 1000 ? 'text-yellow-600' : 'text-red-600',
      bgColor: (metrics?.executionSpeed || 0) <= 500 ? 'bg-green-50' : (metrics?.executionSpeed || 0) <= 1000 ? 'bg-yellow-50' : 'bg-red-50',
      description: 'Average latency',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      {tiles.map((tile) => (
        <Card key={tile.title} className={`hover:shadow-md transition-shadow ${tile.bgColor}`}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-gray-700">{tile.title}</CardTitle>
            <tile.icon className={`h-4 w-4 ${tile.color}`} />
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className={`text-2xl font-bold ${tile.color}`}>{tile.value}</div>
                {tile.trend === 'up' && <TrendingUp className="h-4 w-4 text-green-600" />}
                {tile.trend === 'down' && <TrendingDown className="h-4 w-4 text-red-600" />}
              </div>
              
              <p className="text-xs text-muted-foreground">{tile.description}</p>
              
              {tile.progress !== undefined && (
                <div className="space-y-1">
                  <Progress value={tile.progress} className="h-2" />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>0%</span>
                    <span>100%</span>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}