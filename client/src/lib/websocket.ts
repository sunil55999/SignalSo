import { useEffect, useState, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";

interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
  id?: string;
}

type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error';

export function useWebSocket() {
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const heartbeatIntervalRef = useRef<NodeJS.Timeout>();
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 10;
  const messageQueueRef = useRef<WebSocketMessage[]>([]);
  const acknowledgedMessagesRef = useRef<Set<string>>(new Set());

  const getReconnectDelay = useCallback(() => {
    // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (max)
    const baseDelay = 1000;
    const attempt = reconnectAttemptsRef.current;
    return Math.min(baseDelay * Math.pow(2, attempt), 30000);
  }, []);

  const startHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
    }
    
    heartbeatIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        sendMessage('ping', { timestamp: Date.now() });
      }
    }, 30000); // Send ping every 30 seconds
  }, []);

  const stopHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = undefined;
    }
  }, []);

  const processMessageQueue = useCallback(() => {
    while (messageQueueRef.current.length > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
      const message = messageQueueRef.current.shift();
      if (message) {
        wsRef.current.send(JSON.stringify(message));
      }
    }
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.CONNECTING) {
      return; // Already connecting
    }

    setConnectionState('connecting');
    
    try {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/ws`;
      
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setConnectionState('connected');
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        startHeartbeat();
        processMessageQueue();
        
        console.log("WebSocket connected");
        toast({
          title: "Connection Restored",
          description: "Real-time updates are now active",
          duration: 3000,
        });
      };

      wsRef.current.onclose = (event) => {
        setConnectionState('disconnected');
        setIsConnected(false);
        stopHeartbeat();
        
        console.log("WebSocket disconnected:", event.code, event.reason);
        
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = getReconnectDelay();
          reconnectAttemptsRef.current++;
          
          console.log(`Attempting reconnect ${reconnectAttemptsRef.current}/${maxReconnectAttempts} in ${delay}ms`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          setConnectionState('error');
          toast({
            title: "Connection Failed",
            description: "Unable to establish real-time connection. Please refresh the page.",
            variant: "destructive",
          });
        }
      };

      wsRef.current.onerror = (error) => {
        console.error("WebSocket error:", error);
        setConnectionState('error');
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          
          // Handle heartbeat
          if (message.type === 'pong') {
            return; // Just acknowledge the pong
          }
          
          // Send acknowledgment for messages with ID
          if (message.id && wsRef.current?.readyState === WebSocket.OPEN) {
            sendMessage('ack', { messageId: message.id });
          }
          
          handleMessage(message);
        } catch (error) {
          console.error("Failed to parse WebSocket message:", error);
        }
      };
    } catch (error) {
      console.error("Failed to connect WebSocket:", error);
      setConnectionState('error');
    }
  }, [getReconnectDelay, startHeartbeat, stopHeartbeat, processMessageQueue, toast]);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'mt5_status_update':
        queryClient.invalidateQueries({ queryKey: ["/api/mt5-status"] });
        if (message.data.status === 'disconnected') {
          toast({
            title: "MT5 Disconnected",
            description: "MetaTrader 5 connection lost",
            variant: "destructive",
          });
        }
        break;
      case 'signal_created':
        queryClient.invalidateQueries({ queryKey: ["/api/signals"] });
        queryClient.invalidateQueries({ queryKey: ["/api/dashboard/stats"] });
        toast({
          title: "New Signal",
          description: `Signal received from ${message.data.provider || 'provider'}`,
        });
        break;
      case 'trade_update':
        queryClient.invalidateQueries({ queryKey: ["/api/trades/live"] });
        queryClient.invalidateQueries({ queryKey: ["/api/trades/active"] });
        queryClient.invalidateQueries({ queryKey: ["/api/dashboard/stats"] });
        queryClient.invalidateQueries({ queryKey: ["/api/dashboard/performance"] });
        break;
      case 'trade_opened':
        queryClient.invalidateQueries({ queryKey: ["/api/trades/live"] });
        queryClient.invalidateQueries({ queryKey: ["/api/dashboard/stats"] });
        toast({
          title: "Trade Opened",
          description: `${message.data.symbol} - Lot: ${message.data.lotSize}`,
        });
        break;
      case 'trade_closed':
        queryClient.invalidateQueries({ queryKey: ["/api/trades/live"] });
        queryClient.invalidateQueries({ queryKey: ["/api/dashboard/stats"] });
        toast({
          title: "Trade Closed",
          description: `${message.data.symbol} - P&L: ${message.data.profit > 0 ? '+' : ''}${message.data.profit}`,
          variant: message.data.profit > 0 ? "default" : "destructive",
        });
        break;
      case 'signal_replay':
        queryClient.invalidateQueries({ queryKey: ["/api/signals"] });
        toast({
          title: "Signal Replayed",
          description: "Historical signal has been replayed",
        });
        break;
      case 'emergency_stop':
        queryClient.invalidateQueries({ queryKey: ["/api/mt5-status"] });
        queryClient.invalidateQueries({ queryKey: ["/api/trades/live"] });
        toast({
          title: "Emergency Stop Activated",
          description: "All trading has been stopped",
          variant: "destructive",
        });
        break;
      case 'trading_paused':
        queryClient.invalidateQueries({ queryKey: ["/api/mt5-status"] });
        toast({
          title: "Trading Paused",
          description: "Signal processing has been paused",
        });
        break;
      case 'trading_resumed':
        queryClient.invalidateQueries({ queryKey: ["/api/mt5-status"] });
        toast({
          title: "Trading Resumed",
          description: "Signal processing has been resumed",
        });
        break;
      case 'error_alert':
        console.error("Desktop app error:", message.data);
        toast({
          title: "System Error",
          description: message.data.message || "An error occurred in the desktop app",
          variant: "destructive",
        });
        break;
      case 'desktop_sync_complete':
        queryClient.invalidateQueries({ queryKey: ["/api/mt5-status"] });
        queryClient.invalidateQueries({ queryKey: ["/api/trades/live"] });
        queryClient.invalidateQueries({ queryKey: ["/api/dashboard/stats"] });
        toast({
          title: "Sync Complete",
          description: "Desktop app synchronized successfully",
        });
        break;
      default:
        console.log("Unknown WebSocket message type:", message.type);
    }
  }, [queryClient, toast]);

  useEffect(() => {
    connect();

    // Auto-authenticate when connection is established
    const authTimer = setTimeout(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        sendMessage('authenticate', { userId: 1 }); // Default user for demo
      }
    }, 1000);

    return () => {
      clearTimeout(authTimer);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect, sendMessage]);

  const sendMessage = useCallback((type: string, data: any) => {
    const message: WebSocketMessage = {
      type,
      data,
      timestamp: new Date().toISOString(),
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      // Queue message for when connection is restored
      messageQueueRef.current.push(message);
      if (messageQueueRef.current.length > 100) {
        // Prevent memory leaks - keep only last 100 messages
        messageQueueRef.current = messageQueueRef.current.slice(-100);
      }
    }
  }, []);

  const forceReconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    reconnectAttemptsRef.current = 0;
    connect();
  }, [connect]);

  return {
    isConnected,
    connectionState,
    sendMessage,
    forceReconnect,
    reconnectAttempts: reconnectAttemptsRef.current,
    maxReconnectAttempts,
    queuedMessages: messageQueueRef.current.length,
  };
}
