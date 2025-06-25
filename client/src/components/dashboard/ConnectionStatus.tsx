import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { 
  Wifi, 
  WifiOff, 
  Database,
  Server,
  CheckCircle,
  AlertCircle,
  XCircle
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function ConnectionStatus() {
  const { data: mt5Status } = useQuery({
    queryKey: ["/api/mt5-status"],
    refetchInterval: 10000,
  });

  const isConnected = mt5Status?.isConnected || false;
  
  return (
    <div className="flex items-center space-x-4">
      {/* MT5 Connection Status */}
      <div className="flex items-center space-x-2">
        {isConnected ? (
          <Wifi className="w-4 h-4 text-emerald-500" />
        ) : (
          <WifiOff className="w-4 h-4 text-red-500" />
        )}
        <span className="text-sm font-medium">MT5</span>
        <Badge variant="outline" className={cn(
          "text-xs",
          isConnected 
            ? "border-emerald-200 text-emerald-700 bg-emerald-50" 
            : "border-red-200 text-red-700 bg-red-50"
        )}>
          {isConnected ? "Connected" : "Offline"}
        </Badge>
      </div>

      {/* Database Status */}
      <div className="flex items-center space-x-2">
        <Database className="w-4 h-4 text-emerald-500" />
        <span className="text-sm font-medium">Database</span>
        <Badge variant="outline" className="text-xs border-emerald-200 text-emerald-700 bg-emerald-50">
          Connected
        </Badge>
      </div>

      {/* API Status */}
      <div className="flex items-center space-x-2">
        <Server className="w-4 h-4 text-emerald-500" />
        <span className="text-sm font-medium">API</span>
        <Badge variant="outline" className="text-xs border-emerald-200 text-emerald-700 bg-emerald-50">
          Active
        </Badge>
      </div>
    </div>
  );
}