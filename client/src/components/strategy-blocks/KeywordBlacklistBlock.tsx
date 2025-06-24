import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Trash2, Plus, AlertTriangle, Check, X, Eye, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface KeywordBlacklistConfig {
  keywords: string[];
  caseSensitive: boolean;
  wholeWordsOnly: boolean;
  enableSystemKeywords: boolean;
  matchMode: 'any' | 'all';
  logBlockedSignals: boolean;
  notifyOnBlock: boolean;
}

export interface BlacklistResult {
  isBlocked: boolean;
  matchedKeywords: string[];
  reason: string;
  confidence: number;
}

export interface KeywordBlacklistBlockProps {
  id: string;
  title?: string;
  config: KeywordBlacklistConfig;
  testSignal?: {
    rawMessage: string;
    symbol?: string;
    action?: string;
  };
  onUpdate: (config: KeywordBlacklistConfig) => void;
  onDelete?: () => void;
  className?: string;
}

const DEFAULT_CONFIG: KeywordBlacklistConfig = {
  keywords: [],
  caseSensitive: false,
  wholeWordsOnly: true,
  enableSystemKeywords: true,
  matchMode: 'any',
  logBlockedSignals: true,
  notifyOnBlock: true,
};

const SYSTEM_KEYWORDS = [
  'high risk',
  'manual only',
  'no sl',
  'no stop loss',
  'low accuracy',
  'risky',
  'dangerous',
  'not recommended',
  'use with caution',
  'scalp only',
  'demo only',
  'paper trade',
];

const SUGGESTED_KEYWORDS = [
  'avoid',
  'skip',
  'ignore',
  'experimental',
  'test',
  'uncertain',
  'maybe',
  'probably',
  'might',
  'could be',
  'not sure',
  'doubtful',
];

export default function KeywordBlacklistBlock({
  id,
  title = "Keyword Blacklist",
  config,
  testSignal,
  onUpdate,
  onDelete,
  className
}: KeywordBlacklistBlockProps) {
  const [localConfig, setLocalConfig] = useState<KeywordBlacklistConfig>(config);
  const [newKeyword, setNewKeyword] = useState('');
  const [bulkKeywords, setBulkKeywords] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showBulkAdd, setShowBulkAdd] = useState(false);

  // Get effective keywords list (user + system keywords)
  const effectiveKeywords = useMemo(() => {
    const userKeywords = localConfig.keywords;
    const systemKeywords = localConfig.enableSystemKeywords ? SYSTEM_KEYWORDS : [];
    return [...userKeywords, ...systemKeywords];
  }, [localConfig.keywords, localConfig.enableSystemKeywords]);

  // Check if test signal would be blocked
  const blacklistResult = useMemo((): BlacklistResult => {
    if (!testSignal?.rawMessage) {
      return {
        isBlocked: false,
        matchedKeywords: [],
        reason: 'No test signal provided',
        confidence: 0,
      };
    }

    const message = localConfig.caseSensitive 
      ? testSignal.rawMessage 
      : testSignal.rawMessage.toLowerCase();

    const keywordsToCheck = effectiveKeywords.map(keyword => 
      localConfig.caseSensitive ? keyword : keyword.toLowerCase()
    );

    const matchedKeywords: string[] = [];

    for (const keyword of keywordsToCheck) {
      let isMatch = false;

      if (localConfig.wholeWordsOnly) {
        // Use word boundaries for whole word matching
        const regex = new RegExp(`\\b${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'g');
        isMatch = regex.test(message);
      } else {
        // Simple substring matching
        isMatch = message.includes(keyword);
      }

      if (isMatch) {
        matchedKeywords.push(keyword);
        
        // If mode is 'any', we can stop at first match
        if (localConfig.matchMode === 'any') {
          break;
        }
      }
    }

    const isBlocked = localConfig.matchMode === 'any' 
      ? matchedKeywords.length > 0
      : matchedKeywords.length === keywordsToCheck.length && keywordsToCheck.length > 0;

    let reason = '';
    if (isBlocked) {
      reason = `Signal blocked - matched keywords: ${matchedKeywords.slice(0, 3).join(', ')}${matchedKeywords.length > 3 ? '...' : ''}`;
    } else {
      reason = keywordsToCheck.length === 0 
        ? 'No keywords configured - signal allowed'
        : 'No keyword matches found - signal allowed';
    }

    return {
      isBlocked,
      matchedKeywords,
      reason,
      confidence: isBlocked ? Math.min(95, 60 + (matchedKeywords.length * 10)) : 100,
    };
  }, [testSignal, effectiveKeywords, localConfig]);

  // Update parent when config changes
  useEffect(() => {
    onUpdate(localConfig);
  }, [localConfig, onUpdate]);

  const updateConfig = (updates: Partial<KeywordBlacklistConfig>) => {
    setLocalConfig(prev => ({ ...prev, ...updates }));
  };

  const addKeyword = () => {
    if (newKeyword.trim() && !localConfig.keywords.includes(newKeyword.trim())) {
      updateConfig({
        keywords: [...localConfig.keywords, newKeyword.trim()]
      });
      setNewKeyword('');
    }
  };

  const removeKeyword = (keyword: string) => {
    updateConfig({
      keywords: localConfig.keywords.filter(k => k !== keyword)
    });
  };

  const addBulkKeywords = () => {
    const keywords = bulkKeywords
      .split(/[\n,]/)
      .map(k => k.trim())
      .filter(k => k && !localConfig.keywords.includes(k));
    
    if (keywords.length > 0) {
      updateConfig({
        keywords: [...localConfig.keywords, ...keywords]
      });
      setBulkKeywords('');
      setShowBulkAdd(false);
    }
  };

  const addSuggestedKeyword = (keyword: string) => {
    if (!localConfig.keywords.includes(keyword)) {
      updateConfig({
        keywords: [...localConfig.keywords, keyword]
      });
    }
  };

  const clearAllKeywords = () => {
    updateConfig({ keywords: [] });
  };

  const getStatusColor = () => {
    if (effectiveKeywords.length === 0) return 'bg-gray-500';
    if (blacklistResult.isBlocked) return 'bg-red-500';
    return 'bg-green-500';
  };

  const getStatusText = () => {
    if (effectiveKeywords.length === 0) return 'Inactive';
    if (blacklistResult.isBlocked) return 'Blocked';
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
            <Badge variant={blacklistResult.isBlocked ? "destructive" : "default"} className="text-xs">
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
        {/* Keyword Management */}
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <Label className="text-xs font-medium">Blacklisted Keywords</Label>
            <span className="text-xs text-gray-500">
              {localConfig.keywords.length} custom + {localConfig.enableSystemKeywords ? SYSTEM_KEYWORDS.length : 0} system
            </span>
          </div>

          {/* Add new keyword */}
          <div className="flex gap-2">
            <Input
              placeholder="Enter keyword to blacklist"
              value={newKeyword}
              onChange={(e) => setNewKeyword(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && addKeyword()}
              className="h-8 text-sm"
            />
            <Button
              onClick={addKeyword}
              size="sm"
              disabled={!newKeyword.trim()}
              className="h-8"
            >
              <Plus className="h-3 w-3" />
            </Button>
          </div>

          {/* Bulk add toggle */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowBulkAdd(!showBulkAdd)}
              className="text-xs"
            >
              Bulk Add
            </Button>
            {localConfig.keywords.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={clearAllKeywords}
                className="text-xs text-red-600 hover:text-red-700"
              >
                Clear All
              </Button>
            )}
          </div>

          {/* Bulk add textarea */}
          {showBulkAdd && (
            <div className="space-y-2 bg-gray-50 p-3 rounded-lg">
              <Label className="text-xs">Add multiple keywords (one per line or comma-separated)</Label>
              <Textarea
                placeholder="high risk&#10;manual only&#10;no sl"
                value={bulkKeywords}
                onChange={(e) => setBulkKeywords(e.target.value)}
                className="h-20 text-sm"
              />
              <div className="flex gap-2">
                <Button size="sm" onClick={addBulkKeywords} className="text-xs">
                  Add Keywords
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => setShowBulkAdd(false)}
                  className="text-xs"
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {/* User keywords list */}
          {localConfig.keywords.length > 0 && (
            <div className="space-y-1">
              <Label className="text-xs text-gray-600">Custom Keywords:</Label>
              <div className="flex flex-wrap gap-1">
                {localConfig.keywords.map((keyword, index) => (
                  <Badge key={index} variant="secondary" className="text-xs flex items-center gap-1">
                    {keyword}
                    <button
                      onClick={() => removeKeyword(keyword)}
                      className="text-gray-500 hover:text-red-500"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* System keywords display */}
          {localConfig.enableSystemKeywords && (
            <div className="space-y-1">
              <Label className="text-xs text-gray-600">System Keywords:</Label>
              <div className="flex flex-wrap gap-1">
                {SYSTEM_KEYWORDS.slice(0, 6).map((keyword, index) => (
                  <Badge key={index} variant="outline" className="text-xs">
                    {keyword}
                  </Badge>
                ))}
                {SYSTEM_KEYWORDS.length > 6 && (
                  <Badge variant="outline" className="text-xs">
                    +{SYSTEM_KEYWORDS.length - 6} more
                  </Badge>
                )}
              </div>
            </div>
          )}

          {/* Suggested keywords */}
          <div className="space-y-1">
            <Label className="text-xs text-gray-600">Quick Add:</Label>
            <div className="flex flex-wrap gap-1">
              {SUGGESTED_KEYWORDS.slice(0, 6).map((keyword) => (
                <Button
                  key={keyword}
                  variant="ghost"
                  size="sm"
                  onClick={() => addSuggestedKeyword(keyword)}
                  disabled={localConfig.keywords.includes(keyword)}
                  className="h-6 text-xs px-2"
                >
                  +{keyword}
                </Button>
              ))}
            </div>
          </div>
        </div>

        {/* Test Signal Result */}
        {testSignal && (
          <div className={cn(
            "p-3 rounded-lg border-l-4",
            blacklistResult.isBlocked ? "bg-red-50 border-red-500" : "bg-green-50 border-green-500"
          )}>
            <div className="flex items-center gap-2 mb-2">
              {blacklistResult.isBlocked ? (
                <AlertTriangle className="h-4 w-4 text-red-600" />
              ) : (
                <Search className="h-4 w-4 text-green-600" />
              )}
              <span className="text-sm font-medium">
                {blacklistResult.isBlocked ? 'Signal Blocked' : 'Signal Allowed'}
              </span>
              <Badge variant="outline" className="text-xs">
                {blacklistResult.confidence}% confidence
              </Badge>
            </div>
            <p className="text-xs text-gray-600 mb-2">{blacklistResult.reason}</p>
            {blacklistResult.matchedKeywords.length > 0 && (
              <div className="space-y-1">
                <span className="text-xs font-medium">Matched keywords:</span>
                <div className="flex flex-wrap gap-1">
                  {blacklistResult.matchedKeywords.map((keyword, index) => (
                    <Badge key={index} variant="destructive" className="text-xs">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

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
              {/* Case Sensitivity */}
              <div className="flex items-center justify-between">
                <Label className="text-xs font-medium">Case Sensitive</Label>
                <Switch
                  checked={localConfig.caseSensitive}
                  onCheckedChange={(checked) => updateConfig({ caseSensitive: checked })}
                />
              </div>

              {/* Whole Words Only */}
              <div className="flex items-center justify-between">
                <Label className="text-xs font-medium">Whole Words Only</Label>
                <Switch
                  checked={localConfig.wholeWordsOnly}
                  onCheckedChange={(checked) => updateConfig({ wholeWordsOnly: checked })}
                />
              </div>

              {/* System Keywords */}
              <div className="flex items-center justify-between">
                <Label className="text-xs font-medium">Include System Keywords</Label>
                <Switch
                  checked={localConfig.enableSystemKeywords}
                  onCheckedChange={(checked) => updateConfig({ enableSystemKeywords: checked })}
                />
              </div>

              {/* Match Mode */}
              <div className="space-y-2">
                <Label className="text-xs font-medium">Match Mode</Label>
                <Select
                  value={localConfig.matchMode}
                  onValueChange={(value: 'any' | 'all') => updateConfig({ matchMode: value })}
                >
                  <SelectTrigger className="h-8">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="any">Block if ANY keyword matches</SelectItem>
                    <SelectItem value="all">Block only if ALL keywords match</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Logging Options */}
              <div className="flex items-center justify-between">
                <Label className="text-xs font-medium">Log Blocked Signals</Label>
                <Switch
                  checked={localConfig.logBlockedSignals}
                  onCheckedChange={(checked) => updateConfig({ logBlockedSignals: checked })}
                />
              </div>

              <div className="flex items-center justify-between">
                <Label className="text-xs font-medium">Notify on Block</Label>
                <Switch
                  checked={localConfig.notifyOnBlock}
                  onCheckedChange={(checked) => updateConfig({ notifyOnBlock: checked })}
                />
              </div>
            </div>
          )}
        </div>

        {/* Test Signal Display */}
        {testSignal && (
          <div className="bg-blue-50 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <Search className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-medium">Test Signal</span>
            </div>
            <div className="text-xs space-y-1">
              <div className="bg-white p-2 rounded text-gray-700 font-mono">
                {testSignal.rawMessage.length > 100 
                  ? `${testSignal.rawMessage.substring(0, 100)}...`
                  : testSignal.rawMessage
                }
              </div>
              {testSignal.symbol && <div>Symbol: {testSignal.symbol}</div>}
              {testSignal.action && <div>Action: {testSignal.action}</div>}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}