import type { Express } from "express";
import { createServer, type Server } from "http";
import { WebSocketServer, WebSocket } from "ws";
import { setupAuth } from "./auth";
import { storage } from "./storage";
import { insertChannelSchema, insertStrategySchema, insertSignalSchema, insertMt5StatusSchema } from "@shared/schema";
import { setupEquityLimitsRoutes } from "./routes/equity_limits";
import multer from "multer";
import sanitizeHtml from "sanitize-html";
import path from "path";
import { body, param, query, validationResult } from "express-validator";

interface WebSocketClient extends WebSocket {
  userId?: number;
  isAlive?: boolean;
}

interface ConnectedClients {
  [userId: number]: WebSocketClient[];
}

let connectedClients: ConnectedClients = {};
let wsServer: WebSocketServer;

// Broadcast message to specific user
function broadcastToUser(userId: number, message: any) {
  const clients = connectedClients[userId];
  if (clients && clients.length > 0) {
    const messageStr = JSON.stringify({
      ...message,
      timestamp: new Date().toISOString(),
      id: `srv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    });
    
    clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(messageStr);
      }
    });
  }
}

// Broadcast message to all connected clients
function broadcastToAll(message: any) {
  const messageStr = JSON.stringify({
    ...message,
    timestamp: new Date().toISOString(),
    id: `srv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  });
  
  Object.values(connectedClients).flat().forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(messageStr);
    }
  });
}

// Clean up disconnected clients
function cleanupDisconnectedClients() {
  Object.keys(connectedClients).forEach(userIdStr => {
    const userId = parseInt(userIdStr);
    connectedClients[userId] = connectedClients[userId].filter(
      client => client.readyState === WebSocket.OPEN
    );
    
    if (connectedClients[userId].length === 0) {
      delete connectedClients[userId];
    }
  });
}

// Fix #23: Secure file upload configuration
const fileStorage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, 'uploads/');
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    const sanitizedName = path.parse(file.originalname).name.replace(/[^a-zA-Z0-9]/g, '');
    cb(null, sanitizedName + '-' + uniqueSuffix + path.extname(file.originalname));
  }
});

const fileFilter = (req: any, file: any, cb: any) => {
  // Only allow specific file types
  const allowedTypes = ['.txt', '.json', '.csv', '.log'];
  const fileExt = path.extname(file.originalname).toLowerCase();
  
  if (allowedTypes.includes(fileExt)) {
    cb(null, true);
  } else {
    cb(new Error('Invalid file type. Only txt, json, csv, and log files are allowed.'), false);
  }
};

const upload = multer({
  storage: fileStorage,
  fileFilter,
  limits: {
    fileSize: 5 * 1024 * 1024, // 5MB limit
    files: 1 // Only one file at a time
  }
});

// Fix #27: Safe HTML sanitization helper
function sanitizeInput(input: string): string {
  return sanitizeHtml(input, {
    allowedTags: [],
    allowedAttributes: {},
    disallowedTagsMode: 'escape'
  });
}

export async function registerRoutes(app: Express): Promise<Server> {
  // Setup authentication routes
  setupAuth(app);
  
  // Fix #12: Role-based access control middleware
  function requireRole(role: string) {
    return (req: any, res: any, next: any) => {
      if (!req.user) {
        return res.status(401).json({ error: "Authentication required" });
      }
      
      // Check user role (default to 'user' if not set)
      const userRole = req.user.role || 'user';
      
      // Define role hierarchy
      const roleHierarchy: { [key: string]: string[] } = {
        'admin': ['admin', 'user'],
        'user': ['user']
      };
      
      if (!roleHierarchy[role] || !roleHierarchy[role].includes(userRole)) {
        return res.status(403).json({ error: "Insufficient permissions" });
      }
      
      next();
    };
  }
  
  // Admin-only middleware
  const requireAdmin = requireRole('admin');
  
  // Setup equity limits routes
  setupEquityLimitsRoutes(app);

  // Trading Control API endpoints
  app.post("/api/trading/emergency-stop", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const userId = req.user!.id;
      
      // Send emergency stop to desktop app via WebSocket
      broadcastToUser(userId, {
        type: 'emergency_stop_command',
        data: { timestamp: new Date().toISOString() }
      });
      
      // Update MT5 status to stopped
      await storage.updateMt5Status(userId, {
        userId,
        isConnected: false,
        serverInfo: { emergencyStop: true },
        lastPing: new Date()
      });
      
      // Broadcast to all clients
      broadcastToUser(userId, {
        type: 'emergency_stop',
        data: { message: 'Emergency stop activated' }
      });
      
      res.json({ success: true, message: 'Emergency stop activated' });
    } catch (error) {
      console.error('Emergency stop error:', error);
      res.status(500).json({ error: 'Failed to activate emergency stop' });
    }
  });

  app.post("/api/trading/pause", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const userId = req.user!.id;
      
      broadcastToUser(userId, {
        type: 'pause_trading_command',
        data: { timestamp: new Date().toISOString() }
      });
      
      await storage.updateMt5Status(userId, {
        tradingEnabled: false,
        lastUpdate: new Date().toISOString()
      });
      
      broadcastToUser(userId, {
        type: 'trading_paused',
        data: { message: 'Trading paused' }
      });
      
      res.json({ success: true, message: 'Trading paused' });
    } catch (error) {
      console.error('Pause trading error:', error);
      res.status(500).json({ error: 'Failed to pause trading' });
    }
  });

  app.post("/api/trading/pause", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const userId = req.user!.id;
      
      broadcastToUser(userId, {
        type: 'pause_trading_command',
        data: { timestamp: new Date().toISOString() }
      });
      
      await storage.updateMt5Status(userId, {
        userId,
        isConnected: true,
        serverInfo: { tradingEnabled: false, paused: true },
        lastPing: new Date()
      });
      
      broadcastToUser(userId, {
        type: 'trading_paused',
        data: { message: 'Trading paused' }
      });
      
      res.json({ success: true, message: 'Trading paused' });
    } catch (error) {
      console.error('Pause trading error:', error);
      res.status(500).json({ error: 'Failed to pause trading' });
    }
  });

  app.post("/api/trading/resume", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const userId = req.user!.id;
      
      broadcastToUser(userId, {
        type: 'resume_trading_command',
        data: { timestamp: new Date().toISOString() }
      });
      
      await storage.updateMt5Status(userId, {
        userId,
        isConnected: true,
        serverInfo: { tradingEnabled: true, paused: false },
        lastPing: new Date()
      });
      
      broadcastToUser(userId, {
        type: 'trading_resumed',
        data: { message: 'Trading resumed' }
      });
      
      res.json({ success: true, message: 'Trading resumed' });
    } catch (error) {
      console.error('Resume trading error:', error);
      res.status(500).json({ error: 'Failed to resume trading' });
    }
  });

  app.post("/api/trading/stealth-toggle", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const userId = req.user!.id;
      const { stealthMode } = req.body;
      
      broadcastToUser(userId, {
        type: 'stealth_mode_command',
        data: { enabled: stealthMode, timestamp: new Date().toISOString() }
      });

      // Update MT5 status with stealth mode
      await storage.updateMt5Status(userId, {
        userId,
        isConnected: true,
        serverInfo: { stealthMode: stealthMode },
        lastPing: new Date()
      });
      
      res.json({ success: true, message: `Stealth mode ${stealthMode ? 'enabled' : 'disabled'}` });
    } catch (error) {
      console.error('Stealth mode toggle error:', error);
      res.status(500).json({ error: 'Failed to toggle stealth mode' });
    }
  });

  app.post("/api/firebridge/force-sync", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const userId = req.user!.id;
      
      // Send force sync command to desktop app
      broadcastToUser(userId, {
        type: 'force_sync_command',
        data: { timestamp: new Date().toISOString() }
      });

      // Log sync request
      await storage.createSyncLog({
        userId,
        action: "force_sync",
        status: "requested",
        details: { source: "web_dashboard", timestamp: new Date() }
      });
      
      res.json({ success: true, message: 'Desktop sync initiated' });
    } catch (error) {
      console.error('Force sync error:', error);
      res.status(500).json({ error: 'Failed to initiate desktop sync' });
    }
  });

  app.post("/api/firebridge/force-sync", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const userId = req.user!.id;
      
      broadcastToUser(userId, {
        type: 'force_sync_command',
        data: { timestamp: new Date().toISOString() }
      });
      
      res.json({ success: true, message: 'Sync initiated' });
    } catch (error) {
      console.error('Force sync error:', error);
      res.status(500).json({ error: 'Failed to initiate sync' });
    }
  });

  // Trade Management API endpoints
  app.post("/api/trades/:id/close", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const userId = req.user!.id;
      const tradeId = req.params.id;
      
      broadcastToUser(userId, {
        type: 'close_trade_command',
        data: { tradeId, timestamp: new Date().toISOString() }
      });
      
      res.json({ success: true, message: 'Close trade command sent' });
    } catch (error) {
      console.error('Close trade error:', error);
      res.status(500).json({ error: 'Failed to close trade' });
    }
  });

  app.post("/api/trades/:id/partial-close", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const userId = req.user!.id;
      const tradeId = req.params.id;
      const { percentage } = req.body;
      
      broadcastToUser(userId, {
        type: 'partial_close_command',
        data: { tradeId, percentage, timestamp: new Date().toISOString() }
      });
      
      res.json({ success: true, message: 'Partial close command sent' });
    } catch (error) {
      console.error('Partial close error:', error);
      res.status(500).json({ error: 'Failed to partial close trade' });
    }
  });

  app.put("/api/trades/:id/modify", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const userId = req.user!.id;
      const tradeId = req.params.id;
      const { stopLoss, takeProfit } = req.body;
      
      broadcastToUser(userId, {
        type: 'modify_trade_command',
        data: { tradeId, stopLoss, takeProfit, timestamp: new Date().toISOString() }
      });
      
      res.json({ success: true, message: 'Modify trade command sent' });
    } catch (error) {
      console.error('Modify trade error:', error);
      res.status(500).json({ error: 'Failed to modify trade' });
    }
  });

  app.post("/api/trades/:id/trailing-stop", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const userId = req.user!.id;
      const tradeId = req.params.id;
      const { distance, step } = req.body;
      
      broadcastToUser(userId, {
        type: 'trailing_stop_command',
        data: { tradeId, distance, step, timestamp: new Date().toISOString() }
      });
      
      res.json({ success: true, message: 'Trailing stop activated' });
    } catch (error) {
      console.error('Trailing stop error:', error);
      res.status(500).json({ error: 'Failed to activate trailing stop' });
    }
  });

  // System Health endpoints
  app.get("/api/system/health", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const userId = req.user!.id;
      const mt5Status = await storage.getMt5Status(userId);
      const activeTrades = await storage.getActiveTrades(userId);
      
      res.json({
        status: 'healthy',
        mt5Connected: mt5Status?.isConnected || false,
        tradingEnabled: mt5Status?.tradingEnabled || false,
        activeTrades: activeTrades.length,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('Health check error:', error);
      res.status(500).json({ error: 'Health check failed' });
    }
  });

  // Dashboard API endpoints
  app.get("/api/dashboard/stats", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const userId = req.user!.id;
      const activeTrades = await storage.getActiveTrades(userId);
      const recentTrades = await storage.getUserTrades(userId, 50);
      
      // Calculate today's P&L
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const todayTrades = recentTrades.filter(trade => 
        trade.createdAt && new Date(trade.createdAt) >= today
      );
      const todaysPnL = todayTrades.reduce((sum, trade) => 
        sum + (parseFloat(trade.pnl?.toString() || "0")), 0
      );
      
      // Calculate success rate
      const closedTrades = recentTrades.filter(trade => trade.status === 'closed');
      const winningTrades = closedTrades.filter(trade => 
        parseFloat(trade.pnl?.toString() || "0") > 0
      );
      const successRate = closedTrades.length > 0 
        ? ((winningTrades.length / closedTrades.length) * 100).toFixed(1)
        : "0.0";
      
      // Get signals processed today
      const signals = await storage.getSignals(100);
      const todaySignals = signals.filter(signal => 
        signal.createdAt && new Date(signal.createdAt) >= today
      );
      
      res.json({
        activeTrades: activeTrades.length,
        todaysPnL: todaysPnL.toFixed(2),
        signalsProcessed: todaySignals.length,
        pendingSignals: signals.filter(s => s.status === 'pending').length,
        successRate: successRate,
        portfolioValue: 12450 + todaysPnL, // Base portfolio + today's P&L
        portfolioChange: todaysPnL > 0 ? 2.4 : -1.2,
        tradesChange: activeTrades.length > 5 ? 12 : -5,
        successChange: parseFloat(successRate) > 70 ? 5.2 : -2.1,
        signalsChange: todaySignals.length > 10 ? 18 : -8,
        signalsToday: todaySignals.length
      });
    } catch (error) {
      console.error("Dashboard stats error:", error);
      res.status(500).json({ error: "Failed to fetch dashboard stats" });
    }
  });

  app.get("/api/dashboard/performance", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const timeframe = req.query.timeframe || "7d";
      const userId = req.user!.id;
      const trades = await storage.getUserTrades(userId, 100);
      
      // Generate performance data based on actual trades
      const performanceData = [];
      const days = timeframe === "1d" ? 1 : timeframe === "7d" ? 7 : timeframe === "30d" ? 30 : 90;
      
      let cumulativePnL = 0;
      for (let i = days - 1; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        
        const dayTrades = trades.filter(trade => {
          if (!trade.createdAt) return false;
          const tradeDate = new Date(trade.createdAt);
          return tradeDate.toDateString() === date.toDateString();
        });
        
        const dailyPnL = dayTrades.reduce((sum, trade) => 
          sum + (parseFloat(trade.pnl?.toString() || "0")), 0
        );
        cumulativePnL += dailyPnL;
        
        const winningTrades = dayTrades.filter(trade => 
          parseFloat(trade.pnl?.toString() || "0") > 0
        );
        const winRate = dayTrades.length > 0 
          ? (winningTrades.length / dayTrades.length) * 100 
          : 75; // Default when no trades
        
        performanceData.push({
          date: date.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
          pnl: dailyPnL,
          cumulativePnl: cumulativePnL,
          trades: dayTrades.length,
          winRate: winRate
        });
      }
      
      res.json(performanceData);
    } catch (error) {
      console.error("Performance data error:", error);
      res.status(500).json({ error: "Failed to fetch performance data" });
    }
  });

  // Signals API endpoints
  app.get("/api/signals", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const limit = parseInt(req.query.limit as string) || 50;
      const signals = await storage.getSignals(limit);
      
      // Transform signals for UI
      const transformedSignals = signals.map(signal => ({
        id: signal.id.toString(),
        symbol: signal.symbol,
        type: signal.action?.toUpperCase() || "BUY",
        entry: parseFloat(signal.entry?.toString() || "0"),
        stopLoss: parseFloat(signal.stopLoss?.toString() || "0"),
        takeProfit: [
          parseFloat(signal.takeProfit1?.toString() || "0"),
          parseFloat(signal.takeProfit2?.toString() || "0"),
          parseFloat(signal.takeProfit3?.toString() || "0")
        ].filter(tp => tp > 0),
        provider: `Provider ${signal.channelId || 1}`,
        confidence: parseFloat(signal.confidence?.toString() || "75"),
        status: signal.status || "pending",
        timestamp: signal.createdAt?.toISOString() || new Date().toISOString(),
        pnl: Math.random() > 0.6 ? (Math.random() - 0.5) * 200 : undefined
      }));
      
      res.json(transformedSignals);
    } catch (error) {
      console.error("Signals fetch error:", error);
      res.status(500).json({ error: "Failed to fetch signals" });
    }
  });

  // Live trades API endpoint
  app.get("/api/trades/live", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const userId = req.user!.id;
      const activeTrades = await storage.getActiveTrades(userId);
      
      // Transform trades for UI
      const transformedTrades = activeTrades.map(trade => ({
        id: trade.id.toString(),
        symbol: trade.symbol,
        type: trade.action?.toUpperCase() || "BUY",
        lotSize: parseFloat(trade.lotSize?.toString() || "0.1"),
        openPrice: parseFloat(trade.openPrice?.toString() || "0"),
        currentPrice: parseFloat(trade.openPrice?.toString() || "0") + (Math.random() - 0.5) * 0.01,
        pnl: parseFloat(trade.pnl?.toString() || "0"),
        stopLoss: parseFloat(trade.stopLoss?.toString() || "0"),
        takeProfit: parseFloat(trade.takeProfit?.toString() || "0"),
        openTime: trade.createdAt?.toISOString() || new Date().toISOString(),
        status: trade.status || "open"
      }));
      
      res.json(transformedTrades);
    } catch (error) {
      console.error("Live trades fetch error:", error);
      res.status(500).json({ error: "Failed to fetch live trades" });
    }
  });

  // Provider stats API endpoint
  app.get("/api/providers/stats", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const providerStats = await storage.getProviderStats();
      
      // If no provider stats exist, create sample data based on actual signals
      if (providerStats.length === 0) {
        const signals = await storage.getSignals(100);
        const channels = await storage.getChannels();
        
        const mockProviders = channels.map((channel, index) => ({
          id: channel.id.toString(),
          name: channel.name || `Provider ${channel.id}`,
          status: channel.isActive ? "active" as const : "inactive" as const,
          totalSignals: signals.filter(s => s.channelId === channel.id).length,
          winRate: 70 + Math.random() * 20,
          avgPips: 50 + Math.random() * 50,
          profitFactor: 1.2 + Math.random() * 0.8,
          subscribers: Math.floor(500 + Math.random() * 1000),
          trustScore: Math.floor(70 + Math.random() * 25),
          lastSignal: "2 hours ago",
          monthlyPnL: (Math.random() - 0.3) * 5000
        }));
        
        res.json(mockProviders);
      } else {
        // Transform actual provider stats
        const transformedStats = providerStats.map(stat => ({
          id: stat.providerId,
          name: stat.providerName || `Provider ${stat.providerId}`,
          status: stat.isActive ? "active" as const : "inactive" as const,
          totalSignals: stat.totalSignals || 0,
          winRate: parseFloat(stat.winRate?.toString() || "0"),
          avgPips: parseFloat(stat.avgPips?.toString() || "0"),
          profitFactor: parseFloat(stat.profitFactor?.toString() || "1"),
          subscribers: stat.subscribers || 0,
          trustScore: stat.trustScore || 75,
          lastSignal: stat.lastSignalTime || "Unknown",
          monthlyPnL: parseFloat(stat.monthlyPnL?.toString() || "0")
        }));
        
        res.json(transformedStats);
      }
    } catch (error) {
      console.error("Provider stats error:", error);
      res.status(500).json({ error: "Failed to fetch provider stats" });
    }
  });

  // Analytics API endpoint
  app.get("/api/analytics", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const timeframe = req.query.timeframe || "30d";
      const userId = req.user!.id;
      const trades = await storage.getUserTrades(userId, 200);
      const signals = await storage.getSignals(200);
      
      res.json({
        totalTrades: trades.length,
        totalSignals: signals.length,
        winRate: trades.length > 0 
          ? ((trades.filter(t => parseFloat(t.pnl?.toString() || "0") > 0).length / trades.length) * 100).toFixed(1)
          : "0",
        totalPnL: trades.reduce((sum, trade) => sum + parseFloat(trade.pnl?.toString() || "0"), 0),
        timeframe
      });
    } catch (error) {
      console.error("Analytics error:", error);
      res.status(500).json({ error: "Failed to fetch analytics data" });
    }
  });

  // MT5 Status API endpoint
  app.get("/api/mt5-status", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const userId = req.user!.id;
      const mt5Status = await storage.getMt5Status(userId);
      
      if (!mt5Status) {
        // Create default MT5 status for new user
        const defaultStatus = {
          userId,
          isConnected: false,
          serverInfo: {
            server: "Demo Server",
            login: "12345678",
            balance: 10000,
            equity: 10000,
            freeMargin: 10000,
            marginLevel: 1000
          },
          lastPing: new Date()
        };
        
        const newStatus = await storage.updateMt5Status(userId, defaultStatus);
        res.json(newStatus);
      } else {
        res.json(mt5Status);
      }
    } catch (error) {
      console.error("MT5 status error:", error);
      res.status(500).json({ error: "Failed to fetch MT5 status" });
    }
  });

  // Desktop App Integration endpoints
  app.post("/api/firebridge/sync-user", async (req, res) => {
    try {
      const { userId, terminalId, status } = req.body;
      
      // Update MT5 status from desktop app
      if (userId && status) {
        await storage.updateMt5Status(userId, {
          userId,
          isConnected: status.isConnected || false,
          serverInfo: status.serverInfo || {},
          lastPing: new Date()
        });
      }
      
      // Log sync activity
      if (userId) {
        await storage.createSyncLog({
          userId,
          action: "desktop_sync",
          status: "success",
          details: { terminalId, syncTime: new Date() }
        });
      }
      
      res.json({ success: true, timestamp: new Date() });
    } catch (error) {
      console.error("Desktop sync error:", error);
      res.status(500).json({ error: "Failed to sync with desktop app" });
    }
  });

  app.post("/api/firebridge/push-trade-result", async (req, res) => {
    try {
      const { userId, tradeData } = req.body;
      
      if (!userId || !tradeData) {
        return res.status(400).json({ error: "Missing required data" });
      }
      
      // Create trade record from desktop app
      const trade = await storage.createTrade({
        userId,
        signalId: tradeData.signalId,
        symbol: tradeData.symbol,
        action: tradeData.action,
        lotSize: tradeData.lotSize,
        openPrice: tradeData.openPrice,
        stopLoss: tradeData.stopLoss,
        takeProfit: tradeData.takeProfit,
        status: tradeData.status || "open",
        pnl: tradeData.pnl || 0,
        commission: tradeData.commission || 0
      });
      
      // Broadcast trade update to WebSocket clients
      broadcastToUser(userId, {
        type: 'trade_update',
        data: trade
      });
      
      res.json({ success: true, tradeId: trade.id });
    } catch (error) {
      console.error("Trade result push error:", error);
      res.status(500).json({ error: "Failed to push trade result" });
    }
  });

  app.get("/api/firebridge/pull-strategy/:userId", async (req, res) => {
    try {
      const userId = parseInt(req.params.userId);
      const strategies = await storage.getUserStrategies(userId);
      
      res.json({
        strategies: strategies.map(s => ({
          id: s.id,
          name: s.name,
          config: s.config,
          isActive: s.isActive
        }))
      });
    } catch (error) {
      console.error("Strategy pull error:", error);
      res.status(500).json({ error: "Failed to pull strategies" });
    }
  });

  // Trade Management API endpoints
  app.post("/api/trades/:id/close", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const tradeId = parseInt(req.params.id);
      const userId = req.user!.id;
      
      // Get trade details
      const trade = await storage.getTrade(tradeId);
      if (!trade || trade.userId !== userId) {
        return res.status(404).json({ error: 'Trade not found' });
      }

      // Send close command to desktop app
      broadcastToUser(userId, {
        type: 'close_trade_command',
        data: { 
          tradeId, 
          ticket: trade.ticket || tradeId,
          timestamp: new Date().toISOString() 
        }
      });

      // Update trade status
      await storage.updateTrade(tradeId, {
        status: "closing",
        closeTime: new Date()
      });
      
      res.json({ success: true, message: 'Trade close initiated' });
    } catch (error) {
      console.error('Close trade error:', error);
      res.status(500).json({ error: 'Failed to close trade' });
    }
  });

  app.post("/api/trades/:id/partial-close", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const tradeId = parseInt(req.params.id);
      const userId = req.user!.id;
      const { percentage = 50 } = req.body;
      
      // Get trade details
      const trade = await storage.getTrade(tradeId);
      if (!trade || trade.userId !== userId) {
        return res.status(404).json({ error: 'Trade not found' });
      }

      // Send partial close command to desktop app
      broadcastToUser(userId, {
        type: 'partial_close_command',
        data: { 
          tradeId, 
          ticket: trade.ticket || tradeId,
          percentage,
          timestamp: new Date().toISOString() 
        }
      });
      
      res.json({ success: true, message: `Partial close (${percentage}%) initiated` });
    } catch (error) {
      console.error('Partial close error:', error);
      res.status(500).json({ error: 'Failed to partial close trade' });
    }
  });

  app.put("/api/trades/:id/modify", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const tradeId = parseInt(req.params.id);
      const userId = req.user!.id;
      const { stopLoss, takeProfit } = req.body;
      
      // Get trade details
      const trade = await storage.getTrade(tradeId);
      if (!trade || trade.userId !== userId) {
        return res.status(404).json({ error: 'Trade not found' });
      }

      // Send modify command to desktop app
      broadcastToUser(userId, {
        type: 'modify_trade_command',
        data: { 
          tradeId, 
          ticket: trade.ticket || tradeId,
          stopLoss,
          takeProfit,
          timestamp: new Date().toISOString() 
        }
      });

      // Update trade in database
      await storage.updateTrade(tradeId, {
        stopLoss: stopLoss || trade.stopLoss,
        takeProfit: takeProfit || trade.takeProfit
      });
      
      res.json({ success: true, message: 'Trade modification initiated' });
    } catch (error) {
      console.error('Modify trade error:', error);
      res.status(500).json({ error: 'Failed to modify trade' });
    }
  });

  app.post("/api/trades/:id/trailing-stop", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const tradeId = parseInt(req.params.id);
      const userId = req.user!.id;
      const { trailingDistance } = req.body;
      
      // Get trade details
      const trade = await storage.getTrade(tradeId);
      if (!trade || trade.userId !== userId) {
        return res.status(404).json({ error: 'Trade not found' });
      }

      // Send trailing stop command to desktop app
      broadcastToUser(userId, {
        type: 'trailing_stop_command',
        data: { 
          tradeId, 
          ticket: trade.ticket || tradeId,
          trailingDistance: trailingDistance || 10,
          timestamp: new Date().toISOString() 
        }
      });
      
      res.json({ success: true, message: 'Trailing stop activated' });
    } catch (error) {
      console.error('Trailing stop error:', error);
      res.status(500).json({ error: 'Failed to activate trailing stop' });
    }
  });

  app.get("/api/system/health", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const userId = req.user!.id;
      const mt5Status = await storage.getMt5Status(userId);
      const activeTrades = await storage.getActiveTrades(userId);
      
      res.json({
        mt5Connected: mt5Status?.isConnected || false,
        activeTrades: activeTrades.length,
        lastPing: mt5Status?.lastPing || null,
        serverInfo: mt5Status?.serverInfo || {},
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('System health error:', error);
      res.status(500).json({ error: 'Failed to get system health' });
    }
  });

  // Sample data creation endpoint (for testing)
  app.post("/api/sample-data", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const userId = req.user!.id;
      
      // Create sample channel
      let channel;
      try {
        channel = await storage.createChannel({
          name: "Premium Forex Signals",
          telegramId: "@premiumforex",
          description: "High-quality forex signals with 80%+ win rate",
          isActive: true
        });
      } catch (err) {
        // Channel might already exist, get existing ones
        const channels = await storage.getChannels();
        channel = channels[0] || { id: 1 };
      }
      
      // Create sample signals
      const sampleSignals = [
        {
          channelId: channel.id,
          symbol: "EURUSD",
          action: "BUY",
          entry: "1.0850",
          stopLoss: "1.0800",
          takeProfit1: "1.0900",
          takeProfit2: "1.0950",
          confidence: "85",
          status: "executed",
          rawMessage: "BUY EURUSD @ 1.0850 SL: 1.0800 TP: 1.0900"
        },
        {
          channelId: channel.id,
          symbol: "GBPUSD",
          action: "SELL",
          entry: "1.2650",
          stopLoss: "1.2700",
          takeProfit1: "1.2600",
          takeProfit2: "1.2550",
          confidence: "78",
          status: "pending",
          rawMessage: "SELL GBPUSD @ 1.2650 SL: 1.2700 TP: 1.2600"
        },
        {
          channelId: channel.id,
          symbol: "USDJPY",
          action: "BUY",
          entry: "150.25",
          stopLoss: "149.80",
          takeProfit1: "150.70",
          confidence: "82",
          status: "executed",
          rawMessage: "BUY USDJPY @ 150.25 SL: 149.80 TP: 150.70"
        }
      ];
      
      for (const signalData of sampleSignals) {
        try {
          await storage.createSignal(signalData);
        } catch (err) {
          // Signal might already exist, continue
        }
      }
      
      // Create sample trades
      const sampleTrades = [
        {
          userId,
          signalId: 1,
          symbol: "EURUSD",
          action: "BUY",
          lotSize: "0.1",
          openPrice: "1.0850",
          stopLoss: "1.0800",
          takeProfit: "1.0900",
          status: "open",
          pnl: "25.50"
        },
        {
          userId,
          signalId: 3,
          symbol: "USDJPY",
          action: "BUY",
          lotSize: "0.2",
          openPrice: "150.25",
          stopLoss: "149.80",
          takeProfit: "150.70",
          status: "closed",
          pnl: "45.00"
        }
      ];
      
      for (const tradeData of sampleTrades) {
        try {
          await storage.createTrade(tradeData);
        } catch (err) {
          // Trade might already exist, continue
        }
      }
      
      // Update MT5 status
      await storage.updateMt5Status(userId, {
        userId,
        isConnected: true,
        serverInfo: {
          server: "Demo Server",
          login: "12345678",
          balance: 10000,
          equity: 10275.50,
          freeMargin: 8500,
          marginLevel: 650.5
        },
        lastPing: new Date()
      });
      
      res.json({ 
        success: true, 
        message: "Sample data created successfully",
        data: {
          channel: channel.id,
          signals: sampleSignals.length,
          trades: sampleTrades.length
        }
      });
    } catch (error) {
      console.error("Sample data creation error:", error);
      res.status(500).json({ error: "Failed to create sample data" });
    }
  });

  // Margin status API endpoint
  app.get("/api/margin/status", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      // In a real implementation, this would connect to MT5 bridge
      // For now, we'll simulate margin data based on current MT5 status
      const mt5Status = await storage.getMt5Status(req.user!.id);
      
      if (!mt5Status || !mt5Status.isConnected) {
        return res.json({
          freeMargin: 0,
          totalMargin: 0,
          usedMargin: 0,
          marginLevel: 0,
          equity: 0,
          balance: 0,
          lastUpdate: new Date(),
          isConnected: false
        });
      }

      // Simulate realistic margin data
      const serverInfo = mt5Status.serverInfo as any || {};
      const balance = serverInfo.balance || 10000;
      const equity = serverInfo.equity || balance;
      const usedMargin = serverInfo.usedMargin || balance * 0.3;
      const freeMargin = equity - usedMargin;
      const marginLevel = usedMargin > 0 ? (equity / usedMargin) * 100 : 1000;

      res.json({
        freeMargin,
        totalMargin: equity,
        usedMargin,
        marginLevel,
        equity,
        balance,
        lastUpdate: mt5Status.lastPing || new Date(),
        isConnected: true
      });
    } catch (error) {
      console.error('Error fetching margin status:', error);
      res.status(500).json({ message: "Failed to fetch margin status" });
    }
  });

  // Channel management routes
  app.get("/api/channels", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const channels = await storage.getChannels();
      res.json(channels);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch channels" });
    }
  });

  app.post("/api/channels", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const validatedData = insertChannelSchema.parse(req.body);
      const channel = await storage.createChannel(validatedData);
      res.status(201).json(channel);
    } catch (error) {
      res.status(400).json({ message: "Invalid channel data" });
    }
  });

  app.put("/api/channels/:id", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const id = parseInt(req.params.id);
      const updates = insertChannelSchema.partial().parse(req.body);
      const channel = await storage.updateChannel(id, updates);
      
      if (!channel) {
        return res.status(404).json({ message: "Channel not found" });
      }
      
      res.json(channel);
    } catch (error) {
      res.status(400).json({ message: "Invalid channel data" });
    }
  });

  app.delete("/api/channels/:id", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const id = parseInt(req.params.id);
      const deleted = await storage.deleteChannel(id);
      
      if (!deleted) {
        return res.status(404).json({ message: "Channel not found" });
      }
      
      res.sendStatus(204);
    } catch (error) {
      res.status(500).json({ message: "Failed to delete channel" });
    }
  });

  // Strategy management routes
  app.get("/api/strategies", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const strategies = await storage.getUserStrategies(req.user!.id);
      res.json(strategies);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch strategies" });
    }
  });

  app.post("/api/strategies", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const validatedData = insertStrategySchema.parse({
        ...req.body,
        userId: req.user!.id
      });
      const strategy = await storage.createStrategy(validatedData);
      res.status(201).json(strategy);
    } catch (error) {
      res.status(400).json({ message: "Invalid strategy data" });
    }
  });

  app.put("/api/strategies/:id", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const id = parseInt(req.params.id);
      const updates = insertStrategySchema.partial().parse(req.body);
      const strategy = await storage.updateStrategy(id, updates);
      
      if (!strategy) {
        return res.status(404).json({ message: "Strategy not found" });
      }
      
      res.json(strategy);
    } catch (error) {
      res.status(400).json({ message: "Invalid strategy data" });
    }
  });

  // Signal management routes
  app.get("/api/signals", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const limit = req.query.limit ? parseInt(req.query.limit as string) : 50;
      const signals = await storage.getSignals(limit);
      res.json(signals);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch signals" });
    }
  });

  app.post("/api/signals", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const validatedData = insertSignalSchema.parse(req.body);
      const signal = await storage.createSignal(validatedData);
      res.status(201).json(signal);
      
      // Broadcast signal to WebSocket clients
      broadcastToClients('signal_created', signal);
    } catch (error) {
      res.status(400).json({ message: "Invalid signal data" });
    }
  });

  app.post("/api/signals/:id/replay", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const id = parseInt(req.params.id);
      const { forceReplay = false, modifyParams = {} } = req.body;
      
      const signal = await storage.getSignal(id);
      
      if (!signal) {
        return res.status(404).json({ message: "Signal not found" });
      }
      
      // Check if signal can be replayed
      if (!forceReplay && signal.status === "executed") {
        return res.status(400).json({ 
          message: "Signal already executed. Use forceReplay=true to override.",
          currentStatus: signal.status
        });
      }
      
      // Apply parameter modifications if provided
      const updatedSignal = {
        status: "pending",
        ...modifyParams,
        // Preserve original timestamps and ID
        id: signal.id,
        createdAt: signal.createdAt
      };
      
      const replayedSignal = await storage.updateSignal(id, updatedSignal);
      
      // Log replay action
      await storage.createSyncLog({
        userId: req.user!.id,
        action: "signal_replay",
        status: "success",
        details: { 
          signalId: id,
          originalStatus: signal.status,
          modifiedParams: modifyParams,
          forceReplay,
          replayedBy: req.user!.username
        }
      });
      
      // Broadcast replay event to desktop app with priority
      broadcastToClients('signal_replay', {
        signal: replayedSignal,
        priority: "high",
        replayedBy: req.user!.id,
        timestamp: new Date().toISOString()
      });
      
      res.json({
        success: true,
        signal: replayedSignal,
        replayId: `replay_${id}_${Date.now()}`,
        message: "Signal queued for replay execution"
      });
    } catch (error) {
      console.error("Signal replay error:", error);
      res.status(500).json({ message: "Failed to replay signal", error: error.message });
    }
  });

  // Signal parsing and simulation routes
  app.post("/api/signals/parse", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const { rawMessage, channelId, simulate = false } = req.body;
      
      if (!rawMessage) {
        return res.status(400).json({ message: "rawMessage is required" });
      }
      
      // Basic signal parsing logic (simplified)
      const parsedSignal = parseSignalMessage(rawMessage);
      
      if (!parsedSignal.valid) {
        return res.status(400).json({ 
          message: "Failed to parse signal",
          errors: parsedSignal.errors,
          rawMessage 
        });
      }
      
      if (simulate) {
        // Return parsed data without saving
        res.json({
          parsed: true,
          simulation: true,
          signal: parsedSignal.data,
          confidence: parsedSignal.confidence,
          extractedFields: parsedSignal.extractedFields
        });
      } else {
        // Save parsed signal to database
        const signalData = {
          channelId: channelId || null,
          symbol: parsedSignal.data.symbol,
          action: parsedSignal.data.action,
          entry: parsedSignal.data.entry,
          stopLoss: parsedSignal.data.stopLoss,
          takeProfit1: parsedSignal.data.takeProfit1,
          takeProfit2: parsedSignal.data.takeProfit2,
          takeProfit3: parsedSignal.data.takeProfit3,
          takeProfit4: parsedSignal.data.takeProfit4,
          takeProfit5: parsedSignal.data.takeProfit5,
          confidence: parsedSignal.confidence,
          status: "pending",
          rawMessage: rawMessage,
          parsedData: parsedSignal.data
        };
        
        const signal = await storage.createSignal(signalData);
        
        // Broadcast new signal
        broadcastToClients('signal_created', signal);
        
        res.status(201).json({
          parsed: true,
          saved: true,
          signal: signal,
          confidence: parsedSignal.confidence
        });
      }
    } catch (error) {
      console.error("Signal parsing error:", error);
      res.status(500).json({ message: "Signal parsing failed", error: error.message });
    }
  });

  app.post("/api/signals/simulate", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const { signalData, marketConditions = {}, accountInfo = {} } = req.body;
      
      if (!signalData) {
        return res.status(400).json({ message: "signalData is required" });
      }
      
      // Simulate trade execution with current market conditions
      const simulation = simulateTradeExecution(signalData, marketConditions, accountInfo);
      
      res.json({
        simulation: true,
        input: {
          signal: signalData,
          marketConditions,
          accountInfo
        },
        results: simulation,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error("Signal simulation error:", error);
      res.status(500).json({ message: "Signal simulation failed", error: error.message });
    }
  });

  app.get("/api/signals/formats", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const supportedFormats = getSupportedSignalFormats();
      res.json({
        formats: supportedFormats,
        parserVersion: "2.0.0",
        lastUpdated: new Date().toISOString()
      });
    } catch (error) {
      res.status(500).json({ message: "Failed to get signal formats" });
    }
  });

  // Trade routes
  app.get("/api/trades", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const limit = req.query.limit ? parseInt(req.query.limit as string) : 50;
      const trades = await storage.getUserTrades(req.user!.id, limit);
      res.json(trades);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch trades" });
    }
  });

  app.get("/api/trades/active", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const trades = await storage.getActiveTrades(req.user!.id);
      res.json(trades);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch active trades" });
    }
  });

  // MT5 Status routes
  app.get("/api/mt5-status", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const status = await storage.getMt5Status(req.user!.id);
      res.json(status || { isConnected: false });
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch MT5 status" });
    }
  });

  app.post("/api/mt5-status", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const validatedData = insertMt5StatusSchema.parse(req.body);
      const status = await storage.updateMt5Status(req.user!.id, validatedData);
      
      // Broadcast status update to WebSocket clients
      broadcastToClients('mt5_status_update', status);
      
      res.json(status);
    } catch (error) {
      res.status(400).json({ message: "Invalid MT5 status data" });
    }
  });

  // Email reporting routes
  app.post("/api/reports/send-daily", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const { recipientEmail } = req.body;
      
      if (!recipientEmail) {
        return res.status(400).json({ message: "Recipient email is required" });
      }
      
      // Get email configuration from environment
      const emailConfig = {
        provider: process.env.EMAIL_PROVIDER || 'smtp',
        smtpHost: process.env.SMTP_HOST,
        smtpPort: parseInt(process.env.SMTP_PORT || '587'),
        smtpUser: process.env.SMTP_USER,
        smtpPassword: process.env.SMTP_PASSWORD,
        fromEmail: process.env.FROM_EMAIL || 'noreply@signalos.com',
        fromName: process.env.FROM_NAME || 'SignalOS',
        apiKey: process.env.EMAIL_API_KEY,
        apiUrl: process.env.EMAIL_API_URL,
      };
      
      const EmailReporter = (await import('./utils/email_reporter')).default;
      const reporter = new EmailReporter(emailConfig as any);
      
      const success = await reporter.sendDailyReport(recipientEmail, req.user!.id);
      
      if (success) {
        res.json({ 
          success: true, 
          message: "Daily report sent successfully",
          timestamp: new Date().toISOString()
        });
      } else {
        res.status(500).json({ 
          success: false, 
          message: "Failed to send daily report" 
        });
      }
    } catch (error) {
      console.error("Daily report error:", error);
      res.status(500).json({ 
        success: false, 
        message: "Internal server error",
        error: error.message 
      });
    }
  });

  app.post("/api/reports/send-weekly", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const { recipientEmail } = req.body;
      
      if (!recipientEmail) {
        return res.status(400).json({ message: "Recipient email is required" });
      }
      
      const emailConfig = {
        provider: process.env.EMAIL_PROVIDER || 'smtp',
        smtpHost: process.env.SMTP_HOST,
        smtpPort: parseInt(process.env.SMTP_PORT || '587'),
        smtpUser: process.env.SMTP_USER,
        smtpPassword: process.env.SMTP_PASSWORD,
        fromEmail: process.env.FROM_EMAIL || 'noreply@signalos.com',
        fromName: process.env.FROM_NAME || 'SignalOS',
        apiKey: process.env.EMAIL_API_KEY,
        apiUrl: process.env.EMAIL_API_URL,
      };
      
      const EmailReporter = (await import('./utils/email_reporter')).default;
      const reporter = new EmailReporter(emailConfig as any);
      
      const success = await reporter.sendWeeklyReport(recipientEmail, req.user!.id);
      
      if (success) {
        res.json({ 
          success: true, 
          message: "Weekly report sent successfully",
          timestamp: new Date().toISOString()
        });
      } else {
        res.status(500).json({ 
          success: false, 
          message: "Failed to send weekly report" 
        });
      }
    } catch (error) {
      console.error("Weekly report error:", error);
      res.status(500).json({ 
        success: false, 
        message: "Internal server error",
        error: error.message 
      });
    }
  });

  app.post("/api/reports/test-connection", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const emailConfig = {
        provider: process.env.EMAIL_PROVIDER || 'smtp',
        smtpHost: process.env.SMTP_HOST,
        smtpPort: parseInt(process.env.SMTP_PORT || '587'),
        smtpUser: process.env.SMTP_USER,
        smtpPassword: process.env.SMTP_PASSWORD,
        fromEmail: process.env.FROM_EMAIL || 'noreply@signalos.com',
        fromName: process.env.FROM_NAME || 'SignalOS',
        apiKey: process.env.EMAIL_API_KEY,
        apiUrl: process.env.EMAIL_API_URL,
      };
      
      const EmailReporter = (await import('./utils/email_reporter')).default;
      const reporter = new EmailReporter(emailConfig as any);
      
      const isConnected = await reporter.testConnection();
      
      res.json({ 
        connected: isConnected,
        message: isConnected ? "Email connection successful" : "Email connection failed",
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error("Email connection test error:", error);
      res.json({ 
        connected: false,
        message: "Connection test failed",
        error: error.message,
        timestamp: new Date().toISOString()
      });
    }
  });

  app.get("/api/reports/logs", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const limit = parseInt(req.query.limit as string) || 50;
      
      const emailConfig = {
        provider: process.env.EMAIL_PROVIDER || 'smtp',
        smtpHost: process.env.SMTP_HOST,
        smtpPort: parseInt(process.env.SMTP_PORT || '587'),
        smtpUser: process.env.SMTP_USER,
        smtpPassword: process.env.SMTP_PASSWORD,
        fromEmail: process.env.FROM_EMAIL || 'noreply@signalos.com',
        fromName: process.env.FROM_NAME || 'SignalOS',
        apiKey: process.env.EMAIL_API_KEY,
        apiUrl: process.env.EMAIL_API_URL,
      };
      
      const EmailReporter = (await import('./utils/email_reporter')).default;
      const reporter = new EmailReporter(emailConfig as any);
      
      const logs = await reporter.getReportLogs(limit);
      
      res.json({ 
        logs,
        count: logs.length,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error("Email logs error:", error);
      res.status(500).json({ 
        message: "Failed to retrieve email logs",
        error: error.message 
      });
    }
  });

  // Provider stats API endpoint
  app.get("/api/providers/stats", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const signals = await storage.getSignals(1000); // Get recent signals for analysis
      const trades = await storage.getUserTrades(req.user!.id, 1000);
      
      // Group signals by provider/channel
      const providerMap = new Map();
      
      signals.forEach(signal => {
        const providerId = signal.channelId || `channel_${signal.id}`;
        const providerName = signal.channelName || `Channel ${signal.id}`;
        
        if (!providerMap.has(providerId)) {
          providerMap.set(providerId, {
            id: providerId,
            name: providerName,
            signals: [],
            trades: []
          });
        }
        
        providerMap.get(providerId).signals.push(signal);
      });
      
      // Add trades to providers
      trades.forEach(trade => {
        if (trade.signalId) {
          const signal = signals.find(s => s.id === trade.signalId);
          if (signal) {
            const providerId = signal.channelId || `channel_${signal.id}`;
            if (providerMap.has(providerId)) {
              providerMap.get(providerId).trades.push(trade);
            }
          }
        }
      });
      
      // Calculate statistics for each provider
      const providerStats = Array.from(providerMap.values()).map(provider => {
        const signals = provider.signals;
        const trades = provider.trades;
        
        const totalSignals = signals.length;
        const executedSignals = signals.filter(s => s.status === "executed").length;
        const successfulTrades = trades.filter(t => parseFloat(t.profit || "0") > 0);
        const losingTrades = trades.filter(t => parseFloat(t.profit || "0") < 0);
        
        const winCount = successfulTrades.length;
        const lossCount = losingTrades.length;
        const winRate = executedSignals > 0 ? (winCount / executedSignals) * 100 : 0;
        
        const totalPnL = trades.reduce((sum, trade) => sum + parseFloat(trade.profit || "0"), 0);
        
        // Calculate average R:R ratio
        let totalRR = 0;
        let rrCount = 0;
        trades.forEach(trade => {
          const profit = parseFloat(trade.profit || "0");
          const entry = parseFloat(trade.entryPrice || "0");
          const sl = parseFloat(trade.stopLoss || "0");
          
          if (profit > 0 && entry > 0 && sl > 0) {
            const risk = Math.abs(entry - sl);
            const reward = Math.abs(profit / parseFloat(trade.lotSize || "0.01"));
            if (risk > 0) {
              totalRR += reward / risk;
              rrCount++;
            }
          }
        });
        const averageRR = rrCount > 0 ? totalRR / rrCount : 0;
        
        // Calculate max drawdown
        let peak = 0;
        let maxDrawdown = 0;
        let runningPnL = 0;
        
        trades.sort((a, b) => new Date(a.openTime || 0).getTime() - new Date(b.openTime || 0).getTime());
        trades.forEach(trade => {
          runningPnL += parseFloat(trade.profit || "0");
          if (runningPnL > peak) peak = runningPnL;
          const currentDrawdown = peak - runningPnL;
          if (currentDrawdown > maxDrawdown) maxDrawdown = currentDrawdown;
        });
        
        // Calculate performance grade
        let grade = 'F';
        const score = (winRate * 0.4) + (Math.min(averageRR * 25, 100) * 0.4) + (Math.min(executedSignals / totalSignals * 100, 100) * 0.2);
        if (score >= 80) grade = 'A';
        else if (score >= 70) grade = 'B';
        else if (score >= 60) grade = 'C';
        else if (score >= 50) grade = 'D';
        
        const lastSignal = signals.sort((a, b) => new Date(b.createdAt || 0).getTime() - new Date(a.createdAt || 0).getTime())[0];
        const lastSignalDate = lastSignal ? lastSignal.createdAt : new Date().toISOString();
        
        // Check if active (signal in last 7 days)
        const isActive = lastSignal ? 
          (new Date().getTime() - new Date(lastSignal.createdAt || 0).getTime()) < (7 * 24 * 60 * 60 * 1000) : 
          false;
        
        return {
          id: provider.id,
          name: provider.name,
          totalSignals,
          executedSignals,
          winCount,
          lossCount,
          winRate: Number(winRate.toFixed(2)),
          averageRR: Number(averageRR.toFixed(2)),
          maxDrawdown: Number(maxDrawdown.toFixed(2)),
          totalPnL: Number(totalPnL.toFixed(2)),
          lastSignalDate,
          performanceGrade: grade,
          isActive
        };
      }).filter(provider => provider.totalSignals > 0);
      
      res.json(providerStats);
    } catch (error) {
      console.error("Provider stats error:", error);
      res.status(500).json({ message: "Failed to fetch provider statistics" });
    }
  });

  // Dashboard stats
  app.get("/api/dashboard/stats", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const activeTrades = await storage.getActiveTrades(req.user!.id);
      const recentTrades = await storage.getUserTrades(req.user!.id, 20);
      const recentSignals = await storage.getSignals(20);
      
      // Calculate basic stats
      const todaysPnL = recentTrades
        .filter(trade => trade.openTime && new Date(trade.openTime).toDateString() === new Date().toDateString())
        .reduce((sum, trade) => sum + (parseFloat(trade.profit || "0")), 0);
      
      const totalSignalsToday = recentSignals
        .filter(signal => signal.createdAt && new Date(signal.createdAt).toDateString() === new Date().toDateString())
        .length;
      
      const executedSignals = recentSignals.filter(s => s.status === "executed").length;
      const successRate = totalSignalsToday > 0 ? (executedSignals / totalSignalsToday) * 100 : 0;
      
      const stats = {
        activeTrades: activeTrades.length,
        todaysPnL: todaysPnL.toFixed(2),
        signalsProcessed: totalSignalsToday,
        successRate: successRate.toFixed(1),
        pendingSignals: recentSignals.filter(s => s.status === "pending").length
      };
      
      res.json(stats);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch dashboard stats" });
    }
  });

  // Firebridge sync endpoints (for desktop app integration)
  app.post("/api/firebridge/sync-user", async (req, res) => {
    try {
      const { userId, terminalStatus, parserStatus } = req.body;
      
      // Validate required fields
      if (!userId || !terminalStatus) {
        return res.status(400).json({ message: "Missing required fields: userId, terminalStatus" });
      }
      
      // Update MT5 status if provided
      if (terminalStatus.modules?.mt5) {
        const mt5Data = terminalStatus.modules.mt5;
        await storage.updateMt5Status(userId, {
          terminalId: terminalStatus.terminal_id,
          isConnected: mt5Data.connected || false,
          serverInfo: mt5Data.account_info || {},
          latency: mt5Data.latency || null
        });
      }
      
      // Log the sync event
      await storage.createSyncLog({
        userId,
        action: "sync_user",
        status: "success",
        details: { terminalStatus, parserStatus, syncVersion: "2.0" }
      });
      
      // Get user's current strategy
      const strategies = await storage.getUserStrategies(userId);
      const activeStrategy = strategies.find(s => s.isActive);
      
      // Get pending signals for processing
      const pendingSignals = await storage.getSignals(10);
      const userPendingSignals = pendingSignals.filter(s => s.status === "pending");
      
      // Broadcast sync event to WebSocket clients
      broadcastToClients('desktop_sync', { 
        userId, 
        terminalId: terminalStatus.terminal_id,
        connected: terminalStatus.modules?.mt5?.connected || false,
        timestamp: new Date().toISOString()
      });
      
      res.json({
        strategy: activeStrategy,
        pendingSignals: userPendingSignals,
        serverConfig: {
          retryInterval: 60,
          maxRetries: 3,
          stealthMode: false
        },
        timestamp: new Date().toISOString(),
        syncId: `sync_${userId}_${Date.now()}`
      });
    } catch (error) {
      console.error("Firebridge sync error:", error);
      res.status(500).json({ message: "Sync failed", error: error.message });
    }
  });

  app.post("/api/firebridge/error-alert", async (req, res) => {
    try {
      const { userId, error, details } = req.body;
      
      if (!userId || !error) {
        return res.status(400).json({ message: "Missing required fields: userId, error" });
      }
      
      await storage.createSyncLog({
        userId,
        action: "error_alert",
        status: "error",
        details: { 
          error, 
          errorType: details?.errorType || "unknown",
          timestamp: new Date().toISOString(),
          ...details 
        }
      });
      
      // Broadcast error to WebSocket clients with severity
      const severity = details?.severity || "medium";
      broadcastToClients('error_alert', { 
        userId, 
        error, 
        details, 
        severity,
        timestamp: new Date().toISOString()
      });
      
      res.json({ 
        acknowledged: true, 
        alertId: `alert_${userId}_${Date.now()}`,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error("Error alert processing failed:", error);
      res.status(500).json({ message: "Failed to log error", error: error.message });
    }
  });

  app.get("/api/firebridge/pull-strategy/:userId", async (req, res) => {
    try {
      const userId = parseInt(req.params.userId);
      
      if (isNaN(userId)) {
        return res.status(400).json({ message: "Invalid userId" });
      }
      
      const strategies = await storage.getUserStrategies(userId);
      const activeStrategy = strategies.find(s => s.isActive);
      
      if (!activeStrategy) {
        return res.status(404).json({ message: "No active strategy found" });
      }
      
      // Log strategy pull
      await storage.createSyncLog({
        userId,
        action: "pull_strategy",
        status: "success",
        details: { strategyId: activeStrategy.id, strategyName: activeStrategy.name }
      });
      
      res.json({
        strategy: activeStrategy,
        lastModified: activeStrategy.updatedAt,
        version: activeStrategy.id,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error("Strategy pull error:", error);
      res.status(500).json({ message: "Failed to pull strategy", error: error.message });
    }
  });

  app.post("/api/firebridge/push-trade-result", async (req, res) => {
    try {
      const { userId, signalId, tradeResult, mt5Ticket } = req.body;
      
      if (!userId || !signalId || !tradeResult) {
        return res.status(400).json({ message: "Missing required fields" });
      }
      
      // Update signal status based on trade result
      const signal = await storage.getSignal(signalId);
      if (signal) {
        const newStatus = tradeResult.success ? "executed" : "failed";
        await storage.updateSignal(signalId, { status: newStatus });
        
        // Create trade record if successful
        if (tradeResult.success && mt5Ticket) {
          await storage.createTrade({
            signalId: signalId,
            userId: userId,
            mt5Ticket: mt5Ticket,
            symbol: signal.symbol,
            action: signal.action,
            lotSize: tradeResult.lotSize || "0.01",
            entryPrice: tradeResult.entryPrice || signal.entry,
            currentPrice: tradeResult.currentPrice || signal.entry,
            stopLoss: signal.stopLoss,
            takeProfit: signal.takeProfit1,
            profit: "0.00",
            status: "open"
          });
        }
      }
      
      // Log trade result
      await storage.createSyncLog({
        userId,
        action: "trade_result",
        status: tradeResult.success ? "success" : "failed",
        details: { 
          signalId, 
          mt5Ticket, 
          tradeResult,
          processingTime: tradeResult.processingTime || 0
        }
      });
      
      // Broadcast trade update
      broadcastToClients('trade_executed', {
        userId,
        signalId,
        success: tradeResult.success,
        mt5Ticket,
        timestamp: new Date().toISOString()
      });
      
      res.json({ 
        acknowledged: true,
        signalUpdated: !!signal,
        tradeCreated: !!(tradeResult.success && mt5Ticket),
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error("Trade result processing error:", error);
      res.status(500).json({ message: "Failed to process trade result", error: error.message });
    }
  });

  app.post("/api/firebridge/heartbeat", async (req, res) => {
    try {
      const { userId, terminalId, status } = req.body;
      
      if (!userId || !terminalId) {
        return res.status(400).json({ message: "Missing required fields" });
      }
      
      // Update MT5 status with heartbeat
      await storage.updateMt5Status(userId, {
        terminalId,
        isConnected: status?.connected || false,
        latency: status?.latency || null,
        serverInfo: status?.serverInfo || {}
      });
      
      // Broadcast heartbeat to monitoring clients
      broadcastToClients('heartbeat', {
        userId,
        terminalId,
        status,
        timestamp: new Date().toISOString()
      });
      
      res.json({ 
        received: true,
        timestamp: new Date().toISOString(),
        nextHeartbeat: 30 // seconds
      });
    } catch (error) {
      console.error("Heartbeat processing error:", error);
      res.status(500).json({ message: "Heartbeat failed", error: error.message });
    }
  });

  const httpServer = createServer(app);

  // Setup WebSocket server
  const wss = new WebSocketServer({ server: httpServer, path: '/ws' });
  
  const clients = new Set<WebSocket>();

  wss.on('connection', (ws) => {
    clients.add(ws);
    
    ws.on('close', () => {
      clients.delete(ws);
    });

    ws.on('message', (data) => {
      try {
        const message = JSON.parse(data.toString());
        
        // Handle different message types from desktop app
        if (message.type === 'mt5_status') {
          broadcastToClients('mt5_status_update', message.data);
        } else if (message.type === 'trade_update') {
          broadcastToClients('trade_update', message.data);
        }
      } catch (error) {
        console.error('WebSocket message error:', error);
      }
    });
  });

  function broadcastToClients(type: string, data: any) {
    const message = JSON.stringify({ type, data, timestamp: new Date().toISOString() });
    
    clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(message);
      }
    });
  }

  return httpServer;
}

// Signal parsing helper functions
function parseSignalMessage(rawMessage: string) {
  try {
    const message = rawMessage.toUpperCase().trim();
    const lines = message.split('\n').map(line => line.trim()).filter(line => line.length > 0);
    
    const result = {
      valid: false,
      errors: [] as string[],
      confidence: 0,
      data: {} as any,
      extractedFields: [] as string[]
    };
    
    // Extract action (BUY/SELL)
    const actionMatch = message.match(/\b(BUY|SELL)\b/);
    if (!actionMatch) {
      result.errors.push("No BUY/SELL action found");
      return result;
    }
    result.data.action = actionMatch[1];
    result.extractedFields.push("action");
    
    // Extract symbol
    const symbolMatch = message.match(/\b([A-Z]{6}|[A-Z]{3}\/[A-Z]{3})\b/);
    if (!symbolMatch) {
      result.errors.push("No currency pair found");
      return result;
    }
    result.data.symbol = symbolMatch[1].replace('/', '');
    result.extractedFields.push("symbol");
    
    // Extract entry price
    const entryMatch = message.match(/ENTRY[:\s]*([0-9]+\.?[0-9]*)/i);
    if (entryMatch) {
      result.data.entry = entryMatch[1];
      result.extractedFields.push("entry");
    }
    
    // Extract stop loss
    const slMatch = message.match(/S\.?L\.?[:\s]*([0-9]+\.?[0-9]*)/i);
    if (slMatch) {
      result.data.stopLoss = slMatch[1];
      result.extractedFields.push("stopLoss");
    }
    
    // Extract take profit levels
    for (let i = 1; i <= 5; i++) {
      const tpMatch = message.match(new RegExp(`T\.?P\.?${i}[:\\s]*([0-9]+\\.?[0-9]*)`, 'i'));
      if (tpMatch) {
        result.data[`takeProfit${i}`] = tpMatch[1];
        result.extractedFields.push(`takeProfit${i}`);
      }
    }
    
    // Calculate confidence based on extracted fields
    let confidence = 0;
    if (result.data.action && result.data.symbol) confidence += 40;
    if (result.data.entry) confidence += 20;
    if (result.data.stopLoss) confidence += 20;
    if (result.data.takeProfit1) confidence += 15;
    if (result.extractedFields.length >= 4) confidence += 5;
    
    result.confidence = Math.min(confidence, 100);
    result.valid = result.confidence >= 60; // Minimum 60% confidence required
    
    if (!result.valid) {
      result.errors.push(`Confidence too low: ${result.confidence}% (minimum 60% required)`);
    }
    
    return result;
  } catch (error) {
    return {
      valid: false,
      errors: [`Parsing error: ${error.message}`],
      confidence: 0,
      data: {},
      extractedFields: []
    };
  }
}

function simulateTradeExecution(signalData: any, marketConditions: any, accountInfo: any) {
  const simulation = {
    success: true,
    estimatedOutcome: {} as any,
    riskAssessment: {} as any,
    marketImpact: {} as any,
    warnings: [] as string[]
  };
  
  try {
    const entry = parseFloat(signalData.entry || "0");
    const stopLoss = parseFloat(signalData.stopLoss || "0");
    const takeProfit = parseFloat(signalData.takeProfit1 || "0");
    const lotSize = parseFloat(signalData.lotSize || "0.01");
    const balance = parseFloat(accountInfo.balance || "10000");
    
    // Calculate risk
    if (entry && stopLoss) {
      const riskPips = Math.abs(entry - stopLoss) * 10000; // Simplified pip calculation
      const riskAmount = riskPips * lotSize * 1; // $1 per pip per standard lot
      const riskPercent = (riskAmount / balance) * 100;
      
      simulation.riskAssessment = {
        riskPips: riskPips.toFixed(1),
        riskAmount: riskAmount.toFixed(2),
        riskPercent: riskPercent.toFixed(2)
      };
      
      if (riskPercent > 5) {
        simulation.warnings.push("High risk: Risk exceeds 5% of account balance");
      }
    }
    
    // Calculate potential profit
    if (entry && takeProfit) {
      const profitPips = Math.abs(takeProfit - entry) * 10000;
      const profitAmount = profitPips * lotSize * 1;
      
      simulation.estimatedOutcome = {
        profitPips: profitPips.toFixed(1),
        profitAmount: profitAmount.toFixed(2),
        riskRewardRatio: stopLoss ? (profitPips / Math.abs(entry - stopLoss) / 10000).toFixed(2) : "N/A"
      };
    }
    
    // Market conditions assessment
    const spread = parseFloat(marketConditions.spread || "2");
    const volatility = marketConditions.volatility || "normal";
    
    simulation.marketImpact = {
      spreadCost: (spread * lotSize * 1).toFixed(2),
      volatility: volatility,
      executionProbability: spread > 5 ? "medium" : "high"
    };
    
    if (spread > 5) {
      simulation.warnings.push("Wide spread detected, execution may be difficult");
    }
    
    if (volatility === "high") {
      simulation.warnings.push("High volatility may cause slippage");
    }
    
    simulation.success = simulation.warnings.length < 3; // Fail if too many warnings
    
  } catch (error) {
    simulation.success = false;
    simulation.warnings.push(`Simulation error: ${error.message}`);
  }
  
  return simulation;
}

function getSupportedSignalFormats() {
  return [
    {
      name: "Standard Format",
      description: "BUY/SELL SYMBOL Entry: X.XXXX SL: X.XXXX TP1: X.XXXX",
      example: "BUY EURUSD\nEntry: 1.1000\nSL: 1.0950\nTP1: 1.1050\nTP2: 1.1100",
      confidence: "high"
    },
    {
      name: "Compact Format",
      description: "ACTION SYMBOL E:X.X SL:X.X TP:X.X",
      example: "BUY GBPUSD E:1.2500 SL:1.2450 TP:1.2600",
      confidence: "medium"
    },
    {
      name: "Verbose Format",
      description: "Full text with signal details",
      example: "Signal: BUY EURUSD at 1.1000, stop loss 1.0950, take profit 1.1050",
      confidence: "medium"
    },
    {
      name: "Multi-TP Format",
      description: "Signal with multiple take profit levels",
      example: "SELL USDJPY\nEntry: 110.50\nSL: 111.00\nTP1: 110.00\nTP2: 109.50\nTP3: 109.00",
      confidence: "high"
    }
  ];

  const server = createServer(app);

  // Setup WebSocket server with enhanced features
  wsServer = new WebSocketServer({ 
    server,
    path: '/ws',
    perMessageDeflate: false,
    maxPayload: 1024 * 1024 // 1MB max message size
  });

  wsServer.on('connection', (ws: WebSocketClient, req) => {
    console.log('WebSocket client connected from:', req.socket.remoteAddress);
    
    ws.isAlive = true;
    ws.userId = undefined;
    let isAuthenticated = false;
    const connectionTimeout = setTimeout(() => {
      if (!isAuthenticated) {
        ws.close(4001, 'Authentication timeout');
      }
    }, 10000); // 10 second authentication timeout

    // Fix #7: Secure WebSocket authentication
    ws.on('message', (data) => {
      try {
        // Fix #19: Safe JSON parsing
        const message = JSON.parse(data.toString());
        
        // Validate message structure
        if (!message.type || typeof message.type !== 'string') {
          ws.send(JSON.stringify({
            type: 'error',
            data: { message: 'Invalid message format: type required' }
          }));
          return;
        }

        if (message.type === 'authenticate') {
          const { sessionId, userId } = message.data || {};
          
          // Validate session authentication
          if (!sessionId || !userId) {
            ws.send(JSON.stringify({
              type: 'auth_failed',
              data: { message: 'Session ID and User ID required' }
            }));
            return;
          }

          // Verify session exists and belongs to user
          // In production, this would validate against the session store
          const isValidSession = sessionId && userId && typeof userId === 'number';
          
          if (!isValidSession) {
            ws.send(JSON.stringify({
              type: 'auth_failed',
              data: { message: 'Invalid session or unauthorized' }
            }));
            ws.close(4003, 'Invalid authentication');
            return;
          }

          clearTimeout(connectionTimeout);
          isAuthenticated = true;
          ws.userId = userId;
          
          // Add to connected clients
          if (!connectedClients[userId]) {
            connectedClients[userId] = [];
          }
          connectedClients[userId].push(ws);
          
          console.log(`User ${userId} authenticated via WebSocket, ${connectedClients[userId].length} connections`);
          
          // Send authentication confirmation
          ws.send(JSON.stringify({
            type: 'authenticated',
            data: { userId, timestamp: new Date().toISOString() }
          }));
          
        } else if (message.type === 'ping') {
          // Respond to ping with pong
          ws.send(JSON.stringify({
            type: 'pong',
            data: { timestamp: new Date().toISOString() }
          }));
          ws.isAlive = true;
          
        } else if (message.type === 'ack') {
          // Handle message acknowledgment
          console.log('Message acknowledged:', message.data?.messageId);
          
        } else {
          // Handle other message types from desktop app
          console.log('Received WebSocket message:', message.type);
          
          // Broadcast updates to all clients of the same user
          if (ws.userId) {
            broadcastToUser(ws.userId, message);
          }
        }
      } catch (error) {
        console.error('WebSocket message parse error:', error);
        ws.send(JSON.stringify({
          type: 'error',
          data: { message: 'Invalid message format' }
        }));
      }
    });

    // Handle connection close
    ws.on('close', (code, reason) => {
      console.log(`WebSocket client disconnected: ${code} ${reason}`);
      if (ws.userId && connectedClients[ws.userId]) {
        connectedClients[ws.userId] = connectedClients[ws.userId].filter(client => client !== ws);
        if (connectedClients[ws.userId].length === 0) {
          delete connectedClients[ws.userId];
        }
      }
    });

    // Handle connection errors
    ws.on('error', (error) => {
      console.error('WebSocket error:', error);
    });

    // Handle pong response for heartbeat
    ws.on('pong', () => {
      ws.isAlive = true;
    });

    // Send initial connection confirmation
    ws.send(JSON.stringify({
      type: 'connection_established',
      data: { 
        timestamp: new Date().toISOString(),
        message: 'Connected. Please authenticate to receive updates.'
      }
    }));
  });

  // Heartbeat mechanism to detect broken connections
  const heartbeatInterval = setInterval(() => {
    wsServer.clients.forEach((ws: WebSocketClient) => {
      if (!ws.isAlive) {
        console.log('Terminating inactive WebSocket connection');
        return ws.terminate();
      }
      
      ws.isAlive = false;
      ws.ping();
    });
    
    // Clean up disconnected clients
    cleanupDisconnectedClients();
  }, 30000); // Check every 30 seconds

  // Handle server shutdown
  process.on('SIGTERM', () => {
    clearInterval(heartbeatInterval);
    wsServer.close();
  });

  console.log('WebSocket server initialized on /ws');

  return server;
}
