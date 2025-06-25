import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  TrendingUp, 
  TrendingDown, 
  Users, 
  Activity, 
  Clock,
  Star,
  MoreHorizontal
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ProviderStats {
  id: string;
  name: string;
  avatar?: string;
  status: "active" | "inactive" | "warning";
  totalSignals: number;
  winRate: number;
  avgPips: number;
  profitFactor: number;
  subscribers: number;
  trustScore: number;
  lastSignal: string;
  monthlyPnL: number;
}

interface ProviderStatsCardProps {
  provider: ProviderStats;
  onViewDetails?: (id: string) => void;
  onToggleStatus?: (id: string) => void;
}

export default function ProviderStatsCard({ 
  provider, 
  onViewDetails, 
  onToggleStatus 
}: ProviderStatsCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "active": return "bg-emerald-100 text-emerald-700 border-emerald-200";
      case "inactive": return "bg-slate-100 text-slate-700 border-slate-200";
      case "warning": return "bg-amber-100 text-amber-700 border-amber-200";
      default: return "bg-slate-100 text-slate-700 border-slate-200";
    }
  };

  const getTrustScoreColor = (score: number) => {
    if (score >= 80) return "text-emerald-600";
    if (score >= 60) return "text-amber-600";
    return "text-red-600";
  };

  return (
    <Card className="hover:shadow-lg transition-all duration-300 border-0 shadow-md">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold text-lg">
              {provider.avatar || provider.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <CardTitle className="text-lg font-semibold">{provider.name}</CardTitle>
              <div className="flex items-center space-x-2 mt-1">
                <Badge variant="outline" className={getStatusColor(provider.status)}>
                  {provider.status.charAt(0).toUpperCase() + provider.status.slice(1)}
                </Badge>
                <div className="flex items-center space-x-1">
                  <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                  <span className={cn("text-sm font-medium", getTrustScoreColor(provider.trustScore))}>
                    {provider.trustScore}/100
                  </span>
                </div>
              </div>
            </div>
          </div>
          
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <MoreHorizontal className="w-4 h-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Performance Metrics */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-1">
              <Activity className="w-4 h-4 text-slate-500" />
              <span className="text-sm text-slate-600">Win Rate</span>
            </div>
            <div className="flex items-center space-x-1">
              <span className="text-xl font-bold text-slate-900">{provider.winRate}%</span>
              {provider.winRate >= 70 ? (
                <TrendingUp className="w-4 h-4 text-emerald-500" />
              ) : (
                <TrendingDown className="w-4 h-4 text-red-500" />
              )}
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex items-center space-x-1">
              <Users className="w-4 h-4 text-slate-500" />
              <span className="text-sm text-slate-600">Subscribers</span>
            </div>
            <div className="text-xl font-bold text-slate-900">
              {provider.subscribers.toLocaleString()}
            </div>
          </div>
        </div>

        {/* Additional Stats */}
        <div className="grid grid-cols-3 gap-3 pt-3 border-t border-slate-200">
          <div className="text-center">
            <div className="text-sm text-slate-600 mb-1">Signals</div>
            <div className="font-semibold text-slate-900">{provider.totalSignals}</div>
          </div>
          
          <div className="text-center">
            <div className="text-sm text-slate-600 mb-1">Avg Pips</div>
            <div className="font-semibold text-slate-900">+{provider.avgPips}</div>
          </div>
          
          <div className="text-center">
            <div className="text-sm text-slate-600 mb-1">P.Factor</div>
            <div className="font-semibold text-slate-900">{provider.profitFactor}</div>
          </div>
        </div>

        {/* Monthly P&L */}
        <div className="bg-slate-50 rounded-lg p-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-600">Monthly P&L</span>
            <div className="flex items-center space-x-1">
              <span className={cn(
                "font-bold",
                provider.monthlyPnL >= 0 ? "text-emerald-600" : "text-red-600"
              )}>
                {provider.monthlyPnL >= 0 ? "+" : ""}${provider.monthlyPnL.toFixed(0)}
              </span>
              {provider.monthlyPnL >= 0 ? (
                <TrendingUp className="w-4 h-4 text-emerald-500" />
              ) : (
                <TrendingDown className="w-4 h-4 text-red-500" />
              )}
            </div>
          </div>
        </div>

        {/* Last Signal */}
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center space-x-1 text-slate-600">
            <Clock className="w-4 h-4" />
            <span>Last signal:</span>
          </div>
          <span className="font-medium text-slate-900">{provider.lastSignal}</span>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-2 pt-2">
          <Button 
            variant="outline" 
            size="sm" 
            className="flex-1"
            onClick={() => onViewDetails?.(provider.id)}
          >
            View Details
          </Button>
          <Button 
            variant={provider.status === "active" ? "destructive" : "default"}
            size="sm" 
            className="flex-1"
            onClick={() => onToggleStatus?.(provider.id)}
          >
            {provider.status === "active" ? "Pause" : "Activate"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}