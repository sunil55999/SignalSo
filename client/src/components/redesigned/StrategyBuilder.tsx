import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import { 
  Plus, 
  Play, 
  Save, 
  Edit2, 
  Trash2, 
  Brain,
  Code,
  BarChart3,
  Target,
  TrendingUp,
  Settings,
  Eye,
  TestTube
} from 'lucide-react';

interface Strategy {
  id: string;
  name: string;
  description: string;
  type: 'visual' | 'code' | 'natural';
  conditions: any[];
  riskManagement: {
    maxLotSize: number;
    stopLoss: number;
    takeProfit: number;
    riskPercent: number;
  };
  symbols: string[];
  active: boolean;
  backtest?: {
    period: string;
    results: any;
  };
}

export function StrategyBuilder() {
  const [activeTab, setActiveTab] = useState<'list' | 'builder' | 'backtest'>('list');
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [builderMode, setBuilderMode] = useState<'visual' | 'code' | 'natural'>('visual');
  const [naturalLanguageInput, setNaturalLanguageInput] = useState('');
  const { toast } = useToast();

  const [strategies, setStrategies] = useState<Strategy[]>([
    {
      id: '1',
      name: 'EUR/USD Scalping',
      description: 'High-frequency scalping strategy for EUR/USD pair',
      type: 'visual',
      conditions: [
        { type: 'rsi', value: 30, operator: 'below' },
        { type: 'macd', value: 0, operator: 'above' }
      ],
      riskManagement: {
        maxLotSize: 0.1,
        stopLoss: 20,
        takeProfit: 30,
        riskPercent: 2.0
      },
      symbols: ['EURUSD'],
      active: true,
      backtest: {
        period: '3M',
        results: {
          totalTrades: 245,
          winRate: 68.5,
          totalPnL: 2840.50,
          maxDrawdown: 12.3
        }
      }
    },
    {
      id: '2',
      name: 'Gold Trend Following',
      description: 'Momentum-based strategy for gold trading',
      type: 'code',
      conditions: [],
      riskManagement: {
        maxLotSize: 0.05,
        stopLoss: 50,
        takeProfit: 100,
        riskPercent: 1.5
      },
      symbols: ['XAUUSD'],
      active: false
    }
  ]);

  const handleCreateStrategy = () => {
    const newStrategy: Strategy = {
      id: Date.now().toString(),
      name: 'New Strategy',
      description: 'Strategy description',
      type: builderMode,
      conditions: [],
      riskManagement: {
        maxLotSize: 0.1,
        stopLoss: 20,
        takeProfit: 30,
        riskPercent: 2.0
      },
      symbols: ['EURUSD'],
      active: false
    };
    setStrategies([...strategies, newStrategy]);
    setSelectedStrategy(newStrategy);
    setActiveTab('builder');
  };

  const handleSaveStrategy = () => {
    if (!selectedStrategy) return;
    
    setStrategies(strategies.map(s => 
      s.id === selectedStrategy.id ? selectedStrategy : s
    ));
    
    toast({
      title: 'Strategy Saved',
      description: 'Your strategy has been saved successfully',
    });
  };

  const handleRunBacktest = async (strategyId: string) => {
    const strategy = strategies.find(s => s.id === strategyId);
    if (!strategy) return;

    toast({
      title: 'Backtesting Started',
      description: 'Running backtest simulation...',
    });

    // Mock backtest results
    setTimeout(() => {
      const results = {
        totalTrades: Math.floor(Math.random() * 500) + 100,
        winRate: Math.floor(Math.random() * 40) + 50,
        totalPnL: Math.floor(Math.random() * 5000) + 1000,
        maxDrawdown: Math.floor(Math.random() * 20) + 5
      };

      setStrategies(strategies.map(s => 
        s.id === strategyId 
          ? { ...s, backtest: { period: '3M', results } }
          : s
      ));

      toast({
        title: 'Backtest Complete',
        description: `Win Rate: ${results.winRate}% | P&L: $${results.totalPnL}`,
      });
    }, 3000);
  };

  const handleNaturalLanguageStrategy = () => {
    if (!naturalLanguageInput.trim()) return;

    // Mock AI processing
    const mockStrategy: Strategy = {
      id: Date.now().toString(),
      name: 'AI Generated Strategy',
      description: naturalLanguageInput,
      type: 'natural',
      conditions: [
        { type: 'ai_parsed', value: naturalLanguageInput, operator: 'matches' }
      ],
      riskManagement: {
        maxLotSize: 0.1,
        stopLoss: 25,
        takeProfit: 50,
        riskPercent: 2.0
      },
      symbols: ['EURUSD', 'GBPUSD'],
      active: false
    };

    setStrategies([...strategies, mockStrategy]);
    setNaturalLanguageInput('');
    
    toast({
      title: 'Strategy Generated',
      description: 'AI has created a strategy based on your description',
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Strategy Builder & Backtest</h2>
          <p className="text-muted-foreground">
            Create, test, and deploy trading strategies
          </p>
        </div>
        <Button onClick={handleCreateStrategy} className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Create Strategy
        </Button>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as any)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="list">Strategy List</TabsTrigger>
          <TabsTrigger value="builder">Strategy Builder</TabsTrigger>
          <TabsTrigger value="backtest">Backtest Results</TabsTrigger>
        </TabsList>

        {/* Strategy List */}
        <TabsContent value="list" className="space-y-4">
          <div className="grid gap-4">
            {strategies.map((strategy) => (
              <Card key={strategy.id} className="overflow-hidden">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        {strategy.name}
                        <Badge variant={strategy.type === 'visual' ? 'default' : 
                                     strategy.type === 'code' ? 'secondary' : 'outline'}>
                          {strategy.type}
                        </Badge>
                      </CardTitle>
                      <CardDescription>{strategy.description}</CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={strategy.active}
                        onCheckedChange={(checked) => {
                          setStrategies(strategies.map(s => 
                            s.id === strategy.id ? { ...s, active: checked } : s
                          ));
                        }}
                      />
                      <Button variant="outline" size="sm" onClick={() => {
                        setSelectedStrategy(strategy);
                        setActiveTab('builder');
                      }}>
                        <Edit2 className="h-4 w-4" />
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => handleRunBacktest(strategy.id)}>
                        <Play className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center p-3 rounded-lg bg-muted/50">
                      <div className="text-lg font-bold">{strategy.symbols.join(', ')}</div>
                      <div className="text-xs text-muted-foreground">Symbols</div>
                    </div>
                    <div className="text-center p-3 rounded-lg bg-muted/50">
                      <div className="text-lg font-bold">{strategy.riskManagement.riskPercent}%</div>
                      <div className="text-xs text-muted-foreground">Risk</div>
                    </div>
                    {strategy.backtest && (
                      <>
                        <div className="text-center p-3 rounded-lg bg-muted/50">
                          <div className="text-lg font-bold text-green-600">{strategy.backtest.results.winRate}%</div>
                          <div className="text-xs text-muted-foreground">Win Rate</div>
                        </div>
                        <div className="text-center p-3 rounded-lg bg-muted/50">
                          <div className="text-lg font-bold text-blue-600">${strategy.backtest.results.totalPnL}</div>
                          <div className="text-xs text-muted-foreground">P&L</div>
                        </div>
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Strategy Builder */}
        <TabsContent value="builder" className="space-y-4">
          {selectedStrategy ? (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Strategy Configuration</CardTitle>
                  <CardDescription>
                    Configure your trading strategy parameters
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="name">Strategy Name</Label>
                      <Input
                        id="name"
                        value={selectedStrategy.name}
                        onChange={(e) => setSelectedStrategy({
                          ...selectedStrategy,
                          name: e.target.value
                        })}
                      />
                    </div>
                    <div>
                      <Label htmlFor="symbols">Trading Symbols</Label>
                      <Input
                        id="symbols"
                        value={selectedStrategy.symbols.join(', ')}
                        onChange={(e) => setSelectedStrategy({
                          ...selectedStrategy,
                          symbols: e.target.value.split(',').map(s => s.trim())
                        })}
                        placeholder="EURUSD, GBPUSD, USDJPY"
                      />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      id="description"
                      value={selectedStrategy.description}
                      onChange={(e) => setSelectedStrategy({
                        ...selectedStrategy,
                        description: e.target.value
                      })}
                    />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Risk Management</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <Label htmlFor="maxLot">Max Lot Size</Label>
                      <Input
                        id="maxLot"
                        type="number"
                        step="0.01"
                        value={selectedStrategy.riskManagement.maxLotSize}
                        onChange={(e) => setSelectedStrategy({
                          ...selectedStrategy,
                          riskManagement: {
                            ...selectedStrategy.riskManagement,
                            maxLotSize: parseFloat(e.target.value)
                          }
                        })}
                      />
                    </div>
                    <div>
                      <Label htmlFor="stopLoss">Stop Loss (pips)</Label>
                      <Input
                        id="stopLoss"
                        type="number"
                        value={selectedStrategy.riskManagement.stopLoss}
                        onChange={(e) => setSelectedStrategy({
                          ...selectedStrategy,
                          riskManagement: {
                            ...selectedStrategy.riskManagement,
                            stopLoss: parseInt(e.target.value)
                          }
                        })}
                      />
                    </div>
                    <div>
                      <Label htmlFor="takeProfit">Take Profit (pips)</Label>
                      <Input
                        id="takeProfit"
                        type="number"
                        value={selectedStrategy.riskManagement.takeProfit}
                        onChange={(e) => setSelectedStrategy({
                          ...selectedStrategy,
                          riskManagement: {
                            ...selectedStrategy.riskManagement,
                            takeProfit: parseInt(e.target.value)
                          }
                        })}
                      />
                    </div>
                    <div>
                      <Label htmlFor="riskPercent">Risk Percentage</Label>
                      <Input
                        id="riskPercent"
                        type="number"
                        step="0.1"
                        value={selectedStrategy.riskManagement.riskPercent}
                        onChange={(e) => setSelectedStrategy({
                          ...selectedStrategy,
                          riskManagement: {
                            ...selectedStrategy.riskManagement,
                            riskPercent: parseFloat(e.target.value)
                          }
                        })}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setActiveTab('list')}>
                  Cancel
                </Button>
                <Button onClick={handleSaveStrategy}>
                  <Save className="h-4 w-4 mr-2" />
                  Save Strategy
                </Button>
              </div>
            </div>
          ) : (
            <Card>
              <CardContent className="text-center py-12">
                <Target className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                <h3 className="text-lg font-medium mb-2">No Strategy Selected</h3>
                <p className="text-muted-foreground mb-4">
                  Select a strategy to edit or create a new one
                </p>
                <Button onClick={handleCreateStrategy}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create New Strategy
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Natural Language Strategy Creator */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-5 w-5" />
                Natural Language Strategy Creator
              </CardTitle>
              <CardDescription>
                Describe your trading strategy in plain English and let AI create it for you
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Textarea
                  placeholder="e.g., 'Buy EURUSD when RSI is below 30 and MACD crosses above zero, with 2% risk per trade'"
                  value={naturalLanguageInput}
                  onChange={(e) => setNaturalLanguageInput(e.target.value)}
                  className="min-h-[100px]"
                />
                <Button onClick={handleNaturalLanguageStrategy} disabled={!naturalLanguageInput.trim()}>
                  <Brain className="h-4 w-4 mr-2" />
                  Generate Strategy
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Backtest Results */}
        <TabsContent value="backtest" className="space-y-4">
          <div className="grid gap-4">
            {strategies.filter(s => s.backtest).map((strategy) => (
              <Card key={strategy.id}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5" />
                    {strategy.name} - Backtest Results
                  </CardTitle>
                  <CardDescription>
                    Period: {strategy.backtest?.period} | Last updated: Just now
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {strategy.backtest && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="text-center p-4 rounded-lg bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20">
                        <div className="text-2xl font-bold text-blue-600">{strategy.backtest.results.totalTrades}</div>
                        <div className="text-sm text-blue-600">Total Trades</div>
                      </div>
                      <div className="text-center p-4 rounded-lg bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20">
                        <div className="text-2xl font-bold text-green-600">{strategy.backtest.results.winRate}%</div>
                        <div className="text-sm text-green-600">Win Rate</div>
                      </div>
                      <div className="text-center p-4 rounded-lg bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20">
                        <div className="text-2xl font-bold text-purple-600">${strategy.backtest.results.totalPnL}</div>
                        <div className="text-sm text-purple-600">Total P&L</div>
                      </div>
                      <div className="text-center p-4 rounded-lg bg-gradient-to-br from-red-50 to-red-100 dark:from-red-900/20 dark:to-red-800/20">
                        <div className="text-2xl font-bold text-red-600">{strategy.backtest.results.maxDrawdown}%</div>
                        <div className="text-sm text-red-600">Max Drawdown</div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}