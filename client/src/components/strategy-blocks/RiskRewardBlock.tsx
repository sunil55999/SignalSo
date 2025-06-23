import { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Slider } from '@/components/ui/slider';
import { TrendingUp, TrendingDown, Calculator, AlertTriangle, Target } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface RiskRewardConfig {
  minimumRatio: number;
  calculationMethod: 'simple' | 'weighted' | 'conservative';
  considerMultipleTP: boolean;
  tpWeights: number[];
  riskToleranceMode: 'strict' | 'moderate' | 'flexible';
  dynamicAdjustment: boolean;
}

export interface SignalData {
  symbol: string;
  action: 'BUY' | 'SELL';
  entry: number;
  stopLoss: number;
  takeProfit1?: number;
  takeProfit2?: number;
  takeProfit3?: number;
  takeProfit4?: number;
  takeProfit5?: number;
  lotSize?: number;
}

export interface RiskRewardResult {
  ratio: number;
  riskPips: number;
  rewardPips: number;
  passesFilter: boolean;
  confidence: number;
  breakdown: {
    tp1?: { pips: number; weight: number; contribution: number };
    tp2?: { pips: number; weight: number; contribution: number };
    tp3?: { pips: number; weight: number; contribution: number };
    tp4?: { pips: number; weight: number; contribution: number };
    tp5?: { pips: number; weight: number; contribution: number };
  };
}

export interface RiskRewardBlockProps {
  id: string;
  title?: string;
  config: RiskRewardConfig;
  testSignal?: SignalData;
  onUpdate: (config: RiskRewardConfig) => void;
  onDelete?: () => void;
  className?: string;
}

const SYMBOL_PIP_VALUES: Record<string, number> = {
  'EURUSD': 0.0001,
  'GBPUSD': 0.0001,
  'AUDUSD': 0.0001,
  'NZDUSD': 0.0001,
  'USDCAD': 0.0001,
  'USDCHF': 0.0001,
  'USDJPY': 0.01,
  'EURJPY': 0.01,
  'GBPJPY': 0.01,
  'AUDJPY': 0.01,
  'NZDJPY': 0.01,
  'CADJPY': 0.01,
  'CHFJPY': 0.01,
  'XAUUSD': 0.1,
  'XAGUSD': 0.001,
};

const DEFAULT_CONFIG: RiskRewardConfig = {
  minimumRatio: 1.5,
  calculationMethod: 'weighted',
  considerMultipleTP: true,
  tpWeights: [0.5, 0.3, 0.2, 0.0, 0.0],
  riskToleranceMode: 'moderate',
  dynamicAdjustment: false
};

export function RiskRewardBlock({
  id,
  title = "Risk-Reward Filter",
  config = DEFAULT_CONFIG,
  testSignal,
  onUpdate,
  onDelete,
  className = ""
}: RiskRewardBlockProps) {
  const [localConfig, setLocalConfig] = useState<RiskRewardConfig>(config);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    onUpdate(localConfig);
  }, [localConfig, onUpdate]);

  const updateConfig = (updates: Partial<RiskRewardConfig>) => {
    setLocalConfig(prev => ({ ...prev, ...updates }));
  };

  const calculatePips = (symbol: string, price1: number, price2: number): number => {
    const pipValue = SYMBOL_PIP_VALUES[symbol] || 0.0001;
    return Math.abs(price1 - price2) / pipValue;
  };

  const calculateRiskReward = (signal: SignalData): RiskRewardResult => {
    if (!signal.entry || !signal.stopLoss) {
      return {
        ratio: 0,
        riskPips: 0,
        rewardPips: 0,
        passesFilter: false,
        confidence: 0,
        breakdown: {}
      };
    }

    const riskPips = calculatePips(signal.symbol, signal.entry, signal.stopLoss);
    const breakdown: RiskRewardResult['breakdown'] = {};
    let totalRewardPips = 0;
    let weightSum = 0;

    // Calculate reward based on available take profit levels
    const tpLevels = [
      signal.takeProfit1,
      signal.takeProfit2,
      signal.takeProfit3,
      signal.takeProfit4,
      signal.takeProfit5
    ].filter(tp => tp && tp > 0) as number[];

    if (tpLevels.length === 0) {
      return {
        ratio: 0,
        riskPips,
        rewardPips: 0,
        passesFilter: false,
        confidence: 0,
        breakdown
      };
    }

    // Apply calculation method
    switch (localConfig.calculationMethod) {
      case 'simple':
        // Use only first TP level
        totalRewardPips = calculatePips(signal.symbol, signal.entry, tpLevels[0]);
        breakdown.tp1 = {
          pips: totalRewardPips,
          weight: 1.0,
          contribution: totalRewardPips
        };
        break;

      case 'weighted':
        // Use weighted average of multiple TP levels
        tpLevels.forEach((tp, index) => {
          if (index < localConfig.tpWeights.length && localConfig.tpWeights[index] > 0) {
            const tpPips = calculatePips(signal.symbol, signal.entry, tp);
            const weight = localConfig.tpWeights[index];
            const contribution = tpPips * weight;
            
            totalRewardPips += contribution;
            weightSum += weight;
            
            breakdown[`tp${index + 1}` as keyof typeof breakdown] = {
              pips: tpPips,
              weight,
              contribution
            };
          }
        });
        
        // Normalize if weights don't sum to 1
        if (weightSum > 0 && weightSum !== 1) {
          totalRewardPips = totalRewardPips / weightSum;
        }
        break;

      case 'conservative':
        // Use the closest (most conservative) TP level
        const conservativeTp = signal.action === 'BUY' 
          ? Math.min(...tpLevels.filter(tp => tp > signal.entry))
          : Math.max(...tpLevels.filter(tp => tp < signal.entry));
        
        if (conservativeTp) {
          totalRewardPips = calculatePips(signal.symbol, signal.entry, conservativeTp);
          breakdown.tp1 = {
            pips: totalRewardPips,
            weight: 1.0,
            contribution: totalRewardPips
          };
        }
        break;
    }

    const ratio = riskPips > 0 ? totalRewardPips / riskPips : 0;
    const passesFilter = ratio >= localConfig.minimumRatio;
    
    // Calculate confidence based on how far above minimum ratio
    let confidence = 0;
    if (ratio >= localConfig.minimumRatio) {
      const excess = ratio - localConfig.minimumRatio;
      confidence = Math.min(100, 50 + (excess * 25)); // Base 50% + bonus
    } else {
      confidence = Math.max(0, (ratio / localConfig.minimumRatio) * 50);
    }

    return {
      ratio,
      riskPips,
      rewardPips: totalRewardPips,
      passesFilter,
      confidence,
      breakdown
    };
  };

  const rrResult = useMemo(() => {
    if (!testSignal) return null;
    return calculateRiskReward(testSignal);
  }, [testSignal, localConfig]);

  const formatRatio = (ratio: number): string => {
    return `1:${ratio.toFixed(2)}`;
  };

  const getRatioColor = (ratio: number): string => {
    if (ratio >= localConfig.minimumRatio * 1.5) return 'text-green-600';
    if (ratio >= localConfig.minimumRatio) return 'text-blue-600';
    if (ratio >= localConfig.minimumRatio * 0.8) return 'text-yellow-600';
    return 'text-red-600';
  };

  const updateTPWeight = (index: number, weight: number) => {
    const newWeights = [...localConfig.tpWeights];
    newWeights[index] = weight / 100; // Convert percentage to decimal
    updateConfig({ tpWeights: newWeights });
  };

  return (
    <Card className={cn("strategy-block risk-reward-block", className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center space-x-2">
          <Calculator className="h-4 w-4" />
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
        </div>
        <div className="flex items-center space-x-2">
          {rrResult && (
            <Badge variant={rrResult.passesFilter ? "default" : "destructive"}>
              {formatRatio(rrResult.ratio)}
            </Badge>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-6 w-6 p-0"
          >
            {isExpanded ? '−' : '+'}
          </Button>
          {onDelete && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onDelete}
              className="h-6 w-6 p-0"
            >
              ×
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Quick Status */}
        <div className="flex items-center justify-between p-2 bg-muted rounded-lg">
          <div className="flex items-center space-x-2">
            <Target className="h-4 w-4" />
            <span className="text-sm">Minimum R:R</span>
          </div>
          <span className="text-sm font-mono">
            {formatRatio(localConfig.minimumRatio)}
          </span>
        </div>

        {/* Test Signal Results */}
        {rrResult && (
          <div className="space-y-3 p-3 border rounded-lg">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Current Signal</span>
              <div className="flex items-center space-x-2">
                {rrResult.passesFilter ? (
                  <TrendingUp className="h-4 w-4 text-green-600" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-red-600" />
                )}
                <span className={cn("text-sm font-medium", getRatioColor(rrResult.ratio))}>
                  {formatRatio(rrResult.ratio)}
                </span>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-muted-foreground">Risk:</span>
                <span className="ml-1 font-mono">{rrResult.riskPips.toFixed(1)} pips</span>
              </div>
              <div>
                <span className="text-muted-foreground">Reward:</span>
                <span className="ml-1 font-mono">{rrResult.rewardPips.toFixed(1)} pips</span>
              </div>
            </div>
            
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span>Confidence</span>
                <span>{rrResult.confidence.toFixed(0)}%</span>
              </div>
              <Progress value={rrResult.confidence} className="h-2" />
            </div>
          </div>
        )}

        {/* Configuration */}
        {isExpanded && (
          <div className="space-y-4 border-t pt-4">
            {/* Minimum Ratio */}
            <div className="space-y-2">
              <Label>Minimum R:R Ratio</Label>
              <div className="flex items-center space-x-3">
                <Slider
                  value={[localConfig.minimumRatio]}
                  onValueChange={(value) => updateConfig({ minimumRatio: value[0] })}
                  min={0.5}
                  max={5.0}
                  step={0.1}
                  className="flex-1"
                />
                <span className="text-sm font-mono w-16">
                  1:{localConfig.minimumRatio.toFixed(1)}
                </span>
              </div>
            </div>

            {/* Calculation Method */}
            <div className="space-y-2">
              <Label>Calculation Method</Label>
              <Select
                value={localConfig.calculationMethod}
                onValueChange={(value: 'simple' | 'weighted' | 'conservative') => 
                  updateConfig({ calculationMethod: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="simple">Simple (First TP only)</SelectItem>
                  <SelectItem value="weighted">Weighted Average</SelectItem>
                  <SelectItem value="conservative">Conservative (Closest TP)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Multiple TP Consideration */}
            <div className="flex items-center justify-between">
              <Label>Consider Multiple TPs</Label>
              <Switch
                checked={localConfig.considerMultipleTP}
                onCheckedChange={(checked) => updateConfig({ considerMultipleTP: checked })}
              />
            </div>

            {/* TP Weights (only show if weighted method and multiple TP enabled) */}
            {localConfig.calculationMethod === 'weighted' && localConfig.considerMultipleTP && (
              <div className="space-y-3">
                <Label>Take Profit Weights</Label>
                {localConfig.tpWeights.map((weight, index) => (
                  <div key={index} className="flex items-center space-x-3">
                    <span className="text-sm w-8">TP{index + 1}</span>
                    <Slider
                      value={[weight * 100]}
                      onValueChange={(value) => updateTPWeight(index, value[0])}
                      min={0}
                      max={100}
                      step={5}
                      className="flex-1"
                    />
                    <span className="text-xs w-12">{(weight * 100).toFixed(0)}%</span>
                  </div>
                ))}
                <div className="text-xs text-muted-foreground">
                  Total: {(localConfig.tpWeights.reduce((sum, w) => sum + w, 0) * 100).toFixed(0)}%
                </div>
              </div>
            )}

            {/* Risk Tolerance Mode */}
            <div className="space-y-2">
              <Label>Risk Tolerance</Label>
              <Select
                value={localConfig.riskToleranceMode}
                onValueChange={(value: 'strict' | 'moderate' | 'flexible') => 
                  updateConfig({ riskToleranceMode: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="strict">Strict (Exact ratio required)</SelectItem>
                  <SelectItem value="moderate">Moderate (Small deviation allowed)</SelectItem>
                  <SelectItem value="flexible">Flexible (Adaptive threshold)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Dynamic Adjustment */}
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label>Dynamic Adjustment</Label>
                <p className="text-xs text-muted-foreground">
                  Adjust ratio based on market conditions
                </p>
              </div>
              <Switch
                checked={localConfig.dynamicAdjustment}
                onCheckedChange={(checked) => updateConfig({ dynamicAdjustment: checked })}
              />
            </div>
          </div>
        )}

        {/* Breakdown Display */}
        {rrResult && isExpanded && Object.keys(rrResult.breakdown).length > 0 && (
          <div className="space-y-2 border-t pt-4">
            <Label className="text-xs">Calculation Breakdown</Label>
            {Object.entries(rrResult.breakdown).map(([tp, data]) => (
              <div key={tp} className="flex justify-between text-xs">
                <span className="text-muted-foreground">{tp.toUpperCase()}</span>
                <span>
                  {data.pips.toFixed(1)} pips × {(data.weight * 100).toFixed(0)}% = {data.contribution.toFixed(1)}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Warning for low ratios */}
        {rrResult && !rrResult.passesFilter && (
          <div className="flex items-center space-x-2 p-2 bg-yellow-50 text-yellow-800 rounded-lg text-xs">
            <AlertTriangle className="h-3 w-3" />
            <span>Signal does not meet minimum R:R requirements</span>
          </div>
        )}

        {/* Connection Points */}
        <div className="flex justify-between pt-2 border-t">
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
            <span className="text-xs text-muted-foreground">Signal In</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="text-xs text-muted-foreground">Filtered Out</span>
            <div className={cn(
              "w-3 h-3 rounded-full",
              rrResult?.passesFilter ? "bg-green-500" : "bg-red-500"
            )}></div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default RiskRewardBlock;