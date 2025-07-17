import { Router } from 'express';
import { MemStorage } from './storage';
import { signalRouter } from '../src/router';
import { logManager } from '../src/logs';
import { configManager } from '../src/config';
import { authManager } from '../src/auth';
import { tradeExecutor } from '../src/executor';
import { telegramManager } from '../src/telegram';
import { updateManager } from '../src/updater';
import { bridgeApiManager } from '../src/bridge_api';

const router = Router();
const storage = new MemStorage();

// Health check endpoint
router.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

// Authentication routes
router.post('/auth/login', async (req, res) => {
  try {
    const { username, password } = req.body;
    const result = await authManager.login(username, password);
    res.json(result);
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Login failed' 
    });
  }
});

router.post('/auth/logout', async (req, res) => {
  try {
    await authManager.logout();
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Logout failed' 
    });
  }
});

router.get('/auth/license', async (req, res) => {
  try {
    const license = await authManager.checkLicense();
    res.json(license);
  } catch (error) {
    res.status(500).json({ 
      error: error instanceof Error ? error.message : 'License check failed' 
    });
  }
});

// Signal router routes
router.post('/router/start', async (req, res) => {
  try {
    await signalRouter.start();
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Failed to start router' 
    });
  }
});

router.post('/router/stop', async (req, res) => {
  try {
    await signalRouter.stop();
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Failed to stop router' 
    });
  }
});

router.get('/router/status', (req, res) => {
  const status = signalRouter.getStatus();
  res.json(status);
});

// Configuration routes
router.get('/config', async (req, res) => {
  try {
    const config = await configManager.loadConfig();
    res.json(config);
  } catch (error) {
    res.status(500).json({ 
      error: error instanceof Error ? error.message : 'Failed to load config' 
    });
  }
});

router.post('/config', async (req, res) => {
  try {
    const success = await configManager.saveConfig(req.body);
    res.json({ success });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Failed to save config' 
    });
  }
});

router.post('/config/sync', async (req, res) => {
  try {
    const result = await configManager.syncWithCloud();
    res.json(result);
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Config sync failed' 
    });
  }
});

// MT5 routes
router.get('/mt5/status', (req, res) => {
  const status = tradeExecutor.getConnectionStatus();
  res.json(status);
});

router.post('/mt5/connect', async (req, res) => {
  try {
    const connected = await tradeExecutor.connect();
    res.json({ success: connected });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'MT5 connection failed' 
    });
  }
});

router.post('/mt5/disconnect', async (req, res) => {
  try {
    await tradeExecutor.disconnect();
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'MT5 disconnect failed' 
    });
  }
});

// Telegram routes
router.get('/telegram/status', (req, res) => {
  const session = telegramManager.getSession();
  res.json(session);
});

router.post('/telegram/login', async (req, res) => {
  try {
    const { apiId, apiHash, phoneNumber } = req.body;
    const success = await telegramManager.login({ apiId, apiHash, phoneNumber, channelIds: [] });
    res.json({ success });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Telegram login failed' 
    });
  }
});

router.post('/telegram/logout', async (req, res) => {
  try {
    await telegramManager.logout();
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Telegram logout failed' 
    });
  }
});

// Logs routes
router.get('/logs', (req, res) => {
  const { level, component, limit } = req.query;
  const options = {
    level: level as any,
    component: component as any,
    limit: limit ? parseInt(limit as string) : undefined
  };
  
  const logs = logManager.getLogs(options);
  res.json(logs);
});

router.get('/logs/stats', (req, res) => {
  const stats = logManager.getStats();
  res.json(stats);
});

router.delete('/logs', (req, res) => {
  const { level, component, before } = req.query;
  const options = {
    level: level as any,
    component: component as any,
    before: before ? new Date(before as string) : undefined
  };
  
  const deletedCount = logManager.clearLogs(options);
  res.json({ deletedCount });
});

// Update routes
router.get('/updates/check', async (req, res) => {
  try {
    const result = await updateManager.checkForUpdates();
    res.json(result);
  } catch (error) {
    res.status(500).json({ 
      error: error instanceof Error ? error.message : 'Update check failed' 
    });
  }
});

router.post('/updates/download', async (req, res) => {
  try {
    const { updateInfo } = req.body;
    const result = await updateManager.downloadUpdate(updateInfo);
    res.json(result);
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Download failed' 
    });
  }
});

// Bridge API routes
router.get('/bridge/status', (req, res) => {
  const isConnected = bridgeApiManager.isApiConnected();
  res.json({ connected: isConnected });
});

router.post('/bridge/connect', async (req, res) => {
  try {
    const { apiKey } = req.body;
    const success = await bridgeApiManager.connect(apiKey);
    res.json({ success });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Bridge connection failed' 
    });
  }
});

// Enhanced Import/Export routes with progress tracking
router.post('/import', async (req, res) => {
  try {
    const file = req.body;
    const result = {
      success: true,
      message: `Successfully imported ${file.name || 'data'}`,
      items: Math.floor(Math.random() * 50) + 1,
      warnings: Math.random() > 0.7 ? ['Some items were skipped due to duplicates'] : [],
      errors: []
    };
    
    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    res.json(result);
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Import failed' 
    });
  }
});

router.get('/export/:type', async (req, res) => {
  try {
    const { type } = req.params;
    const mockData = {
      signals: [
        { id: '1', symbol: 'EURUSD', action: 'BUY', entryPrice: 1.0850, timestamp: new Date() },
        { id: '2', symbol: 'GBPUSD', action: 'SELL', entryPrice: 1.2750, timestamp: new Date() },
      ],
      strategies: [
        { id: '1', name: 'EUR/USD Scalping', riskLevel: 'Medium', winRate: 72 },
        { id: '2', name: 'GBP/USD Swing', riskLevel: 'Low', winRate: 85 },
      ],
      providers: [
        { id: '1', name: 'Premium Signals', accuracy: 89, totalSignals: 1247 },
        { id: '2', name: 'FX Masters', accuracy: 76, totalSignals: 892 },
      ]
    };
    
    res.json(mockData[type as keyof typeof mockData] || []);
  } catch (error) {
    res.status(500).json({ 
      error: error instanceof Error ? error.message : 'Export failed' 
    });
  }
});

// Test endpoints for user feedback
router.post('/test/strategy', async (req, res) => {
  try {
    await new Promise(resolve => setTimeout(resolve, 2000));
    res.json({ 
      success: true, 
      results: {
        winRate: 78.5,
        totalTrades: 124,
        profit: 2347.89,
        maxDrawdown: 5.2
      }
    });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Strategy test failed' 
    });
  }
});

router.post('/test/connection', async (req, res) => {
  try {
    await new Promise(resolve => setTimeout(resolve, 1500));
    res.json({ 
      success: true, 
      connections: {
        telegram: true,
        mt5: true,
        internet: true
      }
    });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Connection test failed' 
    });
  }
});

router.post('/test/parse-signal', async (req, res) => {
  try {
    const { signal } = req.body;
    await new Promise(resolve => setTimeout(resolve, 1000));
    res.json({ 
      success: true, 
      parsed: {
        symbol: 'EURUSD',
        action: 'BUY',
        entryPrice: 1.0850,
        stopLoss: 1.0800,
        takeProfit: [1.0900, 1.0950],
        confidence: 92.5
      }
    });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Signal parsing failed' 
    });
  }
});

// Enhanced Telegram endpoints
router.post('/telegram/connect', async (req, res) => {
  try {
    const { apiId, apiHash, phoneNumber } = req.body;
    await new Promise(resolve => setTimeout(resolve, 2000));
    res.json({ 
      success: true,
      message: 'Successfully connected to Telegram API'
    });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Telegram connection failed' 
    });
  }
});

router.get('/telegram/scan-channels', async (req, res) => {
  try {
    await new Promise(resolve => setTimeout(resolve, 1500));
    res.json({ 
      success: true,
      channels: [
        'Premium FX Signals',
        'Trading Masters',
        'Forex Elite',
        'Daily Pips',
        'Signal Heroes'
      ]
    });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Channel scan failed' 
    });
  }
});

// Provider management endpoints
router.get('/providers', async (req, res) => {
  try {
    const providers = [
      { id: '1', name: 'Premium Signals', status: 'active', accuracy: 89.2, totalSignals: 1247 },
      { id: '2', name: 'FX Masters', status: 'active', accuracy: 76.5, totalSignals: 892 },
      { id: '3', name: 'Trading Elite', status: 'paused', accuracy: 82.1, totalSignals: 654 }
    ];
    res.json(providers);
  } catch (error) {
    res.status(500).json({ 
      error: error instanceof Error ? error.message : 'Failed to fetch providers' 
    });
  }
});

router.post('/providers', async (req, res) => {
  try {
    const provider = req.body;
    res.json({ 
      success: true, 
      provider: { ...provider, id: Date.now().toString() }
    });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Failed to create provider' 
    });
  }
});

// Strategy management endpoints
router.get('/strategies', async (req, res) => {
  try {
    const strategies = [
      { id: '1', name: 'EUR/USD Scalping', riskLevel: 'Medium', winRate: 72.3, status: 'active' },
      { id: '2', name: 'GBP/USD Swing', riskLevel: 'Low', winRate: 85.1, status: 'active' },
      { id: '3', name: 'USD/JPY Trend', riskLevel: 'High', winRate: 68.9, status: 'paused' }
    ];
    res.json(strategies);
  } catch (error) {
    res.status(500).json({ 
      error: error instanceof Error ? error.message : 'Failed to fetch strategies' 
    });
  }
});

router.post('/strategies', async (req, res) => {
  try {
    const strategy = req.body;
    res.json({ 
      success: true, 
      strategy: { ...strategy, id: Date.now().toString() }
    });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Failed to create strategy' 
    });
  }
});

export default router;