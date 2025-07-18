import { useQuery, useMutation } from '@tanstack/react-query';
import { apiRequest, API_ENDPOINTS, queryClient } from '@/lib/queryClient';
import { useToast } from '@/hooks/use-toast';

export interface SystemStatus {
  router: {
    status: 'running' | 'stopped' | 'error';
    uptime: number;
    activeTasks: number;
    lastStarted: string;
  };
  mt5: {
    status: 'connected' | 'disconnected' | 'error';
    account: string;
    balance: number;
    equity: number;
    lastConnected: string;
  };
  telegram: {
    status: 'connected' | 'disconnected' | 'error';
    username: string;
    channelCount: number;
    lastMessage: string;
    lastMessageTime: string;
  };
  bridge: {
    status: 'active' | 'inactive' | 'error';
    version: string;
    lastUpdate: string;
  };
  health: {
    status: 'healthy' | 'degraded' | 'error';
    cpu: number;
    memory: number;
    uptime: number;
  };
}

export const useSystemStatus = () => {
  // Query system health with frequent polling
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: [API_ENDPOINTS.HEALTH],
    refetchInterval: 5000, // Poll every 5 seconds
  });

  // Query router status
  const { data: router, isLoading: routerLoading } = useQuery({
    queryKey: [API_ENDPOINTS.ROUTER_STATUS],
    refetchInterval: 10000, // Poll every 10 seconds
  });

  // Query MT5 status
  const { data: mt5, isLoading: mt5Loading } = useQuery({
    queryKey: [API_ENDPOINTS.MT5_STATUS],
    refetchInterval: 15000, // Poll every 15 seconds
  });

  // Query Telegram status
  const { data: telegram, isLoading: telegramLoading } = useQuery({
    queryKey: [API_ENDPOINTS.TELEGRAM_STATUS],
    refetchInterval: 10000, // Poll every 10 seconds
  });

  // Query bridge status
  const { data: bridge, isLoading: bridgeLoading } = useQuery({
    queryKey: [API_ENDPOINTS.BRIDGE_STATUS],
    refetchInterval: 30000, // Poll every 30 seconds
  });

  const isLoading = healthLoading || routerLoading || mt5Loading || telegramLoading || bridgeLoading;

  const systemStatus: SystemStatus = {
    router: router || {
      status: 'stopped',
      uptime: 0,
      activeTasks: 0,
      lastStarted: '',
    },
    mt5: mt5 || {
      status: 'disconnected',
      account: '',
      balance: 0,
      equity: 0,
      lastConnected: '',
    },
    telegram: telegram || {
      status: 'disconnected',
      username: '',
      channelCount: 0,
      lastMessage: '',
      lastMessageTime: '',
    },
    bridge: bridge || {
      status: 'inactive',
      version: '',
      lastUpdate: '',
    },
    health: health || {
      status: 'error',
      cpu: 0,
      memory: 0,
      uptime: 0,
    },
  };

  return {
    systemStatus,
    isLoading,
    refetch: () => {
      queryClient.invalidateQueries({ queryKey: [API_ENDPOINTS.HEALTH] });
      queryClient.invalidateQueries({ queryKey: [API_ENDPOINTS.ROUTER_STATUS] });
      queryClient.invalidateQueries({ queryKey: [API_ENDPOINTS.MT5_STATUS] });
      queryClient.invalidateQueries({ queryKey: [API_ENDPOINTS.TELEGRAM_STATUS] });
      queryClient.invalidateQueries({ queryKey: [API_ENDPOINTS.BRIDGE_STATUS] });
    },
  };
};

export const useSystemActions = () => {
  const { toast } = useToast();

  // Router actions
  const startRouter = useMutation({
    mutationFn: () => apiRequest(API_ENDPOINTS.ROUTER_START, { method: 'POST' }),
    onSuccess: () => {
      toast({
        title: 'Router started',
        description: 'Signal routing service is now active',
      });
      queryClient.invalidateQueries({ queryKey: [API_ENDPOINTS.ROUTER_STATUS] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Router start failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  const stopRouter = useMutation({
    mutationFn: () => apiRequest(API_ENDPOINTS.ROUTER_STOP, { method: 'POST' }),
    onSuccess: () => {
      toast({
        title: 'Router stopped',
        description: 'Signal routing service has been stopped',
      });
      queryClient.invalidateQueries({ queryKey: [API_ENDPOINTS.ROUTER_STATUS] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Router stop failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // MT5 actions
  const connectMT5 = useMutation({
    mutationFn: (credentials: { login: string; password: string; server: string }) =>
      apiRequest(API_ENDPOINTS.MT5_CONNECT, {
        method: 'POST',
        body: JSON.stringify(credentials),
      }),
    onSuccess: () => {
      toast({
        title: 'MT5 connected',
        description: 'Successfully connected to MetaTrader 5',
      });
      queryClient.invalidateQueries({ queryKey: [API_ENDPOINTS.MT5_STATUS] });
    },
    onError: (error: Error) => {
      toast({
        title: 'MT5 connection failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  const disconnectMT5 = useMutation({
    mutationFn: () => apiRequest(API_ENDPOINTS.MT5_DISCONNECT, { method: 'POST' }),
    onSuccess: () => {
      toast({
        title: 'MT5 disconnected',
        description: 'Disconnected from MetaTrader 5',
      });
      queryClient.invalidateQueries({ queryKey: [API_ENDPOINTS.MT5_STATUS] });
    },
    onError: (error: Error) => {
      toast({
        title: 'MT5 disconnect failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Telegram actions
  const connectTelegram = useMutation({
    mutationFn: (credentials: { apiId: string; apiHash: string; phoneNumber: string }) =>
      apiRequest(API_ENDPOINTS.TELEGRAM_LOGIN, {
        method: 'POST',
        body: JSON.stringify(credentials),
      }),
    onSuccess: () => {
      toast({
        title: 'Telegram connected',
        description: 'Successfully connected to Telegram',
      });
      queryClient.invalidateQueries({ queryKey: [API_ENDPOINTS.TELEGRAM_STATUS] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Telegram connection failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  const disconnectTelegram = useMutation({
    mutationFn: () => apiRequest(API_ENDPOINTS.TELEGRAM_LOGOUT, { method: 'POST' }),
    onSuccess: () => {
      toast({
        title: 'Telegram disconnected',
        description: 'Disconnected from Telegram',
      });
      queryClient.invalidateQueries({ queryKey: [API_ENDPOINTS.TELEGRAM_STATUS] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Telegram disconnect failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Bridge actions
  const connectBridge = useMutation({
    mutationFn: () => apiRequest(API_ENDPOINTS.BRIDGE_CONNECT, { method: 'POST' }),
    onSuccess: () => {
      toast({
        title: 'Bridge connected',
        description: 'API bridge is now active',
      });
      queryClient.invalidateQueries({ queryKey: [API_ENDPOINTS.BRIDGE_STATUS] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Bridge connection failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  return {
    startRouter,
    stopRouter,
    connectMT5,
    disconnectMT5,
    connectTelegram,
    disconnectTelegram,
    connectBridge,
  };
};