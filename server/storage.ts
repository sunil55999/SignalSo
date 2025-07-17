import { Signal, InsertSignal, Trade, InsertTrade, Channel, InsertChannel, User, InsertUser, Log, InsertLog, Mt5Status, InsertMt5Status } from '@shared/schema';

// Storage interface for SignalOS data operations
export interface IStorage {
  // User operations
  createUser(user: InsertUser): Promise<User>;
  getUserById(id: string): Promise<User | null>;
  getUserByUsername(username: string): Promise<User | null>;
  updateUser(id: string, updates: Partial<InsertUser>): Promise<User>;
  deleteUser(id: string): Promise<boolean>;

  // Channel operations
  createChannel(channel: InsertChannel): Promise<Channel>;
  getChannelById(id: string): Promise<Channel | null>;
  getChannelsByUserId(userId: string): Promise<Channel[]>;
  updateChannel(id: string, updates: Partial<InsertChannel>): Promise<Channel>;
  deleteChannel(id: string): Promise<boolean>;

  // Signal operations
  createSignal(signal: InsertSignal): Promise<Signal>;
  getSignalById(id: string): Promise<Signal | null>;
  getSignalsByChannelId(channelId: string): Promise<Signal[]>;
  updateSignal(id: string, updates: Partial<InsertSignal>): Promise<Signal>;
  deleteSignal(id: string): Promise<boolean>;

  // Trade operations
  createTrade(trade: InsertTrade): Promise<Trade>;
  getTradeById(id: string): Promise<Trade | null>;
  getTradesBySignalId(signalId: string): Promise<Trade[]>;
  updateTrade(id: string, updates: Partial<InsertTrade>): Promise<Trade>;
  deleteTrade(id: string): Promise<boolean>;

  // MT5 Status operations
  updateMt5Status(status: InsertMt5Status): Promise<Mt5Status>;
  getMt5Status(): Promise<Mt5Status | null>;

  // Log operations
  createLog(log: InsertLog): Promise<Log>;
  getLogsByComponent(component: string): Promise<Log[]>;
  getLogsByLevel(level: string): Promise<Log[]>;
  getRecentLogs(limit: number): Promise<Log[]>;
  deleteLogs(before: Date): Promise<boolean>;
}

// In-memory storage implementation for development
export class MemStorage implements IStorage {
  private users: Map<string, User> = new Map();
  private channels: Map<string, Channel> = new Map();
  private signals: Map<string, Signal> = new Map();
  private trades: Map<string, Trade> = new Map();
  private logs: Map<string, Log> = new Map();
  private mt5Status: Mt5Status | null = null;

  private generateId(): string {
    return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
  }

  // User operations
  async createUser(user: InsertUser): Promise<User> {
    const id = this.generateId();
    const newUser: User = {
      id,
      ...user,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    this.users.set(id, newUser);
    return newUser;
  }

  async getUserById(id: string): Promise<User | null> {
    return this.users.get(id) || null;
  }

  async getUserByUsername(username: string): Promise<User | null> {
    for (const user of this.users.values()) {
      if (user.username === username) {
        return user;
      }
    }
    return null;
  }

  async updateUser(id: string, updates: Partial<InsertUser>): Promise<User> {
    const user = this.users.get(id);
    if (!user) throw new Error('User not found');
    
    const updatedUser: User = {
      ...user,
      ...updates,
      updatedAt: new Date(),
    };
    this.users.set(id, updatedUser);
    return updatedUser;
  }

  async deleteUser(id: string): Promise<boolean> {
    return this.users.delete(id);
  }

  // Channel operations
  async createChannel(channel: InsertChannel): Promise<Channel> {
    const id = this.generateId();
    const newChannel: Channel = {
      id,
      ...channel,
      createdAt: new Date(),
    };
    this.channels.set(id, newChannel);
    return newChannel;
  }

  async getChannelById(id: string): Promise<Channel | null> {
    return this.channels.get(id) || null;
  }

  async getChannelsByUserId(userId: string): Promise<Channel[]> {
    return Array.from(this.channels.values()).filter(channel => channel.userId === userId);
  }

  async updateChannel(id: string, updates: Partial<InsertChannel>): Promise<Channel> {
    const channel = this.channels.get(id);
    if (!channel) throw new Error('Channel not found');
    
    const updatedChannel: Channel = { ...channel, ...updates };
    this.channels.set(id, updatedChannel);
    return updatedChannel;
  }

  async deleteChannel(id: string): Promise<boolean> {
    return this.channels.delete(id);
  }

  // Signal operations
  async createSignal(signal: InsertSignal): Promise<Signal> {
    const id = this.generateId();
    const newSignal: Signal = {
      id,
      ...signal,
      createdAt: new Date(),
    };
    this.signals.set(id, newSignal);
    return newSignal;
  }

  async getSignalById(id: string): Promise<Signal | null> {
    return this.signals.get(id) || null;
  }

  async getSignalsByChannelId(channelId: string): Promise<Signal[]> {
    return Array.from(this.signals.values()).filter(signal => signal.channelId === channelId);
  }

  async updateSignal(id: string, updates: Partial<InsertSignal>): Promise<Signal> {
    const signal = this.signals.get(id);
    if (!signal) throw new Error('Signal not found');
    
    const updatedSignal: Signal = { ...signal, ...updates };
    this.signals.set(id, updatedSignal);
    return updatedSignal;
  }

  async deleteSignal(id: string): Promise<boolean> {
    return this.signals.delete(id);
  }

  // Trade operations
  async createTrade(trade: InsertTrade): Promise<Trade> {
    const id = this.generateId();
    const newTrade: Trade = {
      id,
      ...trade,
      openTime: new Date(),
      closeTime: null,
    };
    this.trades.set(id, newTrade);
    return newTrade;
  }

  async getTradeById(id: string): Promise<Trade | null> {
    return this.trades.get(id) || null;
  }

  async getTradesBySignalId(signalId: string): Promise<Trade[]> {
    return Array.from(this.trades.values()).filter(trade => trade.signalId === signalId);
  }

  async updateTrade(id: string, updates: Partial<InsertTrade>): Promise<Trade> {
    const trade = this.trades.get(id);
    if (!trade) throw new Error('Trade not found');
    
    const updatedTrade: Trade = { ...trade, ...updates };
    this.trades.set(id, updatedTrade);
    return updatedTrade;
  }

  async deleteTrade(id: string): Promise<boolean> {
    return this.trades.delete(id);
  }

  // MT5 Status operations
  async updateMt5Status(status: InsertMt5Status): Promise<Mt5Status> {
    const id = this.generateId();
    const newStatus: Mt5Status = {
      id,
      ...status,
      lastUpdate: new Date(),
    };
    this.mt5Status = newStatus;
    return newStatus;
  }

  async getMt5Status(): Promise<Mt5Status | null> {
    return this.mt5Status;
  }

  // Log operations
  async createLog(log: InsertLog): Promise<Log> {
    const id = this.generateId();
    const newLog: Log = {
      id,
      ...log,
      createdAt: new Date(),
    };
    this.logs.set(id, newLog);
    return newLog;
  }

  async getLogsByComponent(component: string): Promise<Log[]> {
    return Array.from(this.logs.values()).filter(log => log.component === component);
  }

  async getLogsByLevel(level: string): Promise<Log[]> {
    return Array.from(this.logs.values()).filter(log => log.level === level);
  }

  async getRecentLogs(limit: number): Promise<Log[]> {
    return Array.from(this.logs.values())
      .sort((a, b) => b.createdAt!.getTime() - a.createdAt!.getTime())
      .slice(0, limit);
  }

  async deleteLogs(before: Date): Promise<boolean> {
    let deletedCount = 0;
    for (const [id, log] of this.logs.entries()) {
      if (log.createdAt && log.createdAt < before) {
        this.logs.delete(id);
        deletedCount++;
      }
    }
    return deletedCount > 0;
  }
}