import { useQuery } from "@tanstack/react-query";
import { useWebSocket } from "@/lib/websocket";

export default function TopHeader() {
  // Get MT5 status
  const { data: mt5Status } = useQuery({
    queryKey: ["/api/mt5-status"],
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // WebSocket connection for real-time updates
  const { isConnected: wsConnected } = useWebSocket();

  const isConnected = mt5Status?.isConnected || false;

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-dark">Trading Dashboard</h1>
          <p className="text-sm text-muted">Monitor your automated trading signals and strategies</p>
        </div>
        
        {/* Status Indicators */}
        <div className="flex items-center space-x-6">
          {/* MT5 Connection Status */}
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-secondary pulse-dot' : 'bg-gray-400'}`}></div>
            <span className={`text-sm font-medium ${isConnected ? 'text-secondary' : 'text-gray-500'}`}>
              {isConnected ? 'MT5 Connected' : 'MT5 Disconnected'}
            </span>
          </div>
          
          {/* Telegram Bot Status */}
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-secondary rounded-full pulse-dot"></div>
            <span className="text-sm font-medium text-secondary">Bot Active</span>
          </div>
          
          {/* WebSocket Sync Status */}
          <div className="flex items-center space-x-2">
            <i className={`fas fa-sync-alt text-primary ${wsConnected ? 'animate-pulse' : ''}`}></i>
            <span className="text-sm text-primary">
              {wsConnected ? 'Connected' : 'Connecting...'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
