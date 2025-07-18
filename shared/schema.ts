import { z } from 'zod';

// Trading Account Schema
export const accountSchema = z.object({
  id: z.string(),
  balance: z.number(),
  equity: z.number(),
  margin: z.number(),
  marginFree: z.number(),
  marginLevel: z.number(),
  profit: z.number(),
  currency: z.string(),
  server: z.string(),
  leverage: z.number(),
  name: z.string(),
  company: z.string(),
  tradeAllowed: z.boolean(),
  tradeExpert: z.boolean(),
  limitOrders: z.number(),
  marginSoMode: z.number(),
  marginSoCall: z.number(),
  marginSoSo: z.number(),
  marginInitial: z.number(),
  marginMaintenance: z.number(),
  assetsBalance: z.number(),
  assetsCredit: z.number(),
  assetsEquity: z.number(),
  assetsProfit: z.number(),
});

// System Health Schema
export const systemHealthSchema = z.object({
  aiParser: z.object({
    status: z.enum(['online', 'offline', 'error']),
    lastActivity: z.string(),
    successRate: z.number(),
    message: z.string().optional(),
  }),
  mt5Bridge: z.object({
    status: z.enum(['connected', 'disconnected', 'error']),
    lastActivity: z.string(),
    latency: z.number(),
    message: z.string().optional(),
  }),
  telegramLink: z.object({
    status: z.enum(['active', 'inactive', 'error']),
    lastActivity: z.string(),
    channelsConnected: z.number(),
    message: z.string().optional(),
  }),
  marketplace: z.object({
    status: z.enum(['online', 'offline', 'maintenance']),
    lastUpdate: z.string(),
    message: z.string().optional(),
  }),
  notifications: z.object({
    status: z.enum(['enabled', 'disabled', 'error']),
    queueSize: z.number(),
    message: z.string().optional(),
  }),
});

// Trading Metrics Schema
export const tradingMetricsSchema = z.object({
  todaysPnL: z.number(),
  winRate: z.number(),
  tradesExecuted: z.number(),
  parsingSuccessRate: z.number(),
  executionSpeed: z.number(),
  totalTrades: z.number(),
  totalProfit: z.number(),
  totalLoss: z.number(),
  averageWin: z.number(),
  averageLoss: z.number(),
  maxDrawdown: z.number(),
  sharpeRatio: z.number(),
  profitFactor: z.number(),
});

// Activity Event Schema
export const activityEventSchema = z.object({
  id: z.string(),
  timestamp: z.string(),
  type: z.enum(['trade', 'signal', 'error', 'system', 'provider', 'strategy']),
  level: z.enum(['info', 'warning', 'error', 'success']),
  title: z.string(),
  description: z.string(),
  details: z.record(z.any()).optional(),
  provider: z.string().optional(),
  strategy: z.string().optional(),
  symbol: z.string().optional(),
  resolved: z.boolean().default(false),
  actions: z.array(z.object({
    id: z.string(),
    label: z.string(),
    type: z.enum(['retry', 'acknowledge', 'ignore', 'fix']),
  })).optional(),
});

// Provider Schema
export const providerSchema = z.object({
  id: z.string(),
  name: z.string(),
  type: z.enum(['telegram', 'api', 'file', 'manual']),
  status: z.enum(['active', 'inactive', 'error', 'testing']),
  connected: z.boolean(),
  channelId: z.string().optional(),
  channelName: z.string().optional(),
  lastActivity: z.string(),
  performance: z.object({
    totalSignals: z.number(),
    successfulParsing: z.number(),
    executedTrades: z.number(),
    winRate: z.number(),
    profit: z.number(),
    latency: z.number(),
  }),
  settings: z.record(z.any()).optional(),
});

// Strategy Schema
export const strategySchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  status: z.enum(['active', 'inactive', 'testing', 'paused']),
  type: z.enum(['signal_copy', 'grid', 'martingale', 'scalping', 'swing', 'custom']),
  providers: z.array(z.string()),
  rules: z.array(z.object({
    id: z.string(),
    condition: z.string(),
    action: z.string(),
    parameters: z.record(z.any()),
  })),
  riskManagement: z.object({
    maxLotSize: z.number(),
    maxRiskPerTrade: z.number(),
    maxDailyLoss: z.number(),
    stopLossPoints: z.number(),
    takeProfitPoints: z.number(),
  }),
  performance: z.object({
    totalTrades: z.number(),
    winRate: z.number(),
    profit: z.number(),
    drawdown: z.number(),
    lastExecuted: z.string(),
  }),
  backtestResults: z.array(z.object({
    period: z.string(),
    profit: z.number(),
    trades: z.number(),
    winRate: z.number(),
    maxDrawdown: z.number(),
  })).optional(),
});

// Trade Schema
export const tradeSchema = z.object({
  id: z.string(),
  ticket: z.number(),
  symbol: z.string(),
  type: z.enum(['buy', 'sell', 'buy_limit', 'sell_limit', 'buy_stop', 'sell_stop']),
  volume: z.number(),
  openPrice: z.number(),
  currentPrice: z.number(),
  stopLoss: z.number(),
  takeProfit: z.number(),
  profit: z.number(),
  swap: z.number(),
  commission: z.number(),
  comment: z.string(),
  openTime: z.string(),
  closeTime: z.string().optional(),
  status: z.enum(['pending', 'open', 'closed', 'cancelled']),
  provider: z.string(),
  strategy: z.string(),
  signalId: z.string().optional(),
});

// Risk Exposure Schema
export const riskExposureSchema = z.object({
  symbol: z.string(),
  exposure: z.number(),
  margin: z.number(),
  unrealizedPnL: z.number(),
  trades: z.number(),
  providers: z.array(z.string()),
  maxExposure: z.number(),
  riskLevel: z.enum(['low', 'medium', 'high', 'critical']),
});

// Notification Schema
export const notificationSchema = z.object({
  id: z.string(),
  type: z.enum(['info', 'warning', 'error', 'success']),
  title: z.string(),
  message: z.string(),
  timestamp: z.string(),
  read: z.boolean().default(false),
  dismissed: z.boolean().default(false),
  actions: z.array(z.object({
    id: z.string(),
    label: z.string(),
    type: z.enum(['resolve', 'fix', 'dismiss', 'retry']),
    url: z.string().optional(),
  })).optional(),
  category: z.enum(['system', 'trading', 'provider', 'strategy', 'risk']),
  priority: z.enum(['low', 'medium', 'high', 'urgent']),
});

// Dashboard Widget Schema
export const dashboardWidgetSchema = z.object({
  id: z.string(),
  type: z.enum(['account', 'health', 'metrics', 'activity', 'providers', 'strategies', 'risk', 'notifications']),
  title: z.string(),
  position: z.object({
    x: z.number(),
    y: z.number(),
    width: z.number(),
    height: z.number(),
  }),
  visible: z.boolean().default(true),
  pinned: z.boolean().default(false),
  settings: z.record(z.any()).optional(),
});

// License Schema
export const licenseSchema = z.object({
  id: z.string(),
  tier: z.enum(['free', 'basic', 'pro', 'enterprise']),
  status: z.enum(['active', 'expired', 'suspended', 'trial']),
  validUntil: z.string(),
  features: z.array(z.string()),
  limits: z.object({
    providers: z.number(),
    strategies: z.number(),
    trades: z.number(),
    signals: z.number(),
  }),
  deviceId: z.string(),
  userId: z.string(),
  companyName: z.string().optional(),
});

// Export types
export type Account = z.infer<typeof accountSchema>;
export type SystemHealth = z.infer<typeof systemHealthSchema>;
export type TradingMetrics = z.infer<typeof tradingMetricsSchema>;
export type ActivityEvent = z.infer<typeof activityEventSchema>;
export type Provider = z.infer<typeof providerSchema>;
export type Strategy = z.infer<typeof strategySchema>;
export type Trade = z.infer<typeof tradeSchema>;
export type RiskExposure = z.infer<typeof riskExposureSchema>;
export type Notification = z.infer<typeof notificationSchema>;
export type DashboardWidget = z.infer<typeof dashboardWidgetSchema>;
export type License = z.infer<typeof licenseSchema>;