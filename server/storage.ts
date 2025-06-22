import { 
  users, channels, strategies, signals, trades, mt5Status, syncLogs,
  type User, type InsertUser, type Channel, type InsertChannel,
  type Strategy, type InsertStrategy, type Signal, type InsertSignal,
  type Trade, type InsertTrade, type Mt5Status, type InsertMt5Status,
  type SyncLog, type InsertSyncLog
} from "@shared/schema";
import { db } from "./db";
import { eq, desc, and } from "drizzle-orm";
import session from "express-session";
import connectPg from "connect-pg-simple";
import { pool } from "./db";

const PostgresSessionStore = connectPg(session);

export interface IStorage {
  // User operations
  getUser(id: number): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;

  // Channel operations
  getChannels(): Promise<Channel[]>;
  getChannel(id: number): Promise<Channel | undefined>;
  createChannel(channel: InsertChannel): Promise<Channel>;
  updateChannel(id: number, updates: Partial<InsertChannel>): Promise<Channel | undefined>;
  deleteChannel(id: number): Promise<boolean>;

  // Strategy operations
  getUserStrategies(userId: number): Promise<Strategy[]>;
  getStrategy(id: number): Promise<Strategy | undefined>;
  createStrategy(strategy: InsertStrategy): Promise<Strategy>;
  updateStrategy(id: number, updates: Partial<InsertStrategy>): Promise<Strategy | undefined>;
  deleteStrategy(id: number): Promise<boolean>;

  // Signal operations
  getSignals(limit?: number): Promise<Signal[]>;
  getSignal(id: number): Promise<Signal | undefined>;
  createSignal(signal: InsertSignal): Promise<Signal>;
  updateSignal(id: number, updates: Partial<InsertSignal>): Promise<Signal | undefined>;
  getSignalsByChannel(channelId: number): Promise<Signal[]>;

  // Trade operations
  getUserTrades(userId: number, limit?: number): Promise<Trade[]>;
  getActiveTrades(userId: number): Promise<Trade[]>;
  getTrade(id: number): Promise<Trade | undefined>;
  createTrade(trade: InsertTrade): Promise<Trade>;
  updateTrade(id: number, updates: Partial<InsertTrade>): Promise<Trade | undefined>;

  // MT5 Status operations
  getMt5Status(userId: number): Promise<Mt5Status | undefined>;
  updateMt5Status(userId: number, status: InsertMt5Status): Promise<Mt5Status>;

  // Sync Log operations
  getSyncLogs(userId: number, limit?: number): Promise<SyncLog[]>;
  createSyncLog(log: InsertSyncLog): Promise<SyncLog>;

  // Session store
  sessionStore: session.Store;
}

export class DatabaseStorage implements IStorage {
  sessionStore: session.Store;

  constructor() {
    this.sessionStore = new PostgresSessionStore({ 
      pool, 
      createTableIfMissing: true 
    });
  }

  // User operations
  async getUser(id: number): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.id, id));
    return user || undefined;
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.username, username));
    return user || undefined;
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const [user] = await db.insert(users).values(insertUser).returning();
    return user;
  }

  // Channel operations
  async getChannels(): Promise<Channel[]> {
    return await db.select().from(channels).orderBy(desc(channels.createdAt));
  }

  async getChannel(id: number): Promise<Channel | undefined> {
    const [channel] = await db.select().from(channels).where(eq(channels.id, id));
    return channel || undefined;
  }

  async createChannel(channel: InsertChannel): Promise<Channel> {
    const [newChannel] = await db.insert(channels).values(channel).returning();
    return newChannel;
  }

  async updateChannel(id: number, updates: Partial<InsertChannel>): Promise<Channel | undefined> {
    const [updated] = await db.update(channels)
      .set(updates)
      .where(eq(channels.id, id))
      .returning();
    return updated || undefined;
  }

  async deleteChannel(id: number): Promise<boolean> {
    const result = await db.delete(channels).where(eq(channels.id, id));
    return result.rowCount ? result.rowCount > 0 : false;
  }

  // Strategy operations
  async getUserStrategies(userId: number): Promise<Strategy[]> {
    return await db.select().from(strategies)
      .where(eq(strategies.userId, userId))
      .orderBy(desc(strategies.updatedAt));
  }

  async getStrategy(id: number): Promise<Strategy | undefined> {
    const [strategy] = await db.select().from(strategies).where(eq(strategies.id, id));
    return strategy || undefined;
  }

  async createStrategy(strategy: InsertStrategy): Promise<Strategy> {
    const [newStrategy] = await db.insert(strategies).values(strategy).returning();
    return newStrategy;
  }

  async updateStrategy(id: number, updates: Partial<InsertStrategy>): Promise<Strategy | undefined> {
    const [updated] = await db.update(strategies)
      .set({ ...updates, updatedAt: new Date() })
      .where(eq(strategies.id, id))
      .returning();
    return updated || undefined;
  }

  async deleteStrategy(id: number): Promise<boolean> {
    const result = await db.delete(strategies).where(eq(strategies.id, id));
    return result.rowCount ? result.rowCount > 0 : false;
  }

  // Signal operations
  async getSignals(limit: number = 50): Promise<Signal[]> {
    return await db.select().from(signals)
      .orderBy(desc(signals.createdAt))
      .limit(limit);
  }

  async getSignal(id: number): Promise<Signal | undefined> {
    const [signal] = await db.select().from(signals).where(eq(signals.id, id));
    return signal || undefined;
  }

  async createSignal(signal: InsertSignal): Promise<Signal> {
    const [newSignal] = await db.insert(signals).values(signal).returning();
    return newSignal;
  }

  async updateSignal(id: number, updates: Partial<InsertSignal>): Promise<Signal | undefined> {
    const [updated] = await db.update(signals)
      .set(updates)
      .where(eq(signals.id, id))
      .returning();
    return updated || undefined;
  }

  async getSignalsByChannel(channelId: number): Promise<Signal[]> {
    return await db.select().from(signals)
      .where(eq(signals.channelId, channelId))
      .orderBy(desc(signals.createdAt));
  }

  // Trade operations
  async getUserTrades(userId: number, limit: number = 50): Promise<Trade[]> {
    return await db.select().from(trades)
      .where(eq(trades.userId, userId))
      .orderBy(desc(trades.openTime))
      .limit(limit);
  }

  async getActiveTrades(userId: number): Promise<Trade[]> {
    return await db.select().from(trades)
      .where(and(eq(trades.userId, userId), eq(trades.status, "open")))
      .orderBy(desc(trades.openTime));
  }

  async getTrade(id: number): Promise<Trade | undefined> {
    const [trade] = await db.select().from(trades).where(eq(trades.id, id));
    return trade || undefined;
  }

  async createTrade(trade: InsertTrade): Promise<Trade> {
    const [newTrade] = await db.insert(trades).values(trade).returning();
    return newTrade;
  }

  async updateTrade(id: number, updates: Partial<InsertTrade>): Promise<Trade | undefined> {
    const [updated] = await db.update(trades)
      .set(updates)
      .where(eq(trades.id, id))
      .returning();
    return updated || undefined;
  }

  // MT5 Status operations
  async getMt5Status(userId: number): Promise<Mt5Status | undefined> {
    const [status] = await db.select().from(mt5Status)
      .where(eq(mt5Status.userId, userId))
      .orderBy(desc(mt5Status.lastPing))
      .limit(1);
    return status || undefined;
  }

  async updateMt5Status(userId: number, status: InsertMt5Status): Promise<Mt5Status> {
    const existing = await this.getMt5Status(userId);
    
    if (existing) {
      const [updated] = await db.update(mt5Status)
        .set({ ...status, lastPing: new Date() })
        .where(eq(mt5Status.id, existing.id))
        .returning();
      return updated;
    } else {
      const [newStatus] = await db.insert(mt5Status)
        .values({ ...status, userId })
        .returning();
      return newStatus;
    }
  }

  // Sync Log operations
  async getSyncLogs(userId: number, limit: number = 50): Promise<SyncLog[]> {
    return await db.select().from(syncLogs)
      .where(eq(syncLogs.userId, userId))
      .orderBy(desc(syncLogs.timestamp))
      .limit(limit);
  }

  async createSyncLog(log: InsertSyncLog): Promise<SyncLog> {
    const [newLog] = await db.insert(syncLogs).values(log).returning();
    return newLog;
  }
}

export const storage = new DatabaseStorage();
