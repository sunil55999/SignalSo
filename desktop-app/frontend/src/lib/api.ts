import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for auth tokens
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      // Redirect to login or refresh token
    }
    return Promise.reject(error)
  }
)

// API Types
export interface SystemStatus {
  system: string
  status: string
  components: {
    database: string
    ai_parser: string
    mt5_bridge: string
    telegram: string
  }
  stats: {
    signals_today: number
    active_trades: number
    total_profit: number
    win_rate: number
  }
}

export interface Signal {
  id: string
  symbol: string
  type: 'BUY' | 'SELL'
  entry_price: number
  stop_loss: number
  take_profit: number
  lot_size: number
  confidence: number
  status: 'PENDING' | 'EXECUTED' | 'FAILED'
  created_at: string
  raw_signal: string
}

export interface Trade {
  id: string
  mt5_ticket: number
  symbol: string
  trade_type: 'BUY' | 'SELL'
  volume: number
  open_price: number
  close_price?: number
  stop_loss: number
  take_profit: number
  profit: number
  status: 'OPEN' | 'CLOSED' | 'PENDING'
  opened_at: string
  closed_at?: string
}

export interface Account {
  account_number: string
  broker: string
  balance: number
  equity: number
  margin: number
  free_margin: number
  margin_level: number
  server: string
  is_active: boolean
}

export interface ActivityEvent {
  id: string
  type: 'signal' | 'trade' | 'error' | 'system'
  message: string
  timestamp: string
  severity: 'info' | 'warning' | 'error' | 'success'
  data?: any
}

// API Functions
export const apiService = {
  // System status
  getHealth: () => api.get('/health'),
  getSystemStatus: () => api.get<SystemStatus>('/api/status'),
  
  // Signals
  getSignals: () => api.get<{ signals: Signal[] }>('/api/signals'),
  
  // Trades
  getTrades: () => api.get<{ trades: Trade[] }>('/api/trades'),
  
  // Account
  getAccount: () => api.get<Account>('/api/account'),
  
  // Activity feed
  getActivity: (limit?: number) => api.get<{ events: ActivityEvent[] }>(`/api/activity${limit ? `?limit=${limit}` : ''}`),
  
  // Providers
  getProviders: () => api.get('/api/providers'),
  testProvider: (id: string) => api.post(`/api/providers/${id}/test`),
  
  // Strategies
  getStrategies: () => api.get('/api/strategies'),
  runBacktest: (strategyId: string, params: any) => api.post(`/api/strategies/${strategyId}/backtest`, params),
  
  // System controls
  pauseSystem: () => api.post('/api/system/pause'),
  resumeSystem: () => api.post('/api/system/resume'),
  importSignals: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/api/signals/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
}