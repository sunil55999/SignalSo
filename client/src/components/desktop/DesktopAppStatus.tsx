import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  Monitor, 
  Wifi, 
  WifiOff, 
  Activity, 
  AlertCircle,
  CheckCircle,
  RefreshCw
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function DesktopAppStatus() {
  const { data: mt5Status, isLoading, refetch } = useQuery({
    queryKey: ["/api/mt5-status"],
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  if (isLoading) {
    return (
      <Card className="shadow-lg border-0">
        <CardHeader>
          <div className="h-6 bg-slate-200 rounded animate-pulse"></div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="h-4 bg-slate-100 rounded animate-pulse"></div>
            <div className="h-4 bg-slate-100 rounded animate-pulse w-3/4"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const isConnected = mt5Status?.isConnected || false;
  const serverInfo = mt5Status?.serverInfo || {};

  return (
    <Card className="shadow-lg border-0">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center space-x-2">
            <div className={cn(
              "w-8 h-8 rounded-lg flex items-center justify-center",
              isConnected 
                ? "bg-gradient-to-r from-emerald-500 to-green-600" 
                : "bg-gradient-to-r from-red-500 to-orange-600"
            )}>
              <Monitor className="w-4 h-4 text-white" />
            </div>
            <span>Desktop App Status</span>
          </CardTitle>
          
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={() => refetch()}
            className="h-8 w-8"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Connection Status */}
        <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
          <div className="flex items-center space-x-3">
            {isConnected ? (
              <Wifi className="w-5 h-5 text-emerald-600" />
            ) : (
              <WifiOff className="w-5 h-5 text-red-600" />
            )}
            <div>
              <div className="font-medium text-slate-900">MT5 Connection</div>
              <div className="text-sm text-slate-500">
                {isConnected ? "Connected to trading server" : "Disconnected"}
              </div>
            </div>
          </div>
          
          <Badge variant="outline" className={cn(
            isConnected 
              ? "border-emerald-200 text-emerald-700 bg-emerald-50" 
              : "border-red-200 text-red-700 bg-red-50"
          )}>
            {isConnected ? "Online" : "Offline"}
          </Badge>
        </div>

        {/* Server Information */}
        {isConnected && (
          <div className="space-y-3">
            <h4 className="font-medium text-slate-900">Server Information</h4>
            
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-slate-500">Server:</span>
                <div className="font-mono text-slate-900">{serverInfo.server || "Unknown"}</div>
              </div>
              <div>
                <span className="text-slate-500">Account:</span>
                <div className="font-mono text-slate-900">{serverInfo.login || "Unknown"}</div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-slate-500">Balance:</span>
                <div className="font-semibold text-slate-900">
                  ${(serverInfo.balance || 0).toLocaleString()}
                </div>
              </div>
              <div>
                <span className="text-slate-500">Equity:</span>
                <div className="font-semibold text-slate-900">
                  ${(serverInfo.equity || 0).toLocaleString()}
                </div>
              </div>
            </div>

            {serverInfo.marginLevel && (
              <div className="p-3 bg-blue-50 rounded-lg">
                <div className="flex items-center space-x-2 mb-1">
                  <Activity className="w-4 h-4 text-blue-600" />
                  <span className="text-sm font-medium text-blue-900">Margin Level</span>
                </div>
                <div className="text-lg font-bold text-blue-900">
                  {(serverInfo.marginLevel).toFixed(2)}%
                </div>
              </div>
            )}
          </div>
        )}

        {/* Last Update */}
        <div className="pt-3 border-t border-slate-200">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-500">Last Update:</span>
            <span className="text-slate-900">
              {mt5Status?.lastPing 
                ? new Date(mt5Status.lastPing).toLocaleTimeString()
                : "Never"
              }
            </span>
          </div>
        </div>

        {/* Desktop App Integration Status */}
        <div className="space-y-2">
          <h4 className="font-medium text-slate-900">Integration Status</h4>
          
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-4 h-4 text-emerald-500" />
                <span className="text-sm text-slate-700">API Endpoints</span>
              </div>
              <Badge variant="outline" className="border-emerald-200 text-emerald-700 bg-emerald-50">
                Active
              </Badge>
            </div>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-4 h-4 text-emerald-500" />
                <span className="text-sm text-slate-700">Database Connection</span>
              </div>
              <Badge variant="outline" className="border-emerald-200 text-emerald-700 bg-emerald-50">
                Connected
              </Badge>
            </div>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {isConnected ? (
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-amber-500" />
                )}
                <span className="text-sm text-slate-700">Desktop App Sync</span>
              </div>
              <Badge variant="outline" className={cn(
                isConnected 
                  ? "border-emerald-200 text-emerald-700 bg-emerald-50"
                  : "border-amber-200 text-amber-700 bg-amber-50"
              )}>
                {isConnected ? "Synced" : "Pending"}
              </Badge>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}