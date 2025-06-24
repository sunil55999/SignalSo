import { pgTable, text, serial, integer, boolean, timestamp, decimal, jsonb } from "drizzle-orm/pg-core";
import { relations } from "drizzle-orm";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
  email: text("email"),
  role: text("role").default("user"),
  createdAt: timestamp("created_at").defaultNow(),
});

export const channels = pgTable("channels", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  telegramId: text("telegram_id").unique(),
  description: text("description"),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at").defaultNow(),
});

export const strategies = pgTable("strategies", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").references(() => users.id),
  name: text("name").notNull(),
  config: jsonb("config").$type<Record<string, any>>(),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const signals = pgTable("signals", {
  id: serial("id").primaryKey(),
  channelId: integer("channel_id").references(() => channels.id),
  symbol: text("symbol").notNull(),
  action: text("action").notNull(), // BUY, SELL, PENDING
  entry: decimal("entry", { precision: 10, scale: 5 }),
  stopLoss: decimal("stop_loss", { precision: 10, scale: 5 }),
  takeProfit1: decimal("take_profit_1", { precision: 10, scale: 5 }),
  takeProfit2: decimal("take_profit_2", { precision: 10, scale: 5 }),
  takeProfit3: decimal("take_profit_3", { precision: 10, scale: 5 }),
  takeProfit4: decimal("take_profit_4", { precision: 10, scale: 5 }),
  takeProfit5: decimal("take_profit_5", { precision: 10, scale: 5 }),
  confidence: decimal("confidence", { precision: 5, scale: 2 }),
  status: text("status").default("pending"), // pending, executed, failed, skipped
  rawMessage: text("raw_message"),
  parsedData: jsonb("parsed_data").$type<Record<string, any>>(),
  createdAt: timestamp("created_at").defaultNow(),
});

export const trades = pgTable("trades", {
  id: serial("id").primaryKey(),
  signalId: integer("signal_id").references(() => signals.id),
  userId: integer("user_id").references(() => users.id),
  mt5Ticket: text("mt5_ticket"),
  symbol: text("symbol").notNull(),
  action: text("action").notNull(),
  lotSize: decimal("lot_size", { precision: 8, scale: 2 }),
  entryPrice: decimal("entry_price", { precision: 10, scale: 5 }),
  currentPrice: decimal("current_price", { precision: 10, scale: 5 }),
  stopLoss: decimal("stop_loss", { precision: 10, scale: 5 }),
  takeProfit: decimal("take_profit", { precision: 10, scale: 5 }),
  profit: decimal("profit", { precision: 10, scale: 2 }),
  status: text("status").default("open"), // open, closed, pending
  openTime: timestamp("open_time").defaultNow(),
  closeTime: timestamp("close_time"),
});

export const mt5Status = pgTable("mt5_status", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").references(() => users.id),
  terminalId: text("terminal_id"),
  isConnected: boolean("is_connected").default(false),
  lastPing: timestamp("last_ping").defaultNow(),
  latency: integer("latency"),
  serverInfo: jsonb("server_info").$type<Record<string, any>>(),
});

export const syncLogs = pgTable("sync_logs", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").references(() => users.id),
  action: text("action").notNull(),
  status: text("status").notNull(),
  details: jsonb("details").$type<Record<string, any>>(),
  timestamp: timestamp("timestamp").defaultNow(),
});

export const equityLimits = pgTable("equity_limits", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").references(() => users.id).notNull(),
  maxDailyGainPercent: decimal("max_daily_gain_percent", { precision: 5, scale: 2 }),
  maxDailyLossPercent: decimal("max_daily_loss_percent", { precision: 5, scale: 2 }),
  isActive: boolean("is_active").default(true),
  lastTriggered: timestamp("last_triggered"),
  triggerReason: text("trigger_reason"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const providerStats = pgTable("provider_stats", {
  id: serial("id").primaryKey(),
  providerId: text("provider_id").notNull().unique(),
  providerName: text("provider_name").notNull(),
  totalSignals: integer("total_signals").default(0),
  successfulSignals: integer("successful_signals").default(0),
  winRate: decimal("win_rate", { precision: 5, scale: 2 }).default("0"),
  avgRrRatio: decimal("avg_rr_ratio", { precision: 5, scale: 2 }).default("0"),
  avgExecutionDelay: integer("avg_execution_delay").default(0), // in milliseconds
  maxDrawdown: decimal("max_drawdown", { precision: 5, scale: 2 }).default("0"),
  totalProfit: decimal("total_profit", { precision: 10, scale: 2 }).default("0"),
  totalLoss: decimal("total_loss", { precision: 10, scale: 2 }).default("0"),
  avgConfidence: decimal("avg_confidence", { precision: 5, scale: 2 }).default("0"),
  isActive: boolean("is_active").default(true),
  lastSignalAt: timestamp("last_signal_at"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const equityEvents = pgTable("equity_events", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").references(() => users.id).notNull(),
  eventType: text("event_type").notNull(), // limit_triggered, reset, manual_override
  equityPercent: decimal("equity_percent", { precision: 5, scale: 2 }),
  triggerThreshold: decimal("trigger_threshold", { precision: 5, scale: 2 }),
  action: text("action").notNull(), // shutdown_terminals, block_trades, notify
  reason: text("reason"),
  adminUserId: integer("admin_user_id").references(() => users.id),
  timestamp: timestamp("timestamp").defaultNow(),
  details: jsonb("details").$type<Record<string, any>>(),
});

export const drawdownLimits = pgTable("drawdown_limits", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").references(() => users.id).notNull(),
  providerId: integer("provider_id").references(() => channels.id), // null for global limits
  symbol: text("symbol"), // null for all symbols
  maxDrawdownPercent: decimal("max_drawdown_percent", { precision: 5, scale: 2 }).notNull(),
  isActive: boolean("is_active").default(true),
  autoDisable: boolean("auto_disable").default(true), // Auto-disable provider after breach
  notifyOnly: boolean("notify_only").default(false), // Only notify, don't close trades
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const drawdownEvents = pgTable("drawdown_events", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").references(() => users.id).notNull(),
  limitId: integer("limit_id").references(() => drawdownLimits.id).notNull(),
  eventType: text("event_type").notNull(), // breach_detected, trades_closed, provider_disabled, admin_reset
  drawdownPercent: decimal("drawdown_percent", { precision: 5, scale: 2 }).notNull(),
  triggerThreshold: decimal("trigger_threshold", { precision: 5, scale: 2 }).notNull(),
  accountBalance: decimal("account_balance", { precision: 10, scale: 2 }),
  tradesAffected: integer("trades_affected").default(0),
  closedTrades: jsonb("closed_trades").$type<number[]>().default([]),
  providerId: integer("provider_id").references(() => channels.id),
  symbol: text("symbol"),
  adminUserId: integer("admin_user_id").references(() => users.id),
  timestamp: timestamp("timestamp").defaultNow(),
  details: jsonb("details").$type<Record<string, any>>(),
});

// Relations
export const usersRelations = relations(users, ({ many }) => ({
  strategies: many(strategies),
  trades: many(trades),
  mt5Status: many(mt5Status),
  syncLogs: many(syncLogs),
  equityLimits: many(equityLimits),
  equityEvents: many(equityEvents),
}));

export const channelsRelations = relations(channels, ({ many }) => ({
  signals: many(signals),
}));

export const strategiesRelations = relations(strategies, ({ one }) => ({
  user: one(users, {
    fields: [strategies.userId],
    references: [users.id],
  }),
}));

export const signalsRelations = relations(signals, ({ one, many }) => ({
  channel: one(channels, {
    fields: [signals.channelId],
    references: [channels.id],
  }),
  trades: many(trades),
}));

export const tradesRelations = relations(trades, ({ one }) => ({
  signal: one(signals, {
    fields: [trades.signalId],
    references: [signals.id],
  }),
  user: one(users, {
    fields: [trades.userId],
    references: [users.id],
  }),
}));

export const equityLimitsRelations = relations(equityLimits, ({ one, many }) => ({
  user: one(users, {
    fields: [equityLimits.userId],
    references: [users.id],
  }),
  events: many(equityEvents),
}));

export const equityEventsRelations = relations(equityEvents, ({ one }) => ({
  user: one(users, {
    fields: [equityEvents.userId],
    references: [users.id],
  }),
  adminUser: one(users, {
    fields: [equityEvents.adminUserId],
    references: [users.id],
  }),
  equityLimit: one(equityLimits, {
    fields: [equityEvents.userId],
    references: [equityLimits.userId],
  }),
}));

export const drawdownLimitsRelations = relations(drawdownLimits, ({ one, many }) => ({
  user: one(users, {
    fields: [drawdownLimits.userId],
    references: [users.id],
  }),
  provider: one(channels, {
    fields: [drawdownLimits.providerId],
    references: [channels.id],
  }),
  events: many(drawdownEvents),
}));

export const drawdownEventsRelations = relations(drawdownEvents, ({ one }) => ({
  user: one(users, {
    fields: [drawdownEvents.userId],
    references: [users.id],
  }),
  limit: one(drawdownLimits, {
    fields: [drawdownEvents.limitId],
    references: [drawdownLimits.id],
  }),
  provider: one(channels, {
    fields: [drawdownEvents.providerId],
    references: [channels.id],
  }),
  adminUser: one(users, {
    fields: [drawdownEvents.adminUserId],
    references: [users.id],
  }),
}));

export const mt5StatusRelations = relations(mt5Status, ({ one }) => ({
  user: one(users, {
    fields: [mt5Status.userId],
    references: [users.id],
  }),
}));

export const syncLogsRelations = relations(syncLogs, ({ one }) => ({
  user: one(users, {
    fields: [syncLogs.userId],
    references: [users.id],
  }),
}));

// Schemas
export const insertUserSchema = createInsertSchema(users).omit({
  id: true,
  createdAt: true,
});

export const insertChannelSchema = createInsertSchema(channels).omit({
  id: true,
  createdAt: true,
});

export const insertStrategySchema = createInsertSchema(strategies).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
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
  lastPing: true,
});

export const insertSyncLogSchema = createInsertSchema(syncLogs).omit({
  id: true,
  timestamp: true,
});

export const insertEquityLimitSchema = createInsertSchema(equityLimits).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export const insertEquityEventSchema = createInsertSchema(equityEvents).omit({
  id: true,
  timestamp: true,
});

export const insertDrawdownLimitSchema = createInsertSchema(drawdownLimits).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export const insertDrawdownEventSchema = createInsertSchema(drawdownEvents).omit({
  id: true,
  timestamp: true,
});

export const insertProviderStatsSchema = createInsertSchema(providerStats).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

// Types
export type User = typeof users.$inferSelect;
export type InsertUser = z.infer<typeof insertUserSchema>;
export type Channel = typeof channels.$inferSelect;
export type InsertChannel = z.infer<typeof insertChannelSchema>;
export type Strategy = typeof strategies.$inferSelect;
export type InsertStrategy = z.infer<typeof insertStrategySchema>;
export type Signal = typeof signals.$inferSelect;
export type InsertSignal = z.infer<typeof insertSignalSchema>;
export type Trade = typeof trades.$inferSelect;
export type InsertTrade = z.infer<typeof insertTradeSchema>;
export type Mt5Status = typeof mt5Status.$inferSelect;
export type InsertMt5Status = z.infer<typeof insertMt5StatusSchema>;
export type SyncLog = typeof syncLogs.$inferSelect;
export type InsertSyncLog = z.infer<typeof insertSyncLogSchema>;
export type EquityLimit = typeof equityLimits.$inferSelect;
export type InsertEquityLimit = z.infer<typeof insertEquityLimitSchema>;
export type EquityEvent = typeof equityEvents.$inferSelect;
export type InsertEquityEvent = z.infer<typeof insertEquityEventSchema>;
export type DrawdownLimit = typeof drawdownLimits.$inferSelect;
export type InsertDrawdownLimit = z.infer<typeof insertDrawdownLimitSchema>;
export type DrawdownEvent = typeof drawdownEvents.$inferSelect;
export type InsertDrawdownEvent = z.infer<typeof insertDrawdownEventSchema>;
export type ProviderStats = typeof providerStats.$inferSelect;
export type InsertProviderStats = z.infer<typeof insertProviderStatsSchema>;
