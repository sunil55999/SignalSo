import type { Express } from "express";
import { createServer, type Server } from "http";
import { WebSocketServer, WebSocket } from "ws";
import { setupAuth } from "./auth";
import { storage } from "./storage";
import { insertChannelSchema, insertStrategySchema, insertSignalSchema, insertMt5StatusSchema } from "@shared/schema";

export async function registerRoutes(app: Express): Promise<Server> {
  // Setup authentication routes
  setupAuth(app);

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
      const signal = await storage.getSignal(id);
      
      if (!signal) {
        return res.status(404).json({ message: "Signal not found" });
      }
      
      // Reset signal status to pending for replay
      const replayedSignal = await storage.updateSignal(id, { status: "pending" });
      
      // Broadcast replay event to desktop app
      broadcastToClients('signal_replay', replayedSignal);
      
      res.json(replayedSignal);
    } catch (error) {
      res.status(500).json({ message: "Failed to replay signal" });
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
      
      // Log the sync event
      await storage.createSyncLog({
        userId,
        action: "sync_user",
        status: "success",
        details: { terminalStatus, parserStatus }
      });
      
      // Get user's current strategy
      const strategies = await storage.getUserStrategies(userId);
      const activeStrategy = strategies.find(s => s.isActive);
      
      res.json({
        strategy: activeStrategy,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      res.status(500).json({ message: "Sync failed" });
    }
  });

  app.post("/api/firebridge/error-alert", async (req, res) => {
    try {
      const { userId, error, details } = req.body;
      
      await storage.createSyncLog({
        userId,
        action: "error_alert",
        status: "error",
        details: { error, ...details }
      });
      
      // Broadcast error to WebSocket clients
      broadcastToClients('error_alert', { userId, error, details });
      
      res.sendStatus(200);
    } catch (error) {
      res.status(500).json({ message: "Failed to log error" });
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
