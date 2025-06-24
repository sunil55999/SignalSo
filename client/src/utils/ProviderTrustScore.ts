/**
 * Provider Trust Score Engine
 * Evaluates signal providers based on historical performance and signal quality
 * Outputs a numeric trust score (0-100) with detailed metrics breakdown
 */

import { SignalExecutionData, ProviderSuccessStats } from './signal_success_tracker';

export interface TrustScoreMetrics {
  tp_rate: number;           // Take profit hit rate (0-1)
  sl_rate: number;           // Stop loss hit rate (0-1)  
  avg_drawdown: number;      // Average drawdown percentage
  cancel_rate: number;       // Cancelled signal ratio (0-1)
  confidence: number;        // Average parsing confidence (0-1)
  latency: number;          // Average execution delay in seconds
  execution_rate: number;    // Total trades vs total signals (0-1)
}

export interface ProviderTrustResult {
  provider_id: string;
  provider_name?: string;
  trust_score: number;       // 0-100 final score
  grade: 'A+' | 'A' | 'B+' | 'B' | 'C+' | 'C' | 'D' | 'F';
  metrics: TrustScoreMetrics;
  sample_size: number;       // Number of signals analyzed
  last_updated: Date;
  reliability_tier: 'EXCELLENT' | 'GOOD' | 'AVERAGE' | 'POOR' | 'INSUFFICIENT_DATA';
}

export interface TrustScoreWeights {
  tp_rate: number;
  sl_rate: number;
  avg_drawdown: number;
  cancel_rate: number;
  confidence: number;
  latency: number;
  execution_rate: number;
}

// Default weights for trust score calculation
const DEFAULT_WEIGHTS: TrustScoreWeights = {
  tp_rate: 0.25,           // 25% - Most important metric
  sl_rate: 0.15,           // 15% - Inverse weight (lower SL rate is better)
  avg_drawdown: 0.15,      // 15% - Inverse weight (lower drawdown is better) 
  cancel_rate: 0.10,       // 10% - Inverse weight (lower cancel rate is better)
  confidence: 0.15,        // 15% - Higher confidence is better
  latency: 0.10,           // 10% - Inverse weight (lower latency is better)
  execution_rate: 0.10     // 10% - Higher execution rate is better
};

export class ProviderTrustScoreEngine {
  private weights: TrustScoreWeights;
  private minSampleSize: number;

  constructor(weights?: Partial<TrustScoreWeights>, minSampleSize = 10) {
    this.weights = { ...DEFAULT_WEIGHTS, ...weights };
    this.minSampleSize = minSampleSize;
  }

  /**
   * Calculate trust score for a single provider
   */
  calculateTrustScore(
    providerId: string,
    signals: SignalExecutionData[],
    providerStats?: ProviderSuccessStats
  ): ProviderTrustResult {
    if (signals.length < this.minSampleSize) {
      return this.createInsufficientDataResult(providerId, signals);
    }

    const metrics = this.extractMetrics(signals, providerStats);
    const normalizedMetrics = this.normalizeMetrics(metrics);
    const weightedScore = this.calculateWeightedScore(normalizedMetrics);
    const grade = this.calculateGrade(weightedScore);
    const reliabilityTier = this.calculateReliabilityTier(weightedScore, signals.length);

    return {
      provider_id: providerId,
      provider_name: signals[0]?.providerName || providerStats?.providerName,
      trust_score: Math.round(weightedScore * 100) / 100,
      grade,
      metrics,
      sample_size: signals.length,
      last_updated: new Date(),
      reliability_tier: reliabilityTier
    };
  }

  /**
   * Calculate trust scores for multiple providers
   */
  calculateMultipleProviderScores(
    signalsByProvider: Record<string, SignalExecutionData[]>,
    statsByProvider?: Record<string, ProviderSuccessStats>
  ): ProviderTrustResult[] {
    const results: ProviderTrustResult[] = [];

    for (const [providerId, signals] of Object.entries(signalsByProvider)) {
      const stats = statsByProvider?.[providerId];
      const trustResult = this.calculateTrustScore(providerId, signals, stats);
      results.push(trustResult);
    }

    // Sort by trust score descending
    return results.sort((a, b) => b.trust_score - a.trust_score);
  }

  /**
   * Extract raw metrics from signal data
   */
  private extractMetrics(
    signals: SignalExecutionData[],
    providerStats?: ProviderSuccessStats
  ): TrustScoreMetrics {
    const executedSignals = signals.filter(s => s.status === 'EXECUTED' || s.status === 'CLOSED');
    const closedSignals = signals.filter(s => s.status === 'CLOSED' && s.outcome);
    const cancelledSignals = signals.filter(s => s.status === 'CANCELLED');

    // TP and SL rates
    const tpHits = closedSignals.filter(s => s.outcome === 'WIN').length;
    const slHits = closedSignals.filter(s => s.outcome === 'LOSS').length;
    const tp_rate = closedSignals.length > 0 ? tpHits / closedSignals.length : 0;
    const sl_rate = closedSignals.length > 0 ? slHits / closedSignals.length : 0;

    // Average drawdown calculation
    const drawdowns = closedSignals
      .filter(s => s.pnl !== undefined)
      .map(s => s.pnl! < 0 ? Math.abs(s.pnl!) : 0);
    const avg_drawdown = drawdowns.length > 0 
      ? drawdowns.reduce((sum, dd) => sum + dd, 0) / drawdowns.length 
      : 0;

    // Cancel rate
    const cancel_rate = signals.length > 0 ? cancelledSignals.length / signals.length : 0;

    // Average confidence
    const confidenceValues = signals
      .filter(s => s.confidence !== undefined)
      .map(s => s.confidence!);
    const confidence = confidenceValues.length > 0
      ? confidenceValues.reduce((sum, c) => sum + c, 0) / confidenceValues.length
      : 0.5; // Default neutral confidence

    // Average latency (execution delay)
    const latencyValues = executedSignals
      .filter(s => s.closeTime && s.executionTime)
      .map(s => (s.closeTime!.getTime() - s.executionTime.getTime()) / 1000);
    const latency = latencyValues.length > 0
      ? latencyValues.reduce((sum, l) => sum + l, 0) / latencyValues.length
      : 5.0; // Default 5 seconds

    // Execution rate
    const execution_rate = signals.length > 0 ? executedSignals.length / signals.length : 0;

    return {
      tp_rate,
      sl_rate,
      avg_drawdown,
      cancel_rate,
      confidence,
      latency,
      execution_rate
    };
  }

  /**
   * Normalize metrics to 0-1 range for consistent scoring
   */
  private normalizeMetrics(metrics: TrustScoreMetrics): TrustScoreMetrics {
    return {
      tp_rate: Math.max(0, Math.min(1, metrics.tp_rate)), // Already 0-1
      sl_rate: Math.max(0, Math.min(1, 1 - metrics.sl_rate)), // Invert: lower SL rate is better
      avg_drawdown: Math.max(0, Math.min(1, 1 - Math.min(metrics.avg_drawdown / 100, 1))), // Invert and cap at 100%
      cancel_rate: Math.max(0, Math.min(1, 1 - metrics.cancel_rate)), // Invert: lower cancel rate is better
      confidence: Math.max(0, Math.min(1, metrics.confidence)), // Already 0-1
      latency: Math.max(0, Math.min(1, 1 - Math.min(metrics.latency / 30, 1))), // Invert and cap at 30s
      execution_rate: Math.max(0, Math.min(1, metrics.execution_rate)) // Already 0-1
    };
  }

  /**
   * Calculate weighted score from normalized metrics
   */
  private calculateWeightedScore(normalizedMetrics: TrustScoreMetrics): number {
    const score = 
      normalizedMetrics.tp_rate * this.weights.tp_rate +
      normalizedMetrics.sl_rate * this.weights.sl_rate +
      normalizedMetrics.avg_drawdown * this.weights.avg_drawdown +
      normalizedMetrics.cancel_rate * this.weights.cancel_rate +
      normalizedMetrics.confidence * this.weights.confidence +
      normalizedMetrics.latency * this.weights.latency +
      normalizedMetrics.execution_rate * this.weights.execution_rate;

    return Math.max(0, Math.min(100, score * 100));
  }

  /**
   * Convert numeric score to letter grade
   */
  private calculateGrade(score: number): 'A+' | 'A' | 'B+' | 'B' | 'C+' | 'C' | 'D' | 'F' {
    if (score >= 95) return 'A+';
    if (score >= 90) return 'A';
    if (score >= 85) return 'B+';
    if (score >= 80) return 'B';
    if (score >= 75) return 'C+';
    if (score >= 70) return 'C';
    if (score >= 60) return 'D';
    return 'F';
  }

  /**
   * Calculate reliability tier based on score and sample size
   */
  private calculateReliabilityTier(
    score: number, 
    sampleSize: number
  ): 'EXCELLENT' | 'GOOD' | 'AVERAGE' | 'POOR' | 'INSUFFICIENT_DATA' {
    if (sampleSize < this.minSampleSize) {
      return 'INSUFFICIENT_DATA';
    }

    // Adjust thresholds based on sample size confidence
    const confidenceMultiplier = Math.min(1, sampleSize / 50); // Full confidence at 50+ signals
    const adjustedScore = score * confidenceMultiplier;

    if (adjustedScore >= 85) return 'EXCELLENT';
    if (adjustedScore >= 70) return 'GOOD';
    if (adjustedScore >= 55) return 'AVERAGE';
    return 'POOR';
  }

  /**
   * Create result for providers with insufficient data
   */
  private createInsufficientDataResult(
    providerId: string,
    signals: SignalExecutionData[]
  ): ProviderTrustResult {
    return {
      provider_id: providerId,
      provider_name: signals[0]?.providerName,
      trust_score: 50, // Neutral score
      grade: 'C',
      metrics: {
        tp_rate: 0,
        sl_rate: 0,
        avg_drawdown: 0,
        cancel_rate: 0,
        confidence: 0.5,
        latency: 5.0,
        execution_rate: 0
      },
      sample_size: signals.length,
      last_updated: new Date(),
      reliability_tier: 'INSUFFICIENT_DATA'
    };
  }

  /**
   * Get comparative analysis between providers
   */
  getComparativeAnalysis(results: ProviderTrustResult[]): {
    best_performer: ProviderTrustResult | null;
    worst_performer: ProviderTrustResult | null;
    average_score: number;
    score_distribution: Record<string, number>;
    recommendations: string[];
  } {
    if (results.length === 0) {
      return {
        best_performer: null,
        worst_performer: null,
        average_score: 0,
        score_distribution: {},
        recommendations: ['No provider data available for analysis']
      };
    }

    const validResults = results.filter(r => r.reliability_tier !== 'INSUFFICIENT_DATA');
    const sortedResults = [...validResults].sort((a, b) => b.trust_score - a.trust_score);

    const average_score = validResults.length > 0
      ? validResults.reduce((sum, r) => sum + r.trust_score, 0) / validResults.length
      : 0;

    // Score distribution by grade
    const score_distribution: Record<string, number> = {};
    results.forEach(r => {
      score_distribution[r.grade] = (score_distribution[r.grade] || 0) + 1;
    });

    // Generate recommendations
    const recommendations: string[] = [];
    
    if (sortedResults.length > 0) {
      const topProvider = sortedResults[0];
      if (topProvider.trust_score >= 80) {
        recommendations.push(`Consider prioritizing signals from ${topProvider.provider_name || topProvider.provider_id} (${topProvider.trust_score}% trust score)`);
      }

      const poorProviders = sortedResults.filter(r => r.trust_score < 50);
      if (poorProviders.length > 0) {
        recommendations.push(`Review or reduce allocation to ${poorProviders.length} underperforming provider(s)`);
      }

      const insufficientData = results.filter(r => r.reliability_tier === 'INSUFFICIENT_DATA');
      if (insufficientData.length > 0) {
        recommendations.push(`${insufficientData.length} provider(s) need more signal history for reliable scoring`);
      }
    }

    return {
      best_performer: sortedResults[0] || null,
      worst_performer: sortedResults[sortedResults.length - 1] || null,
      average_score: Math.round(average_score * 100) / 100,
      score_distribution,
      recommendations
    };
  }

  /**
   * Real-time recalculation support
   */
  updateProviderScore(
    existingResult: ProviderTrustResult,
    newSignals: SignalExecutionData[]
  ): ProviderTrustResult {
    // This would typically merge with existing signal data
    // For now, recalculate with new signals
    return this.calculateTrustScore(existingResult.provider_id, newSignals);
  }

  /**
   * Export configuration for custom weighting
   */
  getConfiguration(): { weights: TrustScoreWeights; minSampleSize: number } {
    return {
      weights: { ...this.weights },
      minSampleSize: this.minSampleSize
    };
  }

  /**
   * Update scoring configuration
   */
  updateConfiguration(newWeights?: Partial<TrustScoreWeights>, newMinSampleSize?: number): void {
    if (newWeights) {
      this.weights = { ...this.weights, ...newWeights };
    }
    if (newMinSampleSize !== undefined) {
      this.minSampleSize = newMinSampleSize;
    }
  }
}

// Default engine instance
export const trustScoreEngine = new ProviderTrustScoreEngine();

// Utility functions for common use cases
export const calculateProviderTrustScore = (
  providerId: string,
  signals: SignalExecutionData[],
  stats?: ProviderSuccessStats
): ProviderTrustResult => {
  return trustScoreEngine.calculateTrustScore(providerId, signals, stats);
};

export const calculateMultipleProviderTrustScores = (
  signalsByProvider: Record<string, SignalExecutionData[]>,
  statsByProvider?: Record<string, ProviderSuccessStats>
): ProviderTrustResult[] => {
  return trustScoreEngine.calculateMultipleProviderScores(signalsByProvider, statsByProvider);
};

export const getProviderComparison = (results: ProviderTrustResult[]) => {
  return trustScoreEngine.getComparativeAnalysis(results);
};