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

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

// Development mode - serve the enhanced HTML page for now
app.get('*', (req, res) => {
  const htmlPath = path.join(__dirname, '../dist/index.html');
  res.sendFile(htmlPath);
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 SignalOS server running on http://0.0.0.0:${PORT}`);
});

export default app;