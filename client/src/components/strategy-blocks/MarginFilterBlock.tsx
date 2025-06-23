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
import { AlertTriangle, DollarSign, Shield, TrendingUp, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useQuery } from '@tanstack/react-query';

export interface MarginFilterConfig {
  filterType: 'percentage' | 'absolute';
  thresholdPercentage: number;
  thresholdAbsolute: number;
  allowOverride: boolean;
  overrideSignalTypes: string[];
  emergencyThreshold: number;
  checkInterval: number;
  enableRealTimeCheck: boolean;
}

export interface MarginStatus {
  freeMargin: number;
  totalMargin: number;
  usedMargin: number;
  marginLevel: number;
  equity: number;
  balance: number;
  lastUpdate: Date;
  isConnected: boolean;
}

export interface MarginFilterResult {
  passesFilter: boolean;
  currentMargin: number;
  thresholdValue: number;
  marginLevel: number;
  reason: string;
  overrideApplied: boolean;
  emergencyMode: boolean;
}

export interface MarginFilterBlockProps {
  id: string;
  title?: string;
  config: MarginFilterConfig;
  testSignal?: {
    symbol: string;
    action: 'BUY' | 'SELL';
    signalType?: string;
  };
  onUpdate: (config: MarginFilterConfig) => void;
  onDelete?: () => void;
  className?: string;
}

const DEFAULT_CONFIG: MarginFilterConfig = {
  filterType: 'percentage',
  thresholdPercentage: 25,
  thresholdAbsolute: 1000,
  allowOverride: false,
  overrideSignalTypes: [],
  emergencyThreshold: 10,
  checkInterval: 30,
  enableRealTimeCheck: true,
};

const SIGNAL_TYPES = [
  { value: 'HIGH_CONFIDENCE', label: 'High Confidence' },
  { value: 'BREAKOUT', label: 'Breakout' },
  { value: 'REVERSAL', label: 'Reversal' },
  { value: 'SCALP', label: 'Scalp' },
  { value: 'SWING', label: 'Swing' },
];

export default function MarginFilterBlock({
  id,
  title = "Margin Filter",
  config,
  testSignal,
  onUpdate,
  onDelete,
  className
}: MarginFilterBlockProps) {
  const [localConfig, setLocalConfig] = useState<MarginFilterConfig>(config);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Fetch current margin status
  const { data: marginStatus, isLoading: marginLoading } = useQuery<MarginStatus>({
    queryKey: ['/api/margin/status'],
    refetchInterval: localConfig.enableRealTimeCheck ? localConfig.checkInterval * 1000 : false,
    retry: 2,
  });

  // Calculate margin filter result
  const filterResult = useMemo((): MarginFilterResult => {
    if (!marginStatus) {
      return {
        passesFilter: false,
        currentMargin: 0,
        thresholdValue: localConfig.filterType === 'percentage' ? localConfig.thresholdPercentage : localConfig.thresholdAbsolute,
        marginLevel: 0,
        reason: 'Margin data unavailable',
        overrideApplied: false,
        emergencyMode: false,
      };
    }

    const currentValue = localConfig.filterType === 'percentage' 
      ? marginStatus.marginLevel 
      : marginStatus.freeMargin;
    
    const threshold = localConfig.filterType === 'percentage' 
      ? localConfig.thresholdPercentage 
      : localConfig.thresholdAbsolute;

    const emergency = marginStatus.marginLevel < localConfig.emergencyThreshold;
    
    // Check for override conditions
    const overrideApplied = localConfig.allowOverride && 
      testSignal?.signalType && 
      localConfig.overrideSignalTypes.includes(testSignal.signalType);

    const basePass = currentValue >= threshold;
    const passesFilter = emergency ? false : (basePass || Boolean(overrideApplied));

    let reason = '';
    if (emergency) {
      reason = `Emergency threshold breached (${marginStatus.marginLevel.toFixed(1)}% < ${localConfig.emergencyThreshold}%)`;
    } else if (!basePass && !overrideApplied) {
      reason = localConfig.filterType === 'percentage' 
        ? `Margin level too low (${marginStatus.marginLevel.toFixed(1)}% < ${threshold}%)`
        : `Free margin too low ($${marginStatus.freeMargin.toFixed(2)} < $${threshold})`;
    } else if (overrideApplied) {
      reason = `Override applied for ${testSignal?.signalType} signal type`;
    } else {
      reason = localConfig.filterType === 'percentage'
        ? `Margin level sufficient (${marginStatus.marginLevel.toFixed(1)}% ≥ ${threshold}%)`
        : `Free margin sufficient ($${marginStatus.freeMargin.toFixed(2)} ≥ $${threshold})`;
    }

    return {
      passesFilter,
      currentMargin: currentValue,
      thresholdValue: threshold,
      marginLevel: marginStatus.marginLevel,
      reason,
      overrideApplied: Boolean(overrideApplied),
      emergencyMode: Boolean(emergency),
    };
  }, [marginStatus, localConfig, testSignal]);

  // Update parent when config changes
  useEffect(() => {
    onUpdate(localConfig);
  }, [localConfig, onUpdate]);

  const updateConfig = (updates: Partial<MarginFilterConfig>) => {
    setLocalConfig(prev => ({ ...prev, ...updates }));
  };

  const getStatusColor = () => {
    if (!marginStatus?.isConnected) return 'bg-gray-500';
    if (filterResult.emergencyMode) return 'bg-red-500';
    if (!filterResult.passesFilter) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getStatusText = () => {
    if (!marginStatus?.isConnected) return 'Disconnected';
    if (filterResult.emergencyMode) return 'Emergency';
    if (!filterResult.passesFilter) return 'Blocked';
    return 'Active';
  };

  return (
    <Card className={cn("w-full max-w-md mx-auto relative", className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Shield className="h-4 w-4" />
            {title}
          </CardTitle>
          <div className="flex items-center gap-2">
            <div className={cn("w-2 h-2 rounded-full", getStatusColor())} />
            <Badge variant={filterResult.passesFilter ? "default" : "destructive"} className="text-xs">
              {getStatusText()}
            </Badge>
            {onDelete && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onDelete}
                className="h-6 w-6 p-0 text-gray-400 hover:text-red-500"
              >
                ×
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Filter Type Selection */}
        <div className="space-y-2">
          <Label className="text-xs font-medium">Filter Type</Label>
          <Select
            value={localConfig.filterType}
            onValueChange={(value: 'percentage' | 'absolute') => updateConfig({ filterType: value })}
          >
            <SelectTrigger className="h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="percentage">Margin Level (%)</SelectItem>
              <SelectItem value="absolute">Free Margin ($)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Threshold Configuration */}
        <div className="space-y-2">
          <Label className="text-xs font-medium">
            {localConfig.filterType === 'percentage' ? 'Minimum Margin Level (%)' : 'Minimum Free Margin ($)'}
          </Label>
          <div className="px-2">
            <Slider
              value={[localConfig.filterType === 'percentage' ? localConfig.thresholdPercentage : localConfig.thresholdAbsolute]}
              onValueChange={([value]) => updateConfig({
                [localConfig.filterType === 'percentage' ? 'thresholdPercentage' : 'thresholdAbsolute']: value
              })}
              min={localConfig.filterType === 'percentage' ? 0 : 0}
              max={localConfig.filterType === 'percentage' ? 1000 : 10000}
              step={localConfig.filterType === 'percentage' ? 5 : 100}
              className="w-full"
            />
          </div>
          <div className="text-center text-sm text-gray-600">
            {localConfig.filterType === 'percentage' 
              ? `${localConfig.thresholdPercentage}%` 
              : `$${localConfig.thresholdAbsolute.toLocaleString()}`}
          </div>
        </div>

        {/* Current Status Display */}
        {marginStatus && (
          <div className="bg-gray-50 rounded-lg p-3 space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-600">Current Margin Level</span>
              <span className="text-sm font-medium">{marginStatus.marginLevel.toFixed(1)}%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-600">Free Margin</span>
              <span className="text-sm font-medium">${marginStatus.freeMargin.toLocaleString()}</span>
            </div>
            <Progress 
              value={Math.min(marginStatus.marginLevel, 1000)} 
              className="h-2"
            />
          </div>
        )}

        {/* Filter Result */}
        <div className={cn(
          "p-3 rounded-lg border-l-4",
          filterResult.passesFilter ? "bg-green-50 border-green-500" : "bg-red-50 border-red-500"
        )}>
          <div className="flex items-center gap-2 mb-2">
            {filterResult.passesFilter ? (
              <TrendingUp className="h-4 w-4 text-green-600" />
            ) : (
              <AlertTriangle className="h-4 w-4 text-red-600" />
            )}
            <span className="text-sm font-medium">
              {filterResult.passesFilter ? 'Signal Allowed' : 'Signal Blocked'}
            </span>
          </div>
          <p className="text-xs text-gray-600">{filterResult.reason}</p>
          {filterResult.overrideApplied && (
            <Badge variant="outline" className="mt-1 text-xs">Override Applied</Badge>
          )}
        </div>

        {/* Advanced Settings */}
        <div className="space-y-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full justify-start text-xs"
          >
            <Settings className="h-3 w-3 mr-2" />
            Advanced Settings
          </Button>

          {showAdvanced && (
            <div className="space-y-3 bg-gray-50 p-3 rounded-lg">
              {/* Emergency Threshold */}
              <div className="space-y-2">
                <Label className="text-xs font-medium">Emergency Threshold (%)</Label>
                <Input
                  type="number"
                  value={localConfig.emergencyThreshold}
                  onChange={(e) => updateConfig({ emergencyThreshold: Number(e.target.value) })}
                  className="h-8"
                  min={0}
                  max={100}
                />
              </div>

              {/* Allow Override */}
              <div className="flex items-center justify-between">
                <Label className="text-xs font-medium">Allow Signal Override</Label>
                <Switch
                  checked={localConfig.allowOverride}
                  onCheckedChange={(checked) => updateConfig({ allowOverride: checked })}
                />
              </div>

              {/* Override Signal Types */}
              {localConfig.allowOverride && (
                <div className="space-y-2">
                  <Label className="text-xs font-medium">Override Signal Types</Label>
                  <div className="space-y-1">
                    {SIGNAL_TYPES.map((type) => (
                      <label key={type.value} className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={localConfig.overrideSignalTypes.includes(type.value)}
                          onChange={(e) => {
                            const types = e.target.checked
                              ? [...localConfig.overrideSignalTypes, type.value]
                              : localConfig.overrideSignalTypes.filter(t => t !== type.value);
                            updateConfig({ overrideSignalTypes: types });
                          }}
                          className="h-3 w-3"
                        />
                        <span className="text-xs">{type.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {/* Real-time Check */}
              <div className="flex items-center justify-between">
                <Label className="text-xs font-medium">Real-time Monitoring</Label>
                <Switch
                  checked={localConfig.enableRealTimeCheck}
                  onCheckedChange={(checked) => updateConfig({ enableRealTimeCheck: checked })}
                />
              </div>

              {/* Check Interval */}
              {localConfig.enableRealTimeCheck && (
                <div className="space-y-2">
                  <Label className="text-xs font-medium">Check Interval (seconds)</Label>
                  <Select
                    value={localConfig.checkInterval.toString()}
                    onValueChange={(value) => updateConfig({ checkInterval: Number(value) })}
                  >
                    <SelectTrigger className="h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="10">10 seconds</SelectItem>
                      <SelectItem value="30">30 seconds</SelectItem>
                      <SelectItem value="60">1 minute</SelectItem>
                      <SelectItem value="300">5 minutes</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Test Signal Display */}
        {testSignal && (
          <div className="bg-blue-50 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-medium">Test Signal</span>
            </div>
            <div className="text-xs space-y-1">
              <div>Symbol: {testSignal.symbol}</div>
              <div>Action: {testSignal.action}</div>
              {testSignal.signalType && <div>Type: {testSignal.signalType}</div>}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}