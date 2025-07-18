import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  TrendingUp, 
  TrendingDown, 
  Target, 
  Clock, 
  Zap,
  DollarSign,
  BarChart3,
  Shield
} from 'lucide-react';

interface TradingMetric {
  title: string;
  value: string | number;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon: React.ReactNode;
  description: string;
}

export function TradingMetrics() {
  const { data: routerStatus } = useQuery({
    queryKey: ['/api/router/status'],
    refetchInterval: 2000,
  });

  const { data: mt5Status } = useQuery({
    queryKey: ['/api/mt5/status'],
    refetchInterval: 2000,
  });

  const { data: logs } = useQuery({
    queryKey: ['/api/logs'],
    refetchInterval: 5000,
  });

  // Mock data for demo - in production these would come from your APIs
  const todayMetrics: TradingMetric[] = [
    {
      title: 'Signals Processed',
      value: 23,
      change: '+12%',
      changeType: 'positive',
      icon: <Zap className="h-4 w-4" />,
      description: 'Total signals processed today'
    },
    {
      title: 'Win Rate',
      value: '78%',
      change: '+5%',
      changeType: 'positive',
      icon: <Target className="h-4 w-4" />,
      description: 'Today\'s success rate'
    },
    {
      title: 'Avg Execution Speed',
      value: '1.2s',
      change: '-0.3s',
      changeType: 'positive',
      icon: <Clock className="h-4 w-4" />,
      description: 'Average signal to execution time'
    },
    {
      title: 'Parser Confidence',
      value: '95%',
      change: '+2%',
      changeType: 'positive',
      icon: <BarChart3 className="h-4 w-4" />,
      description: 'AI parsing confidence level'
    },
    {
      title: 'Daily PnL',
      value: '+$1,247',
      change: '+$247',
      changeType: 'positive',
      icon: <DollarSign className="h-4 w-4" />,
      description: 'Today\'s profit/loss'
    },
    {
      title: 'Risk Usage',
      value: '45%',
      change: '+5%',
      changeType: 'neutral',
      icon: <Shield className="h-4 w-4" />,
      description: 'Current risk exposure'
    }
  ];

  const getChangeIcon = (changeType: 'positive' | 'negative' | 'neutral') => {
    switch (changeType) {
      case 'positive':
        return <TrendingUp className="h-3 w-3 text-green-500" />;
      case 'negative':
        return <TrendingDown className="h-3 w-3 text-red-500" />;
      default:
        return null;
    }
  };

  const getChangeColor = (changeType: 'positive' | 'negative' | 'neutral') => {
    switch (changeType) {
      case 'positive':
        return 'text-green-600';
      case 'negative':
        return 'text-red-600';
      default:
        return 'text-muted-foreground';
    }
  };

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {todayMetrics.map((metric) => (
        <Card key={metric.title} className="hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{metric.title}</CardTitle>
            <div className="text-muted-foreground">{metric.icon}</div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metric.value}</div>
            <div className="flex items-center gap-1 mt-1">
              {metric.change && (
                <>
                  {getChangeIcon(metric.changeType!)}
                  <span className={`text-xs ${getChangeColor(metric.changeType!)}`}>
                    {metric.change}
                  </span>
                </>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-1">{metric.description}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}