import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Shield, 
  AlertTriangle, 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Target,
  Activity,
  AlertCircle,
  CheckCircle,
  XCircle
} from 'lucide-react';
import { RiskExposure, Trade } from '@shared/schema';

interface RiskPanelProps {
  riskExposures?: RiskExposure[];
  openTrades?: Trade[];
  marginLevel?: number;
  totalExposure?: number;
  isLoading?: boolean;
}

export function RiskPanel({ 
  riskExposures = [], 
  openTrades = [], 
  marginLevel = 0, 
  totalExposure = 0, 
  isLoading 
}: RiskPanelProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Shield className="h-5 w-5" />
            <span>Risk Management</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="h-16 bg-gray-200 rounded animate-pulse"></div>
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-12 bg-gray-200 rounded animate-pulse"></div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'low':
        return 'bg-green-100 text-green-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'critical':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getRiskIcon = (level: string) => {
    switch (level) {
      case 'low':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'medium':
        return <AlertCircle className="h-4 w-4 text-yellow-600" />;
      case 'high':
        return <AlertTriangle className="h-4 w-4 text-orange-600" />;
      case 'critical':
        return <XCircle className="h-4 w-4 text-red-600" />;
      default:
        return <Activity className="h-4 w-4 text-gray-600" />;
    }
  };

  const getMarginLevelColor = (level: number) => {
    if (level > 300) return 'text-green-600';
    if (level > 150) return 'text-yellow-600';
    if (level > 100) return 'text-orange-600';
    return 'text-red-600';
  };

  const getMarginLevelStatus = (level: number) => {
    if (level > 300) return 'Healthy';
    if (level > 150) return 'Moderate';
    if (level > 100) return 'Warning';
    return 'Critical';
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const totalUnrealizedPnL = openTrades.reduce((sum, trade) => sum + trade.profit, 0);
  const totalMargin = riskExposures.reduce((sum, exposure) => sum + exposure.margin, 0);
  const overallRiskLevel = riskExposures.some(r => r.riskLevel === 'critical') ? 'critical' :
                          riskExposures.some(r => r.riskLevel === 'high') ? 'high' :
                          riskExposures.some(r => r.riskLevel === 'medium') ? 'medium' : 'low';

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Shield className="h-5 w-5" />
            <span>Risk Management</span>
          </div>
          <div className="flex items-center space-x-2">
            {getRiskIcon(overallRiskLevel)}
            <Badge variant="secondary" className={getRiskLevelColor(overallRiskLevel)}>
              {overallRiskLevel.toUpperCase()}
            </Badge>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Risk Alerts */}
          {overallRiskLevel === 'critical' && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Critical risk detected! Some positions exceed maximum exposure limits.
              </AlertDescription>
            </Alert>
          )}
          
          {marginLevel > 0 && marginLevel <= 150 && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Low margin warning! Current margin level: {marginLevel.toFixed(2)}%
              </AlertDescription>
            </Alert>
          )}

          {/* Overall Risk Summary */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-center space-x-2 mb-1">
                <Target className="h-4 w-4 text-blue-600" />
                <span className="text-sm font-medium">Total Exposure</span>
              </div>
              <p className="text-lg font-bold">{formatCurrency(totalExposure)}</p>
            </div>
            
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-center space-x-2 mb-1">
                <DollarSign className="h-4 w-4 text-green-600" />
                <span className="text-sm font-medium">Unrealized P&L</span>
              </div>
              <p className={`text-lg font-bold ${
                totalUnrealizedPnL >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {formatCurrency(totalUnrealizedPnL)}
              </p>
            </div>
            
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-center space-x-2 mb-1">
                <Activity className="h-4 w-4 text-purple-600" />
                <span className="text-sm font-medium">Open Trades</span>
              </div>
              <p className="text-lg font-bold">{openTrades.length}</p>
            </div>
            
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-center space-x-2 mb-1">
                <Shield className="h-4 w-4 text-orange-600" />
                <span className="text-sm font-medium">Margin Level</span>
              </div>
              <p className={`text-lg font-bold ${getMarginLevelColor(marginLevel)}`}>
                {marginLevel.toFixed(1)}%
              </p>
              <p className="text-xs text-muted-foreground">
                {getMarginLevelStatus(marginLevel)}
              </p>
            </div>
          </div>

          {/* Symbol Exposure Breakdown */}
          <div>
            <h4 className="font-medium mb-3">Symbol Exposure</h4>
            <div className="space-y-3">
              {riskExposures.length === 0 ? (
                <div className="text-center py-4 text-muted-foreground">
                  <Target className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No active positions</p>
                </div>
              ) : (
                riskExposures.map((exposure) => (
                  <div key={exposure.symbol} className="p-3 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <span className="font-medium">{exposure.symbol}</span>
                        <Badge variant="outline" className="text-xs">
                          {exposure.trades} trades
                        </Badge>
                        <Badge variant="secondary" className={`text-xs ${getRiskLevelColor(exposure.riskLevel)}`}>
                          {exposure.riskLevel}
                        </Badge>
                      </div>
                      <div className="flex items-center space-x-2">
                        {exposure.unrealizedPnL >= 0 ? (
                          <TrendingUp className="h-4 w-4 text-green-600" />
                        ) : (
                          <TrendingDown className="h-4 w-4 text-red-600" />
                        )}
                        <span className={`font-medium ${
                          exposure.unrealizedPnL >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {formatCurrency(exposure.unrealizedPnL)}
                        </span>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-4 text-sm mb-2">
                      <div>
                        <span className="text-muted-foreground">Exposure:</span>
                        <p className="font-medium">{formatCurrency(exposure.exposure)}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Margin:</span>
                        <p className="font-medium">{formatCurrency(exposure.margin)}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Providers:</span>
                        <p className="font-medium">{exposure.providers.join(', ')}</p>
                      </div>
                    </div>
                    
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span>Exposure vs Max</span>
                        <span>{((exposure.exposure / exposure.maxExposure) * 100).toFixed(1)}%</span>
                      </div>
                      <Progress 
                        value={(exposure.exposure / exposure.maxExposure) * 100} 
                        className="h-2"
                      />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Risk Warnings */}
          {riskExposures.filter(r => r.riskLevel === 'high' || r.riskLevel === 'critical').length > 0 && (
            <div>
              <h4 className="font-medium mb-3 text-red-600">Risk Warnings</h4>
              <div className="space-y-2">
                {riskExposures
                  .filter(r => r.riskLevel === 'high' || r.riskLevel === 'critical')
                  .map((exposure) => (
                    <div key={exposure.symbol} className="p-2 bg-red-50 border-l-4 border-red-400 rounded">
                      <div className="flex items-center space-x-2">
                        <AlertTriangle className="h-4 w-4 text-red-600" />
                        <span className="font-medium text-red-800">{exposure.symbol}</span>
                        <span className="text-red-600 text-sm">
                          {exposure.riskLevel === 'critical' ? 'Critical exposure' : 'High exposure'}
                        </span>
                      </div>
                      <p className="text-sm text-red-700 mt-1">
                        Exposure: {formatCurrency(exposure.exposure)} / Max: {formatCurrency(exposure.maxExposure)}
                      </p>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}