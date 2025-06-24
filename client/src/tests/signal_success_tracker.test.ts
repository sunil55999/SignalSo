/**
 * Unit Tests for SignalSuccessTracker
 * Tests success rate calculation, RR aggregation, and analytics functionality
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { 
  SignalSuccessTracker, 
  SignalExecutionData, 
  getProviderStats, 
  trackSignal, 
  getAllProviderStats 
} from '../utils/signal_success_tracker';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    }
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

describe('SignalSuccessTracker', () => {
  let tracker: SignalSuccessTracker;

  beforeEach(() => {
    localStorageMock.clear();
    tracker = new SignalSuccessTracker({ enableLocalStorage: false });
  });

  afterEach(() => {
    localStorageMock.clear();
  });

  // Helper function to create test signal data
  const createTestSignal = (overrides: Partial<SignalExecutionData> = {}): SignalExecutionData => ({
    id: Math.random().toString(36).substr(2, 9),
    providerId: 'test-provider',
    providerName: 'Test Provider',
    symbol: 'EURUSD',
    entryPrice: 1.1000,
    exitPrice: 1.1050,
    stopLoss: 1.0950,
    takeProfit: 1.1100,
    lotSize: 0.1,
    direction: 'BUY',
    status: 'CLOSED',
    outcome: 'WIN',
    pnl: 50,
    riskRewardRatio: 2.0,
    executionTime: new Date(),
    closeTime: new Date(Date.now() + 3600000), // 1 hour later
    confidence: 85,
    signalFormat: 'standard',
    metadata: { originalText: 'EURUSD BUY 1.1000 SL 1.0950 TP 1.1100' },
    ...overrides
  });

  describe('Basic Functionality', () => {
    it('should add signal data correctly', () => {
      const signal = createTestSignal();
      tracker.addSignalData(signal);
      
      const stats = tracker.getSuccessStats('test-provider');
      expect(stats).toBeTruthy();
      expect(stats?.totalSignals).toBe(1);
      expect(stats?.executedSignals).toBe(1);
      expect(stats?.winCount).toBe(1);
    });

    it('should update existing signal data', () => {
      const signalId = 'test-signal-1';
      const signal1 = createTestSignal({ id: signalId, status: 'PENDING', outcome: undefined });
      const signal2 = createTestSignal({ id: signalId, status: 'CLOSED', outcome: 'WIN' });
      
      tracker.addSignalData(signal1);
      let stats = tracker.getSuccessStats('test-provider');
      expect(stats?.executedSignals).toBe(0);
      
      tracker.addSignalData(signal2);
      stats = tracker.getSuccessStats('test-provider');
      expect(stats?.executedSignals).toBe(1);
      expect(stats?.winCount).toBe(1);
    });

    it('should handle batch signal addition', () => {
      const signals = [
        createTestSignal({ id: '1', outcome: 'WIN' }),
        createTestSignal({ id: '2', outcome: 'LOSS' }),
        createTestSignal({ id: '3', outcome: 'WIN' })
      ];
      
      tracker.addSignalDataBatch(signals);
      const stats = tracker.getSuccessStats('test-provider');
      
      expect(stats?.totalSignals).toBe(3);
      expect(stats?.winCount).toBe(2);
      expect(stats?.lossCount).toBe(1);
    });
  });

  describe('Win Rate Calculation', () => {
    it('should calculate correct win rate with mixed results', () => {
      const signals = [
        createTestSignal({ id: '1', outcome: 'WIN' }),
        createTestSignal({ id: '2', outcome: 'LOSS' }),
        createTestSignal({ id: '3', outcome: 'WIN' }),
        createTestSignal({ id: '4', outcome: 'WIN' }),
        createTestSignal({ id: '5', outcome: 'LOSS' })
      ];
      
      tracker.addSignalDataBatch(signals);
      const stats = tracker.getSuccessStats('test-provider');
      
      expect(stats?.winRate).toBe(60); // 3 wins out of 5 = 60%
      expect(stats?.winCount).toBe(3);
      expect(stats?.lossCount).toBe(2);
    });

    it('should handle 100% win rate', () => {
      const signals = [
        createTestSignal({ id: '1', outcome: 'WIN' }),
        createTestSignal({ id: '2', outcome: 'WIN' }),
        createTestSignal({ id: '3', outcome: 'WIN' })
      ];
      
      tracker.addSignalDataBatch(signals);
      const stats = tracker.getSuccessStats('test-provider');
      
      expect(stats?.winRate).toBe(100);
      expect(stats?.lossCount).toBe(0);
    });

    it('should handle 0% win rate', () => {
      const signals = [
        createTestSignal({ id: '1', outcome: 'LOSS' }),
        createTestSignal({ id: '2', outcome: 'LOSS' }),
        createTestSignal({ id: '3', outcome: 'LOSS' })
      ];
      
      tracker.addSignalDataBatch(signals);
      const stats = tracker.getSuccessStats('test-provider');
      
      expect(stats?.winRate).toBe(0);
      expect(stats?.winCount).toBe(0);
      expect(stats?.lossCount).toBe(3);
    });

    it('should exclude pending signals from win rate calculation', () => {
      const signals = [
        createTestSignal({ id: '1', status: 'PENDING', outcome: undefined }),
        createTestSignal({ id: '2', outcome: 'WIN' }),
        createTestSignal({ id: '3', outcome: 'LOSS' })
      ];
      
      tracker.addSignalDataBatch(signals);
      const stats = tracker.getSuccessStats('test-provider');
      
      expect(stats?.totalSignals).toBe(3);
      expect(stats?.executedSignals).toBe(2);
      expect(stats?.winRate).toBe(50); // 1 win out of 2 executed = 50%
    });
  });

  describe('Risk-Reward Ratio Calculation', () => {
    it('should calculate correct average RR', () => {
      const signals = [
        createTestSignal({ id: '1', riskRewardRatio: 2.0 }),
        createTestSignal({ id: '2', riskRewardRatio: 1.5 }),
        createTestSignal({ id: '3', riskRewardRatio: 3.0 }),
        createTestSignal({ id: '4', riskRewardRatio: 1.0 })
      ];
      
      tracker.addSignalDataBatch(signals);
      const stats = tracker.getSuccessStats('test-provider');
      
      expect(stats?.averageRR).toBe(1.875); // (2.0 + 1.5 + 3.0 + 1.0) / 4
      expect(stats?.bestRR).toBe(3.0);
      expect(stats?.worstRR).toBe(1.0);
    });

    it('should handle missing RR values', () => {
      const signals = [
        createTestSignal({ id: '1', riskRewardRatio: 2.0 }),
        createTestSignal({ id: '2', riskRewardRatio: undefined }),
        createTestSignal({ id: '3', riskRewardRatio: 1.5 })
      ];
      
      tracker.addSignalDataBatch(signals);
      const stats = tracker.getSuccessStats('test-provider');
      
      expect(stats?.averageRR).toBe(1.75); // (2.0 + 1.5) / 2, ignoring undefined
    });

    it('should handle all missing RR values', () => {
      const signals = [
        createTestSignal({ id: '1', riskRewardRatio: undefined }),
        createTestSignal({ id: '2', riskRewardRatio: undefined })
      ];
      
      tracker.addSignalDataBatch(signals);
      const stats = tracker.getSuccessStats('test-provider');
      
      expect(stats?.averageRR).toBe(0);
      expect(stats?.bestRR).toBe(0);
      expect(stats?.worstRR).toBe(0);
    });
  });

  describe('Edge Cases', () => {
    it('should handle provider with 0 trades', () => {
      const stats = tracker.getSuccessStats('non-existent-provider');
      expect(stats).toBeNull();
    });

    it('should handle extreme drawdowns', () => {
      const signals = [
        createTestSignal({ id: '1', pnl: 100, executionTime: new Date('2024-01-01') }),
        createTestSignal({ id: '2', pnl: -500, executionTime: new Date('2024-01-02') }),
        createTestSignal({ id: '3', pnl: -200, executionTime: new Date('2024-01-03') }),
        createTestSignal({ id: '4', pnl: 300, executionTime: new Date('2024-01-04') })
      ];
      
      tracker.addSignalDataBatch(signals);
      const stats = tracker.getSuccessStats('test-provider');
      
      expect(stats?.maxDrawdown).toBe(600); // Peak at 100, lowest at -500
      expect(stats?.totalPnL).toBe(-300); // 100 - 500 - 200 + 300
    });

    it('should handle breakeven trades', () => {
      const signals = [
        createTestSignal({ id: '1', outcome: 'WIN', pnl: 50 }),
        createTestSignal({ id: '2', outcome: 'BREAKEVEN', pnl: 0 }),
        createTestSignal({ id: '3', outcome: 'LOSS', pnl: -30 })
      ];
      
      tracker.addSignalDataBatch(signals);
      const stats = tracker.getSuccessStats('test-provider');
      
      expect(stats?.winCount).toBe(1);
      expect(stats?.lossCount).toBe(1);
      expect(stats?.breakevenCount).toBe(1);
      expect(stats?.winRate).toBe(33.33333333333333); // 1 win out of 3 executed
    });

    it('should handle very large numbers', () => {
      const signals = [
        createTestSignal({ id: '1', pnl: 1000000, riskRewardRatio: 50 }),
        createTestSignal({ id: '2', pnl: -2000000, riskRewardRatio: 0.1 })
      ];
      
      tracker.addSignalDataBatch(signals);
      const stats = tracker.getSuccessStats('test-provider');
      
      expect(stats?.totalPnL).toBe(-1000000);
      expect(stats?.averageRR).toBe(25.05); // (50 + 0.1) / 2
    });
  });

  describe('Multiple Providers', () => {
    it('should track multiple providers separately', () => {
      const provider1Signals = [
        createTestSignal({ id: '1', providerId: 'provider-1', outcome: 'WIN' }),
        createTestSignal({ id: '2', providerId: 'provider-1', outcome: 'LOSS' })
      ];
      
      const provider2Signals = [
        createTestSignal({ id: '3', providerId: 'provider-2', outcome: 'WIN' }),
        createTestSignal({ id: '4', providerId: 'provider-2', outcome: 'WIN' }),
        createTestSignal({ id: '5', providerId: 'provider-2', outcome: 'WIN' })
      ];
      
      tracker.addSignalDataBatch([...provider1Signals, ...provider2Signals]);
      
      const stats1 = tracker.getSuccessStats('provider-1');
      const stats2 = tracker.getSuccessStats('provider-2');
      
      expect(stats1?.winRate).toBe(50); // 1 win out of 2
      expect(stats2?.winRate).toBe(100); // 3 wins out of 3
      expect(stats1?.totalSignals).toBe(2);
      expect(stats2?.totalSignals).toBe(3);
    });

    it('should get all provider stats correctly', () => {
      const signals = [
        createTestSignal({ id: '1', providerId: 'provider-1', outcome: 'WIN' }),
        createTestSignal({ id: '2', providerId: 'provider-2', outcome: 'WIN' }),
        createTestSignal({ id: '3', providerId: 'provider-3', outcome: 'LOSS' })
      ];
      
      tracker.addSignalDataBatch(signals);
      const allStats = tracker.getAllProviderStats();
      
      expect(allStats).toHaveLength(3);
      expect(allStats.find(s => s.providerId === 'provider-1')).toBeTruthy();
      expect(allStats.find(s => s.providerId === 'provider-2')).toBeTruthy();
      expect(allStats.find(s => s.providerId === 'provider-3')).toBeTruthy();
    });

    it('should sort providers by win rate', () => {
      const signals = [
        createTestSignal({ id: '1', providerId: 'low-performer', outcome: 'LOSS' }),
        createTestSignal({ id: '2', providerId: 'high-performer', outcome: 'WIN' }),
        createTestSignal({ id: '3', providerId: 'medium-performer', outcome: 'WIN' }),
        createTestSignal({ id: '4', providerId: 'medium-performer', outcome: 'LOSS' })
      ];
      
      tracker.addSignalDataBatch(signals);
      const allStats = tracker.getAllProviderStats();
      
      expect(allStats[0].providerId).toBe('high-performer'); // 100% win rate
      expect(allStats[1].providerId).toBe('medium-performer'); // 50% win rate
      expect(allStats[2].providerId).toBe('low-performer'); // 0% win rate
    });
  });

  describe('Signal Format Tracking', () => {
    it('should track signal formats correctly', () => {
      const signals = [
        createTestSignal({ id: '1', signalFormat: 'format-a', outcome: 'WIN' }),
        createTestSignal({ id: '2', signalFormat: 'format-a', outcome: 'LOSS' }),
        createTestSignal({ id: '3', signalFormat: 'format-b', outcome: 'WIN' })
      ];
      
      tracker.addSignalDataBatch(signals);
      const formatStats = tracker.getFormatStats();
      
      const formatA = formatStats.find(f => f.format === 'format-a');
      const formatB = formatStats.find(f => f.format === 'format-b');
      
      expect(formatA?.totalSignals).toBe(2);
      expect(formatA?.successRate).toBe(50); // 1 win out of 2
      expect(formatB?.totalSignals).toBe(1);
      expect(formatB?.successRate).toBe(100); // 1 win out of 1
    });
  });

  describe('Filtering and Trends', () => {
    it('should filter signals by criteria', () => {
      const signals = [
        createTestSignal({ 
          id: '1', 
          providerId: 'provider-1', 
          symbol: 'EURUSD', 
          outcome: 'WIN',
          executionTime: new Date('2024-01-01')
        }),
        createTestSignal({ 
          id: '2', 
          providerId: 'provider-2', 
          symbol: 'GBPUSD', 
          outcome: 'LOSS',
          executionTime: new Date('2024-01-02')
        }),
        createTestSignal({ 
          id: '3', 
          providerId: 'provider-1', 
          symbol: 'EURUSD', 
          outcome: 'WIN',
          executionTime: new Date('2024-01-03')
        })
      ];
      
      tracker.addSignalDataBatch(signals);
      
      const filtered = tracker.filterSignals({
        providerId: 'provider-1',
        symbol: 'EURUSD',
        outcome: 'WIN'
      });
      
      expect(filtered).toHaveLength(2);
      expect(filtered.every(s => s.providerId === 'provider-1')).toBe(true);
      expect(filtered.every(s => s.symbol === 'EURUSD')).toBe(true);
      expect(filtered.every(s => s.outcome === 'WIN')).toBe(true);
    });

    it('should generate performance trends', () => {
      const signals = [
        createTestSignal({ 
          id: '1', 
          outcome: 'WIN', 
          pnl: 50,
          executionTime: new Date('2024-01-01')
        }),
        createTestSignal({ 
          id: '2', 
          outcome: 'LOSS', 
          pnl: -30,
          executionTime: new Date('2024-01-01')
        }),
        createTestSignal({ 
          id: '3', 
          outcome: 'WIN', 
          pnl: 40,
          executionTime: new Date('2024-01-02')
        })
      ];
      
      tracker.addSignalDataBatch(signals);
      const trends = tracker.getTrends('test-provider', 30);
      
      expect(trends).toHaveLength(2); // 2 different dates
      expect(trends[0].date).toBe('2024-01-01');
      expect(trends[0].winRate).toBe(50); // 1 win, 1 loss
      expect(trends[0].pnl).toBe(20); // 50 - 30
      expect(trends[1].date).toBe('2024-01-02');
      expect(trends[1].winRate).toBe(100); // 1 win
      expect(trends[1].pnl).toBe(40);
    });
  });

  describe('Platform Statistics', () => {
    it('should calculate platform-wide statistics', () => {
      const signals = [
        createTestSignal({ id: '1', providerId: 'p1', outcome: 'WIN', pnl: 100, riskRewardRatio: 2.0 }),
        createTestSignal({ id: '2', providerId: 'p1', outcome: 'LOSS', pnl: -50, riskRewardRatio: 1.0 }),
        createTestSignal({ id: '3', providerId: 'p2', outcome: 'WIN', pnl: 75, riskRewardRatio: 1.5 }),
        createTestSignal({ id: '4', providerId: 'p2', outcome: 'WIN', pnl: 60, riskRewardRatio: 3.0 })
      ];
      
      tracker.addSignalDataBatch(signals);
      const platformStats = tracker.getPlatformStats();
      
      expect(platformStats.totalProviders).toBe(2);
      expect(platformStats.totalSignals).toBe(4);
      expect(platformStats.overallWinRate).toBe(75); // 3 wins out of 4
      expect(platformStats.totalPnL).toBe(185); // 100 - 50 + 75 + 60
      expect(platformStats.averageRR).toBe(1.875); // (2.0 + 1.0 + 1.5 + 3.0) / 4
    });
  });

  describe('Performance Grading', () => {
    it('should assign correct performance grades', () => {
      // High performer: high win rate, good RR, high execution rate
      const highPerformerSignals = Array.from({ length: 10 }, (_, i) => 
        createTestSignal({ 
          id: `hp-${i}`, 
          providerId: 'high-performer',
          outcome: i < 8 ? 'WIN' : 'LOSS', // 80% win rate
          riskRewardRatio: 2.5 // Good RR 
        })
      );
      
      // Low performer: low win rate, poor RR, low execution rate
      const lowPerformerSignals = [
        createTestSignal({ 
          id: 'lp-1', 
          providerId: 'low-performer',
          outcome: 'LOSS',
          riskRewardRatio: 0.5
        }),
        createTestSignal({ 
          id: 'lp-2', 
          providerId: 'low-performer',
          outcome: 'LOSS',
          riskRewardRatio: 0.3
        })
      ];
      
      tracker.addSignalDataBatch([...highPerformerSignals, ...lowPerformerSignals]);
      
      const highStats = tracker.getSuccessStats('high-performer');
      const lowStats = tracker.getSuccessStats('low-performer');
      
      expect(highStats?.performanceGrade).toBe('A');
      expect(lowStats?.performanceGrade).toBe('F');
    });
  });

  describe('Data Export', () => {
    it('should export analytics data correctly', () => {
      const signals = [
        createTestSignal({ id: '1', outcome: 'WIN' }),
        createTestSignal({ id: '2', outcome: 'LOSS' })
      ];
      
      tracker.addSignalDataBatch(signals);
      const exportData = tracker.exportAnalyticsData();
      
      expect(exportData.providerStats).toHaveLength(1);
      expect(exportData.signalData).toHaveLength(2);
      expect(exportData.metadata.totalSignals).toBe(2);
      expect(exportData.metadata.exportDate).toBeInstanceOf(Date);
    });
  });

  describe('Convenience Functions', () => {
    it('should use convenience functions correctly', () => {
      const signal = createTestSignal();
      trackSignal(signal);
      
      const stats = getProviderStats('test-provider');
      expect(stats?.totalSignals).toBe(1);
      
      const allStats = getAllProviderStats();
      expect(allStats).toHaveLength(1);
      expect(allStats[0].providerId).toBe('test-provider');
    });
  });

  describe('Cache and Storage', () => {
    it('should handle localStorage persistence', () => {
      const trackerWithStorage = new SignalSuccessTracker({ enableLocalStorage: true });
      const signal = createTestSignal();
      
      trackerWithStorage.addSignalData(signal);
      
      // Create new instance to test persistence
      const newTracker = new SignalSuccessTracker({ enableLocalStorage: true });
      const stats = newTracker.getSuccessStats('test-provider');
      
      expect(stats?.totalSignals).toBe(1);
    });

    it('should clear cache correctly', () => {
      const signal = createTestSignal();
      tracker.addSignalData(signal);
      
      let stats = tracker.getSuccessStats('test-provider');
      expect(stats).toBeTruthy();
      
      tracker.clearCache();
      stats = tracker.getSuccessStats('test-provider');
      expect(stats).toBeNull();
    });
  });
});