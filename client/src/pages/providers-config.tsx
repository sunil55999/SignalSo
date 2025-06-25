import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import MainLayout from "@/layouts/MainLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { 
  Settings, 
  Plus, 
  Edit, 
  Trash2, 
  Eye, 
  EyeOff,
  HelpCircle,
  MessageSquare,
  Target,
  Shield,
  Zap,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  BarChart3,
  Filter,
  Activity
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

// Fix Button dashed variant
declare module "@/components/ui/button" {
  interface ButtonProps {
    variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link" | "dashed";
  }
}

interface Provider {
  id: string;
  name: string;
  type: "telegram";
  channelId: string;
  isActive: boolean;
  totalSignals: number;
  successRate: number;
  avgRiskReward: number;
  status: "connected" | "disconnected" | "error";
}

interface StrategyBlock {
  id: string;
  type: string;
  name: string;
  icon: React.ElementType;
  color: string;
  enabled: boolean;
  config: Record<string, any>;
}

interface SignalStrategy {
  id: string;
  name: string;
  description: string;
  blocks: StrategyBlock[];
  isActive: boolean;
  priority: number;
}

export default function ProvidersConfigPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
  const [showProviderModal, setShowProviderModal] = useState(false);
  const [showStrategyModal, setShowStrategyModal] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState<SignalStrategy | null>(null);
  const [activeTab, setActiveTab] = useState("overview");

  // Mock data - in real app this would come from API
  const [providers, setProviders] = useState<Provider[]>([
    {
      id: "1544",
      name: "Telegram Signals Copier",
      type: "telegram",
      channelId: "@signals_channel",
      isActive: true,
      totalSignals: 1544,
      successRate: 78.5,
      avgRiskReward: 1.85,
      status: "connected"
    }
  ]);

  const [strategies, setStrategies] = useState<SignalStrategy[]>([
    {
      id: "1",
      name: "Order Resume Strategy",
      description: "Manage order execution and resume logic",
      blocks: [
        {
          id: "actions",
          type: "action",
          name: "Actions",
          icon: Zap,
          color: "blue",
          enabled: true,
          config: {}
        },
        {
          id: "break-even",
          type: "breakEven",
          name: "Break Even",
          icon: Target,
          color: "green",
          enabled: true,
          config: {}
        },
        {
          id: "manipulate-signal",
          type: "manipulateSignal",
          name: "Manipulate Signal",
          icon: Activity,
          color: "purple",
          enabled: true,
          config: {}
        },
        {
          id: "pending-orders",
          type: "pendingOrders",
          name: "Pending Orders",
          icon: Clock,
          color: "orange",
          enabled: true,
          config: {}
        },
        {
          id: "filter-signals",
          type: "filterSignals",
          name: "Filter Signals",
          icon: Filter,
          color: "red",
          enabled: true,
          config: {}
        },
        {
          id: "money-mgmt",
          type: "moneyManagement",
          name: "Money Management",
          icon: BarChart3,
          color: "indigo",
          enabled: true,
          config: {}
        }
      ],
      isActive: true,
      priority: 1
    }
  ]);

  const strategyBlockTypes = [
    { type: "action", name: "Actions", icon: Zap, color: "blue" },
    { type: "breakEven", name: "Break Even", icon: Target, color: "green" },
    { type: "manipulateSignal", name: "Manipulate Signal", icon: Activity, color: "purple" },
    { type: "pendingOrders", name: "Pending Orders", icon: Clock, color: "orange" },
    { type: "filterSignals", name: "Filter Signals", icon: Filter, color: "red" },
    { type: "moneyManagement", name: "Money Management", icon: BarChart3, color: "indigo" },
    { type: "trailingStop", name: "Trailing SL", icon: TrendingUp, color: "emerald" },
    { type: "riskManagement", name: "Risk Management", icon: Shield, color: "amber" }
  ];

  const openProviderConfig = (provider: Provider) => {
    setSelectedProvider(provider);
    setShowProviderModal(true);
  };

  const openStrategyConfig = (strategy: SignalStrategy) => {
    setSelectedStrategy(strategy);
    setShowStrategyModal(true);
  };

  const addNewProvider = () => {
    setSelectedProvider(null);
    setShowProviderModal(true);
  };

  const addNewStrategy = () => {
    setSelectedStrategy(null);
    setShowStrategyModal(true);
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Configure Providers
            </h1>
            <p className="text-slate-600 dark:text-slate-400 mt-1">
              Manage Telegram channels and signal strategies
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <Button variant="outline" size="sm">
              <HelpCircle className="w-4 h-4 mr-2" />
              Help me pick the correct template
            </Button>
            <Button size="sm" onClick={addNewProvider}>
              <Plus className="w-4 h-4 mr-2" />
              Add Provider
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-6">
          {/* Left Sidebar - Providers List */}
          <div className="col-span-4">
            <Card className="h-fit">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">Channels ({providers.length})</CardTitle>
                  <Button variant="ghost" size="sm">
                    <Settings className="w-4 h-4" />
                  </Button>
                </div>
                <p className="text-sm text-muted-foreground">Configured channels</p>
              </CardHeader>
              <CardContent className="space-y-3">
                {providers.map((provider) => (
                  <div
                    key={provider.id}
                    className={cn(
                      "p-4 rounded-lg border cursor-pointer transition-all",
                      selectedProvider?.id === provider.id 
                        ? "border-blue-500 bg-blue-50 dark:bg-blue-950/20" 
                        : "hover:border-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                    )}
                    onClick={() => openProviderConfig(provider)}
                  >
                    <div className="flex items-start space-x-3">
                      <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/20 rounded-lg flex items-center justify-center">
                        <MessageSquare className="w-5 h-5 text-blue-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <h3 className="font-medium text-sm truncate">{provider.name}</h3>
                          <Badge variant={provider.isActive ? "default" : "secondary"} className="text-xs">
                            {provider.isActive ? "Active" : "Inactive"}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          TELEGRAM CHANNEL
                        </p>
                        <div className="flex items-center space-x-4 mt-2 text-xs text-muted-foreground">
                          <span>Signals: {provider.totalSignals}</span>
                          <span>Success: {provider.successRate}%</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                
                <Button 
                  variant="dashed" 
                  className="w-full py-8 border-dashed border-2 text-muted-foreground"
                  onClick={addNewProvider}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add new channel
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Main Content */}
          <div className="col-span-8">
            {selectedProvider ? (
              <ProviderConfigPanel 
                provider={selectedProvider} 
                strategies={strategies}
                onStrategyEdit={openStrategyConfig}
                onAddStrategy={addNewStrategy}
              />
            ) : (
              <Card className="h-96 flex items-center justify-center">
                <div className="text-center">
                  <MessageSquare className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-muted-foreground">
                    Select a provider to configure
                  </h3>
                  <p className="text-sm text-muted-foreground mt-2">
                    Choose a Telegram channel from the left panel to manage its settings
                  </p>
                </div>
              </Card>
            )}
          </div>
        </div>

        {/* Strategy Builder Modal */}
        <StrategyBuilderModal 
          isOpen={showStrategyModal}
          onClose={() => setShowStrategyModal(false)}
          strategy={selectedStrategy}
          blocks={strategyBlockTypes}
        />
      </div>
    </MainLayout>
  );
}

interface ProviderConfigPanelProps {
  provider: Provider;
  strategies: SignalStrategy[];
  onStrategyEdit: (strategy: SignalStrategy) => void;
  onAddStrategy: () => void;
}

function ProviderConfigPanel({ provider, strategies, onStrategyEdit, onAddStrategy }: ProviderConfigPanelProps) {
  const [activeTab, setActiveTab] = useState("strategy");

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-xl">{provider.name}</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Channel ID: {provider.channelId}
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Badge variant="outline" className="text-xs">
              <CheckCircle className="w-3 h-3 mr-1" />
              Connected
            </Badge>
            <Button variant="outline" size="sm">
              <Settings className="w-4 h-4 mr-2" />
              Settings
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="strategy">Signal Strategy</TabsTrigger>
            <TabsTrigger value="resume">Order Resume</TabsTrigger>
            <TabsTrigger value="template">Message Template</TabsTrigger>
            <TabsTrigger value="tp2">TP2 Strategy</TabsTrigger>
          </TabsList>

          <TabsContent value="strategy" className="space-y-6 mt-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">4. Signal Strategy</h3>
                <HelpCircle className="w-4 h-4 text-muted-foreground" />
              </div>
              
              <div className="flex items-center space-x-3">
                <Button variant="outline" size="sm">
                  Strategy Templates
                </Button>
                <Button size="sm" onClick={onAddStrategy}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Custom Template
                </Button>
                <Button variant="outline" size="sm">
                  Clear Strategy
                </Button>
              </div>

              <div className="relative">
                <Input
                  placeholder="Search for a strategy..."
                  className="pl-8"
                />
                <HelpCircle className="w-4 h-4 absolute left-2.5 top-3 text-muted-foreground" />
              </div>

              {/* Strategy Blocks */}
              <div className="grid grid-cols-6 gap-3">
                {strategies[0]?.blocks.map((block) => {
                  const Icon = block.icon;
                  return (
                    <div
                      key={block.id}
                      className={cn(
                        "p-3 rounded-lg border-2 cursor-pointer transition-all text-center",
                        block.enabled 
                          ? `border-${block.color}-200 bg-${block.color}-50 dark:bg-${block.color}-950/20` 
                          : "border-gray-200 bg-gray-50 dark:bg-gray-800"
                      )}
                      onClick={() => onStrategyEdit(strategies[0])}
                    >
                      <Icon className={cn(
                        "w-6 h-6 mx-auto mb-2",
                        block.enabled ? `text-${block.color}-600` : "text-gray-400"
                      )} />
                      <p className="text-xs font-medium">{block.name}</p>
                    </div>
                  );
                })}
              </div>

              {/* Limit Configuration */}
              <div className="space-y-4 pt-4 border-t">
                <h4 className="font-medium">Limit open trades</h4>
                
                <div className="space-y-3">
                  <div className="flex items-center space-x-3">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Max. open trades:</span>
                        <div className="flex items-center space-x-2">
                          <span className="text-sm text-muted-foreground">(for this provider only)</span>
                          <HelpCircle className="w-4 h-4 text-muted-foreground" />
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-3">
                    <div className="w-3 h-3 rounded-full border-2 border-gray-300"></div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm">Max. open trades:</span>
                        <div className="flex items-center space-x-2">
                          <span className="text-sm text-muted-foreground">(across all providers)</span>
                          <HelpCircle className="w-4 h-4 text-muted-foreground" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-3 pt-4">
                  <h4 className="font-medium">Limit open trades per pair</h4>
                  
                  <div className="space-y-3">
                    <div className="flex items-center space-x-3">
                      <div className="w-3 h-3 rounded-full border-2 border-gray-300"></div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Max. open trades per pair:</span>
                          <div className="flex items-center space-x-2">
                            <span className="text-sm text-muted-foreground">(for this provider only)</span>
                            <HelpCircle className="w-4 h-4 text-muted-foreground" />
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-3">
                      <div className="w-3 h-3 rounded-full border-2 border-gray-300"></div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Max. open trades per pair</span>
                          <div className="flex items-center space-x-2">
                            <span className="text-sm text-muted-foreground">(across all providers)</span>
                            <HelpCircle className="w-4 h-4 text-muted-foreground" />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-3 pt-4">
                  <h4 className="font-medium">Conditions to execute signals</h4>
                  
                  <div className="space-y-3">
                    <div className="flex items-center space-x-3">
                      <div className="w-3 h-3 rounded-full border-2 border-gray-300"></div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Only enter signals if the text</span>
                          <div className="flex items-center space-x-2">
                            <Input placeholder="keywords" className="w-32 h-8 text-sm" />
                            <span className="text-sm">is detected in the message</span>
                            <HelpCircle className="w-4 h-4 text-muted-foreground" />
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-3">
                      <div className="w-3 h-3 rounded-full border-2 border-gray-300"></div>
                      <div className="flex-1">
                        <span className="text-sm">Only enter signals for the following symbols</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="resume" className="space-y-4 mt-6">
            <OrderResumeConfig />
          </TabsContent>

          <TabsContent value="template" className="space-y-4 mt-6">
            <MessageTemplateConfig />
          </TabsContent>

          <TabsContent value="tp2" className="space-y-4 mt-6">
            <TP2StrategyConfig />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

function OrderResumeConfig() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">3.1. Order Resume</h3>
        <Button size="sm">
          <Plus className="w-4 h-4 mr-2" />
          Add a new Take Profit level
        </Button>
      </div>
      
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          ONE order rising 100% will be inserted.<br/>
          When TP1 hits, 50% of the initial volume will be closed.<br/>
          When TP2 hits, 50% of the initial volume will be closed.
        </p>
        
        <p className="text-sm text-muted-foreground">
          For signals with less than 2 TP's, the leftover will still be the same as above, but will close fully once the final TP in the signal is reached.
        </p>
      </div>
    </div>
  );
}

function MessageTemplateConfig() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">1. Message Template</h3>
        <HelpCircle className="w-4 h-4 text-muted-foreground" />
      </div>
      
      <div className="space-y-4">
        <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
          Help me pick the correct template
        </Button>
        
        <div className="flex items-center space-x-3">
          <Select defaultValue="automatic">
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="automatic">Automatic</SelectItem>
              <SelectItem value="manual">Manual</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm">
            Test Message
          </Button>
          <Button variant="outline" size="sm">
            Update Templates
          </Button>
        </div>
      </div>
    </div>
  );
}

function TP2StrategyConfig() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">TP2 Strategy</h3>
        <HelpCircle className="w-4 h-4 text-muted-foreground" />
      </div>
      
      <div className="space-y-4">
        <div className="flex items-center space-x-2">
          <input type="checkbox" className="rounded" />
          <span className="text-sm">Use TP2 strategy for better risk management, if the signal only has 2 TP levels</span>
        </div>
        
        <div className="space-y-3">
          <h4 className="font-medium">When TP2 Hits</h4>
          
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <input type="radio" name="tp2-action" className="rounded-full" />
              <span className="text-sm">When TP2 hits, set SL to ENTRYPOINT + pips</span>
            </div>
            
            <div className="flex items-center space-x-2">
              <input type="radio" name="tp2-action" className="rounded-full" defaultChecked />
              <span className="text-sm">When TP2 hits, set SL to TP1 + pips</span>
            </div>
            
            <div className="flex items-center space-x-2">
              <input type="checkbox" className="rounded" />
              <span className="text-sm">When TP2 hits, multiply the amount of pips in SL by</span>
            </div>
          </div>
        </div>
        
        <div className="space-y-3">
          <h4 className="font-medium">TP2 Manipulation</h4>
          
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <input type="checkbox" className="rounded" />
              <span className="text-sm">Change TP2 to pips</span>
            </div>
            
            <div className="flex items-center space-x-2">
              <input type="checkbox" className="rounded" />
              <span className="text-sm">Change TP2 to 1: Risk-Reward ratio</span>
            </div>
            
            <div className="flex items-center space-x-2">
              <input type="checkbox" className="rounded" />
              <span className="text-sm">Only apply the above changes to TP2 if the signal doesn't have TP2</span>
            </div>
            
            <div className="flex items-center space-x-2">
              <input type="checkbox" className="rounded" />
              <span className="text-sm">Copy original value to TP2</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

interface StrategyBuilderModalProps {
  isOpen: boolean;
  onClose: () => void;
  strategy: SignalStrategy | null;
  blocks: any[];
}

function StrategyBuilderModal({ isOpen, onClose, strategy, blocks }: StrategyBuilderModalProps) {
  const [selectedBlocks, setSelectedBlocks] = useState<StrategyBlock[]>(strategy?.blocks || []);
  const [strategyName, setStrategyName] = useState(strategy?.name || "");

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {strategy ? "Edit Strategy" : "Create New Strategy"}
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-6">
          <div>
            <Label htmlFor="strategy-name">Strategy Name</Label>
            <Input
              id="strategy-name"
              value={strategyName}
              onChange={(e) => setStrategyName(e.target.value)}
              placeholder="Enter strategy name..."
            />
          </div>
          
          <div>
            <h4 className="font-medium mb-3">Available Blocks</h4>
            <div className="grid grid-cols-4 gap-3">
              {blocks.map((block) => {
                const Icon = block.icon;
                const isSelected = selectedBlocks.some(b => b.type === block.type);
                
                return (
                  <div
                    key={block.type}
                    className={cn(
                      "p-4 rounded-lg border-2 cursor-pointer transition-all text-center",
                      isSelected
                        ? `border-${block.color}-500 bg-${block.color}-50`
                        : "border-gray-200 hover:border-gray-300"
                    )}
                  >
                    <Icon className={cn(
                      "w-8 h-8 mx-auto mb-2",
                      isSelected ? `text-${block.color}-600` : "text-gray-400"
                    )} />
                    <p className="text-sm font-medium">{block.name}</p>
                  </div>
                );
              })}
            </div>
          </div>
          
          <div className="flex justify-end space-x-3">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button>
              {strategy ? "Update Strategy" : "Create Strategy"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}