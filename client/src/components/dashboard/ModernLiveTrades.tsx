import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  Clock,
  DollarSign,
  MoreHorizontal,
  X,
  Pause,
  Play
} from "lucide-react";
import { cn } from "@/lib/utils";

interface LiveTrade {
  id: string;
  symbol: string;
  type: "BUY" | "SELL";
  lotSize: number;
  openPrice: number;
  currentPrice: number;
  stopLoss: number;
  takeProfit: number;
  pnl: number;
  openTime: string;
  provider: string;
  status: "running" | "closing" | "paused";
}

export default function ModernLiveTrades() {
  const { data: trades, isLoading } = useQuery({
    queryKey: ["/api/trades/live"],
    refetchInterval: 2000, // Refresh every 2 seconds for live data
  });

  const mockTrades: LiveTrade[] = [
    {
      id: "1",
      symbol: "EURUSD",
      type: "BUY",
      lotSize: 0.1,
      openPrice: 1.0850,
      currentPrice: 1.0867,
      stopLoss: 1.0830,
      takeProfit: 1.0890,
      pnl: 17.0,
      openTime: "2 hours ago",
      provider: "ForexMaster Pro",
      status: "running"
    },
    {
      id: "2", 
      symbol: "GBPJPY",
      type: "SELL",
      lotSize: 0.05,
      openPrice: 191.245,
      currentPrice: 191.180,
      stopLoss: 191.380,
      takeProfit: 191.100,
      pnl: 32.5,
      openTime: "45 minutes ago",
      provider: "TechAnalysis Elite",
      status: "running"
    },
    {
      id: "3",
      symbol: "USDJPY",
      type: "BUY", 
      lotSize: 0.08,
      openPrice: 149.850,
      currentPrice: 149.820,
      stopLoss: 149.780,
      takeProfit: 149.950,
      pnl: -24.0,
      openTime: "1 hour ago",
      provider: "SwingTrade Signals",
      status: "paused"
    }
  ];

  const liveTrades = trades || mockTrades;

  const totalPnL = liveTrades.reduce((sum, trade) => sum + trade.pnl, 0);
  const runningTrades = liveTrades.filter(t => t.status === "running").length;

  if (isLoading) {
    return (
      <Card className="w-full border-0 shadow-lg">
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

  return (
    <Card className="w-full border-0 shadow-lg">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl font-semibold flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-r from-emerald-500 to-teal-600 rounded-lg flex items-center justify-center">
              <Activity className="w-4 h-4 text-white" />
            </div>
            <span>Live Trades</span>
          </CardTitle>
          
          <div className="flex items-center space-x-2">
            <Badge variant="outline" className="text-emerald-700 border-emerald-200 bg-emerald-50">
              {runningTrades} Active
            </Badge>
            <Badge variant="outline" className={cn(
              totalPnL >= 0 
                ? "text-emerald-700 border-emerald-200 bg-emerald-50"
                : "text-red-700 border-red-200 bg-red-50"
            )}>
              {totalPnL >= 0 ? "+" : ""}${totalPnL.toFixed(2)}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {liveTrades.length === 0 ? (
          <div className="text-center py-12">
            <Activity className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500 font-medium">No active trades</p>
            <p className="text-slate-400 text-sm">Trades will appear here when signals are executed</p>
          </div>
        ) : (
          <div className="space-y-4">
            {liveTrades.map((trade) => (
              <Card key={trade.id} className="border border-slate-200 hover:shadow-md transition-shadow">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    {/* Trade Info */}
                    <div className="flex items-center space-x-4">
                      <div className="flex items-center space-x-2">
                        {trade.type === "BUY" ? (
                          <TrendingUp className="w-5 h-5 text-emerald-500" />
                        ) : (
                          <TrendingDown className="w-5 h-5 text-red-500" />
                        )}
                        <div>
                          <div className="font-semibold text-slate-900">{trade.symbol}</div>
                          <div className="text-xs text-slate-500">
                            {trade.type} {trade.lotSize} lots
                          </div>
                        </div>
                      </div>

                      {/* Prices */}
                      <div className="space-y-1">
                        <div className="text-sm">
                          <span className="text-slate-600">Entry:</span>
                          <span className="font-mono ml-1">{trade.openPrice}</span>
                        </div>
                        <div className="text-sm">
                          <span className="text-slate-600">Current:</span>
                          <span className="font-mono ml-1">{trade.currentPrice}</span>
                        </div>
                      </div>

                      {/* SL/TP */}
                      <div className="space-y-1">
                        <div className="text-xs text-slate-600">
                          SL: <span className="font-mono">{trade.stopLoss}</span>
                        </div>
                        <div className="text-xs text-slate-600">
                          TP: <span className="font-mono">{trade.takeProfit}</span>
                        </div>
                      </div>
                    </div>

                    {/* P&L and Controls */}
                    <div className="flex items-center space-x-4">
                      <div className="text-right">
                        <div className={cn(
                          "text-lg font-bold",
                          trade.pnl >= 0 ? "text-emerald-600" : "text-red-600"
                        )}>
                          {trade.pnl >= 0 ? "+" : ""}${trade.pnl.toFixed(2)}
                        </div>
                        <div className="text-xs text-slate-500 flex items-center space-x-1">
                          <Clock className="w-3 h-3" />
                          <span>{trade.openTime}</span>
                        </div>
                      </div>

                      {/* Status & Actions */}
                      <div className="flex items-center space-x-2">
                        <Badge variant="outline" className={cn(
                          trade.status === "running" 
                            ? "text-emerald-700 border-emerald-200 bg-emerald-50"
                            : trade.status === "paused"
                            ? "text-amber-700 border-amber-200 bg-amber-50" 
                            : "text-red-700 border-red-200 bg-red-50"
                        )}>
                          {trade.status.charAt(0).toUpperCase() + trade.status.slice(1)}
                        </Badge>

                        <div className="flex items-center space-x-1">
                          {trade.status === "running" ? (
                            <Button size="sm" variant="ghost" className="h-8 w-8 p-0 text-amber-600 hover:bg-amber-50">
                              <Pause className="w-4 h-4" />
                            </Button>
                          ) : (
                            <Button size="sm" variant="ghost" className="h-8 w-8 p-0 text-emerald-600 hover:bg-emerald-50">
                              <Play className="w-4 h-4" />
                            </Button>
                          )}
                          
                          <Button size="sm" variant="ghost" className="h-8 w-8 p-0 text-red-600 hover:bg-red-50">
                            <X className="w-4 h-4" />
                          </Button>
                          
                          <Button size="sm" variant="ghost" className="h-8 w-8 p-0">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Provider */}
                  <div className="mt-3 pt-3 border-t border-slate-100">
                    <div className="flex items-center justify-between">
                      <div className="text-sm text-slate-600">
                        Provider: <span className="font-medium text-slate-900">{trade.provider}</span>
                      </div>
                      
                      {/* Progress indicator for SL/TP */}
                      <div className="flex items-center space-x-2">
                        <div className="text-xs text-slate-500">Risk/Reward Progress</div>
                        <div className="w-20 h-2 bg-slate-200 rounded-full overflow-hidden">
                          <div 
                            className={cn(
                              "h-full transition-all duration-500",
                              trade.pnl >= 0 ? "bg-emerald-500" : "bg-red-500"
                            )}
                            style={{ 
                              width: `${Math.min(Math.abs(trade.pnl / 50) * 100, 100)}%` 
                            }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}