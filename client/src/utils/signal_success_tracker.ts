/**
 * Signal Success Tracker Utility
 * Analyzes signal success rates and provides performance analytics for providers
 * Tracks execution results, RR targets, and drawdown patterns
 */

export interface SignalExecutionData {
  id: string;
  providerId: string;
  providerName?: string;
  symbol: string;
  entryPrice: number;
  exitPrice?: number;
  stopLoss?: number;
  takeProfit?: number;
  lotSize: number;
  direction: 'BUY' | 'SELL';
  status: 'PENDING' | 'EXECUTED' | 'CLOSED' | 'CANCELLED';
  outcome?: 'WIN' | 'LOSS' | 'BREAKEVEN';
  pnl?: number;
  riskRewardRatio?: number;
  executionTime: Date;
  closeTime?: Date;
  confidence?: number;
  signalFormat?: string;
  metadata?: Record<string, any>;
}

export interface ProviderSuccessStats {
  providerId: string;
  providerName?: string;
  totalSignals: number;
  executedSignals: number;
  winCount: number;
  lossCount: number;
  breakevenCount: number;
  winRate: number;
  averageRR: number;
  bestRR: number;
  worstRR: number;
  totalPnL: number;
  maxDrawdown: number;
  averageConfidence: number;
  executionRate: number;
  averageHoldTime: number;
  lastUpdated: Date;
  performanceGrade: 'A' | 'B' | 'C' | 'D' | 'F';
  signalFormats: Record<string, number>;
}

export interface SignalFormatStats {
  format: string;
  totalSignals: number;
  successRate: number;
  averageConfidence: number;
  examples: string[];
}

export interface TrackerConfig {
  cacheExpiry: number; // milliseconds
  minSignalsForStats: number;
  enableLocalStorage: boolean;
  apiEndpoint?: string;
}

const DEFAULT_CONFIG: TrackerConfig = {
  cacheExpiry: 5 * 60 * 1000, // 5 minutes
  minSignalsForStats: 5,
  enableLocalStorage: true,
  apiEndpoint: '/api/signals'
};

const STORAGE_KEYS = {
  PROVIDER_STATS: 'signalos_provider_stats',
  SIGNAL_DATA: 'signalos_signal_data',
  FORMAT_STATS: 'signalos_format_stats',
  LAST_UPDATE: 'signalos_stats_update'
} as const;

export class SignalSuccessTracker {
  private config: TrackerConfig;
  private cache: Map<string, ProviderSuccessStats> = new Map();
  private signalData: SignalExecutionData[] = [];
  private formatStats: Map<string, SignalFormatStats> = new Map();
  private lastUpdate: Date | null = null;

  constructor(config?: Partial<TrackerConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.loadFromStorage();
  }

  /**
   * Add signal execution data to tracker
   */
  addSignalData(signal: SignalExecutionData): void {
    const existingIndex = this.signalData.findIndex(s => s.id === signal.id);
    
    if (existingIndex >= 0) {
      this.signalData[existingIndex] = signal;
    } else {
      this.signalData.push(signal);
    }

    this.updateProviderStats(signal.providerId);
    this.updateFormatStats(signal);
    this.saveToStorage();
  }

  /**
   * Add multiple signal execution records
   */
  addSignalDataBatch(signals: SignalExecutionData[]): void {
    signals.forEach(signal => {
      const existingIndex = this.signalData.findIndex(s => s.id === signal.id);
      if (existingIndex >= 0) {
        this.signalData[existingIndex] = signal;
      } else {
        this.signalData.push(signal);
      }
    });

    // Update stats for all affected providers
    const providerIds = [...new Set(signals.map(s => s.providerId))];
    providerIds.forEach(providerId => {
      this.updateProviderStats(providerId);
    });

    signals.forEach(signal => this.updateFormatStats(signal));
    this.saveToStorage();
  }

  /**
   * Get success statistics for a specific provider
   */
  getSuccessStats(providerId: string): ProviderSuccessStats | null {
    if (this.shouldRefreshCache()) {
      this.refreshAllStats();
    }

    return this.cache.get(providerId) || null;
  }

  /**
   * Get success statistics for all providers
   */
  getAllProviderStats(): ProviderSuccessStats[] {
    if (this.shouldRefreshCache()) {
      this.refreshAllStats();
    }

    return Array.from(this.cache.values()).sort((a, b) => b.winRate - a.winRate);
  }

  /**
   * Get top performing providers
   */
  getTopProviders(limit: number = 10): ProviderSuccessStats[] {
    return this.getAllProviderStats()
      .filter(stats => stats.totalSignals >= this.config.minSignalsForStats)
      .slice(0, limit);
  }

  /**
   * Get signal format statistics
   */
  getFormatStats(): SignalFormatStats[] {
    return Array.from(this.formatStats.values())
      .sort((a, b) => b.successRate - a.successRate);
  }

  /**
   * Get aggregated platform statistics
   */
  getPlatformStats(): {
    totalProviders: number;
    totalSignals: number;
    overallWinRate: number;
    averageRR: number;
    totalPnL: number;
    activeProviders: number;
  } {
    const allStats = this.getAllProviderStats();
    const totalSignals = allStats.reduce((sum, stats) => sum + stats.totalSignals, 0);
    const totalWins = allStats.reduce((sum, stats) => sum + stats.winCount, 0);
    const totalRR = allStats.reduce((sum, stats) => sum + (stats.averageRR * stats.executedSignals), 0);
    const totalExecuted = allStats.reduce((sum, stats) => sum + stats.executedSignals, 0);
    const totalPnL = allStats.reduce((sum, stats) => sum + stats.totalPnL, 0);

    return {
      totalProviders: allStats.length,
      totalSignals,
      overallWinRate: totalExecuted > 0 ? (totalWins / totalExecuted) * 100 : 0,
      averageRR: totalExecuted > 0 ? totalRR / totalExecuted : 0,
      totalPnL,
      activeProviders: allStats.filter(s => s.totalSignals >= this.config.minSignalsForStats).length
    };
  }

  /**
   * Filter signals by various criteria
   */
  filterSignals(filters: {
    providerId?: string;
    symbol?: string;
    outcome?: 'WIN' | 'LOSS' | 'BREAKEVEN';
    dateFrom?: Date;
    dateTo?: Date;
    minConfidence?: number;
  }): SignalExecutionData[] {
    return this.signalData.filter(signal => {
      if (filters.providerId && signal.providerId !== filters.providerId) return false;
      if (filters.symbol && signal.symbol !== filters.symbol) return false;
      if (filters.outcome && signal.outcome !== filters.outcome) return false;
      if (filters.dateFrom && signal.executionTime < filters.dateFrom) return false;
      if (filters.dateTo && signal.executionTime > filters.dateTo) return false;
      if (filters.minConfidence && (signal.confidence || 0) < filters.minConfidence) return false;
      return true;
    });
  }

  /**
   * Get performance trends over time
   */
  getTrends(providerId?: string, days: number = 30): {
    date: string;
    winRate: number;
    totalSignals: number;
    pnl: number;
  }[] {
    const endDate = new Date();
    const startDate = new Date(endDate.getTime() - (days * 24 * 60 * 60 * 1000));
    
    const filteredSignals = this.signalData.filter(signal => {
      if (providerId && signal.providerId !== providerId) return false;
      return signal.executionTime >= startDate && signal.executionTime <= endDate;
    });

    const dailyStats = new Map<string, { wins: number; total: number; pnl: number }>();
    
    filteredSignals.forEach(signal => {
      if (signal.status !== 'CLOSED' || !signal.outcome) return;
      
      const date = signal.executionTime.toISOString().split('T')[0];
      const existing = dailyStats.get(date) || { wins: 0, total: 0, pnl: 0 };
      
      existing.total++;
      existing.pnl += signal.pnl || 0;
      if (signal.outcome === 'WIN') existing.wins++;
      
      dailyStats.set(date, existing);
    });

    return Array.from(dailyStats.entries())
      .map(([date, stats]) => ({
        date,
        winRate: stats.total > 0 ? (stats.wins / stats.total) * 100 : 0,
        totalSignals: stats.total,
        pnl: stats.pnl
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }

  /**
   * Export analytics data for parser training
   */
  exportAnalyticsData(): {
    providerStats: ProviderSuccessStats[];
    formatStats: SignalFormatStats[];
    signalData: SignalExecutionData[];
    metadata: {
      exportDate: Date;
      totalSignals: number;
      dateRange: { from: Date; to: Date };
    };
  } {
    const sortedSignals = [...this.signalData].sort((a, b) => 
      a.executionTime.getTime() - b.executionTime.getTime()
    );

    return {
      providerStats: this.getAllProviderStats(),
      formatStats: this.getFormatStats(),
      signalData: sortedSignals,
      metadata: {
        exportDate: new Date(),
        totalSignals: this.signalData.length,
        dateRange: {
          from: sortedSignals[0]?.executionTime || new Date(),
          to: sortedSignals[sortedSignals.length - 1]?.executionTime || new Date()
        }
      }
    };
  }

  /**
   * Clear all cached data
   */
  clearCache(): void {
    this.cache.clear();
    this.signalData = [];
    this.formatStats.clear();
    this.lastUpdate = null;
    this.clearStorage();
  }

  /**
   * Update statistics for a specific provider
   */
  private updateProviderStats(providerId: string): void {
    const providerSignals = this.signalData.filter(s => s.providerId === providerId);
    
    if (providerSignals.length === 0) {
      this.cache.delete(providerId);
      return;
    }

    const executedSignals = providerSignals.filter(s => s.status === 'CLOSED' && s.outcome);
    const winCount = executedSignals.filter(s => s.outcome === 'WIN').length;
    const lossCount = executedSignals.filter(s => s.outcome === 'LOSS').length;
    const breakevenCount = executedSignals.filter(s => s.outcome === 'BREAKEVEN').length;

    const validRRSignals = executedSignals.filter(s => s.riskRewardRatio != null);
    const averageRR = validRRSignals.length > 0 
      ? validRRSignals.reduce((sum, s) => sum + (s.riskRewardRatio || 0), 0) / validRRSignals.length
      : 0;

    const bestRR = validRRSignals.length > 0 
      ? Math.max(...validRRSignals.map(s => s.riskRewardRatio || 0))
      : 0;

    const worstRR = validRRSignals.length > 0 
      ? Math.min(...validRRSignals.map(s => s.riskRewardRatio || 0))
      : 0;

    const totalPnL = executedSignals.reduce((sum, s) => sum + (s.pnl || 0), 0);
    const maxDrawdown = this.calculateMaxDrawdown(executedSignals);

    const confidenceSignals = providerSignals.filter(s => s.confidence != null);
    const averageConfidence = confidenceSignals.length > 0
      ? confidenceSignals.reduce((sum, s) => sum + (s.confidence || 0), 0) / confidenceSignals.length
      : 0;

    const holdTimes = executedSignals
      .filter(s => s.closeTime)
      .map(s => (s.closeTime!.getTime() - s.executionTime.getTime()) / (1000 * 60 * 60)); // hours

    const averageHoldTime = holdTimes.length > 0
      ? holdTimes.reduce((sum, time) => sum + time, 0) / holdTimes.length
      : 0;

    const signalFormats: Record<string, number> = {};
    providerSignals.forEach(signal => {
      if (signal.signalFormat) {
        signalFormats[signal.signalFormat] = (signalFormats[signal.signalFormat] || 0) + 1;
      }
    });

    const winRate = executedSignals.length > 0 ? (winCount / executedSignals.length) * 100 : 0;
    const executionRate = providerSignals.length > 0 ? (executedSignals.length / providerSignals.length) * 100 : 0;

    const stats: ProviderSuccessStats = {
      providerId,
      providerName: providerSignals[0]?.providerName,
      totalSignals: providerSignals.length,
      executedSignals: executedSignals.length,
      winCount,
      lossCount,
      breakevenCount,
      winRate,
      averageRR,
      bestRR,
      worstRR,
      totalPnL,
      maxDrawdown,
      averageConfidence,
      executionRate,
      averageHoldTime,
      lastUpdated: new Date(),
      performanceGrade: this.calculatePerformanceGrade(winRate, averageRR, executionRate),
      signalFormats
    };

    this.cache.set(providerId, stats);
  }

  /**
   * Update signal format statistics
   */
  private updateFormatStats(signal: SignalExecutionData): void {
    if (!signal.signalFormat) return;

    const existing = this.formatStats.get(signal.signalFormat) || {
      format: signal.signalFormat,
      totalSignals: 0,
      successRate: 0,
      averageConfidence: 0,
      examples: []
    };

    existing.totalSignals++;
    
    // Update examples (keep last 5)
    if (signal.metadata?.originalText && !existing.examples.includes(signal.metadata.originalText)) {
      existing.examples.push(signal.metadata.originalText);
      if (existing.examples.length > 5) {
        existing.examples = existing.examples.slice(-5);
      }
    }

    // Recalculate success rate and confidence
    const formatSignals = this.signalData.filter(s => s.signalFormat === signal.signalFormat);
    const successfulSignals = formatSignals.filter(s => s.outcome === 'WIN');
    const executedSignals = formatSignals.filter(s => s.status === 'CLOSED' && s.outcome);
    
    existing.successRate = executedSignals.length > 0 ? (successfulSignals.length / executedSignals.length) * 100 : 0;
    
    const confidenceSignals = formatSignals.filter(s => s.confidence != null);
    existing.averageConfidence = confidenceSignals.length > 0
      ? confidenceSignals.reduce((sum, s) => sum + (s.confidence || 0), 0) / confidenceSignals.length
      : 0;

    this.formatStats.set(signal.signalFormat, existing);
  }

  /**
   * Calculate maximum drawdown for a series of trades
   */
  private calculateMaxDrawdown(signals: SignalExecutionData[]): number {
    if (signals.length === 0) return 0;

    let peak = 0;
    let maxDrawdown = 0;
    let runningPnL = 0;

    signals
      .sort((a, b) => a.executionTime.getTime() - b.executionTime.getTime())
      .forEach(signal => {
        runningPnL += signal.pnl || 0;
        
        if (runningPnL > peak) {
          peak = runningPnL;
        }
        
        const currentDrawdown = peak - runningPnL;
        if (currentDrawdown > maxDrawdown) {
          maxDrawdown = currentDrawdown;
        }
      });

    return maxDrawdown;
  }

  /**
   * Calculate performance grade based on key metrics
   */
  private calculatePerformanceGrade(winRate: number, averageRR: number, executionRate: number): 'A' | 'B' | 'C' | 'D' | 'F' {
    const score = (winRate * 0.4) + (Math.min(averageRR * 25, 100) * 0.4) + (executionRate * 0.2);
    
    if (score >= 80) return 'A';
    if (score >= 70) return 'B';
    if (score >= 60) return 'C';
    if (score >= 50) return 'D';
    return 'F';
  }

  /**
   * Check if cache should be refreshed
   */
  private shouldRefreshCache(): boolean {
    if (!this.lastUpdate) return true;
    return (Date.now() - this.lastUpdate.getTime()) > this.config.cacheExpiry;
  }

  /**
   * Refresh all provider statistics
   */
  private refreshAllStats(): void {
    const providerIds = [...new Set(this.signalData.map(s => s.providerId))];
    providerIds.forEach(providerId => {
      this.updateProviderStats(providerId);
    });
    this.lastUpdate = new Date();
  }

  /**
   * Load data from localStorage
   */
  private loadFromStorage(): void {
    if (!this.config.enableLocalStorage) return;

    try {
      const statsData = localStorage.getItem(STORAGE_KEYS.PROVIDER_STATS);
      if (statsData) {
        const parsed = JSON.parse(statsData);
        parsed.forEach((stats: ProviderSuccessStats) => {
          stats.lastUpdated = new Date(stats.lastUpdated);
          this.cache.set(stats.providerId, stats);
        });
      }

      const signalData = localStorage.getItem(STORAGE_KEYS.SIGNAL_DATA);
      if (signalData) {
        this.signalData = JSON.parse(signalData).map((signal: any) => ({
          ...signal,
          executionTime: new Date(signal.executionTime),
          closeTime: signal.closeTime ? new Date(signal.closeTime) : undefined
        }));
      }

      const formatData = localStorage.getItem(STORAGE_KEYS.FORMAT_STATS);
      if (formatData) {
        const parsed = JSON.parse(formatData);
        parsed.forEach((stats: SignalFormatStats) => {
          this.formatStats.set(stats.format, stats);
        });
      }

      const lastUpdate = localStorage.getItem(STORAGE_KEYS.LAST_UPDATE);
      if (lastUpdate) {
        this.lastUpdate = new Date(lastUpdate);
      }
    } catch (error) {
      console.warn('Failed to load signal tracker data from localStorage:', error);
    }
  }

  /**
   * Save data to localStorage
   */
  private saveToStorage(): void {
    if (!this.config.enableLocalStorage) return;

    try {
      localStorage.setItem(STORAGE_KEYS.PROVIDER_STATS, JSON.stringify(Array.from(this.cache.values())));
      localStorage.setItem(STORAGE_KEYS.SIGNAL_DATA, JSON.stringify(this.signalData));
      localStorage.setItem(STORAGE_KEYS.FORMAT_STATS, JSON.stringify(Array.from(this.formatStats.values())));
      localStorage.setItem(STORAGE_KEYS.LAST_UPDATE, new Date().toISOString());
    } catch (error) {
      console.warn('Failed to save signal tracker data to localStorage:', error);
    }
  }

  /**
   * Clear localStorage data
   */
  private clearStorage(): void {
    if (!this.config.enableLocalStorage) return;

    Object.values(STORAGE_KEYS).forEach(key => {
      localStorage.removeItem(key);
    });
  }
}

/**
 * Default singleton instance for easy usage
 */
export const defaultSignalTracker = new SignalSuccessTracker();

/**
 * Convenience function to get provider stats
 */
export function getProviderStats(providerId: string): ProviderSuccessStats | null {
  return defaultSignalTracker.getSuccessStats(providerId);
}

/**
 * Convenience function to add signal data
 */
export function trackSignal(signal: SignalExecutionData): void {
  return defaultSignalTracker.addSignalData(signal);
}

/**
 * Convenience function to get all provider stats
 */
export function getAllProviderStats(): ProviderSuccessStats[] {
  return defaultSignalTracker.getAllProviderStats();
}