import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import { apiRequest } from '@/lib/queryClient';
import { 
  TrendingUp, 
  TrendingDown, 
  Edit2, 
  X, 
  DollarSign,
  Clock,
  Target,
  Shield,
  AlertTriangle,
  CheckCircle,
  Activity
} from 'lucide-react';

interface Trade {
  id: string;
  ticket: string;
  symbol: string;
  action: 'BUY' | 'SELL';
  volume: number;
  openPrice: number;
  currentPrice: number;
  stopLoss: number;
  takeProfit: number;
  profit: number;
  openTime: string;
  status: 'open' | 'closed' | 'pending';
  comment?: string;
}

export function ActiveTradesPanel() {
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [editingTrade, setEditingTrade] = useState<Trade | null>(null);
  const [showCloseDialog, setShowCloseDialog] = useState(false);
  const { toast } = useToast();

  // Mock trades data - in real app, this would come from MT5 API
  const [trades, setTrades] = useState<Trade[]>([
    {
      id: '1',
      ticket: '123456789',
      symbol: 'EURUSD',
      action: 'BUY',
      volume: 0.1,
      openPrice: 1.0850,
      currentPrice: 1.0875,
      stopLoss: 1.0800,
      takeProfit: 1.0950,
      profit: 25.0,
      openTime: new Date(Date.now() - 3600000).toISOString(),
      status: 'open',
      comment: 'Premium Signals'
    },
    {
      id: '2',
      ticket: '123456790',
      symbol: 'GBPUSD',
      action: 'SELL',
      volume: 0.05,
      openPrice: 1.2650,
      currentPrice: 1.2625,
      stopLoss: 1.2700,
      takeProfit: 1.2600,
      profit: 12.5,
      openTime: new Date(Date.now() - 7200000).toISOString(),
      status: 'open',
      comment: 'Gold Signals Pro'
    },
    {
      id: '3',
      ticket: '123456791',
      symbol: 'XAUUSD',
      action: 'BUY',
      volume: 0.02,
      openPrice: 2045.50,
      currentPrice: 2040.25,
      stopLoss: 2030.00,
      takeProfit: 2060.00,
      profit: -10.5,
      openTime: new Date(Date.now() - 1800000).toISOString(),
      status: 'open',
      comment: 'Manual Trade'
    }
  ]);

  const handleModifyTrade = async (trade: Trade) => {
    if (!editingTrade) return;

    try {
      // Mock API call - in real app, this would call MT5 API
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setTrades(trades.map(t => 
        t.id === editingTrade.id ? editingTrade : t
      ));
      
      setEditingTrade(null);
      
      toast({
        title: 'Trade Modified',
        description: `${trade.symbol} trade updated successfully`,
      });
      
    } catch (error) {
      toast({
        title: 'Modification Failed',
        description: 'Failed to modify trade',
        variant: 'destructive',
      });
    }
  };

  const handleCloseTrade = async (trade: Trade, closeType: 'full' | 'partial', volume?: number) => {
    try {
      // Mock API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      if (closeType === 'full') {
        setTrades(trades.filter(t => t.id !== trade.id));
      } else if (closeType === 'partial' && volume) {
        setTrades(trades.map(t => 
          t.id === trade.id 
            ? { ...t, volume: t.volume - volume }
            : t
        ));
      }
      
      setShowCloseDialog(false);
      setSelectedTrade(null);
      
      toast({
        title: 'Trade Closed',
        description: `${trade.symbol} ${closeType} close executed`,
      });
      
    } catch (error) {
      toast({
        title: 'Close Failed',
        description: 'Failed to close trade',
        variant: 'destructive',
      });
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const getProfitColor = (profit: number) => {
    return profit >= 0 ? 'text-green-600' : 'text-red-600';
  };

  const getProfitIcon = (profit: number) => {
    return profit >= 0 ? <TrendingUp className="h-4 w-4 text-green-600" /> : <TrendingDown className="h-4 w-4 text-red-600" />;
  };

  const calculatePips = (trade: Trade) => {
    const pipValue = trade.symbol.includes('JPY') ? 0.01 : 0.0001;
    const pips = (trade.currentPrice - trade.openPrice) * (trade.action === 'BUY' ? 1 : -1) / pipValue;
    return Math.round(pips * 10) / 10;
  };

  const openTrades = trades.filter(t => t.status === 'open');
  const totalProfit = openTrades.reduce((sum, trade) => sum + trade.profit, 0);
  const totalVolume = openTrades.reduce((sum, trade) => sum + trade.volume, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Active Trades & Positions</h2>
          <p className="text-muted-foreground">
            Monitor and manage your open positions
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-center">
            <div className={`text-2xl font-bold ${getProfitColor(totalProfit)}`}>
              {formatCurrency(totalProfit)}
            </div>
            <div className="text-sm text-muted-foreground">Total P&L</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold">{openTrades.length}</div>
            <div className="text-sm text-muted-foreground">Open Trades</div>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-blue-600" />
              <div>
                <div className="text-2xl font-bold">{openTrades.length}</div>
                <div className="text-sm text-muted-foreground">Open Positions</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-green-600" />
              <div>
                <div className={`text-2xl font-bold ${getProfitColor(totalProfit)}`}>
                  {formatCurrency(totalProfit)}
                </div>
                <div className="text-sm text-muted-foreground">Floating P&L</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Target className="h-4 w-4 text-purple-600" />
              <div>
                <div className="text-2xl font-bold">{totalVolume.toFixed(2)}</div>
                <div className="text-sm text-muted-foreground">Total Volume</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-orange-600" />
              <div>
                <div className="text-2xl font-bold">2.1%</div>
                <div className="text-sm text-muted-foreground">Risk Exposure</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Trades List */}
      <Card>
        <CardHeader>
          <CardTitle>Open Positions</CardTitle>
          <CardDescription>
            Real-time view of your active trades with edit capabilities
          </CardDescription>
        </CardHeader>
        <CardContent>
          {openTrades.length === 0 ? (
            <div className="text-center py-12">
              <Activity className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <h3 className="text-lg font-medium mb-2">No Active Trades</h3>
              <p className="text-muted-foreground">
                Your open positions will appear here
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {openTrades.map((trade) => (
                <div key={trade.id} className="p-4 border rounded-lg hover:bg-muted/50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        {getProfitIcon(trade.profit)}
                        <div>
                          <div className="font-medium text-lg">
                            {trade.symbol}
                            <Badge variant={trade.action === 'BUY' ? 'default' : 'destructive'} className="ml-2">
                              {trade.action}
                            </Badge>
                          </div>
                          <div className="text-sm text-muted-foreground">
                            Ticket: {trade.ticket} • Volume: {trade.volume}
                          </div>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-4 gap-4 text-sm">
                        <div>
                          <div className="text-muted-foreground">Open Price</div>
                          <div className="font-medium">{trade.openPrice.toFixed(5)}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Current Price</div>
                          <div className="font-medium">{trade.currentPrice.toFixed(5)}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Pips</div>
                          <div className={`font-medium ${getProfitColor(trade.profit)}`}>
                            {calculatePips(trade) > 0 ? '+' : ''}{calculatePips(trade)}
                          </div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">P&L</div>
                          <div className={`font-medium ${getProfitColor(trade.profit)}`}>
                            {formatCurrency(trade.profit)}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button variant="outline" size="sm" onClick={() => setEditingTrade(trade)}>
                            <Edit2 className="h-4 w-4" />
                          </Button>
                        </DialogTrigger>
                        <DialogContent>
                          <DialogHeader>
                            <DialogTitle>Modify Trade</DialogTitle>
                            <DialogDescription>
                              Edit stop loss and take profit levels
                            </DialogDescription>
                          </DialogHeader>
                          {editingTrade && (
                            <div className="space-y-4">
                              <div className="grid grid-cols-2 gap-4">
                                <div>
                                  <Label htmlFor="stopLoss">Stop Loss</Label>
                                  <Input
                                    id="stopLoss"
                                    type="number"
                                    step="0.00001"
                                    value={editingTrade.stopLoss}
                                    onChange={(e) => setEditingTrade({
                                      ...editingTrade,
                                      stopLoss: parseFloat(e.target.value)
                                    })}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="takeProfit">Take Profit</Label>
                                  <Input
                                    id="takeProfit"
                                    type="number"
                                    step="0.00001"
                                    value={editingTrade.takeProfit}
                                    onChange={(e) => setEditingTrade({
                                      ...editingTrade,
                                      takeProfit: parseFloat(e.target.value)
                                    })}
                                  />
                                </div>
                              </div>
                              <div className="flex justify-end gap-2">
                                <Button variant="outline" onClick={() => setEditingTrade(null)}>
                                  Cancel
                                </Button>
                                <Button onClick={() => handleModifyTrade(trade)}>
                                  Save Changes
                                </Button>
                              </div>
                            </div>
                          )}
                        </DialogContent>
                      </Dialog>

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSelectedTrade(trade);
                          setShowCloseDialog(true);
                        }}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  <div className="mt-3 pt-3 border-t flex items-center justify-between text-sm">
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3 text-muted-foreground" />
                        <span className="text-muted-foreground">Opened: {formatTime(trade.openTime)}</span>
                      </div>
                      {trade.comment && (
                        <div className="text-muted-foreground">
                          Signal: {trade.comment}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-muted-foreground">
                      <span>SL: {trade.stopLoss.toFixed(5)}</span>
                      <span>TP: {trade.takeProfit.toFixed(5)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Close Trade Dialog */}
      <Dialog open={showCloseDialog} onOpenChange={setShowCloseDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Close Trade</DialogTitle>
            <DialogDescription>
              Choose how you want to close this position
            </DialogDescription>
          </DialogHeader>
          {selectedTrade && (
            <div className="space-y-4">
              <div className="p-4 border rounded-lg bg-muted/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">{selectedTrade.symbol} {selectedTrade.action}</span>
                  <span className={`font-medium ${getProfitColor(selectedTrade.profit)}`}>
                    {formatCurrency(selectedTrade.profit)}
                  </span>
                </div>
                <div className="text-sm text-muted-foreground">
                  Volume: {selectedTrade.volume} • Current Price: {selectedTrade.currentPrice.toFixed(5)}
                </div>
              </div>
              
              <div className="flex gap-2">
                <Button
                  onClick={() => handleCloseTrade(selectedTrade, 'full')}
                  className="flex-1"
                >
                  Close Full Position
                </Button>
                <Button
                  onClick={() => handleCloseTrade(selectedTrade, 'partial', selectedTrade.volume / 2)}
                  variant="outline"
                  className="flex-1"
                >
                  Close 50%
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}