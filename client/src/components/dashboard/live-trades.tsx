import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { 
  X, 
  Edit3, 
  TrendingUp, 
  Loader2,
  ArrowUp,
  ArrowDown
} from "lucide-react";

export default function LiveTrades() {
  const { data: trades, isLoading } = useQuery({
    queryKey: ["/api/trades/live"],
    refetchInterval: 3000, // Refresh every 3 seconds for live data
  });

  const { toast } = useToast();
  const queryClient = useQueryClient();

  const closeTradeMediation = useMutation({
    mutationFn: async (tradeId: string) => {
      return apiRequest(`/api/trades/${tradeId}/close`, {
        method: "POST",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/trades/live"] });
      queryClient.invalidateQueries({ queryKey: ["/api/dashboard/stats"] });
      toast({
        title: "Close Trade Command Sent",
        description: "Trade will be closed on MT5",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to Close Trade",
        description: error.message || "Could not send close command",
        variant: "destructive",
      });
    },
  });

  const partialCloseMediation = useMutation({
    mutationFn: async ({ tradeId, percentage }: { tradeId: string; percentage: number }) => {
      return apiRequest(`/api/trades/${tradeId}/partial-close`, {
        method: "POST",
        body: JSON.stringify({ percentage }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/trades/live"] });
      toast({
        title: "Partial Close Command Sent",
        description: "Partial close will be executed on MT5",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to Partial Close",
        description: error.message || "Could not send partial close command",
        variant: "destructive",
      });
    },
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
              const profit = parseFloat(trade.pnl || trade.profit || "0");
              const isProfit = profit > 0;
              const isLoss = profit < 0;
              
              return (
                <div 
                  key={trade.id} 
                  className={`p-4 rounded-lg border transition-all ${
                    isProfit ? 'bg-green-50 border-green-200' :
                    isLoss ? 'bg-red-50 border-red-200' :
                    'bg-gray-50 border-gray-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        trade.action === 'BUY' ? 'bg-green-500' : 'bg-red-500'
                      }`}>
                        {trade.action === 'BUY' ? (
                          <ArrowUp className="w-5 h-5 text-white" />
                        ) : (
                          <ArrowDown className="w-5 h-5 text-white" />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <p className="font-medium text-gray-900">{trade.symbol}</p>
                          <Badge variant={trade.action === 'BUY' ? 'default' : 'destructive'} className="text-xs">
                            {trade.action}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-600">
                          Entry: {trade.entryPrice} • Lot: {trade.lotSize}
                        </p>
                        {trade.stopLoss && (
                          <p className="text-xs text-gray-500">
                            SL: {trade.stopLoss} • TP: {trade.takeProfit || 'N/A'}
                          </p>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-3">
                      <div className="text-right">
                        <p className={`font-semibold ${
                          isProfit ? 'text-green-600' : isLoss ? 'text-red-600' : 'text-gray-600'
                        }`}>
                          {profit >= 0 ? '+' : ''}${profit.toFixed(2)}
                        </p>
                        <p className="text-xs text-gray-500">
                          {trade.status || 'OPEN'}
                        </p>
                      </div>
                      
                      <div className="flex items-center space-x-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => partialCloseMediation.mutate({ 
                            tradeId: trade.id.toString(), 
                            percentage: 50 
                          })}
                          disabled={partialCloseMediation.isPending}
                          className="h-8 px-2"
                        >
                          {partialCloseMediation.isPending ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            "50%"
                          )}
                        </Button>
                        
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-8 px-2"
                        >
                          <Edit3 className="w-3 h-3" />
                        </Button>
                        
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => closeTradeMediation.mutate(trade.id.toString())}
                          disabled={closeTradeMediation.isPending}
                          className="h-8 px-2"
                        >
                          {closeTradeMediation.isPending ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <X className="w-3 h-3" />
                          )}
                        </Button>
                      </div>
                    </div>
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
