/**
 * Database Query Optimization Module
 * Addresses inefficient database queries (Issue #17)
 */

import { eq, and, desc, asc, between, sql } from 'drizzle-orm';
import { DatabaseStorage } from './storage';

export class QueryOptimizer {
  private static instance: QueryOptimizer;
  private queryCache = new Map<string, { data: any; timestamp: number; ttl: number }>();
  private readonly CACHE_TTL = 5 * 60 * 1000; // 5 minutes

  static getInstance(): QueryOptimizer {
    if (!QueryOptimizer.instance) {
      QueryOptimizer.instance = new QueryOptimizer();
    }
    return QueryOptimizer.instance;
  }

  /**
   * Cache query results with TTL
   */
  private setCache(key: string, data: any, ttl: number = this.CACHE_TTL): void {
    this.queryCache.set(key, {
      data,
      timestamp: Date.now(),
      ttl
    });
  }

  /**
   * Get cached query result if valid
   */
  private getCache(key: string): any | null {
    const cached = this.queryCache.get(key);
    if (!cached) return null;

    const isExpired = Date.now() - cached.timestamp > cached.ttl;
    if (isExpired) {
      this.queryCache.delete(key);
      return null;
    }

    return cached.data;
  }

  /**
   * Optimized signal queries with pagination and caching
   */
  async getSignalsPaginated(
    storage: DatabaseStorage,
    page: number = 1,
    limit: number = 50,
    filters: {
      userId?: number;
      channelId?: number;
      symbol?: string;
      status?: string;
      dateFrom?: Date;
      dateTo?: Date;
    } = {}
  ) {
    const cacheKey = `signals_${JSON.stringify({ page, limit, ...filters })}`;
    const cached = this.getCache(cacheKey);
    if (cached) return cached;

    const offset = (page - 1) * limit;
    
    // Build optimized query with indexes
    let query = storage.db.select().from(storage.signals);
    
    const conditions = [];
    if (filters.userId) conditions.push(eq(storage.signals.userId, filters.userId));
    if (filters.channelId) conditions.push(eq(storage.signals.channelId, filters.channelId));
    if (filters.symbol) conditions.push(eq(storage.signals.symbol, filters.symbol));
    if (filters.status) conditions.push(eq(storage.signals.status, filters.status));
    if (filters.dateFrom && filters.dateTo) {
      conditions.push(between(storage.signals.createdAt, filters.dateFrom, filters.dateTo));
    }

    if (conditions.length > 0) {
      query = query.where(and(...conditions));
    }

    const result = await query
      .orderBy(desc(storage.signals.createdAt))
      .limit(limit)
      .offset(offset);

    this.setCache(cacheKey, result);
    return result;
  }

  /**
   * Optimized trade statistics with aggregation
   */
  async getTradeStatistics(storage: DatabaseStorage, userId: number, days: number = 30) {
    const cacheKey = `trade_stats_${userId}_${days}`;
    const cached = this.getCache(cacheKey);
    if (cached) return cached;

    const dateFrom = new Date();
    dateFrom.setDate(dateFrom.getDate() - days);

    // Single optimized query for all statistics
    const stats = await storage.db
      .select({
        totalTrades: sql<number>`count(*)`,
        winningTrades: sql<number>`count(case when status = 'closed' and profit > 0 then 1 end)`,
        losingTrades: sql<number>`count(case when status = 'closed' and profit < 0 then 1 end)`,
        totalProfit: sql<number>`sum(case when status = 'closed' then profit else 0 end)`,
        avgProfit: sql<number>`avg(case when status = 'closed' then profit else null end)`,
        maxProfit: sql<number>`max(case when status = 'closed' then profit else null end)`,
        maxLoss: sql<number>`min(case when status = 'closed' then profit else null end)`
      })
      .from(storage.trades)
      .where(
        and(
          eq(storage.trades.userId, userId),
          sql`${storage.trades.openTime} >= ${dateFrom}`
        )
      );

    const result = stats[0] || {
      totalTrades: 0,
      winningTrades: 0,
      losingTrades: 0,
      totalProfit: 0,
      avgProfit: 0,
      maxProfit: 0,
      maxLoss: 0
    };

    // Calculate derived metrics
    const enhancedStats = {
      ...result,
      winRate: result.totalTrades > 0 ? (result.winningTrades / result.totalTrades) * 100 : 0,
      profitFactor: result.losingTrades > 0 ? Math.abs(result.totalProfit / (result.maxLoss * result.losingTrades)) : 0
    };

    this.setCache(cacheKey, enhancedStats, 10 * 60 * 1000); // 10 minute cache
    return enhancedStats;
  }

  /**
   * Optimized channel performance query
   */
  async getChannelPerformance(storage: DatabaseStorage, limit: number = 10) {
    const cacheKey = `channel_performance_${limit}`;
    const cached = this.getCache(cacheKey);
    if (cached) return cached;

    const performance = await storage.db
      .select({
        channelId: storage.channels.id,
        providerName: storage.channels.providerName,
        totalSignals: sql<number>`count(${storage.signals.id})`,
        successfulSignals: sql<number>`count(case when ${storage.signals.status} = 'success' then 1 end)`,
        winRate: sql<number>`round((count(case when ${storage.signals.status} = 'success' then 1 end) * 100.0 / count(${storage.signals.id})), 2)`
      })
      .from(storage.channels)
      .leftJoin(storage.signals, eq(storage.channels.id, storage.signals.channelId))
      .groupBy(storage.channels.id, storage.channels.providerName)
      .orderBy(desc(sql`win_rate`))
      .limit(limit);

    this.setCache(cacheKey, performance, 15 * 60 * 1000); // 15 minute cache
    return performance;
  }

  /**
   * Clear cache for specific patterns or all
   */
  clearCache(pattern?: string): void {
    if (!pattern) {
      this.queryCache.clear();
      return;
    }

    const keysToDelete = Array.from(this.queryCache.keys()).filter(key => 
      key.includes(pattern)
    );
    
    keysToDelete.forEach(key => this.queryCache.delete(key));
  }

  /**
   * Get cache statistics
   */
  getCacheStats() {
    return {
      totalEntries: this.queryCache.size,
      entries: Array.from(this.queryCache.entries()).map(([key, value]) => ({
        key,
        age: Date.now() - value.timestamp,
        ttl: value.ttl
      }))
    };
  }
}

export const queryOptimizer = QueryOptimizer.getInstance();