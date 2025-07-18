import { QueryClient } from '@tanstack/react-query';

// Get base URL from environment variable
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// API request helper for mutations with baseURL
export const apiRequest = async (url: string, options?: RequestInit) => {
  const fullUrl = `${API_BASE_URL}${url}`;
  const response = await fetch(fullUrl, {
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