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

export default router;