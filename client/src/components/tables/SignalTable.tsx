import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { 
  Search, 
  Filter, 
  TrendingUp, 
  TrendingDown, 
  Clock, 
  CheckCircle, 
  XCircle,
  Copy,
  MoreHorizontal
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Signal {
  id: string;
  symbol: string;
  type: "BUY" | "SELL";
  entry: number;
  stopLoss: number;
  takeProfit: number[];
  provider: string;
  confidence: number;
  status: "pending" | "executed" | "failed" | "cancelled";
  timestamp: string;
  pnl?: number;
}

export default function SignalTable() {
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");

  const { data: signals, isLoading } = useQuery({
    queryKey: ["/api/signals"],
    refetchInterval: 5000,
  });

  const filteredSignals = (signals || []).filter((signal: Signal) => {
    const matchesSearch = signal.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         signal.provider.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterStatus === "all" || signal.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "executed": return <CheckCircle className="w-4 h-4 text-emerald-500" />;
      case "failed": return <XCircle className="w-4 h-4 text-red-500" />;
      case "pending": return <Clock className="w-4 h-4 text-amber-500" />;
      default: return <XCircle className="w-4 h-4 text-slate-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      executed: "bg-emerald-100 text-emerald-700 border-emerald-200",
      failed: "bg-red-100 text-red-700 border-red-200",
      pending: "bg-amber-100 text-amber-700 border-amber-200",
      cancelled: "bg-slate-100 text-slate-700 border-slate-200"
    };
    
    return (
      <Badge variant="outline" className={cn("text-xs", variants[status as keyof typeof variants])}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    );
  };

  if (isLoading) {
    return (
      <Card className="w-full">
        <CardHeader>
          <div className="h-6 bg-slate-200 rounded animate-pulse"></div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-slate-100 rounded animate-pulse"></div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full shadow-lg border-0">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl font-semibold flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-white" />
            </div>
            <span>Live Signals</span>
          </CardTitle>
          
          <div className="flex items-center space-x-2">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
              <Input
                placeholder="Search signals..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 w-64"
              />
            </div>
            
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="executed">Executed</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-3 px-4 font-medium text-slate-600">Signal</th>
                <th className="text-left py-3 px-4 font-medium text-slate-600">Type</th>
                <th className="text-left py-3 px-4 font-medium text-slate-600">Entry</th>
                <th className="text-left py-3 px-4 font-medium text-slate-600">SL/TP</th>
                <th className="text-left py-3 px-4 font-medium text-slate-600">Provider</th>
                <th className="text-left py-3 px-4 font-medium text-slate-600">Confidence</th>
                <th className="text-left py-3 px-4 font-medium text-slate-600">Status</th>
                <th className="text-left py-3 px-4 font-medium text-slate-600">P&L</th>
                <th className="text-right py-3 px-4 font-medium text-slate-600">Actions</th>
              </tr>
            </thead>
            
            <tbody>
              {filteredSignals.map((signal: Signal) => (
                <tr key={signal.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                  <td className="py-4 px-4">
                    <div className="flex items-center space-x-2">
                      <div className="font-semibold text-slate-900">{signal.symbol}</div>
                      <div className="text-xs text-slate-500">
                        {new Date(signal.timestamp).toLocaleDateString()}
                      </div>
                    </div>
                  </td>
                  
                  <td className="py-4 px-4">
                    <div className="flex items-center space-x-1">
                      {signal.type === "BUY" ? (
                        <TrendingUp className="w-4 h-4 text-emerald-500" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-red-500" />
                      )}
                      <span className={cn(
                        "font-medium text-sm",
                        signal.type === "BUY" ? "text-emerald-600" : "text-red-600"
                      )}>
                        {signal.type}
                      </span>
                    </div>
                  </td>
                  
                  <td className="py-4 px-4">
                    <span className="font-mono text-sm">{signal.entry}</span>
                  </td>
                  
                  <td className="py-4 px-4">
                    <div className="text-xs space-y-1">
                      <div>SL: <span className="font-mono">{signal.stopLoss}</span></div>
                      <div>TP: <span className="font-mono">{signal.takeProfit[0]}</span></div>
                    </div>
                  </td>
                  
                  <td className="py-4 px-4">
                    <div className="text-sm font-medium text-slate-700">{signal.provider}</div>
                  </td>
                  
                  <td className="py-4 px-4">
                    <div className="flex items-center space-x-2">
                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        signal.confidence >= 80 ? "bg-emerald-500" :
                        signal.confidence >= 60 ? "bg-amber-500" : "bg-red-500"
                      )}></div>
                      <span className="text-sm font-medium">{signal.confidence}%</span>
                    </div>
                  </td>
                  
                  <td className="py-4 px-4">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(signal.status)}
                      {getStatusBadge(signal.status)}
                    </div>
                  </td>
                  
                  <td className="py-4 px-4">
                    {signal.pnl !== undefined ? (
                      <span className={cn(
                        "font-mono text-sm font-medium",
                        signal.pnl >= 0 ? "text-emerald-600" : "text-red-600"
                      )}>
                        {signal.pnl >= 0 ? "+" : ""}${signal.pnl.toFixed(2)}
                      </span>
                    ) : (
                      <span className="text-slate-400 text-sm">-</span>
                    )}
                  </td>
                  
                  <td className="py-4 px-4 text-right">
                    <div className="flex items-center justify-end space-x-1">
                      <Button size="sm" variant="ghost" className="h-8 w-8 p-0">
                        <Copy className="w-4 h-4" />
                      </Button>
                      <Button size="sm" variant="ghost" className="h-8 w-8 p-0">
                        <MoreHorizontal className="w-4 h-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {filteredSignals.length === 0 && (
            <div className="text-center py-12">
              <TrendingUp className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500 font-medium">No signals found</p>
              <p className="text-slate-400 text-sm">Try adjusting your search or filter criteria</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}