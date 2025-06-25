import { useWebSocket } from "@/lib/websocket";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  Wifi, 
  WifiOff, 
  Loader2, 
  AlertCircle, 
  RefreshCw 
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function ConnectionStatus() {
  const { 
    isConnected, 
    connectionState, 
    forceReconnect, 
    reconnectAttempts, 
    maxReconnectAttempts,
    queuedMessages 
  } = useWebSocket();

  const getStatusIcon = () => {
    switch (connectionState) {
      case 'connected':
        return <Wifi className="w-4 h-4" />;
      case 'connecting':
        return <Loader2 className="w-4 h-4 animate-spin" />;
      case 'error':
        return <AlertCircle className="w-4 h-4" />;
      default:
        return <WifiOff className="w-4 h-4" />;
    }
  };

  const getStatusText = () => {
    switch (connectionState) {
      case 'connected':
        return 'Connected';
      case 'connecting':
        return 'Connecting...';
      case 'error':
        return 'Connection Failed';
      default:
        return 'Disconnected';
    }
  };

  const getStatusVariant = () => {
    switch (connectionState) {
      case 'connected':
        return 'default';
      case 'connecting':
        return 'secondary';
      case 'error':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  return (
    <div className="flex items-center space-x-3">
      <Badge variant={getStatusVariant()} className="flex items-center space-x-2">
        {getStatusIcon()}
        <span className="text-xs">{getStatusText()}</span>
      </Badge>
      
      {connectionState === 'error' && (
        <Button 
          variant="outline" 
          size="sm" 
          onClick={forceReconnect}
          className="h-6 px-2"
        >
          <RefreshCw className="w-3 h-3 mr-1" />
          Retry
        </Button>
      )}
      
      {connectionState === 'connecting' && reconnectAttempts > 0 && (
        <span className="text-xs text-muted-foreground">
          Attempt {reconnectAttempts}/{maxReconnectAttempts}
        </span>
      )}
      
      {queuedMessages > 0 && (
        <Badge variant="outline" className="text-xs">
          {queuedMessages} queued
        </Badge>
      )}
    </div>
  );
}