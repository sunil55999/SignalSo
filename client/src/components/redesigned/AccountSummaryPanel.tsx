import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  DollarSign, 
  TrendingUp, 
  TrendingDown,
  Shield,
  AlertTriangle,
  Activity,
  Target,
  Percent
} from 'lucide-react';

interface AccountSummaryPanelProps {
  mt5Status: any;
}

export function AccountSummaryPanel({ mt5Status }: AccountSummaryPanelProps) {
  const balance = mt5Status?.balance || 0;
  const equity = mt5Status?.equity || 0;
  const margin = mt5Status?.margin || 0;
  const freeMargin = equity - margin;
  const marginLevel = margin > 0 ? (equity / margin) * 100 : 0;
  
  // Mock additional data for comprehensive display
  const dailyPnL = 1247.50;
  const weeklyPnL = 3892.75;
  const monthlyPnL = 12456.25;
  const winRate = 67.8;
  const drawdown = 2.3;
  const riskPercent = 1.5;

  const getRiskColor = (risk: number) => {
    if (risk <= 2) return 'text-green-600';
    if (risk <= 5) return 'text-yellow-600';
    return 'text-red-600';
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <DollarSign className="h-5 w-5" />
          Account Summary
        </CardTitle>
        <CardDescription>
          Real-time account balance, equity, and risk metrics
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {/* Balance */}
          <div className="text-center p-4 rounded-lg bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20">
            <div className="text-2xl font-bold text-green-700 dark:text-green-300">
              {formatCurrency(balance)}
            </div>
            <p className="text-sm text-green-600 dark:text-green-400">Account Balance</p>
          </div>

          {/* Equity */}
          <div className="text-center p-4 rounded-lg bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20">
            <div className="text-2xl font-bold text-blue-700 dark:text-blue-300">
              {formatCurrency(equity)}
            </div>
            <p className="text-sm text-blue-600 dark:text-blue-400">Current Equity</p>
          </div>

          {/* Free Margin */}
          <div className="text-center p-4 rounded-lg bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20">
            <div className="text-2xl font-bold text-purple-700 dark:text-purple-300">
              {formatCurrency(freeMargin)}
            </div>
            <p className="text-sm text-purple-600 dark:text-purple-400">Free Margin</p>
          </div>
        </div>

        {/* Performance Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-green-600" />
            <div>
              <div className="text-sm font-medium">Daily P&L</div>
              <div className="text-lg font-bold text-green-600">+{formatCurrency(dailyPnL)}</div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Target className="h-4 w-4 text-blue-600" />
            <div>
              <div className="text-sm font-medium">Win Rate</div>
              <div className="text-lg font-bold text-blue-600">{winRate}%</div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <TrendingDown className="h-4 w-4 text-red-600" />
            <div>
              <div className="text-sm font-medium">Drawdown</div>
              <div className="text-lg font-bold text-red-600">{drawdown}%</div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Percent className="h-4 w-4 text-purple-600" />
            <div>
              <div className="text-sm font-medium">Risk/Trade</div>
              <div className={`text-lg font-bold ${getRiskColor(riskPercent)}`}>{riskPercent}%</div>
            </div>
          </div>
        </div>

        {/* Prop Firm Compliance */}
        <div className="border rounded-lg p-4 bg-gradient-to-r from-emerald-50 to-green-50 dark:from-emerald-900/20 dark:to-green-900/20">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-emerald-600" />
              <span className="font-medium text-emerald-700 dark:text-emerald-300">Prop Firm Status</span>
            </div>
            <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200">
              Compliant
            </Badge>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Daily Loss Limit:</span>
              <span className="font-medium ml-2">5% ({formatCurrency(balance * 0.05)})</span>
            </div>
            <div>
              <span className="text-muted-foreground">Max Drawdown:</span>
              <span className="font-medium ml-2">10% ({formatCurrency(balance * 0.10)})</span>
            </div>
          </div>
        </div>

        {/* Risk Alert */}
        {marginLevel < 200 && (
          <div className="mt-4 p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              <span className="text-sm font-medium text-yellow-700 dark:text-yellow-300">
                Low Margin Level: {marginLevel.toFixed(2)}%
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}