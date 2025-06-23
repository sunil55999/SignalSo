import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import request from 'supertest';
import express from 'express';
import session from 'express-session';
import { db } from '../db';
import { users, equityLimits, equityEvents } from '@shared/schema';
import { setupEquityLimitsRoutes } from '../routes/equity_limits';
import { eq } from 'drizzle-orm';

// Test app setup
function createTestApp() {
  const app = express();
  
  app.use(express.json());
  app.use(session({
    secret: 'test-secret',
    resave: false,
    saveUninitialized: false,
    cookie: { secure: false }
  }));

  // Mock authentication middleware
  app.use((req, res, next) => {
    req.isAuthenticated = () => !!req.session?.user;
    req.user = req.session?.user;
    next();
  });

  setupEquityLimitsRoutes(app);
  return app;
}

// Helper to authenticate user in session
function authenticateUser(agent: any, user: any) {
  return agent
    .post('/login')
    .send({ user })
    .then(() => {
      agent.auth = { user };
    });
}

describe('Equity Limits API', () => {
  let app: express.Application;
  let testUserId: number;
  let adminUserId: number;

  beforeEach(async () => {
    app = createTestApp();

    // Create test users
    const testUsers = await db.insert(users).values([
      { username: 'testuser', password: 'hashedpassword', role: 'user' },
      { username: 'admin', password: 'hashedpassword', role: 'admin' }
    ]).returning();

    testUserId = testUsers[0].id;
    adminUserId = testUsers[1].id;
  });

  afterEach(async () => {
    // Cleanup test data
    await db.delete(equityEvents);
    await db.delete(equityLimits);
    await db.delete(users);
  });

  describe('POST /api/equity-limit/check', () => {
    it('should return safe status when no limits configured', async () => {
      const agent = request.agent(app);
      agent.session = { user: { id: testUserId, role: 'user' } };

      const response = await agent
        .post('/api/equity-limit/check')
        .send({
          userId: testUserId,
          currentEquity: 10500,
          startOfDayEquity: 10000
        });

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('safe');
      expect(response.body.limitTriggered).toBe(false);
      expect(response.body.message).toBe('No equity limits configured');
    });

    it('should trigger gain limit when exceeded', async () => {
      // Create equity limits
      await db.insert(equityLimits).values({
        userId: testUserId,
        maxDailyGainPercent: '5.0', // 5% gain limit
        maxDailyLossPercent: '10.0',
        isActive: true
      });

      const agent = request.agent(app);
      agent.session = { user: { id: testUserId, role: 'user' } };

      const response = await agent
        .post('/api/equity-limit/check')
        .send({
          userId: testUserId,
          currentEquity: 11000, // 10% gain (exceeds 5% limit)
          startOfDayEquity: 10000
        });

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('limit_exceeded');
      expect(response.body.limitTriggered).toBe(true);
      expect(response.body.action).toBe('shutdown_terminals');
      expect(response.body.thresholdType).toBe('gain');
      expect(response.body.currentEquityPercent).toBe(10);
    });

    it('should trigger loss limit when exceeded', async () => {
      // Create equity limits
      await db.insert(equityLimits).values({
        userId: testUserId,
        maxDailyGainPercent: '10.0',
        maxDailyLossPercent: '5.0', // 5% loss limit
        isActive: true
      });

      const agent = request.agent(app);
      agent.session = { user: { id: testUserId, role: 'user' } };

      const response = await agent
        .post('/api/equity-limit/check')
        .send({
          userId: testUserId,
          currentEquity: 9000, // 10% loss (exceeds 5% limit)
          startOfDayEquity: 10000
        });

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('limit_exceeded');
      expect(response.body.limitTriggered).toBe(true);
      expect(response.body.action).toBe('shutdown_terminals');
      expect(response.body.thresholdType).toBe('loss');
      expect(Math.abs(response.body.currentEquityPercent)).toBe(10);
    });

    it('should show warning when approaching limits', async () => {
      // Create equity limits
      await db.insert(equityLimits).values({
        userId: testUserId,
        maxDailyGainPercent: '10.0', // 10% gain limit
        maxDailyLossPercent: '10.0',
        isActive: true
      });

      const agent = request.agent(app);
      agent.session = { user: { id: testUserId, role: 'user' } };

      const response = await agent
        .post('/api/equity-limit/check')
        .send({
          userId: testUserId,
          currentEquity: 10850, // 8.5% gain (85% of 10% limit)
          startOfDayEquity: 10000
        });

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('warning');
      expect(response.body.limitTriggered).toBe(false);
      expect(response.body.message).toContain('Approaching daily gain limit');
    });

    it('should deny access for unauthorized user', async () => {
      const agent = request.agent(app);
      // No authentication

      const response = await agent
        .post('/api/equity-limit/check')
        .send({
          userId: testUserId,
          currentEquity: 10500,
          startOfDayEquity: 10000
        });

      expect(response.status).toBe(401);
    });

    it('should deny access when checking other user limits', async () => {
      const otherUserId = testUserId + 1;
      
      const agent = request.agent(app);
      agent.session = { user: { id: testUserId, role: 'user' } };

      const response = await agent
        .post('/api/equity-limit/check')
        .send({
          userId: otherUserId,
          currentEquity: 10500,
          startOfDayEquity: 10000
        });

      expect(response.status).toBe(403);
    });
  });

  describe('GET /api/equity-limit/status/:userId', () => {
    it('should return status when user has limits', async () => {
      // Create equity limits
      const limits = await db.insert(equityLimits).values({
        userId: testUserId,
        maxDailyGainPercent: '10.0',
        maxDailyLossPercent: '5.0',
        isActive: true
      }).returning();

      const agent = request.agent(app);
      agent.session = { user: { id: testUserId, role: 'user' } };

      const response = await agent
        .get(`/api/equity-limit/status/${testUserId}`);

      expect(response.status).toBe(200);
      expect(response.body.hasLimits).toBe(true);
      expect(response.body.isActive).toBe(true);
      expect(response.body.limits.maxDailyGainPercent).toBe('10.0');
      expect(response.body.limits.maxDailyLossPercent).toBe('5.0');
    });

    it('should return no limits when user has none', async () => {
      const agent = request.agent(app);
      agent.session = { user: { id: testUserId, role: 'user' } };

      const response = await agent
        .get(`/api/equity-limit/status/${testUserId}`);

      expect(response.status).toBe(200);
      expect(response.body.hasLimits).toBe(false);
      expect(response.body.isActive).toBe(false);
      expect(response.body.limits).toBe(null);
    });
  });

  describe('PUT /api/equity-limit/:userId', () => {
    it('should create new limits (admin only)', async () => {
      const agent = request.agent(app);
      agent.session = { user: { id: adminUserId, role: 'admin' } };

      const response = await agent
        .put(`/api/equity-limit/${testUserId}`)
        .send({
          maxDailyGainPercent: 15.0,
          maxDailyLossPercent: 8.0,
          isActive: true
        });

      expect(response.status).toBe(200);
      expect(response.body.maxDailyGainPercent).toBe('15');
      expect(response.body.maxDailyLossPercent).toBe('8');
      expect(response.body.isActive).toBe(true);

      // Verify in database
      const dbLimits = await db.select()
        .from(equityLimits)
        .where(eq(equityLimits.userId, testUserId));
      
      expect(dbLimits).toHaveLength(1);
      expect(dbLimits[0].maxDailyGainPercent).toBe('15');
    });

    it('should update existing limits (admin only)', async () => {
      // Create existing limits
      await db.insert(equityLimits).values({
        userId: testUserId,
        maxDailyGainPercent: '10.0',
        maxDailyLossPercent: '5.0',
        isActive: true
      });

      const agent = request.agent(app);
      agent.session = { user: { id: adminUserId, role: 'admin' } };

      const response = await agent
        .put(`/api/equity-limit/${testUserId}`)
        .send({
          maxDailyGainPercent: 20.0,
          isActive: false
        });

      expect(response.status).toBe(200);
      expect(response.body.maxDailyGainPercent).toBe('20');
      expect(response.body.isActive).toBe(false);
    });

    it('should deny access for non-admin users', async () => {
      const agent = request.agent(app);
      agent.session = { user: { id: testUserId, role: 'user' } };

      const response = await agent
        .put(`/api/equity-limit/${testUserId}`)
        .send({
          maxDailyGainPercent: 15.0
        });

      expect(response.status).toBe(403);
    });

    it('should return 404 for non-existent user', async () => {
      const agent = request.agent(app);
      agent.session = { user: { id: adminUserId, role: 'admin' } };

      const response = await agent
        .put('/api/equity-limit/99999')
        .send({
          maxDailyGainPercent: 15.0
        });

      expect(response.status).toBe(404);
    });
  });

  describe('POST /api/equity-limit/reset/:userId', () => {
    it('should reset limits (admin only)', async () => {
      // Create limits with trigger data
      await db.insert(equityLimits).values({
        userId: testUserId,
        maxDailyGainPercent: '10.0',
        maxDailyLossPercent: '5.0',
        isActive: true,
        lastTriggered: new Date(),
        triggerReason: 'Test trigger'
      });

      const agent = request.agent(app);
      agent.session = { user: { id: adminUserId, role: 'admin' } };

      const response = await agent
        .post(`/api/equity-limit/reset/${testUserId}`)
        .send({
          reason: 'Manual reset for testing'
        });

      expect(response.status).toBe(200);
      expect(response.body.message).toBe('Equity limits reset successfully');
      expect(response.body.limits.lastTriggered).toBe(null);
      expect(response.body.limits.triggerReason).toBe(null);
    });

    it('should deny access for non-admin users', async () => {
      const agent = request.agent(app);
      agent.session = { user: { id: testUserId, role: 'user' } };

      const response = await agent
        .post(`/api/equity-limit/reset/${testUserId}`)
        .send({
          reason: 'Test reset'
        });

      expect(response.status).toBe(403);
    });

    it('should return 404 when no limits exist', async () => {
      const agent = request.agent(app);
      agent.session = { user: { id: adminUserId, role: 'admin' } };

      const response = await agent
        .post(`/api/equity-limit/reset/${testUserId}`)
        .send({
          reason: 'Test reset'
        });

      expect(response.status).toBe(404);
    });
  });

  describe('GET /api/equity-limit/events/:userId', () => {
    it('should return events with pagination', async () => {
      // Create test events
      await db.insert(equityEvents).values([
        {
          userId: testUserId,
          eventType: 'limit_triggered',
          equityPercent: '10.5',
          triggerThreshold: '10.0',
          action: 'shutdown_terminals',
          reason: 'Daily gain limit exceeded'
        },
        {
          userId: testUserId,
          eventType: 'reset',
          action: 'limits_reset',
          reason: 'Manual reset by admin',
          adminUserId: adminUserId
        }
      ]);

      const agent = request.agent(app);
      agent.session = { user: { id: testUserId, role: 'user' } };

      const response = await agent
        .get(`/api/equity-limit/events/${testUserId}`)
        .query({ limit: 10, offset: 0 });

      expect(response.status).toBe(200);
      expect(response.body.events).toHaveLength(2);
      expect(response.body.pagination.limit).toBe(10);
      expect(response.body.pagination.offset).toBe(0);
    });

    it('should deny access for unauthorized user', async () => {
      const agent = request.agent(app);
      // No authentication

      const response = await agent
        .get(`/api/equity-limit/events/${testUserId}`);

      expect(response.status).toBe(401);
    });
  });

  describe('POST /api/equity-limit/auto-reset', () => {
    it('should auto-reset triggered limits (admin only)', async () => {
      // Create limits that were triggered yesterday
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);

      await db.insert(equityLimits).values({
        userId: testUserId,
        maxDailyGainPercent: '10.0',
        maxDailyLossPercent: '5.0',
        isActive: true,
        lastTriggered: yesterday,
        triggerReason: 'Daily gain limit exceeded'
      });

      const agent = request.agent(app);
      agent.session = { user: { id: adminUserId, role: 'admin' } };

      const response = await agent
        .post('/api/equity-limit/auto-reset');

      expect(response.status).toBe(200);
      expect(response.body.message).toContain('Auto-reset completed');
      expect(response.body.resetCount).toBeGreaterThanOrEqual(0);
    });

    it('should deny access for non-admin users', async () => {
      const agent = request.agent(app);
      agent.session = { user: { id: testUserId, role: 'user' } };

      const response = await agent
        .post('/api/equity-limit/auto-reset');

      expect(response.status).toBe(403);
    });
  });

  describe('Input validation', () => {
    it('should validate equity check request data', async () => {
      const agent = request.agent(app);
      agent.session = { user: { id: testUserId, role: 'user' } };

      const response = await agent
        .post('/api/equity-limit/check')
        .send({
          userId: 'invalid', // Should be number
          currentEquity: 10500,
          startOfDayEquity: 10000
        });

      expect(response.status).toBe(400);
      expect(response.body.message).toBe('Invalid request data');
    });

    it('should validate limit update data', async () => {
      const agent = request.agent(app);
      agent.session = { user: { id: adminUserId, role: 'admin' } };

      const response = await agent
        .put(`/api/equity-limit/${testUserId}`)
        .send({
          maxDailyGainPercent: 150.0, // Should be <= 100
        });

      expect(response.status).toBe(400);
      expect(response.body.message).toBe('Invalid request data');
    });

    it('should validate reset request data', async () => {
      await db.insert(equityLimits).values({
        userId: testUserId,
        maxDailyGainPercent: '10.0',
        isActive: true
      });

      const agent = request.agent(app);
      agent.session = { user: { id: adminUserId, role: 'admin' } };

      const response = await agent
        .post(`/api/equity-limit/reset/${testUserId}`)
        .send({
          reason: '' // Should not be empty
        });

      expect(response.status).toBe(400);
      expect(response.body.message).toBe('Invalid request data');
    });
  });

  describe('Edge cases', () => {
    it('should handle zero equity change', async () => {
      await db.insert(equityLimits).values({
        userId: testUserId,
        maxDailyGainPercent: '10.0',
        maxDailyLossPercent: '5.0',
        isActive: true
      });

      const agent = request.agent(app);
      agent.session = { user: { id: testUserId, role: 'user' } };

      const response = await agent
        .post('/api/equity-limit/check')
        .send({
          userId: testUserId,
          currentEquity: 10000, // No change
          startOfDayEquity: 10000
        });

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('safe');
      expect(response.body.currentEquityPercent).toBe(0);
    });

    it('should handle inactive limits', async () => {
      await db.insert(equityLimits).values({
        userId: testUserId,
        maxDailyGainPercent: '1.0', // Very low limit
        maxDailyLossPercent: '1.0',
        isActive: false // Inactive
      });

      const agent = request.agent(app);
      agent.session = { user: { id: testUserId, role: 'user' } };

      const response = await agent
        .post('/api/equity-limit/check')
        .send({
          userId: testUserId,
          currentEquity: 15000, // 50% gain
          startOfDayEquity: 10000
        });

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('safe'); // Should be safe because limits are inactive
    });

    it('should handle limits exactly at threshold', async () => {
      await db.insert(equityLimits).values({
        userId: testUserId,
        maxDailyGainPercent: '10.0',
        maxDailyLossPercent: '5.0',
        isActive: true
      });

      const agent = request.agent(app);
      agent.session = { user: { id: testUserId, role: 'user' } };

      const response = await agent
        .post('/api/equity-limit/check')
        .send({
          userId: testUserId,
          currentEquity: 11000, // Exactly 10% gain
          startOfDayEquity: 10000
        });

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('safe'); // Should be safe at exact threshold
    });
  });
});