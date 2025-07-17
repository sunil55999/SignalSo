import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// API request helper for mutations
export const apiRequest = async (url: string, options?: RequestInit) => {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
  }

  return response.json();
};

// API endpoints for easier management
export const API_ENDPOINTS = {
  HEALTH: '/api/health',
  ROUTER_STATUS: '/api/router/status',
  ROUTER_START: '/api/router/start',
  ROUTER_STOP: '/api/router/stop',
  MT5_STATUS: '/api/mt5/status',
  MT5_CONNECT: '/api/mt5/connect',
  MT5_DISCONNECT: '/api/mt5/disconnect',
  TELEGRAM_STATUS: '/api/telegram/status',
  TELEGRAM_LOGIN: '/api/telegram/login',
  TELEGRAM_LOGOUT: '/api/telegram/logout',
  LOGS: '/api/logs',
  LOGS_STATS: '/api/logs/stats',
  AUTH_LOGIN: '/api/auth/login',
  AUTH_LOGOUT: '/api/auth/logout',
  AUTH_LICENSE: '/api/auth/license',
  CONFIG: '/api/config',
  CONFIG_SYNC: '/api/config/sync',
  UPDATES_CHECK: '/api/updates/check',
  UPDATES_DOWNLOAD: '/api/updates/download',
  BRIDGE_STATUS: '/api/bridge/status',
  BRIDGE_CONNECT: '/api/bridge/connect',
};