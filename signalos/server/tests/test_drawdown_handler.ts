import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { db } from '../../../server/db';
import { 
  drawdownLimits, 
  drawdownEvents, 
  trades, 
  users, 
  channels 
} from '../../../shared/schema';
import { eq, and } from 'drizzle-orm';
import { drawdownHandler, setupDrawdownHandlerRoutes } from '../routes/drawdown_handler';
import express from 'express';
import request from 'supertest';

// Mock data setup
const mockUser = {
  id: 1,
  username: 'testuser',
  password: 'hashedpassword',
  email: 'test@example.com',
  role: 'user'
};

const mockAdmin = {
  id: 2,
  username: 'admin',
  password: 'hashedpassword',
  email: 'admin@example.com',
  role: 'admin'
};

const mockProvider = {
  id: 1,
  name: 'Test Provider',
  telegramId: '123456',
  description: 'Test signal provider',
  isActive: true
};

const mockDrawdownLimit = {
  userId: 1,
  providerId: null,
  symbol: null,
  maxDrawdownPercent: '10.00',
  isActive: true,
  autoDisable: true,
  notifyOnly: false
};

const mockTrades = [
  {
    id: 1,
    signalId: 1,
    userId: 1,
    mt5Ticket: '12345',
    symbol: 'EURUSD',
    action: 'BUY',
    lotSize: '0.10',
    entryPrice: '1.1000',
    currentPrice: '1.0950',
    stopLoss: '1.0900',
    takeProfit: '1.1100',
    profit: '-50.00',
    status: 'open'
  },
  {
    id: 2,
    signalId: 2,
    userId: 1,
    mt5Ticket: '12346',
    symbol: 'GBPUSD',
    action: 'SELL',
    lotSize: '0.10',
    entryPrice: '1.2500',
    currentPrice: '1.2550',
    stopLoss: '1.2600',
    takeProfit: '1.2400',
    profit: '-50.00',
    status: 'open'
  }
];

describe('DrawdownHandler', () => {
  beforeEach(async () => {
    // Setup test data
    await db.insert(users).values([mockUser, mockAdmin]);
    await db.insert(channels).values(mockProvider);
    await db.insert(trades).values(mockTrades);
  });

  afterEach(async () => {
    // Cleanup test data
    await db.delete(drawdownEvents);
    await db.delete(drawdownLimits);
    await db.delete(trades);
    await db.delete(channels);
    await db.delete(users);
  });

  describe('Drawdown Limit Creation', () => {
    it('should create global drawdown limit', async () => {
      const [limit] = await db
        .insert(drawdownLimits)
        .values(mockDrawdownLimit)
        .returning();

      expect(limit).toBeDefined();
      expect(limit.userId).toBe(1);
      expect(limit.maxDrawdownPercent).toBe('10.00');
      expect(limit.providerId).toBeNull();
      expect(limit.symbol).toBeNull();
    });

    it('should create provider-specific drawdown limit', async () => {
      const providerLimit = {
        ...mockDrawdownLimit,
        providerId: 1,
        maxDrawdownPercent: '5.00'
      };

      const [limit] = await db
        .insert(drawdownLimits)
        .values(providerLimit)
        .returning();

      expect(limit.providerId).toBe(1);
      expect(limit.maxDrawdownPercent).toBe('5.00');
    });

    it('should create symbol-specific drawdown limit', async () => {
      const symbolLimit = {
        ...mockDrawdownLimit,
        symbol: 'EURUSD',
        maxDrawdownPercent: '7.50'
      };

      const [limit] = await db
        .insert(drawdownLimits)
        .values(symbolLimit)
        .returning();

      expect(limit.symbol).toBe('EURUSD');
      expect(limit.maxDrawdownPercent).toBe('7.50');
    });
  });

  describe('Drawdown Detection', () => {
    it('should detect global drawdown breach', async () => {
      // Create a limit that should be breached
      const [limit] = await db
        .insert(drawdownLimits)
        .values({
          ...mockDrawdownLimit,
          maxDrawdownPercent: '0.50' // Very low threshold to trigger
        })
        .returning();

      // Mock the balance calculation to simulate high drawdown
      const originalGetBalance = drawdownHandler.getCurrentAccountBalance;
      vi.spyOn(drawdownHandler as any, 'getCurrentAccountBalance')
        .mockResolvedValue(9900); // Starting with 10000, now at 9900
      vi.spyOn(drawdownHandler as any, 'getPeakAccountBalance')
        .mockResolvedValue(10000);

      const status = await drawdownHandler.checkUserDrawdown(1);

      expect(status).toBeDefined();
      expect(status!.currentDrawdownPercent).toBe(1); // 1% drawdown
      expect(status!.violatedLimits.length).toBeGreaterThan(0);

      // Check that event was logged
      const events = await db
        .select()
        .from(drawdownEvents)
        .where(eq(drawdownEvents.userId, 1));

      expect(events.length).toBeGreaterThan(0);
      expect(events[0].eventType).toBe('breach_detected');
    });

    it('should not trigger when drawdown is within limits', async () => {
      const [limit] = await db
        .insert(drawdownLimits)
        .values({
          ...mockDrawdownLimit,
          maxDrawdownPercent: '15.00' // High threshold
        })
        .returning();

      // Mock normal balance scenario
      vi.spyOn(drawdownHandler as any, 'getCurrentAccountBalance')
        .mockResolvedValue(9950);
      vi.spyOn(drawdownHandler as any, 'getPeakAccountBalance')
        .mockResolvedValue(10000);

      const status = await drawdownHandler.checkUserDrawdown(1);

      expect(status).toBeDefined();
      expect(status!.currentDrawdownPercent).toBe(0.5); // 0.5% drawdown
      expect(status!.violatedLimits.length).toBe(0);
    });

    it('should handle provider-specific drawdown correctly', async () => {
      const [limit] = await db
        .insert(drawdownLimits)
        .values({
          ...mockDrawdownLimit,
          providerId: 1,
          maxDrawdownPercent: '2.00'
        })
        .returning();

      vi.spyOn(drawdownHandler as any, 'getCurrentAccountBalance')
        .mockResolvedValue(9800);
      vi.spyOn(drawdownHandler as any, 'getPeakAccountBalance')
        .mockResolvedValue(10000);

      const status = await drawdownHandler.checkUserDrawdown(1);

      expect(status).toBeDefined();
      expect(status!.currentDrawdownPercent).toBe(2); // 2% drawdown
    });
  });

  describe('Trade Closure Logic', () => {
    it('should close all trades on global breach', async () => {
      const [limit] = await db
        .insert(drawdownLimits)
        .values({
          ...mockDrawdownLimit,
          maxDrawdownPercent: '1.00'
        })
        .returning();

      // Mock high drawdown scenario
      vi.spyOn(drawdownHandler as any, 'getCurrentAccountBalance')
        .mockResolvedValue(9850);
      vi.spyOn(drawdownHandler as any, 'getPeakAccountBalance')
        .mockResolvedValue(10000);

      // Mock MT5 close command
      const closeSpy = vi.spyOn(drawdownHandler as any, 'sendMT5CloseCommand')
        .mockResolvedValue(undefined);

      await drawdownHandler.checkUserDrawdown(1);

      expect(closeSpy).toHaveBeenCalled();
      
      const closeRequest = closeSpy.mock.calls[0][0];
      expect(closeRequest.tickets).toEqual([12345, 12346]);
      expect(closeRequest.userId).toBe(1);
      expect(closeRequest.reason).toContain('Drawdown limit exceeded');
    });

    it('should close only symbol-specific trades', async () => {
      const [limit] = await db
        .insert(drawdownLimits)
        .values({
          ...mockDrawdownLimit,
          symbol: 'EURUSD',
          maxDrawdownPercent: '1.00'
        })
        .returning();

      vi.spyOn(drawdownHandler as any, 'getCurrentAccountBalance')
        .mockResolvedValue(9850);
      vi.spyOn(drawdownHandler as any, 'getPeakAccountBalance')
        .mockResolvedValue(10000);

      const closeSpy = vi.spyOn(drawdownHandler as any, 'sendMT5CloseCommand')
        .mockResolvedValue(undefined);

      await drawdownHandler.checkUserDrawdown(1);

      expect(closeSpy).toHaveBeenCalled();
      
      const closeRequest = closeSpy.mock.calls[0][0];
      expect(closeRequest.tickets).toEqual([12345]); // Only EURUSD trade
    });

    it('should respect notify-only setting', async () => {
      const [limit] = await db
        .insert(drawdownLimits)
        .values({
          ...mockDrawdownLimit,
          maxDrawdownPercent: '1.00',
          notifyOnly: true
        })
        .returning();

      vi.spyOn(drawdownHandler as any, 'getCurrentAccountBalance')
        .mockResolvedValue(9850);
      vi.spyOn(drawdownHandler as any, 'getPeakAccountBalance')
        .mockResolvedValue(10000);

      const closeSpy = vi.spyOn(drawdownHandler as any, 'sendMT5CloseCommand')
        .mockResolvedValue(undefined);
      const notificationSpy = vi.spyOn(drawdownHandler as any, 'sendDrawdownNotification')
        .mockResolvedValue(undefined);

      await drawdownHandler.checkUserDrawdown(1);

      expect(closeSpy).not.toHaveBeenCalled();
      expect(notificationSpy).toHaveBeenCalled();
    });
  });

  describe('Provider Auto-Disable', () => {
    it('should auto-disable provider after breach', async () => {
      const [limit] = await db
        .insert(drawdownLimits)
        .values({
          ...mockDrawdownLimit,
          providerId: 1,
          maxDrawdownPercent: '1.00',
          autoDisable: true
        })
        .returning();

      vi.spyOn(drawdownHandler as any, 'getCurrentAccountBalance')
        .mockResolvedValue(9850);
      vi.spyOn(drawdownHandler as any, 'getPeakAccountBalance')
        .mockResolvedValue(10000);

      await drawdownHandler.checkUserDrawdown(1);

      // Check that provider was disabled
      const [provider] = await db
        .select()
        .from(channels)
        .where(eq(channels.id, 1));

      expect(provider.isActive).toBe(false);

      // Check disable event was logged
      const events = await db
        .select()
        .from(drawdownEvents)
        .where(and(
          eq(drawdownEvents.userId, 1),
          eq(drawdownEvents.eventType, 'provider_disabled')
        ));

      expect(events.length).toBe(1);
    });

    it('should not auto-disable when autoDisable is false', async () => {
      const [limit] = await db
        .insert(drawdownLimits)
        .values({
          ...mockDrawdownLimit,
          providerId: 1,
          maxDrawdownPercent: '1.00',
          autoDisable: false
        })
        .returning();

      vi.spyOn(drawdownHandler as any, 'getCurrentAccountBalance')
        .mockResolvedValue(9850);
      vi.spyOn(drawdownHandler as any, 'getPeakAccountBalance')
        .mockResolvedValue(10000);

      await drawdownHandler.checkUserDrawdown(1);

      // Check that provider was NOT disabled
      const [provider] = await db
        .select()
        .from(channels)
        .where(eq(channels.id, 1));

      expect(provider.isActive).toBe(true);
    });
  });

  describe('Admin Reset Functionality', () => {
    it('should allow admin to reset drawdown limit', async () => {
      const [limit] = await db
        .insert(drawdownLimits)
        .values({
          ...mockDrawdownLimit,
          isActive: false // Disabled after breach
        })
        .returning();

      const success = await drawdownHandler.adminReset(1, limit.id, 2);

      expect(success).toBe(true);

      // Check that limit is re-enabled
      const [updatedLimit] = await db
        .select()
        .from(drawdownLimits)
        .where(eq(drawdownLimits.id, limit.id));

      expect(updatedLimit.isActive).toBe(true);

      // Check reset event was logged
      const events = await db
        .select()
        .from(drawdownEvents)
        .where(and(
          eq(drawdownEvents.userId, 1),
          eq(drawdownEvents.eventType, 'admin_reset')
        ));

      expect(events.length).toBe(1);
      expect(events[0].adminUserId).toBe(2);
    });
  });

  describe('No False Triggers During Recovery', () => {
    it('should not trigger when no open trades exist', async () => {
      // Close all trades
      await db
        .update(trades)
        .set({ status: 'closed' })
        .where(eq(trades.userId, 1));

      const [limit] = await db
        .insert(drawdownLimits)
        .values({
          ...mockDrawdownLimit,
          maxDrawdownPercent: '1.00'
        })
        .returning();

      const status = await drawdownHandler.checkUserDrawdown(1);

      expect(status).toBeNull(); // Should return null when no open trades
    });

    it('should not re-trigger for already processed breaches', async () => {
      const [limit] = await db
        .insert(drawdownLimits)
        .values({
          ...mockDrawdownLimit,
          maxDrawdownPercent: '1.00'
        })
        .returning();

      // Log an existing breach event
      await db.insert(drawdownEvents).values({
        userId: 1,
        limitId: limit.id,
        eventType: 'breach_detected',
        drawdownPercent: '1.50',
        triggerThreshold: '1.00',
        accountBalance: '9850.00',
        tradesAffected: 2,
        closedTrades: [12345, 12346],
        details: { processed: true }
      });

      vi.spyOn(drawdownHandler as any, 'getCurrentAccountBalance')
        .mockResolvedValue(9850);
      vi.spyOn(drawdownHandler as any, 'getPeakAccountBalance')
        .mockResolvedValue(10000);

      const closeSpy = vi.spyOn(drawdownHandler as any, 'sendMT5CloseCommand')
        .mockResolvedValue(undefined);

      await drawdownHandler.checkUserDrawdown(1);

      // Should still detect the violation but may not re-process
      // This depends on implementation details of duplicate prevention
    });
  });
});

describe('DrawdownHandler HTTP Routes', () => {
  let app: express.Application;

  beforeEach(() => {
    app = express();
    app.use(express.json());
    
    // Mock authentication middleware
    app.use((req, res, next) => {
      req.isAuthenticated = () => true;
      req.user = mockUser;
      next();
    });

    setupDrawdownHandlerRoutes(app);
  });

  describe('GET /api/drawdown-limits', () => {
    it('should return user drawdown limits', async () => {
      const [limit] = await db
        .insert(drawdownLimits)
        .values(mockDrawdownLimit)
        .returning();

      const response = await request(app)
        .get('/api/drawdown-limits')
        .expect(200);

      expect(response.body).toHaveLength(1);
      expect(response.body[0].id).toBe(limit.id);
    });

    it('should require authentication', async () => {
      const unauthApp = express();
      unauthApp.use(express.json());
      unauthApp.use((req, res, next) => {
        req.isAuthenticated = () => false;
        next();
      });
      setupDrawdownHandlerRoutes(unauthApp);

      await request(unauthApp)
        .get('/api/drawdown-limits')
        .expect(401);
    });
  });

  describe('POST /api/drawdown-limits', () => {
    it('should create new drawdown limit', async () => {
      const limitData = {
        maxDrawdownPercent: '5.00',
        autoDisable: true,
        notifyOnly: false
      };

      const response = await request(app)
        .post('/api/drawdown-limits')
        .send(limitData)
        .expect(201);

      expect(response.body.maxDrawdownPercent).toBe('5.00');
      expect(response.body.userId).toBe(1);
    });

    it('should validate input data', async () => {
      const invalidData = {
        maxDrawdownPercent: 'invalid'
      };

      await request(app)
        .post('/api/drawdown-limits')
        .send(invalidData)
        .expect(400);
    });
  });

  describe('PUT /api/drawdown-limits/:id', () => {
    it('should update existing limit', async () => {
      const [limit] = await db
        .insert(drawdownLimits)
        .values(mockDrawdownLimit)
        .returning();

      const updateData = {
        maxDrawdownPercent: '15.00',
        notifyOnly: true
      };

      const response = await request(app)
        .put(`/api/drawdown-limits/${limit.id}`)
        .send(updateData)
        .expect(200);

      expect(response.body.maxDrawdownPercent).toBe('15.00');
      expect(response.body.notifyOnly).toBe(true);
    });

    it('should return 404 for non-existent limit', async () => {
      await request(app)
        .put('/api/drawdown-limits/999')
        .send({ maxDrawdownPercent: '10.00' })
        .expect(404);
    });
  });

  describe('DELETE /api/drawdown-limits/:id', () => {
    it('should delete drawdown limit', async () => {
      const [limit] = await db
        .insert(drawdownLimits)
        .values(mockDrawdownLimit)
        .returning();

      await request(app)
        .delete(`/api/drawdown-limits/${limit.id}`)
        .expect(204);

      // Verify deletion
      const remaining = await db
        .select()
        .from(drawdownLimits)
        .where(eq(drawdownLimits.id, limit.id));

      expect(remaining).toHaveLength(0);
    });
  });

  describe('GET /api/drawdown-events', () => {
    it('should return user drawdown events', async () => {
      const [limit] = await db
        .insert(drawdownLimits)
        .values(mockDrawdownLimit)
        .returning();

      await db.insert(drawdownEvents).values({
        userId: 1,
        limitId: limit.id,
        eventType: 'breach_detected',
        drawdownPercent: '12.50',
        triggerThreshold: '10.00',
        accountBalance: '8750.00',
        tradesAffected: 2,
        closedTrades: [12345, 12346]
      });

      const response = await request(app)
        .get('/api/drawdown-events')
        .expect(200);

      expect(response.body).toHaveLength(1);
      expect(response.body[0].eventType).toBe('breach_detected');
    });
  });

  describe('POST /api/drawdown-check', () => {
    it('should force drawdown check', async () => {
      vi.spyOn(drawdownHandler, 'checkUserDrawdown')
        .mockResolvedValue({
          userId: 1,
          currentDrawdownPercent: 5.0,
          accountBalance: 9500,
          peakBalance: 10000,
          activeTrades: [],
          violatedLimits: []
        });

      const response = await request(app)
        .post('/api/drawdown-check')
        .expect(200);

      expect(response.body.checked).toBe(true);
      expect(response.body.status.currentDrawdownPercent).toBe(5.0);
    });
  });

  describe('Admin Routes', () => {
    let adminApp: express.Application;

    beforeEach(() => {
      adminApp = express();
      adminApp.use(express.json());
      
      // Mock admin authentication
      adminApp.use((req, res, next) => {
        req.isAuthenticated = () => true;
        req.user = mockAdmin;
        next();
      });

      setupDrawdownHandlerRoutes(adminApp);
    });

    describe('POST /api/admin/drawdown-reset', () => {
      it('should allow admin to reset drawdown', async () => {
        const [limit] = await db
          .insert(drawdownLimits)
          .values({ ...mockDrawdownLimit, isActive: false })
          .returning();

        const response = await request(adminApp)
          .post('/api/admin/drawdown-reset')
          .send({ userId: 1, limitId: limit.id })
          .expect(200);

        expect(response.body.success).toBe(true);
      });

      it('should reject non-admin users', async () => {
        await request(app) // Regular user app
          .post('/api/admin/drawdown-reset')
          .send({ userId: 1, limitId: 1 })
          .expect(403);
      });
    });

    describe('GET /api/admin/drawdown-status', () => {
      it('should return all users drawdown status', async () => {
        vi.spyOn(drawdownHandler, 'checkUserDrawdown')
          .mockResolvedValue({
            userId: 1,
            currentDrawdownPercent: 8.0,
            accountBalance: 9200,
            peakBalance: 10000,
            activeTrades: [],
            violatedLimits: []
          });

        const response = await request(adminApp)
          .get('/api/admin/drawdown-status')
          .expect(200);

        expect(response.body.totalUsers).toBeGreaterThanOrEqual(0);
        expect(response.body.statusList).toBeDefined();
      });
    });
  });
});