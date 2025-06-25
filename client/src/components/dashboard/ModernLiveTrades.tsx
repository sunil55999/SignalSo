import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  TrendingUp, 
  TrendingDown, 
  Clock,
  MoreHorizontal,
  X,
  Edit
} from "lucide-react";
import { cn } from "@/lib/utils";

interface LiveTrade {
  id: string;
  symbol: string;
  type: "BUY" | "SELL";
  lotSize: number;
  openPrice: number;
  currentPrice: number;
  pnl: number;
  stopLoss: number;
  takeProfit: number;
  openTime: string;
  status: string;
}

export default function ModernLiveTrades() {
  const { data: trades, isLoading } = useQuery({
    queryKey: ["/api/trades/live"],
    refetchInterval: 3000, // Refresh every 3 seconds
  });

  const handleCloseTrade = (tradeId: string) => {
    console.log("Close trade:", tradeId);
  };

  const handleModifyTrade = (tradeId: string) => {
    console.log("Modify trade:", tradeId);
  };

  if (isLoading) {
    return (
      <Card className="shadow-lg border-0">
        <CardHeader>
          <div className="h-6 bg-slate-200 rounded animate-pulse"></div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-20 bg-slate-100 rounded animate-pulse"></div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const liveTradesData: LiveTrade[] = trades || [];

  return (
    <Card className="shadow-lg border-0">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-r from-emerald-500 to-blue-600 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-white" />
            </div>
            <span>Live Trades</span>
          </CardTitle>
          
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
            <span className="text-sm text-slate-600">{liveTradesData.length} Active</span>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {liveTradesData.length === 0 ? (
          <div className="text-center py-8">
            <TrendingUp className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500 font-medium">No active trades</p>
            <p className="text-slate-400 text-sm">Your live trades will appear here</p>
          </div>
        ) : (
          <div className="space-y-4">
            {liveTradesData.map((trade) => {
              const isProfit = trade.pnl >= 0;
              const Icon = trade.type === "BUY" ? TrendingUp : TrendingDown;
              
              return (
                <div
                  key={trade.id}
                  className="bg-slate-50 rounded-xl p-4 hover:bg-slate-100 transition-colors"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <div className={cn(
                        "w-10 h-10 rounded-lg flex items-center justify-center",
                        trade.type === "BUY" 
                          ? "bg-emerald-100 text-emerald-600" 
                          : "bg-red-100 text-red-600"
                      )}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-slate-900">{trade.symbol}</span>
                          <Badge variant="outline" className={cn(
                            "text-xs",
                            trade.type === "BUY" 
                              ? "border-emerald-200 text-emerald-700" 
                              : "border-red-200 text-red-700"
                          )}>
                            {trade.type}
                          </Badge>
                        </div>
                        <div className="text-sm text-slate-500">
                          {trade.lotSize} lots • Opened {new Date(trade.openTime).toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <div className={cn(
                        "text-lg font-bold",
                        isProfit ? "text-emerald-600" : "text-red-600"
                      )}>
                        {isProfit ? "+" : ""}${trade.pnl.toFixed(2)}
                      </div>
                      <div className="text-sm text-slate-500">
                        {trade.currentPrice.toFixed(5)}
                      </div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 mb-3 text-sm">
                    <div>
                      <span className="text-slate-500">Open:</span>
                      <span className="ml-2 font-mono">{trade.openPrice.toFixed(5)}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">SL:</span>
                      <span className="ml-2 font-mono">{trade.stopLoss.toFixed(5)}</span>
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div className="text-sm">
                      <span className="text-slate-500">TP:</span>
                      <span className="ml-2 font-mono">{trade.takeProfit.toFixed(5)}</span>
                    </div>
                    
                    <div className="flex items-center space-x-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-8 w-8 p-0"
                        onClick={() => handleModifyTrade(trade.id)}
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-8 w-8 p-0 text-red-600 hover:text-red-700"
                        onClick={() => handleCloseTrade(trade.id)}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-8 w-8 p-0"
                      >
                        <MoreHorizontal className="w-4 h-4" />
                      </Button>
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