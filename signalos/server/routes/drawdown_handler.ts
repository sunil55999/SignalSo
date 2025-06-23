import type { Express } from "express";
import { eq, and, isNull, or } from "drizzle-orm";
import { db } from "../../../server/db";
import { 
  drawdownLimits, 
  drawdownEvents, 
  trades, 
  channels, 
  users,
  insertDrawdownLimitSchema,
  insertDrawdownEventSchema,
  type DrawdownLimit,
  type DrawdownEvent,
  type Trade
} from "../../../shared/schema";

// Types for drawdown monitoring
interface DrawdownStatus {
  userId: number;
  currentDrawdownPercent: number;
  accountBalance: number;
  peakBalance: number;
  activeTrades: Trade[];
  violatedLimits: DrawdownLimit[];
}

interface DrawdownAction {
  type: 'close_all' | 'close_provider' | 'close_symbol' | 'notify_only';
  tradesAffected: number[];
  limitId: number;
  providerId?: number;
  symbol?: string;
}

interface MT5CloseRequest {
  tickets: number[];
  reason: string;
  userId: number;
}

class DrawdownHandler {
  private isMonitoring = false;
  private monitoringInterval: NodeJS.Timeout | null = null;
  private readonly MONITORING_INTERVAL_MS = 30000; // 30 seconds

  constructor() {
    this.startMonitoring();
  }

  /**
   * Start real-time drawdown monitoring
   */
  private startMonitoring(): void {
    if (this.isMonitoring) return;
    
    this.isMonitoring = true;
    this.monitoringInterval = setInterval(async () => {
      await this.checkAllUsersDrawdown();
    }, this.MONITORING_INTERVAL_MS);
    
    console.log('[DrawdownHandler] Real-time monitoring started');
  }

  /**
   * Stop drawdown monitoring
   */
  stopMonitoring(): void {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }
    this.isMonitoring = false;
    console.log('[DrawdownHandler] Monitoring stopped');
  }

  /**
   * Check drawdown for all users with active limits
   */
  private async checkAllUsersDrawdown(): Promise<void> {
    try {
      const activeLimits = await db
        .select()
        .from(drawdownLimits)
        .where(eq(drawdownLimits.isActive, true));

      const userIds = Array.from(new Set(activeLimits.map(limit => limit.userId)));
      
      for (const userId of userIds) {
        await this.checkUserDrawdown(userId);
      }
    } catch (error) {
      console.error('[DrawdownHandler] Error in monitoring loop:', error);
    }
  }

  /**
   * Check drawdown for specific user
   */
  async checkUserDrawdown(userId: number): Promise<DrawdownStatus | null> {
    try {
      const userTrades = await db
        .select()
        .from(trades)
        .where(and(
          eq(trades.userId, userId),
          eq(trades.status, 'open')
        ));

      if (userTrades.length === 0) {
        return null; // No open trades, no drawdown risk
      }

      // Calculate current account status
      const accountBalance = await this.getCurrentAccountBalance(userId);
      const peakBalance = await this.getPeakAccountBalance(userId);
      const currentDrawdownPercent = ((peakBalance - accountBalance) / peakBalance) * 100;

      const drawdownStatus: DrawdownStatus = {
        userId,
        currentDrawdownPercent,
        accountBalance,
        peakBalance,
        activeTrades: userTrades,
        violatedLimits: []
      };

      // Get active limits for this user
      const userLimits = await db
        .select()
        .from(drawdownLimits)
        .where(and(
          eq(drawdownLimits.userId, userId),
          eq(drawdownLimits.isActive, true)
        ));

      // Check each limit
      for (const limit of userLimits) {
        const isViolated = await this.checkLimitViolation(limit, drawdownStatus);
        if (isViolated) {
          drawdownStatus.violatedLimits.push(limit);
          await this.handleDrawdownViolation(limit, drawdownStatus);
        }
      }

      return drawdownStatus;
    } catch (error) {
      console.error(`[DrawdownHandler] Error checking drawdown for user ${userId}:`, error);
      return null;
    }
  }

  /**
   * Check if a specific limit is violated
   */
  private async checkLimitViolation(limit: DrawdownLimit, status: DrawdownStatus): Promise<boolean> {
    let applicableDrawdown = status.currentDrawdownPercent;

    // For provider-specific limits, calculate drawdown from that provider's trades only
    if (limit.providerId) {
      const providerTrades = status.activeTrades.filter(trade => {
        // This would need to be enhanced to track provider per trade
        return true; // Simplified for now
      });
      
      if (providerTrades.length === 0) return false;
      
      const providerPnL = providerTrades.reduce((sum, trade) => 
        sum + parseFloat(trade.profit || "0"), 0);
      applicableDrawdown = Math.abs(providerPnL / status.accountBalance) * 100;
    }

    // For symbol-specific limits
    if (limit.symbol) {
      const symbolTrades = status.activeTrades.filter(trade => 
        trade.symbol === limit.symbol);
      
      if (symbolTrades.length === 0) return false;
      
      const symbolPnL = symbolTrades.reduce((sum, trade) => 
        sum + parseFloat(trade.profit || "0"), 0);
      applicableDrawdown = Math.abs(symbolPnL / status.accountBalance) * 100;
    }

    return applicableDrawdown >= parseFloat(limit.maxDrawdownPercent);
  }

  /**
   * Handle drawdown limit violation
   */
  private async handleDrawdownViolation(limit: DrawdownLimit, status: DrawdownStatus): Promise<void> {
    try {
      // Determine which trades to close
      const action = this.determineDrawdownAction(limit, status);
      
      // Log the breach event
      const eventData = {
        userId: limit.userId,
        limitId: limit.id,
        eventType: 'breach_detected' as const,
        drawdownPercent: status.currentDrawdownPercent.toString(),
        triggerThreshold: limit.maxDrawdownPercent,
        accountBalance: status.accountBalance.toString(),
        tradesAffected: action.tradesAffected.length,
        closedTrades: action.tradesAffected,
        providerId: limit.providerId,
        symbol: limit.symbol,
        details: {
          actionType: action.type,
          peakBalance: status.peakBalance,
          totalActiveTrades: status.activeTrades.length
        }
      };

      await db.insert(drawdownEvents).values(eventData);

      // Execute the action
      if (!limit.notifyOnly) {
        await this.executeDrawdownAction(action, limit, status);
      }

      // Send notification
      await this.sendDrawdownNotification(limit, status, action);

      // Auto-disable provider if configured
      if (limit.autoDisable && limit.providerId) {
        await this.disableProvider(limit.providerId, limit.userId);
      }

    } catch (error) {
      console.error('[DrawdownHandler] Error handling violation:', error);
    }
  }

  /**
   * Determine what action to take for drawdown violation
   */
  private determineDrawdownAction(limit: DrawdownLimit, status: DrawdownStatus): DrawdownAction {
    let tradesAffected: number[] = [];

    if (limit.providerId && limit.symbol) {
      // Close trades from specific provider and symbol
      tradesAffected = status.activeTrades
        .filter(trade => trade.symbol === limit.symbol)
        .map(trade => parseInt(trade.mt5Ticket || "0"))
        .filter(ticket => ticket > 0);
      
      return {
        type: 'close_symbol',
        tradesAffected,
        limitId: limit.id,
        providerId: limit.providerId,
        symbol: limit.symbol
      };
    } else if (limit.providerId) {
      // Close all trades from specific provider
      tradesAffected = status.activeTrades
        .map(trade => parseInt(trade.mt5Ticket || "0"))
        .filter(ticket => ticket > 0);
      
      return {
        type: 'close_provider',
        tradesAffected,
        limitId: limit.id,
        providerId: limit.providerId
      };
    } else if (limit.symbol) {
      // Close all trades for specific symbol
      tradesAffected = status.activeTrades
        .filter(trade => trade.symbol === limit.symbol)
        .map(trade => parseInt(trade.mt5Ticket || "0"))
        .filter(ticket => ticket > 0);
      
      return {
        type: 'close_symbol',
        tradesAffected,
        limitId: limit.id,
        symbol: limit.symbol
      };
    } else {
      // Close all trades (global limit)
      tradesAffected = status.activeTrades
        .map(trade => parseInt(trade.mt5Ticket || "0"))
        .filter(ticket => ticket > 0);
      
      return {
        type: 'close_all',
        tradesAffected,
        limitId: limit.id
      };
    }
  }

  /**
   * Execute the drawdown action (close trades via MT5)
   */
  private async executeDrawdownAction(action: DrawdownAction, limit: DrawdownLimit, status: DrawdownStatus): Promise<void> {
    if (action.tradesAffected.length === 0) return;

    try {
      // This would integrate with your MT5 bridge/command executor
      const closeRequest: MT5CloseRequest = {
        tickets: action.tradesAffected,
        reason: `Drawdown limit exceeded: ${status.currentDrawdownPercent.toFixed(2)}%`,
        userId: limit.userId
      };

      // Call MT5 bridge to close trades
      await this.sendMT5CloseCommand(closeRequest);

      // Update trades status in database
      await this.updateClosedTradesStatus(action.tradesAffected, 'closed');

      // Log successful closure
      await db.insert(drawdownEvents).values({
        userId: limit.userId,
        limitId: limit.id,
        eventType: 'trades_closed',
        drawdownPercent: status.currentDrawdownPercent.toString(),
        triggerThreshold: limit.maxDrawdownPercent,
        accountBalance: status.accountBalance.toString(),
        tradesAffected: action.tradesAffected.length,
        closedTrades: action.tradesAffected,
        providerId: limit.providerId,
        symbol: limit.symbol,
        details: {
          actionType: action.type,
          closeReason: 'drawdown_limit_exceeded'
        }
      });

    } catch (error) {
      console.error('[DrawdownHandler] Error executing drawdown action:', error);
      throw error;
    }
  }

  /**
   * Send MT5 close command (placeholder for actual MT5 integration)
   */
  private async sendMT5CloseCommand(request: MT5CloseRequest): Promise<void> {
    // This would integrate with your existing MT5 bridge
    // For now, we'll log the action
    console.log(`[DrawdownHandler] MT5 Close Request:`, {
      userId: request.userId,
      tickets: request.tickets,
      reason: request.reason,
      timestamp: new Date().toISOString()
    });

    // In a real implementation, this would call your MT5 bridge:
    // await mt5Bridge.closePositions(request.tickets, request.reason);
  }

  /**
   * Update trades status after closure
   */
  private async updateClosedTradesStatus(tickets: number[], status: string): Promise<void> {
    try {
      for (const ticket of tickets) {
        await db
          .update(trades)
          .set({ 
            status,
            closeTime: new Date()
          })
          .where(eq(trades.mt5Ticket, ticket.toString()));
      }
    } catch (error) {
      console.error('[DrawdownHandler] Error updating trade status:', error);
    }
  }

  /**
   * Send drawdown notification (integrates with Telegram bot)
   */
  private async sendDrawdownNotification(limit: DrawdownLimit, status: DrawdownStatus, action: DrawdownAction): Promise<void> {
    try {
      const user = await db
        .select()
        .from(users)
        .where(eq(users.id, limit.userId))
        .limit(1);

      if (user.length === 0) return;

      const notification = {
        type: 'drawdown_alert',
        userId: limit.userId,
        username: user[0].username,
        currentDrawdown: status.currentDrawdownPercent.toFixed(2),
        threshold: limit.maxDrawdownPercent,
        actionTaken: action.type,
        tradesAffected: action.tradesAffected.length,
        accountBalance: status.accountBalance,
        timestamp: new Date().toISOString()
      };

      // This would integrate with your Telegram copilot bot
      console.log('[DrawdownHandler] Drawdown Alert:', notification);
      
      // In real implementation:
      // await telegramBot.sendDrawdownAlert(notification);
    } catch (error) {
      console.error('[DrawdownHandler] Error sending notification:', error);
    }
  }

  /**
   * Disable provider after drawdown breach
   */
  private async disableProvider(providerId: number, userId: number): Promise<void> {
    try {
      // This would disable signal reception from the provider
      await db
        .update(channels)
        .set({ isActive: false })
        .where(eq(channels.id, providerId));

      // Log the disable event
      await db.insert(drawdownEvents).values({
        userId,
        limitId: 0, // Special case for provider disable
        eventType: 'provider_disabled',
        drawdownPercent: "0",
        triggerThreshold: "0",
        providerId,
        details: {
          reason: 'auto_disabled_after_drawdown_breach',
          disabledAt: new Date().toISOString()
        }
      });

      console.log(`[DrawdownHandler] Provider ${providerId} auto-disabled for user ${userId}`);
    } catch (error) {
      console.error('[DrawdownHandler] Error disabling provider:', error);
    }
  }

  /**
   * Get current account balance (placeholder - integrate with MT5)
   */
  private async getCurrentAccountBalance(userId: number): Promise<number> {
    // This would integrate with your MT5 status tracking
    // For now, calculate from trades
    try {
      const userTrades = await db
        .select()
        .from(trades)
        .where(eq(trades.userId, userId));

      const totalPnL = userTrades.reduce((sum, trade) => 
        sum + parseFloat(trade.profit || "0"), 0);

      // Assume starting balance of 10000 (this should come from MT5)
      return 10000 + totalPnL;
    } catch (error) {
      console.error('[DrawdownHandler] Error getting balance:', error);
      return 10000; // Fallback
    }
  }

  /**
   * Get peak account balance for drawdown calculation
   */
  private async getPeakAccountBalance(userId: number): Promise<number> {
    // This should track the highest balance achieved
    // For now, use current balance + 20% as peak
    const currentBalance = await this.getCurrentAccountBalance(userId);
    return Math.max(currentBalance * 1.2, 10000);
  }

  /**
   * Admin reset - re-enable trading after drawdown breach
   */
  async adminReset(userId: number, limitId: number, adminUserId: number): Promise<boolean> {
    try {
      // Re-enable the limit
      await db
        .update(drawdownLimits)
        .set({ 
          isActive: true,
          updatedAt: new Date()
        })
        .where(and(
          eq(drawdownLimits.id, limitId),
          eq(drawdownLimits.userId, userId)
        ));

      // Log the reset
      await db.insert(drawdownEvents).values({
        userId,
        limitId,
        eventType: 'admin_reset',
        drawdownPercent: "0",
        triggerThreshold: "0",
        adminUserId,
        details: {
          resetBy: adminUserId,
          resetAt: new Date().toISOString(),
          reason: 'manual_admin_reset'
        }
      });

      return true;
    } catch (error) {
      console.error('[DrawdownHandler] Error in admin reset:', error);
      return false;
    }
  }
}

// Global instance
const drawdownHandler = new DrawdownHandler();

/**
 * Setup drawdown handler routes
 */
export function setupDrawdownHandlerRoutes(app: Express): void {
  // Get user's drawdown limits
  app.get("/api/drawdown-limits", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const limits = await db
        .select()
        .from(drawdownLimits)
        .where(eq(drawdownLimits.userId, (req.user as any).id));
      
      res.json(limits);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch drawdown limits" });
    }
  });

  // Create drawdown limit
  app.post("/api/drawdown-limits", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const validatedData = insertDrawdownLimitSchema.parse({
        ...req.body,
        userId: (req.user as any).id
      });
      
      const [limit] = await db
        .insert(drawdownLimits)
        .values(validatedData)
        .returning();
      
      res.status(201).json(limit);
    } catch (error) {
      res.status(400).json({ message: "Invalid drawdown limit data" });
    }
  });

  // Update drawdown limit
  app.put("/api/drawdown-limits/:id", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const id = parseInt(req.params.id);
      const updates = insertDrawdownLimitSchema.partial().parse(req.body);
      
      const [limit] = await db
        .update(drawdownLimits)
        .set({ ...updates, updatedAt: new Date() })
        .where(and(
          eq(drawdownLimits.id, id),
          eq(drawdownLimits.userId, (req.user as any).id)
        ))
        .returning();
      
      if (!limit) {
        return res.status(404).json({ message: "Drawdown limit not found" });
      }
      
      res.json(limit);
    } catch (error) {
      res.status(400).json({ message: "Invalid drawdown limit data" });
    }
  });

  // Delete drawdown limit
  app.delete("/api/drawdown-limits/:id", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const id = parseInt(req.params.id);
      
      const result = await db
        .delete(drawdownLimits)
        .where(and(
          eq(drawdownLimits.id, id),
          eq(drawdownLimits.userId, (req.user as any).id)
        ))
        .returning();
      
      if (result.length === 0) {
        return res.status(404).json({ message: "Drawdown limit not found" });
      }
      
      res.sendStatus(204);
    } catch (error) {
      res.status(500).json({ message: "Failed to delete drawdown limit" });
    }
  });

  // Get drawdown events/history
  app.get("/api/drawdown-events", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const limit = req.query.limit ? parseInt(req.query.limit as string) : 50;
      
      const events = await db
        .select()
        .from(drawdownEvents)
        .where(eq(drawdownEvents.userId, (req.user as any).id))
        .orderBy(drawdownEvents.timestamp)
        .limit(limit);
      
      res.json(events);
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch drawdown events" });
    }
  });

  // Force drawdown check for user
  app.post("/api/drawdown-check", async (req, res) => {
    if (!req.isAuthenticated()) return res.sendStatus(401);
    
    try {
      const status = await drawdownHandler.checkUserDrawdown((req.user as any).id);
      
      res.json({
        checked: true,
        status,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      res.status(500).json({ message: "Failed to check drawdown" });
    }
  });

  // Admin routes (require admin role)
  app.post("/api/admin/drawdown-reset", async (req, res) => {
    if (!req.isAuthenticated() || (req.user as any).role !== 'admin') {
      return res.sendStatus(403);
    }
    
    try {
      const { userId, limitId } = req.body;
      
      if (!userId || !limitId) {
        return res.status(400).json({ message: "userId and limitId are required" });
      }
      
      const success = await drawdownHandler.adminReset(userId, limitId, (req.user as any).id);
      
      if (success) {
        res.json({ success: true, message: "Drawdown limit reset successfully" });
      } else {
        res.status(500).json({ message: "Failed to reset drawdown limit" });
      }
    } catch (error) {
      res.status(500).json({ message: "Admin reset failed" });
    }
  });

  // Get all users' drawdown status (admin only)
  app.get("/api/admin/drawdown-status", async (req, res) => {
    if (!req.isAuthenticated() || (req.user as any).role !== 'admin') {
      return res.sendStatus(403);
    }
    
    try {
      const allLimits = await db
        .select()
        .from(drawdownLimits)
        .where(eq(drawdownLimits.isActive, true));
      
      const userIds = Array.from(new Set(allLimits.map(limit => limit.userId)));
      const statusList: DrawdownStatus[] = [];
      
      for (const userId of userIds) {
        const status = await drawdownHandler.checkUserDrawdown(userId);
        if (status) {
          statusList.push(status);
        }
      }
      
      res.json({
        totalUsers: userIds.length,
        usersWithViolations: statusList.filter(s => s.violatedLimits.length > 0).length,
        statusList
      });
    } catch (error) {
      res.status(500).json({ message: "Failed to fetch drawdown status" });
    }
  });
}

// Cleanup on process exit
process.on('SIGINT', () => {
  drawdownHandler.stopMonitoring();
  process.exit(0);
});

process.on('SIGTERM', () => {
  drawdownHandler.stopMonitoring();
  process.exit(0);
});

export { drawdownHandler };