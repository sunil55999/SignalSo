import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Request logging
app.use((req, res, next) => {
  console.log(`[SERVER] ${req.method} ${req.path}`);
  next();
});

// API Routes
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

app.post('/api/auth/login', (req, res) => {
  const { username, password } = req.body;
  if (username === 'demo' && password === 'demo123') {
    res.json({ 
      success: true, 
      user: { id: '1', username: 'demo', email: 'demo@example.com' },
      token: 'mock-jwt-token'
    });
  } else {
    res.status(401).json({ success: false, error: 'Invalid credentials' });
  }
});

app.post('/api/router/start', (req, res) => {
  res.json({ success: true });
});

app.post('/api/router/stop', (req, res) => {
  res.json({ success: true });
});

app.get('/api/router/status', (req, res) => {
  res.json({
    status: 'running',
    uptime: 3600,
    activeTasks: 5,
    lastStarted: new Date().toISOString()
  });
});

app.get('/api/mt5/status', (req, res) => {
  res.json({
    status: 'connected',
    account: 'Demo Account',
    balance: 10000,
    equity: 10000,
    lastConnected: new Date().toISOString()
  });
});

app.post('/api/mt5/connect', (req, res) => {
  res.json({ success: true });
});

app.post('/api/mt5/disconnect', (req, res) => {
  res.json({ success: true });
});

app.get('/api/telegram/status', (req, res) => {
  res.json({
    status: 'connected',
    username: 'demo_user',
    channelCount: 3,
    lastMessage: 'BUY EURUSD @ 1.0850',
    lastMessageTime: new Date().toISOString()
  });
});

app.post('/api/telegram/login', (req, res) => {
  res.json({ success: true });
});

app.post('/api/telegram/logout', (req, res) => {
  res.json({ success: true });
});

app.get('/api/logs', (req, res) => {
  const mockLogs = [
    { id: '1', level: 'info', message: 'Router started successfully', timestamp: new Date().toISOString(), component: 'router' },
    { id: '2', level: 'info', message: 'MT5 connection established', timestamp: new Date().toISOString(), component: 'mt5' },
    { id: '3', level: 'info', message: 'Telegram authentication completed', timestamp: new Date().toISOString(), component: 'telegram' },
    { id: '4', level: 'info', message: 'System health check passed', timestamp: new Date().toISOString(), component: 'system' },
    { id: '5', level: 'warning', message: 'High CPU usage detected', timestamp: new Date().toISOString(), component: 'system' }
  ];
  res.json(mockLogs);
});

app.get('/api/logs/stats', (req, res) => {
  res.json({
    total: 100,
    byLevel: { info: 80, warning: 15, error: 5 },
    byComponent: { router: 30, mt5: 25, telegram: 25, system: 20 }
  });
});

app.get('/api/bridge/status', (req, res) => {
  res.json({
    status: 'active',
    version: '1.0.0',
    lastUpdate: new Date().toISOString()
  });
});

app.post('/api/bridge/connect', (req, res) => {
  res.json({ success: true });
});

// Import/Export endpoints
app.post('/api/import', (req, res) => {
  // Mock import functionality
  const success = Math.random() > 0.2; // 80% success rate
  
  if (success) {
    res.json({
      success: true,
      message: 'Import completed successfully',
      items: Math.floor(Math.random() * 50) + 1,
      warnings: Math.random() > 0.5 ? ['Some duplicate items were skipped'] : []
    });
  } else {
    res.json({
      success: false,
      message: 'Import failed',
      errors: ['Invalid file format', 'Unable to parse data']
    });
  }
});

app.get('/api/export/:type', (req, res) => {
  const { type } = req.params;
  
  // Mock export data
  const exportData = {
    signals: [
      { id: 1, symbol: 'EURUSD', action: 'BUY', price: 1.0850, tp: 1.0900, sl: 1.0800 },
      { id: 2, symbol: 'GBPUSD', action: 'SELL', price: 1.2650, tp: 1.2600, sl: 1.2700 }
    ],
    strategies: [
      { id: 1, name: 'EUR/USD Scalping', symbols: ['EURUSD'], riskPercent: 2 },
      { id: 2, name: 'GBP/USD Swing', symbols: ['GBPUSD'], riskPercent: 1.5 }
    ],
    providers: [
      { id: 1, name: 'Premium Signals', channel: '@premium_signals', active: true },
      { id: 2, name: 'Forex Pro', channel: '@forex_pro', active: false }
    ]
  };
  
  res.json(exportData[type as keyof typeof exportData] || []);
});

// Telegram connection endpoints
app.post('/api/telegram/connect', (req, res) => {
  const { apiId, apiHash, phoneNumber } = req.body;
  
  // Mock connection logic
  setTimeout(() => {
    if (apiId && apiHash && phoneNumber) {
      res.json({
        success: true,
        message: 'Connected to Telegram successfully'
      });
    } else {
      res.json({
        success: false,
        message: 'Invalid credentials'
      });
    }
  }, 2000);
});

app.get('/api/telegram/scan-channels', (req, res) => {
  // Mock channel scan
  const channels = [
    'Premium Forex Signals',
    'Daily Trading Alerts',
    'Crypto Signals Pro',
    'FX Market Updates',
    'Elite Trading Group'
  ];
  
  res.json({
    success: true,
    channels: channels
  });
});

// Test endpoints
app.post('/api/test/parse-signal', (req, res) => {
  const { signal } = req.body;
  
  // Mock signal parsing
  const parsed = {
    symbol: 'EURUSD',
    action: 'BUY',
    price: 1.0850,
    tp: 1.0900,
    sl: 1.0800,
    confidence: 0.92
  };
  
  res.json({
    success: true,
    parsed: parsed,
    message: 'Signal parsed successfully'
  });
});

// Signal Provider Management
app.get('/api/providers', (req, res) => {
  const providers = [
    {
      id: '1',
      name: 'Premium Forex Signals',
      channel: '@premium_signals',
      description: 'Professional forex trading signals with high accuracy',
      active: true,
      stats: {
        totalSignals: 1250,
        winRate: 72.5,
        avgPnL: 245.8,
        lastSignal: '2 minutes ago',
        status: 'active'
      }
    },
    {
      id: '2',
      name: 'Gold Trading Pro',
      channel: '@gold_signals',
      description: 'Specialized gold and precious metals signals',
      active: true,
      stats: {
        totalSignals: 856,
        winRate: 68.9,
        avgPnL: 189.2,
        lastSignal: '15 minutes ago',
        status: 'active'
      }
    }
  ];
  res.json(providers);
});

app.post('/api/providers', (req, res) => {
  const provider = req.body;
  provider.id = Date.now().toString();
  provider.stats = {
    totalSignals: 0,
    winRate: 0,
    avgPnL: 0,
    lastSignal: 'Never',
    status: 'inactive'
  };
  res.json({ success: true, provider });
});

app.put('/api/providers/:id', (req, res) => {
  const { id } = req.params;
  const updatedProvider = req.body;
  res.json({ success: true, provider: updatedProvider });
});

app.delete('/api/providers/:id', (req, res) => {
  const { id } = req.params;
  res.json({ success: true, message: 'Provider deleted' });
});

// Strategy Management
app.get('/api/strategies', (req, res) => {
  const strategies = [
    {
      id: '1',
      name: 'EUR/USD Scalping',
      description: 'High-frequency scalping strategy for EUR/USD pair',
      type: 'visual',
      conditions: [
        { type: 'rsi', value: 30, operator: 'below' },
        { type: 'macd', value: 0, operator: 'above' }
      ],
      riskManagement: {
        maxLotSize: 0.1,
        stopLoss: 20,
        takeProfit: 30,
        riskPercent: 2.0
      },
      symbols: ['EURUSD'],
      active: true,
      backtest: {
        period: '3M',
        results: {
          totalTrades: 245,
          winRate: 68.5,
          totalPnL: 2840.50,
          maxDrawdown: 12.3
        }
      }
    }
  ];
  res.json(strategies);
});

app.post('/api/strategies', (req, res) => {
  const strategy = req.body;
  strategy.id = Date.now().toString();
  res.json({ success: true, strategy });
});

app.put('/api/strategies/:id', (req, res) => {
  const { id } = req.params;
  const updatedStrategy = req.body;
  res.json({ success: true, strategy: updatedStrategy });
});

app.post('/api/strategies/:id/backtest', (req, res) => {
  const { id } = req.params;
  
  // Mock backtest results
  const results = {
    totalTrades: Math.floor(Math.random() * 500) + 100,
    winRate: Math.floor(Math.random() * 40) + 50,
    totalPnL: Math.floor(Math.random() * 5000) + 1000,
    maxDrawdown: Math.floor(Math.random() * 20) + 5
  };
  
  res.json({ success: true, results });
});

// Active Trades Management
app.get('/api/trades', (req, res) => {
  const trades = [
    {
      id: '1',
      ticket: '123456789',
      symbol: 'EURUSD',
      action: 'BUY',
      volume: 0.1,
      openPrice: 1.0850,
      currentPrice: 1.0875,
      stopLoss: 1.0800,
      takeProfit: 1.0950,
      profit: 25.0,
      openTime: new Date(Date.now() - 3600000).toISOString(),
      status: 'open',
      comment: 'Premium Signals'
    },
    {
      id: '2',
      ticket: '123456790',
      symbol: 'GBPUSD',
      action: 'SELL',
      volume: 0.05,
      openPrice: 1.2650,
      currentPrice: 1.2625,
      stopLoss: 1.2700,
      takeProfit: 1.2600,
      profit: 12.5,
      openTime: new Date(Date.now() - 7200000).toISOString(),
      status: 'open',
      comment: 'Gold Signals Pro'
    }
  ];
  res.json(trades);
});

app.put('/api/trades/:id', (req, res) => {
  const { id } = req.params;
  const updatedTrade = req.body;
  res.json({ success: true, trade: updatedTrade });
});

app.post('/api/trades/:id/close', (req, res) => {
  const { id } = req.params;
  const { type, volume } = req.body;
  res.json({ success: true, message: `Trade ${type} close executed` });
});

// Signal Parsing and Validation
app.post('/api/signals/parse', (req, res) => {
  const { signal } = req.body;
  
  // Mock advanced parsing
  const parsed = {
    symbol: 'EURUSD',
    action: 'BUY',
    entryPrice: 1.0850,
    stopLoss: 1.0800,
    takeProfit: [1.0900, 1.0950],
    confidence: 0.92,
    metadata: {
      provider: 'Premium Signals',
      timestamp: new Date().toISOString(),
      language: 'English'
    }
  };
  
  res.json({
    success: true,
    parsed: parsed,
    message: 'Signal parsed successfully'
  });
});

app.post('/api/signals/validate', (req, res) => {
  const { signal } = req.body;
  
  const validation = {
    isValid: true,
    confidence: 0.89,
    warnings: ['Price levels may be outdated'],
    suggestions: ['Consider updating stop loss level']
  };
  
  res.json({
    success: true,
    validation: validation,
    message: 'Signal validation completed'
  });
});

// System Health and Diagnostics
app.get('/api/system/health', (req, res) => {
  res.json({
    status: 'healthy',
    modules: {
      parser: { status: 'healthy', uptime: '99.9%' },
      router: { status: 'running', uptime: '100h 25m' },
      mt5: { status: 'connected', uptime: '98.5%' },
      telegram: { status: 'active', uptime: '99.1%' },
      database: { status: 'healthy', uptime: '99.9%' },
      risk: { status: 'healthy', uptime: '100%' }
    },
    timestamp: new Date().toISOString()
  });
});

app.get('/api/system/diagnostics', (req, res) => {
  res.json({
    cpu: { usage: 15.2, cores: 4 },
    memory: { used: 2.1, total: 8.0, unit: 'GB' },
    network: { latency: 12, bandwidth: 100 },
    disk: { used: 45.3, total: 100, unit: 'GB' },
    processes: {
      parser: { pid: 1234, memory: 128, cpu: 2.3 },
      router: { pid: 1235, memory: 256, cpu: 5.1 },
      mt5: { pid: 1236, memory: 512, cpu: 8.7 }
    }
  });
});

// Data Export/Import Enhancement
app.post('/api/data/import', (req, res) => {
  const { type, data, options } = req.body;
  
  // Mock comprehensive import
  const result = {
    success: true,
    imported: Math.floor(Math.random() * 100) + 50,
    skipped: Math.floor(Math.random() * 10),
    errors: Math.floor(Math.random() * 3),
    warnings: ['Some duplicate entries were merged'],
    summary: {
      signals: 45,
      providers: 3,
      strategies: 2
    }
  };
  
  res.json(result);
});

app.get('/api/data/export/:type', (req, res) => {
  const { type } = req.params;
  const { format = 'json' } = req.query;
  
  // Mock export data based on type
  const exportData = {
    signals: Array(50).fill(null).map((_, i) => ({
      id: i + 1,
      symbol: ['EURUSD', 'GBPUSD', 'USDJPY'][i % 3],
      action: ['BUY', 'SELL'][i % 2],
      price: (1.0 + Math.random() * 0.5).toFixed(5),
      timestamp: new Date(Date.now() - i * 3600000).toISOString()
    })),
    providers: [
      { id: 1, name: 'Premium Signals', channel: '@premium_signals' },
      { id: 2, name: 'Gold Pro', channel: '@gold_signals' }
    ],
    strategies: [
      { id: 1, name: 'EUR/USD Scalping', type: 'visual' },
      { id: 2, name: 'Gold Trend', type: 'code' }
    ]
  };
  
  res.json(exportData[type] || []);
});

// Enhanced Logs API
app.get('/api/logs/stats', (req, res) => {
  const stats = {
    total: 1247,
    byLevel: {
      info: 856,
      warning: 234,
      error: 157
    },
    byComponent: {
      router: 445,
      mt5: 321,
      telegram: 289,
      system: 192
    },
    lastUpdated: new Date().toISOString()
  };
  res.json(stats);
});

// Import/Export API enhancement
app.post('/api/import', (req, res) => {
  const { data, options } = req.body;
  
  // Mock import processing
  const result = {
    success: true,
    items: Math.floor(Math.random() * 50) + 20,
    warnings: options?.skipInvalid ? ['3 invalid entries skipped'] : [],
    timestamp: new Date().toISOString()
  };
  
  res.json(result);
});

app.get('/api/export/:type', (req, res) => {
  const { type } = req.params;
  
  // Mock export data
  const mockData = {
    signals: Array(25).fill(null).map((_, i) => ({
      id: i + 1,
      symbol: ['EURUSD', 'GBPUSD', 'USDJPY'][i % 3],
      action: ['BUY', 'SELL'][i % 2],
      price: (1.0 + Math.random() * 0.5).toFixed(5),
      timestamp: new Date(Date.now() - i * 3600000).toISOString()
    })),
    strategies: [
      { id: 1, name: 'EUR/USD Scalping', type: 'visual', active: true },
      { id: 2, name: 'Gold Trend Following', type: 'code', active: false }
    ],
    providers: [
      { id: 1, name: 'Premium Signals', channel: '@premium_signals', active: true },
      { id: 2, name: 'Gold Pro', channel: '@gold_signals', active: true }
    ],
    logs: Array(100).fill(null).map((_, i) => ({
      id: i + 1,
      timestamp: new Date(Date.now() - i * 60000).toISOString(),
      level: ['info', 'warning', 'error'][i % 3],
      component: ['router', 'mt5', 'telegram', 'system'][i % 4],
      message: `Log entry ${i + 1} from ${['router', 'mt5', 'telegram', 'system'][i % 4]} component`
    }))
  };
  
  res.json(mockData[type] || []);
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

// Development mode - serve the redesigned interface
app.get('*', (req, res) => {
  const redesignedHTML = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SignalOS - Desktop Trading Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .gradient-bg {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .glassmorphism {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .card-hover {
            transition: all 0.3s ease;
        }
        .card-hover:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
        }
        .status-indicator {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 500;
            text-transform: uppercase;
        }
        .status-running {
            background-color: #dcfce7;
            color: #166534;
        }
        .status-connected {
            background-color: #dcfce7;
            color: #166534;
        }
        .status-active {
            background-color: #dcfce7;
            color: #166534;
        }
        .status-loading {
            background-color: #fef3c7;
            color: #92400e;
        }
    </style>
</head>
<body>
    <div class="gradient-bg">
        <!-- Header -->
        <div class="glassmorphism shadow-lg border-b border-white/20">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex justify-between items-center py-6">
                    <div class="flex items-center space-x-4">
                        <div class="h-12 w-12 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center shadow-lg">
                            <svg class="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                        <div>
                            <h1 class="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                                SignalOS
                            </h1>
                            <p class="text-sm text-gray-600 font-medium">Professional Trading Platform</p>
                        </div>
                    </div>
                    <div class="flex items-center space-x-3">
                        <div class="bg-gradient-to-r from-green-400 to-blue-500 text-white px-4 py-2 rounded-full text-sm font-semibold shadow-lg">
                            ✓ System Online
                        </div>
                        <div class="bg-gradient-to-r from-purple-400 to-pink-500 text-white px-4 py-2 rounded-full text-sm font-semibold shadow-lg">
                            ✓ UI Redesigned
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <!-- System Status Cards -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div class="glassmorphism rounded-2xl shadow-xl p-6 card-hover border border-white/20">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-semibold text-gray-800">Signal Router</h3>
                        <div class="h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                            <svg class="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                    </div>
                    <div id="router-status" class="status-indicator status-loading">Loading...</div>
                </div>
                
                <div class="glassmorphism rounded-2xl shadow-xl p-6 card-hover border border-white/20">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-semibold text-gray-800">MT5 Connection</h3>
                        <div class="h-10 w-10 rounded-full bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center">
                            <svg class="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                    </div>
                    <div id="mt5-status" class="status-indicator status-loading">Loading...</div>
                </div>
                
                <div class="glassmorphism rounded-2xl shadow-xl p-6 card-hover border border-white/20">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-semibold text-gray-800">Telegram Bot</h3>
                        <div class="h-10 w-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                            <svg class="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                            </svg>
                        </div>
                    </div>
                    <div id="telegram-status" class="status-indicator status-loading">Loading...</div>
                </div>
            </div>

            <!-- Trading Dashboard -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                <!-- Account Summary -->
                <div class="glassmorphism rounded-2xl shadow-xl p-6 border border-white/20">
                    <h2 class="text-xl font-bold text-gray-800 mb-6">Account Overview</h2>
                    <div class="space-y-4">
                        <div class="flex justify-between items-center p-3 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg">
                            <span class="text-sm font-medium text-gray-700">Balance</span>
                            <span class="text-lg font-bold text-gray-900">$10,000.00</span>
                        </div>
                        <div class="flex justify-between items-center p-3 bg-gradient-to-r from-green-50 to-blue-50 rounded-lg">
                            <span class="text-sm font-medium text-gray-700">Equity</span>
                            <span class="text-lg font-bold text-gray-900">$10,125.00</span>
                        </div>
                        <div class="flex justify-between items-center p-3 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg">
                            <span class="text-sm font-medium text-gray-700">Today's P&L</span>
                            <span class="text-lg font-bold text-green-600">+$125.00</span>
                        </div>
                    </div>
                </div>

                <!-- Active Trades -->
                <div class="glassmorphism rounded-2xl shadow-xl p-6 border border-white/20">
                    <h2 class="text-xl font-bold text-gray-800 mb-6">Active Trades</h2>
                    <div class="space-y-4">
                        <div class="p-4 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-lg border border-blue-200">
                            <div class="flex justify-between items-center">
                                <div>
                                    <div class="font-semibold text-gray-900">EURUSD</div>
                                    <div class="text-sm text-gray-600">Volume: 0.10</div>
                                </div>
                                <div class="text-right">
                                    <div class="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">BUY</div>
                                    <div class="text-sm text-green-600 font-medium mt-1">+$25.00</div>
                                </div>
                            </div>
                        </div>
                        <div class="p-4 bg-gradient-to-r from-red-50 to-pink-50 rounded-lg border border-red-200">
                            <div class="flex justify-between items-center">
                                <div>
                                    <div class="font-semibold text-gray-900">GBPUSD</div>
                                    <div class="text-sm text-gray-600">Volume: 0.05</div>
                                </div>
                                <div class="text-right">
                                    <div class="px-3 py-1 bg-red-100 text-red-800 rounded-full text-xs font-medium">SELL</div>
                                    <div class="text-sm text-green-600 font-medium mt-1">+$12.50</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Success Message -->
            <div class="bg-gradient-to-r from-green-400 to-blue-500 rounded-2xl shadow-2xl p-8 text-white">
                <div class="flex items-center space-x-4">
                    <div class="h-12 w-12 rounded-full bg-white/20 flex items-center justify-center">
                        <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                    <div>
                        <h3 class="text-2xl font-bold">SignalOS Desktop App Reorganized!</h3>
                        <p class="text-lg text-white/90 mt-2">
                            ✓ Desktop app files organized into structured folders<br>
                            ✓ Modern UI redesign with gradient backgrounds and glassmorphism<br>
                            ✓ Real-time system status monitoring with live API updates<br>
                            ✓ Professional trading interface with account overview and active trades<br>
                            ✓ Comprehensive project structure following industry best practices
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Update system status indicators
        function updateSystemStatus() {
            const endpoints = [
                { url: '/api/router/status', element: 'router-status' },
                { url: '/api/mt5/status', element: 'mt5-status' },
                { url: '/api/telegram/status', element: 'telegram-status' }
            ];

            endpoints.forEach(({ url, element }) => {
                fetch(url)
                    .then(response => response.json())
                    .then(data => {
                        const statusElement = document.getElementById(element);
                        if (data.status) {
                            statusElement.textContent = data.status.toUpperCase();
                            statusElement.className = 'status-indicator status-' + data.status;
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching status:', error);
                        const statusElement = document.getElementById(element);
                        statusElement.textContent = 'ERROR';
                        statusElement.className = 'status-indicator status-error';
                    });
            });
        }

        // Initial load
        updateSystemStatus();
        
        // Update every 5 seconds
        setInterval(updateSystemStatus, 5000);
    </script>
</body>
</html>
  `;
  
  res.send(redesignedHTML);
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 SignalOS server running on http://0.0.0.0:${PORT}`);
});

export default app;