import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function LiveTrades() {
  const { data: trades, isLoading } = useQuery({
    queryKey: ["/api/trades/active"],
    refetchInterval: 5000, // Refresh every 5 seconds for live data
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Live Trades</CardTitle>
            <Button variant="ghost" size="sm">View All</Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="animate-pulse p-4 bg-gray-100 rounded-lg">
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="border-b border-gray-200">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold text-dark">Live Trades</CardTitle>
          <Button variant="ghost" size="sm" className="text-primary hover:text-primary/80">
            View All
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-6">
        {!trades || trades.length === 0 ? (
          <div className="text-center py-8">
            <i className="fas fa-chart-line text-4xl text-gray-400 mb-4"></i>
            <p className="text-gray-500 font-medium">No Active Trades</p>
            <p className="text-sm text-gray-400">Live trades will appear here when signals are executed</p>
          </div>
        ) : (
          <div className="space-y-4">
            {trades.map((trade) => {
              const profit = parseFloat(trade.profit || "0");
              const isProfit = profit > 0;
              const isLoss = profit < 0;
              
              return (
                <div 
                  key={trade.id} 
                  className={`flex items-center justify-between p-4 rounded-lg border ${
                    isProfit ? 'bg-success-light border-secondary/20' :
                    isLoss ? 'bg-error-light border-accent/20' :
                    'bg-gray-50'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      trade.action === 'BUY' ? 'bg-secondary' : 'bg-accent'
                    }`}>
                      <i className={`fas ${
                        trade.action === 'BUY' ? 'fa-arrow-up' : 'fa-arrow-down'
                      } text-white text-sm`}></i>
                    </div>
                    <div>
                      <p className="font-medium text-dark">{trade.symbol} {trade.action}</p>
                      <p className="text-sm text-muted">Entry: {trade.entryPrice}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`font-medium ${
                      isProfit ? 'text-secondary' : isLoss ? 'text-accent' : 'text-gray-600'
                    }`}>
                      {profit >= 0 ? '+' : ''}${profit.toFixed(2)}
                    </p>
                    <p className="text-sm text-muted">{trade.lotSize} lots</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
