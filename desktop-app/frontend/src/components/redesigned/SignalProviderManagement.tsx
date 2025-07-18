import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/hooks/use-toast';
import { apiRequest } from '@/lib/queryClient';
import { 
  Plus, 
  Edit2, 
  Trash2, 
  MessageSquare, 
  TrendingUp, 
  TrendingDown,
  Activity,
  Settings,
  Users,
  BarChart3,
  Clock,
  CheckCircle,
  XCircle
} from 'lucide-react';

export function SignalProviderManagement() {
  const [activeProvider, setActiveProvider] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newProvider, setNewProvider] = useState({
    name: '',
    channel: '',
    description: '',
    riskPercent: 1.0,
    maxLotSize: 0.1,
    symbols: [] as string[],
    active: true
  });
  const { toast } = useToast();

  // Mock provider data - in real app, this would come from API
  const [providers, setProviders] = useState([
    {
      id: '1',
      name: 'Premium Forex Signals',
      channel: '@premium_signals',
      description: 'Professional forex trading signals with high accuracy',
      active: true,
      riskPercent: 2.0,
      maxLotSize: 0.5,
      symbols: ['EURUSD', 'GBPUSD', 'USDJPY'],
      stats: {
        totalSignals: 1250,
        winRate: 72.5,
        avgPnL: 245.8,
        lastSignal: '2 minutes ago',
        status: 'active'
      }
    },
    {
      id: '2',
      name: 'Gold Trading Pro',
      channel: '@gold_signals',
      description: 'Specialized gold and precious metals signals',
      active: true,
      riskPercent: 1.5,
      maxLotSize: 0.3,
      symbols: ['XAUUSD', 'XAGUSD'],
      stats: {
        totalSignals: 856,
        winRate: 68.9,
        avgPnL: 189.2,
        lastSignal: '15 minutes ago',
        status: 'active'
      }
    },
    {
      id: '3',
      name: 'Crypto Signals Elite',
      channel: '@crypto_elite',
      description: 'High-frequency crypto trading signals',
      active: false,
      riskPercent: 3.0,
      maxLotSize: 0.2,
      symbols: ['BTCUSD', 'ETHUSD'],
      stats: {
        totalSignals: 2340,
        winRate: 58.3,
        avgPnL: 156.7,
        lastSignal: '2 hours ago',
        status: 'inactive'
      }
    }
  ]);

  const handleAddProvider = async () => {
    if (!newProvider.name || !newProvider.channel) {
      toast({
        title: 'Validation Error',
        description: 'Please fill in all required fields',
        variant: 'destructive',
      });
      return;
    }

    const provider = {
      id: Date.now().toString(),
      ...newProvider,
      stats: {
        totalSignals: 0,
        winRate: 0,
        avgPnL: 0,
        lastSignal: 'Never',
        status: 'inactive'
      }
    };

    setProviders([...providers, provider]);
    setNewProvider({
      name: '',
      channel: '',
      description: '',
      riskPercent: 1.0,
      maxLotSize: 0.1,
      symbols: [],
      active: true
    });
    setShowAddForm(false);

    toast({
      title: 'Provider Added',
      description: `${provider.name} has been added successfully`,
    });
  };

  const handleToggleProvider = (id: string) => {
    setProviders(providers.map(p => 
      p.id === id ? { ...p, active: !p.active } : p
    ));
  };

  const handleDeleteProvider = (id: string) => {
    setProviders(providers.filter(p => p.id !== id));
    toast({
      title: 'Provider Deleted',
      description: 'Provider has been removed successfully',
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-600';
      case 'inactive': return 'text-gray-600';
      default: return 'text-yellow-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active': return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'inactive': return <XCircle className="h-4 w-4 text-gray-600" />;
      default: return <Activity className="h-4 w-4 text-yellow-600" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Signal Provider Management</h2>
          <p className="text-muted-foreground">
            Manage Telegram channels and signal providers
          </p>
        </div>
        <Button onClick={() => setShowAddForm(true)} className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Add Provider
        </Button>
      </div>

      {/* Add Provider Form */}
      {showAddForm && (
        <Card>
          <CardHeader>
            <CardTitle>Add New Provider</CardTitle>
            <CardDescription>
              Configure a new signal provider or Telegram channel
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="name">Provider Name</Label>
                <Input
                  id="name"
                  value={newProvider.name}
                  onChange={(e) => setNewProvider({...newProvider, name: e.target.value})}
                  placeholder="e.g., Premium Forex Signals"
                />
              </div>
              <div>
                <Label htmlFor="channel">Telegram Channel</Label>
                <Input
                  id="channel"
                  value={newProvider.channel}
                  onChange={(e) => setNewProvider({...newProvider, channel: e.target.value})}
                  placeholder="e.g., @premium_signals"
                />
              </div>
              <div className="md:col-span-2">
                <Label htmlFor="description">Description</Label>
                <Input
                  id="description"
                  value={newProvider.description}
                  onChange={(e) => setNewProvider({...newProvider, description: e.target.value})}
                  placeholder="Brief description of the provider"
                />
              </div>
              <div>
                <Label htmlFor="risk">Risk Percentage</Label>
                <Input
                  id="risk"
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="10"
                  value={newProvider.riskPercent}
                  onChange={(e) => setNewProvider({...newProvider, riskPercent: parseFloat(e.target.value)})}
                />
              </div>
              <div>
                <Label htmlFor="maxLot">Max Lot Size</Label>
                <Input
                  id="maxLot"
                  type="number"
                  step="0.01"
                  min="0.01"
                  max="10"
                  value={newProvider.maxLotSize}
                  onChange={(e) => setNewProvider({...newProvider, maxLotSize: parseFloat(e.target.value)})}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="outline" onClick={() => setShowAddForm(false)}>
                Cancel
              </Button>
              <Button onClick={handleAddProvider}>
                Add Provider
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Provider List */}
      <div className="grid gap-4">
        {providers.map((provider) => (
          <Card key={provider.id} className="overflow-hidden">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary/10">
                    <MessageSquare className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">{provider.name}</CardTitle>
                    <CardDescription>{provider.channel}</CardDescription>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    checked={provider.active}
                    onCheckedChange={() => handleToggleProvider(provider.id)}
                  />
                  <Button variant="outline" size="sm">
                    <Edit2 className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => handleDeleteProvider(provider.id)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">{provider.description}</p>
                
                {/* Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center p-3 rounded-lg bg-muted/50">
                    <div className="text-2xl font-bold">{provider.stats.totalSignals}</div>
                    <div className="text-xs text-muted-foreground">Total Signals</div>
                  </div>
                  <div className="text-center p-3 rounded-lg bg-muted/50">
                    <div className="text-2xl font-bold text-green-600">{provider.stats.winRate}%</div>
                    <div className="text-xs text-muted-foreground">Win Rate</div>
                  </div>
                  <div className="text-center p-3 rounded-lg bg-muted/50">
                    <div className="text-2xl font-bold text-blue-600">${provider.stats.avgPnL}</div>
                    <div className="text-xs text-muted-foreground">Avg P&L</div>
                  </div>
                  <div className="text-center p-3 rounded-lg bg-muted/50">
                    <div className="flex items-center justify-center gap-1 text-sm">
                      {getStatusIcon(provider.stats.status)}
                      <span className={getStatusColor(provider.stats.status)}>
                        {provider.stats.status}
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground">Status</div>
                  </div>
                </div>

                {/* Configuration */}
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-4">
                    <div>
                      <span className="text-muted-foreground">Risk:</span>
                      <span className="font-medium ml-1">{provider.riskPercent}%</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Max Lot:</span>
                      <span className="font-medium ml-1">{provider.maxLotSize}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Symbols:</span>
                      <span className="font-medium ml-1">{provider.symbols.join(', ')}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    <span className="text-xs">Last: {provider.stats.lastSignal}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {providers.length === 0 && (
        <Card>
          <CardContent className="text-center py-12">
            <Users className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-medium mb-2">No Providers Configured</h3>
            <p className="text-muted-foreground mb-4">
              Add your first signal provider to start receiving trading signals
            </p>
            <Button onClick={() => setShowAddForm(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Provider
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}