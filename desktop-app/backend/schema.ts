import { pgTable, text, timestamp, boolean, integer, decimal, json } from 'drizzle-orm/pg-core';
import { createInsertSchema } from 'drizzle-zod';
import { z } from 'zod';

// Users table for authentication
export const users = pgTable('users', {
  id: text('id').primaryKey(),
  username: text('username').notNull().unique(),
  email: text('email').notNull().unique(),
  passwordHash: text('password_hash').notNull(),
  telegramId: text('telegram_id'),
  role: text('role').default('user'),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

// Channels table for Telegram channel management
export const channels = pgTable('channels', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  telegramId: text('telegram_id').notNull().unique(),
  isActive: boolean('is_active').default(true),
  config: json('config'),
  userId: text('user_id').references(() => users.id),
  createdAt: timestamp('created_at').defaultNow(),
});

// Signals table for parsed trading signals
export const signals = pgTable('signals', {
  id: text('id').primaryKey(),
  rawMessage: text('raw_message').notNull(),
  parsedData: json('parsed_data'),
  symbol: text('symbol'),
  action: text('action'), // BUY, SELL
  entryPrice: decimal('entry_price', { precision: 10, scale: 5 }),
  stopLoss: decimal('stop_loss', { precision: 10, scale: 5 }),
  takeProfit: text('take_profit').array(), // Array of TP levels
  confidence: decimal('confidence', { precision: 5, scale: 2 }),
  status: text('status').default('pending'), // pending, executed, failed
  channelId: text('channel_id').references(() => channels.id),
  createdAt: timestamp('created_at').defaultNow(),
});

// Trades table for executed trades
export const trades = pgTable('trades', {
  id: text('id').primaryKey(),
  signalId: text('signal_id').references(() => signals.id),
  ticket: text('ticket'),
  symbol: text('symbol').notNull(),
  action: text('action').notNull(),
  volume: decimal('volume', { precision: 10, scale: 2 }),
  openPrice: decimal('open_price', { precision: 10, scale: 5 }),
  closePrice: decimal('close_price', { precision: 10, scale: 5 }),
  profit: decimal('profit', { precision: 10, scale: 2 }),
  status: text('status').default('open'), // open, closed, cancelled
  openTime: timestamp('open_time').defaultNow(),
  closeTime: timestamp('close_time'),
});

// MT5 Status table for connection monitoring
export const mt5Status = pgTable('mt5_status', {
  id: text('id').primaryKey(),
  isConnected: boolean('is_connected').default(false),
  accountInfo: json('account_info'),
  balance: decimal('balance', { precision: 15, scale: 2 }),
  equity: decimal('equity', { precision: 15, scale: 2 }),
  margin: decimal('margin', { precision: 15, scale: 2 }),
  lastUpdate: timestamp('last_update').defaultNow(),
});

// Logs table for system logs
export const logs = pgTable('logs', {
  id: text('id').primaryKey(),
  level: text('level').notNull(), // info, warning, error
  message: text('message').notNull(),
  component: text('component'), // parser, executor, telegram, etc.
  data: json('data'),
  createdAt: timestamp('created_at').defaultNow(),
});

// Create insert schemas using drizzle-zod
export const insertUserSchema = createInsertSchema(users).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export const insertChannelSchema = createInsertSchema(channels).omit({
  id: true,
  createdAt: true,
});

export const insertSignalSchema = createInsertSchema(signals).omit({
  id: true,
  createdAt: true,
});

export const insertTradeSchema = createInsertSchema(trades).omit({
  id: true,
  openTime: true,
  closeTime: true,
});

export const insertMt5StatusSchema = createInsertSchema(mt5Status).omit({
  id: true,
  lastUpdate: true,
});

export const insertLogSchema = createInsertSchema(logs).omit({
  id: true,
  createdAt: true,
});

// Create types
export type User = typeof users.$inferSelect;
export type InsertUser = z.infer<typeof insertUserSchema>;

export type Channel = typeof channels.$inferSelect;
export type InsertChannel = z.infer<typeof insertChannelSchema>;

export type Signal = typeof signals.$inferSelect;
export type InsertSignal = z.infer<typeof insertSignalSchema>;

export type Trade = typeof trades.$inferSelect;
export type InsertTrade = z.infer<typeof insertTradeSchema>;

export type Mt5Status = typeof mt5Status.$inferSelect;
export type InsertMt5Status = z.infer<typeof insertMt5StatusSchema>;

export type Log = typeof logs.$inferSelect;
export type InsertLog = z.infer<typeof insertLogSchema>;

// Additional types for SignalOS specific data
export type ParsedSignalData = {
  symbol: string;
  action: 'BUY' | 'SELL';
  entryPrice: number;
  stopLoss: number;
  takeProfit: number[];
  confidence: number;
  metadata?: any;
};

export type TelegramConfig = {
  apiId: string;
  apiHash: string;
  phoneNumber: string;
  channelIds: string[];
};

export type MT5Config = {
  server: string;
  login: string;
  password: string;
  path: string;
};

export type ParserConfig = {
  aiModel: string;
  confidenceThreshold: number;
  fallbackEnabled: boolean;
  language: string;
};

export type SystemConfig = {
  telegram: TelegramConfig;
  mt5: MT5Config;
  parser: ParserConfig;
  riskManagement: {
    maxLotSize: number;
    maxDrawdown: number;
    maxDailyTrades: number;
  };
};