/**
 * Tests for Provider Trust Score Engine
 * Test scenarios: TP > 60% & low SL = high score, High cancel ratio → trust < 50,
 * Score normalizes correctly, Edge case: < 10 signals → neutral score fallback
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  ProviderTrustScoreEngine,
  calculateProviderTrustScore,
  calculateMultipleProviderTrustScores,
  getProviderComparison,
  TrustScoreWeights
} from '../utils/ProviderTrustScore';
import { SignalExecutionData } from '../utils/signal_success_tracker';

describe('ProviderTrustScoreEngine', () => {
  let engine: ProviderTrustScoreEngine;
  let mockSignals: SignalExecutionData[];

  beforeEach(() => {
    engine = new ProviderTrustScoreEngine();
    
    // Create base mock signals for testing
    mockSignals = [
      {
        id: '1',
        providerId: '@gold_signals',
        providerName: 'Gold Signals Pro',
        symbol: 'XAUUSD',
        entryPrice: 2000.0,
        exitPrice: 2020.0,
        stopLoss: 1990.0,
        takeProfit: 2030.0,
        lotSize: 0.1,
        direction: 'BUY',
        status: 'CLOSED',
        outcome: 'WIN',
        pnl: 200.0,
        riskRewardRatio: 2.0,
        executionTime: new Date('2024-01-01T10:00:00Z'),
        closeTime: new Date('2024-01-01T12:00:00Z'),
        confidence: 0.95,
        signalFormat: 'premium',
        metadata: {}
      },
      {
        id: '2',
        providerId: '@gold_signals',
        providerName: 'Gold Signals Pro',
        symbol: 'XAUUSD',
        entryPrice: 2010.0,
        exitPrice: 2005.0,
        stopLoss: 2000.0,
        takeProfit: 2040.0,
        lotSize: 0.1,
        direction: 'SELL',
        status: 'CLOSED',
        outcome: 'LOSS',
        pnl: -50.0,
        riskRewardRatio: 3.0,
        executionTime: new Date('2024-01-02T10:00:00Z'),
        closeTime: new Date('2024-01-02T11:30:00Z'),
        confidence: 0.88,
        signalFormat: 'standard',
        metadata: {}
      }
    ];
  });

  describe('calculateTrustScore', () => {
    it('should return high score for TP > 60% and low SL rate', () => {
      // Create signals with 70% TP rate (7 wins, 3 losses)
      const highPerformanceSignals: SignalExecutionData[] = [
        ...Array(7).fill(null).map((_, i) => ({
          ...mockSignals[0],
          id: `win_${i}`,
          outcome: 'WIN' as const,
          pnl: 100 + i * 10,
          confidence: 0.9 + (i * 0.01)
        })),
        ...Array(3).fill(null).map((_, i) => ({
          ...mockSignals[1],
          id: `loss_${i}`,
          outcome: 'LOSS' as const,
          pnl: -50 - i * 5,
          confidence: 0.85 + (i * 0.01)
        }))
      ];

      const result = engine.calculateTrustScore('@high_performance', highPerformanceSignals);

      expect(result.trust_score).toBeGreaterThan(70);
      expect(result.metrics.tp_rate).toBe(0.7);
      expect(result.metrics.sl_rate).toBe(0.3);
      expect(result.grade).toMatch(/^[A-C]/); // Should be A, B, or C grade
      expect(result.reliability_tier).toBe('GOOD');
    });

    it('should return trust score < 50 for high cancel ratio', () => {
      // Create signals with high cancellation rate (60% cancelled)
      const highCancelSignals: SignalExecutionData[] = [
        ...Array(6).fill(null).map((_, i) => ({
          ...mockSignals[0],
          id: `cancelled_${i}`,
          status: 'CANCELLED' as const,
          outcome: undefined,
          pnl: undefined,
          confidence: 0.7
        })),
        ...Array(4).fill(null).map((_, i) => ({
          ...mockSignals[0],
          id: `executed_${i}`,
          status: 'CLOSED' as const,
          outcome: 'WIN' as const,
          pnl: 50,
          confidence: 0.8
        }))
      ];

      const result = engine.calculateTrustScore('@high_cancel', highCancelSignals);

      expect(result.trust_score).toBeLessThan(50);
      expect(result.metrics.cancel_rate).toBe(0.6);
      expect(result.reliability_tier).toBe('POOR');
    });

    it('should normalize scores correctly across different providers', () => {
      // Provider A: Good performance
      const providerASignals: SignalExecutionData[] = Array(15).fill(null).map((_, i) => ({
        ...mockSignals[0],
        id: `a_${i}`,
        outcome: i < 10 ? 'WIN' : 'LOSS',
        pnl: i < 10 ? 100 : -50,
        confidence: 0.9,
        executionTime: new Date(`2024-01-${i + 1}T10:00:00Z`),
        closeTime: new Date(`2024-01-${i + 1}T10:01:00Z`)
      }));

      // Provider B: Poor performance  
      const providerBSignals: SignalExecutionData[] = Array(15).fill(null).map((_, i) => ({
        ...mockSignals[1],
        id: `b_${i}`,
        outcome: i < 5 ? 'WIN' : 'LOSS',
        pnl: i < 5 ? 50 : -100,
        confidence: 0.6,
        executionTime: new Date(`2024-01-${i + 1}T10:00:00Z`),
        closeTime: new Date(`2024-01-${i + 1}T10:05:00Z`) // Higher latency
      }));

      const resultA = engine.calculateTrustScore('provider_a', providerASignals);
      const resultB = engine.calculateTrustScore('provider_b', providerBSignals);

      expect(resultA.trust_score).toBeGreaterThan(resultB.trust_score);
      expect(resultA.metrics.tp_rate).toBeGreaterThan(resultB.metrics.tp_rate);
      expect(resultA.metrics.confidence).toBeGreaterThan(resultB.metrics.confidence);
      expect(resultA.grade).toBeDefined();
      expect(resultB.grade).toBeDefined();
    });

    it('should return neutral score fallback for < 10 signals', () => {
      const fewSignals = mockSignals.slice(0, 5); // Only 5 signals

      const result = engine.calculateTrustScore('@insufficient_data', fewSignals);

      expect(result.trust_score).toBe(50); // Neutral score
      expect(result.grade).toBe('C');
      expect(result.sample_size).toBe(5);
      expect(result.reliability_tier).toBe('INSUFFICIENT_DATA');
    });

    it('should handle edge cases properly', () => {
      // Test with empty signals array
      const emptyResult = engine.calculateTrustScore('@empty', []);
      expect(emptyResult.reliability_tier).toBe('INSUFFICIENT_DATA');
      expect(emptyResult.trust_score).toBe(50);

      // Test with all pending signals
      const pendingSignals: SignalExecutionData[] = Array(15).fill(null).map((_, i) => ({
        ...mockSignals[0],
        id: `pending_${i}`,
        status: 'PENDING',
        outcome: undefined,
        pnl: undefined,
        closeTime: undefined
      }));

      const pendingResult = engine.calculateTrustScore('@pending_only', pendingSignals);
      expect(pendingResult.metrics.execution_rate).toBe(0);
      expect(pendingResult.trust_score).toBeLessThan(60); // Should be penalized for low execution
    });

    it('should calculate metrics correctly', () => {
      const testSignals: SignalExecutionData[] = [
        // 3 wins
        ...Array(3).fill(null).map((_, i) => ({
          ...mockSignals[0],
          id: `win_${i}`,
          outcome: 'WIN' as const,
          pnl: 100,
          confidence: 0.9,
          executionTime: new Date('2024-01-01T10:00:00Z'),
          closeTime: new Date('2024-01-01T10:01:00Z') // 1 second latency
        })),
        // 2 losses  
        ...Array(2).fill(null).map((_, i) => ({
          ...mockSignals[1],
          id: `loss_${i}`,
          outcome: 'LOSS' as const,
          pnl: -50,
          confidence: 0.8,
          executionTime: new Date('2024-01-01T10:00:00Z'),
          closeTime: new Date('2024-01-01T10:02:00Z') // 2 seconds latency
        })),
        // 1 cancelled
        {
          ...mockSignals[0],
          id: 'cancelled_1',
          status: 'CANCELLED',
          outcome: undefined,
          pnl: undefined,
          confidence: 0.7
        },
        // 4 executed but not closed yet
        ...Array(4).fill(null).map((_, i) => ({
          ...mockSignals[0],
          id: `executed_${i}`,
          status: 'EXECUTED' as const,
          outcome: undefined,
          closeTime: undefined,
          confidence: 0.85
        }))
      ];

      const result = engine.calculateTrustScore('@test_metrics', testSignals);

      // TP rate: 3 wins / 5 closed = 0.6
      expect(result.metrics.tp_rate).toBe(0.6);
      
      // SL rate: 2 losses / 5 closed = 0.4
      expect(result.metrics.sl_rate).toBe(0.4);
      
      // Cancel rate: 1 cancelled / 10 total = 0.1
      expect(result.metrics.cancel_rate).toBe(0.1);
      
      // Execution rate: 9 executed / 10 total = 0.9
      expect(result.metrics.execution_rate).toBe(0.9);
      
      // Average confidence: (0.9*3 + 0.8*2 + 0.7*1 + 0.85*4) / 10 = 0.84
      expect(result.metrics.confidence).toBeCloseTo(0.84, 2);
    });
  });

  describe('calculateMultipleProviderScores', () => {
    it('should calculate and sort multiple providers correctly', () => {
      const signalsByProvider = {
        '@excellent_provider': Array(20).fill(null).map((_, i) => ({
          ...mockSignals[0],
          id: `excellent_${i}`,
          outcome: i < 16 ? 'WIN' : 'LOSS', // 80% win rate
          confidence: 0.95,
          pnl: i < 16 ? 100 : -25
        })),
        '@poor_provider': Array(20).fill(null).map((_, i) => ({
          ...mockSignals[1],
          id: `poor_${i}`,
          outcome: i < 6 ? 'WIN' : 'LOSS', // 30% win rate
          confidence: 0.6,
          pnl: i < 6 ? 50 : -75
        }))
      };

      const results = engine.calculateMultipleProviderScores(signalsByProvider);

      expect(results).toHaveLength(2);
      expect(results[0].provider_id).toBe('@excellent_provider'); // Should be sorted first
      expect(results[0].trust_score).toBeGreaterThan(results[1].trust_score);
    });
  });

  describe('getComparativeAnalysis', () => {
    it('should provide correct comparative analysis', () => {
      const results = [
        {
          provider_id: '@best',
          trust_score: 90,
          grade: 'A' as const,
          metrics: {} as any,
          sample_size: 50,
          last_updated: new Date(),
          reliability_tier: 'EXCELLENT' as const
        },
        {
          provider_id: '@worst',
          trust_score: 30,
          grade: 'F' as const,
          metrics: {} as any,
          sample_size: 20,
          last_updated: new Date(),
          reliability_tier: 'POOR' as const
        },
        {
          provider_id: '@insufficient',
          trust_score: 50,
          grade: 'C' as const,
          metrics: {} as any,
          sample_size: 5,
          last_updated: new Date(),
          reliability_tier: 'INSUFFICIENT_DATA' as const
        }
      ];

      const analysis = engine.getComparativeAnalysis(results);

      expect(analysis.best_performer?.provider_id).toBe('@best');
      expect(analysis.worst_performer?.provider_id).toBe('@worst');
      expect(analysis.average_score).toBe(60); // (90 + 30) / 2, excluding insufficient data
      expect(analysis.score_distribution).toHaveProperty('A', 1);
      expect(analysis.score_distribution).toHaveProperty('F', 1);
      expect(analysis.recommendations).toContain(
        expect.stringContaining('Consider prioritizing signals from @best')
      );
      expect(analysis.recommendations).toContain(
        expect.stringContaining('Review or reduce allocation to 1 underperforming provider')
      );
    });
  });

  describe('Configuration and Updates', () => {
    it('should allow custom weights configuration', () => {
      const customWeights: Partial<TrustScoreWeights> = {
        tp_rate: 0.4,  // Increase importance of TP rate
        sl_rate: 0.2,
        confidence: 0.2
      };

      const customEngine = new ProviderTrustScoreEngine(customWeights, 5);
      const config = customEngine.getConfiguration();

      expect(config.weights.tp_rate).toBe(0.4);
      expect(config.weights.sl_rate).toBe(0.2);
      expect(config.weights.confidence).toBe(0.2);
      expect(config.minSampleSize).toBe(5);
    });

    it('should support real-time score updates', () => {
      const initialResult = engine.calculateTrustScore('@realtime', mockSignals);
      
      const newSignals = [
        ...mockSignals,
        {
          ...mockSignals[0],
          id: 'new_signal',
          outcome: 'WIN' as const,
          pnl: 150,
          confidence: 0.98
        }
      ];

      const updatedResult = engine.updateProviderScore(initialResult, newSignals);

      expect(updatedResult.last_updated.getTime()).toBeGreaterThan(initialResult.last_updated.getTime());
      expect(updatedResult.sample_size).toBe(newSignals.length);
    });
  });

  describe('Utility Functions', () => {
    it('should work with utility functions', () => {
      const result = calculateProviderTrustScore('@utility_test', mockSignals);
      expect(result).toBeDefined();
      expect(result.provider_id).toBe('@utility_test');

      const multipleResults = calculateMultipleProviderTrustScores({
        '@provider1': mockSignals,
        '@provider2': mockSignals
      });
      expect(multipleResults).toHaveLength(2);

      const comparison = getProviderComparison(multipleResults);
      expect(comparison).toHaveProperty('best_performer');
      expect(comparison).toHaveProperty('average_score');
    });
  });

  describe('Grade Calculation', () => {
    it('should assign correct grades based on scores', () => {
      const testCases = [
        { score: 97, expectedGrade: 'A+' },
        { score: 92, expectedGrade: 'A' },
        { score: 87, expectedGrade: 'B+' },
        { score: 82, expectedGrade: 'B' },
        { score: 77, expectedGrade: 'C+' },
        { score: 72, expectedGrade: 'C' },
        { score: 62, expectedGrade: 'D' },
        { score: 45, expectedGrade: 'F' }
      ];

      testCases.forEach(({ score, expectedGrade }) => {
        // Create signals that would result in the target score
        const targetSignals = Array(15).fill(null).map((_, i) => ({
          ...mockSignals[0],
          id: `grade_test_${i}`,
          outcome: 'WIN' as const,
          confidence: score / 100,
          pnl: 100
        }));

        // Use custom weights to control the score more precisely
        const testEngine = new ProviderTrustScoreEngine({ 
          confidence: 1.0, // Use only confidence for predictable scoring
          tp_rate: 0, sl_rate: 0, avg_drawdown: 0, cancel_rate: 0, latency: 0, execution_rate: 0
        });

        const result = testEngine.calculateTrustScore(`@grade_${score}`, targetSignals);
        expect(result.grade).toBe(expectedGrade);
      });
    });
  });
});