import type { Express } from "express";
import { eq, and, desc, gte } from "drizzle-orm";
import { db } from "../db";
import { equityLimits, equityEvents, trades, users, insertEquityLimitSchema, insertEquityEventSchema } from "@shared/schema";
import { z } from "zod";

// Request schemas
const equityCheckSchema = z.object({
  userId: z.number(),
  currentEquity: z.number(),
  startOfDayEquity: z.number(),
});

const equityLimitUpdateSchema = z.object({
  maxDailyGainPercent: z.number().min(0).max(1000).optional(),
  maxDailyLossPercent: z.number().min(0).max(100).optional(),
  isActive: z.boolean().optional(),
});

const adminResetSchema = z.object({
  userId: z.number(),
  reason: z.string().min(1),
});

interface EquityCheckResult {
  status: "safe" | "warning" | "limit_exceeded";
  limitTriggered: boolean;
  action: string | null;
  currentEquityPercent: number;
  thresholdType?: "gain" | "loss";
  thresholdValue?: number;
  message: string;
}

export function setupEquityLimitsRoutes(app: Express) {
  
  // POST /api/equity-limit/check - Check if equity limits are exceeded
  app.post("/api/equity-limit/check", async (req, res) => {
    if (!req.isAuthenticated()) {
      return res.status(401).json({ message: "Authentication required" });
    }

    try {
      const { userId, currentEquity, startOfDayEquity } = equityCheckSchema.parse(req.body);
      
      // Verify user has permission to check this user's limits
      if (req.user?.id !== userId && req.user?.role !== "admin") {
        return res.status(403).json({ message: "Access denied" });
      }

      // Get user's equity limits
      const userLimits = await db.select()
        .from(equityLimits)
        .where(and(
          eq(equityLimits.userId, userId),
          eq(equityLimits.isActive, true)
        ))
        .limit(1);

      if (userLimits.length === 0) {
        return res.json({
          status: "safe",
          limitTriggered: false,
          action: null,
          currentEquityPercent: 0,
          message: "No equity limits configured"
        } as EquityCheckResult);
      }

      const limits = userLimits[0];
      
      // Calculate current equity change percentage
      const equityChangePercent = ((currentEquity - startOfDayEquity) / startOfDayEquity) * 100;
      
      let result: EquityCheckResult = {
        status: "safe",
        limitTriggered: false,
        action: null,
        currentEquityPercent: equityChangePercent,
        message: "Within equity limits"
      };

      // Check for gain limit exceeded
      if (limits.maxDailyGainPercent && equityChangePercent > Number(limits.maxDailyGainPercent)) {
        result = {
          status: "limit_exceeded",
          limitTriggered: true,
          action: "shutdown_terminals",
          currentEquityPercent: equityChangePercent,
          thresholdType: "gain",
          thresholdValue: Number(limits.maxDailyGainPercent),
          message: `Daily gain limit exceeded: ${equityChangePercent.toFixed(2)}% > ${limits.maxDailyGainPercent}%`
        };

        // Log the limit trigger event
        await logEquityEvent({
          userId,
          eventType: "limit_triggered",
          equityPercent: equityChangePercent,
          triggerThreshold: Number(limits.maxDailyGainPercent),
          action: "shutdown_terminals",
          reason: `Daily gain limit exceeded`
        });

        // Update limits table with trigger info
        await db.update(equityLimits)
          .set({
            lastTriggered: new Date(),
            triggerReason: `Daily gain limit exceeded: ${equityChangePercent.toFixed(2)}%`,
            updatedAt: new Date()
          })
          .where(eq(equityLimits.id, limits.id));
      }
      // Check for loss limit exceeded
      else if (limits.maxDailyLossPercent && equityChangePercent < -Number(limits.maxDailyLossPercent)) {
        result = {
          status: "limit_exceeded",
          limitTriggered: true,
          action: "shutdown_terminals",
          currentEquityPercent: equityChangePercent,
          thresholdType: "loss",
          thresholdValue: Number(limits.maxDailyLossPercent),
          message: `Daily loss limit exceeded: ${Math.abs(equityChangePercent).toFixed(2)}% > ${limits.maxDailyLossPercent}%`
        };

        // Log the limit trigger event
        await logEquityEvent({
          userId,
          eventType: "limit_triggered",
          equityPercent: equityChangePercent,
          triggerThreshold: Number(limits.maxDailyLossPercent),
          action: "shutdown_terminals",
          reason: `Daily loss limit exceeded`
        });

        // Update limits table with trigger info
        await db.update(equityLimits)
          .set({
            lastTriggered: new Date(),
            triggerReason: `Daily loss limit exceeded: ${Math.abs(equityChangePercent).toFixed(2)}%`,
            updatedAt: new Date()
          })
          .where(eq(equityLimits.id, limits.id));
      }
      // Warning zone (80% of limit)
      else if (limits.maxDailyGainPercent && equityChangePercent > Number(limits.maxDailyGainPercent) * 0.8) {
        result.status = "warning";
        result.message = `Approaching daily gain limit: ${equityChangePercent.toFixed(2)}% of ${limits.maxDailyGainPercent}%`;
      }
      else if (limits.maxDailyLossPercent && equityChangePercent < -Number(limits.maxDailyLossPercent) * 0.8) {
        result.status = "warning";
        result.message = `Approaching daily loss limit: ${Math.abs(equityChangePercent).toFixed(2)}% of ${limits.maxDailyLossPercent}%`;
      }

      res.json(result);

    } catch (error) {
      console.error("Equity limit check error:", error);
      if (error instanceof z.ZodError) {
        return res.status(400).json({ 
          message: "Invalid request data",
          errors: error.errors 
        });
      }
      res.status(500).json({ message: "Internal server error" });
    }
  });

  // GET /api/equity-limit/status/:userId - Get current equity limit status
  app.get("/api/equity-limit/status/:userId", async (req, res) => {
    if (!req.isAuthenticated()) {
      return res.status(401).json({ message: "Authentication required" });
    }

    try {
      const userId = parseInt(req.params.userId);
      
      // Verify user has permission
      if (req.user?.id !== userId && req.user?.role !== "admin") {
        return res.status(403).json({ message: "Access denied" });
      }

      // Get user's equity limits
      const userLimits = await db.select()
        .from(equityLimits)
        .where(eq(equityLimits.userId, userId))
        .limit(1);

      if (userLimits.length === 0) {
        return res.json({
          hasLimits: false,
          isActive: false,
          limits: null,
          lastTriggered: null
        });
      }

      const limits = userLimits[0];

      // Get recent events
      const recentEvents = await db.select()
        .from(equityEvents)
        .where(eq(equityEvents.userId, userId))
        .orderBy(desc(equityEvents.timestamp))
        .limit(10);

      res.json({
        hasLimits: true,
        isActive: limits.isActive,
        limits: {
          maxDailyGainPercent: limits.maxDailyGainPercent,
          maxDailyLossPercent: limits.maxDailyLossPercent,
          lastTriggered: limits.lastTriggered,
          triggerReason: limits.triggerReason
        },
        recentEvents: recentEvents.map(event => ({
          eventType: event.eventType,
          equityPercent: event.equityPercent,
          triggerThreshold: event.triggerThreshold,
          action: event.action,
          reason: event.reason,
          timestamp: event.timestamp
        }))
      });

    } catch (error) {
      console.error("Get equity limit status error:", error);
      res.status(500).json({ message: "Internal server error" });
    }
  });

  // PUT /api/equity-limit/:userId - Update equity limits (admin only)
  app.put("/api/equity-limit/:userId", async (req, res) => {
    if (!req.isAuthenticated() || req.user?.role !== "admin") {
      return res.status(403).json({ message: "Admin access required" });
    }

    try {
      const userId = parseInt(req.params.userId);
      const updates = equityLimitUpdateSchema.parse(req.body);

      // Check if user exists
      const user = await db.select().from(users).where(eq(users.id, userId)).limit(1);
      if (user.length === 0) {
        return res.status(404).json({ message: "User not found" });
      }

      // Check if limits already exist
      const existingLimits = await db.select()
        .from(equityLimits)
        .where(eq(equityLimits.userId, userId))
        .limit(1);

      let result;

      if (existingLimits.length === 0) {
        // Create new limits
        const newLimits = await db.insert(equityLimits)
          .values({
            userId,
            maxDailyGainPercent: updates.maxDailyGainPercent?.toString(),
            maxDailyLossPercent: updates.maxDailyLossPercent?.toString(),
            isActive: updates.isActive,
            updatedAt: new Date()
          })
          .returning();
        result = newLimits[0];

        // Log creation event
        await logEquityEvent({
          userId,
          eventType: "manual_override",
          action: "limits_created",
          reason: "Equity limits created by admin",
          adminUserId: req.user.id
        });
      } else {
        // Update existing limits
        const updatedLimits = await db.update(equityLimits)
          .set({
            maxDailyGainPercent: updates.maxDailyGainPercent?.toString(),
            maxDailyLossPercent: updates.maxDailyLossPercent?.toString(),
            isActive: updates.isActive,
            updatedAt: new Date()
          })
          .where(eq(equityLimits.userId, userId))
          .returning();
        result = updatedLimits[0];

        // Log update event
        await logEquityEvent({
          userId,
          eventType: "manual_override",
          action: "limits_updated",
          reason: "Equity limits updated by admin",
          adminUserId: req.user.id
        });
      }

      res.json(result);

    } catch (error) {
      console.error("Update equity limit error:", error);
      if (error instanceof z.ZodError) {
        return res.status(400).json({ 
          message: "Invalid request data",
          errors: error.errors 
        });
      }
      res.status(500).json({ message: "Internal server error" });
    }
  });

  // POST /api/equity-limit/reset/:userId - Reset equity limits (admin only)
  app.post("/api/equity-limit/reset/:userId", async (req, res) => {
    if (!req.isAuthenticated() || req.user?.role !== "admin") {
      return res.status(403).json({ message: "Admin access required" });
    }

    try {
      const userId = parseInt(req.params.userId);
      const { reason } = adminResetSchema.parse(req.body);

      // Reset the limits
      const resetLimits = await db.update(equityLimits)
        .set({
          lastTriggered: null,
          triggerReason: null,
          updatedAt: new Date()
        })
        .where(eq(equityLimits.userId, userId))
        .returning();

      if (resetLimits.length === 0) {
        return res.status(404).json({ message: "No equity limits found for user" });
      }

      // Log reset event
      await logEquityEvent({
        userId,
        eventType: "reset",
        action: "limits_reset",
        reason: `Manual reset by admin: ${reason}`,
        adminUserId: req.user.id
      });

      res.json({
        message: "Equity limits reset successfully",
        limits: resetLimits[0]
      });

    } catch (error) {
      console.error("Reset equity limit error:", error);
      if (error instanceof z.ZodError) {
        return res.status(400).json({ 
          message: "Invalid request data",
          errors: error.errors 
        });
      }
      res.status(500).json({ message: "Internal server error" });
    }
  });

  // GET /api/equity-limit/events/:userId - Get equity events history
  app.get("/api/equity-limit/events/:userId", async (req, res) => {
    if (!req.isAuthenticated()) {
      return res.status(401).json({ message: "Authentication required" });
    }

    try {
      const userId = parseInt(req.params.userId);
      const limit = parseInt(req.query.limit as string) || 50;
      const offset = parseInt(req.query.offset as string) || 0;

      // Verify user has permission
      if (req.user?.id !== userId && req.user?.role !== "admin") {
        return res.status(403).json({ message: "Access denied" });
      }

      // Get events with pagination
      const events = await db.select({
        id: equityEvents.id,
        eventType: equityEvents.eventType,
        equityPercent: equityEvents.equityPercent,
        triggerThreshold: equityEvents.triggerThreshold,
        action: equityEvents.action,
        reason: equityEvents.reason,
        timestamp: equityEvents.timestamp,
        details: equityEvents.details
      })
        .from(equityEvents)
        .where(eq(equityEvents.userId, userId))
        .orderBy(desc(equityEvents.timestamp))
        .limit(limit)
        .offset(offset);

      res.json({
        events,
        pagination: {
          limit,
          offset,
          hasMore: events.length === limit
        }
      });

    } catch (error) {
      console.error("Get equity events error:", error);
      res.status(500).json({ message: "Internal server error" });
    }
  });

  // POST /api/equity-limit/auto-reset - Auto-reset daily limits (called by cron job)
  app.post("/api/equity-limit/auto-reset", async (req, res) => {
    if (!req.isAuthenticated() || req.user?.role !== "admin") {
      return res.status(403).json({ message: "Admin access required" });
    }

    try {
      // Get all limits that were triggered yesterday or earlier
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      yesterday.setHours(23, 59, 59, 999);

      const triggeredLimits = await db.select()
        .from(equityLimits)
        .where(and(
          eq(equityLimits.isActive, true),
          gte(equityLimits.lastTriggered, yesterday)
        ));

      let resetCount = 0;

      for (const limit of triggeredLimits) {
        await db.update(equityLimits)
          .set({
            lastTriggered: null,
            triggerReason: null,
            updatedAt: new Date()
          })
          .where(eq(equityLimits.id, limit.id));

        // Log auto-reset event
        await logEquityEvent({
          userId: limit.userId,
          eventType: "reset",
          action: "auto_reset",
          reason: "Daily automatic reset",
          adminUserId: req.user.id
        });

        resetCount++;
      }

      res.json({
        message: `Auto-reset completed for ${resetCount} users`,
        resetCount
      });

    } catch (error) {
      console.error("Auto-reset equity limits error:", error);
      res.status(500).json({ message: "Internal server error" });
    }
  });
}

// Helper function to log equity events
async function logEquityEvent(eventData: {
  userId: number;
  eventType: string;
  equityPercent?: number;
  triggerThreshold?: number;
  action: string;
  reason: string;
  adminUserId?: number;
}) {
  try {
    await db.insert(equityEvents).values({
      userId: eventData.userId,
      eventType: eventData.eventType,
      equityPercent: eventData.equityPercent?.toString(),
      triggerThreshold: eventData.triggerThreshold?.toString(),
      action: eventData.action,
      reason: eventData.reason,
      adminUserId: eventData.adminUserId,
      details: {}
    });
  } catch (error) {
    console.error("Failed to log equity event:", error);
  }
}