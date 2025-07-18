import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function StrategyBacktest() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Strategy Backtest</h1>
      
      <Card>
        <CardHeader>
          <CardTitle>Backtesting Engine</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Test your trading strategies with historical data.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}