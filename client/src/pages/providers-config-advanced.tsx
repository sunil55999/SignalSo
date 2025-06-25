import { useState } from "react";
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
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import KeywordFilterBlock from "@/components/strategy-blocks/KeywordFilterBlock";
import TrailingStopBlock from "@/components/strategy-blocks/TrailingStopBlock";
import RiskManagementBlock from "@/components/strategy-blocks/RiskManagementBlock";
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
  Activity,
  Copy,
  Save
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

// Advanced Provider Configuration matching the images exactly
export default function ProvidersConfigAdvanced() {
  const { toast } = useToast();
  const [selectedTab, setSelectedTab] = useState("strategy");
  const [showKeywordModal, setShowKeywordModal] = useState(false);
  const [showTemplateModal, setShowTemplateModal] = useState(false);

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Configure Providers</h1>
            <p className="text-slate-600 dark:text-slate-400 mt-1">
              Channels (1544)
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <div className="w-3 h-3 bg-red-500 rounded-full"></div>
              <div className="w-3 h-3 bg-gray-300 rounded-full"></div>
            </div>
            <Button variant="outline" size="sm">
              <HelpCircle className="w-4 h-4 mr-2" />
              Add a new Take Profit level
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-6">
          {/* Left Sidebar */}
          <div className="col-span-3">
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-muted-foreground">Configured channels</div>
                  <Button variant="ghost" size="sm">
                    <Settings className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="p-3 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                        <MessageSquare className="w-4 h-4 text-blue-600" />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-medium text-sm">Telegram Signals Copier</h3>
                        <p className="text-xs text-blue-600 bg-green-100 px-2 py-1 rounded mt-1 inline-block">
                          Channel
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Main Content */}
          <div className="col-span-9">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Telegram Signals Copier</CardTitle>
                  <div className="flex items-center space-x-2">
                    <Badge variant="outline" className="text-green-600 border-green-200">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      Connected
                    </Badge>
                    <Button variant="outline" size="sm">Close</Button>
                    <Button size="sm">
                      <Plus className="w-4 h-4 mr-2" />
                      Add Provider
                    </Button>
                  </div>
                </div>
              </CardHeader>
              
              <CardContent>
                <Tabs value={selectedTab} onValueChange={setSelectedTab}>
                  <TabsList className="grid w-full grid-cols-4 mb-6">
                    <TabsTrigger value="resume">3.1. Order Resume</TabsTrigger>
                    <TabsTrigger value="strategy">4. Signal Strategy</TabsTrigger>
                    <TabsTrigger value="template">1. Message Template</TabsTrigger>
                    <TabsTrigger value="tp2">TP2 Strategy</TabsTrigger>
                  </TabsList>

                  <TabsContent value="strategy" className="space-y-6">
                    <StrategyConfiguration onOpenKeywords={() => setShowKeywordModal(true)} />
                  </TabsContent>

                  <TabsContent value="resume" className="space-y-6">
                    <OrderResumeConfiguration />
                  </TabsContent>

                  <TabsContent value="template" className="space-y-6">
                    <MessageTemplateConfiguration onOpenTemplate={() => setShowTemplateModal(true)} />
                  </TabsContent>

                  <TabsContent value="tp2" className="space-y-6">
                    <TP2StrategyConfiguration />
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Keyword Configuration Modal */}
        <Dialog open={showKeywordModal} onOpenChange={setShowKeywordModal}>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Keyword Configuration</DialogTitle>
            </DialogHeader>
            <KeywordFilterBlock 
              config={{
                type: "required",
                keywords: ["CLOSE FULLY", "CLOSE HALF"],
                caseSensitive: false,
                exactMatch: false,
                action: "execute"
              }}
              onChange={(config) => console.log("Keyword config:", config)}
            />
          </DialogContent>
        </Dialog>

        {/* Template Configuration Modal */}
        <Dialog open={showTemplateModal} onOpenChange={setShowTemplateModal}>
          <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Telegram Signals Copier - Template Configuration</DialogTitle>
            </DialogHeader>
            <TemplateConfigurationModal />
          </DialogContent>
        </Dialog>
      </div>
    </MainLayout>
  );
}

function StrategyConfiguration({ onOpenKeywords }: { onOpenKeywords: () => void }) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium flex items-center space-x-2">
          <span className="w-6 h-6 bg-blue-500 text-white rounded-full text-xs flex items-center justify-center">4</span>
          <span>Signal Strategy</span>
        </h3>
        <HelpCircle className="w-4 h-4 text-muted-foreground" />
      </div>
      
      <div className="flex items-center space-x-3">
        <Button variant="outline" size="sm">Strategy Templates</Button>
        <Button size="sm">
          <Plus className="w-4 h-4 mr-2" />
          Add Custom Template
        </Button>
        <Button variant="outline" size="sm">Clear Strategy</Button>
      </div>

      <div className="relative">
        <Input placeholder="Search for a strategy..." className="pl-8" />
        <HelpCircle className="w-4 h-4 absolute left-2.5 top-3 text-muted-foreground" />
      </div>

      {/* Strategy Blocks Grid */}
      <div className="grid grid-cols-6 gap-3">
        {[
          { name: "Actions", icon: Zap, color: "blue", active: true },
          { name: "Break Even", icon: Target, color: "green", active: true },
          { name: "Manipulate Signal", icon: Activity, color: "purple", active: true },
          { name: "Pending Orders", icon: Clock, color: "orange", active: true },
          { name: "Filter Signals", icon: Filter, color: "red", active: true },
          { name: "Money Management", icon: BarChart3, color: "indigo", active: true }
        ].map((block, index) => {
          const Icon = block.icon;
          return (
            <div
              key={index}
              className={cn(
                "p-3 rounded-lg border-2 text-center cursor-pointer transition-all",
                block.active 
                  ? `border-${block.color}-200 bg-${block.color}-50 dark:bg-${block.color}-950/20`
                  : "border-gray-200 bg-gray-50"
              )}
              onClick={block.name === "Filter Signals" ? onOpenKeywords : undefined}
            >
              <Icon className={cn(
                "w-6 h-6 mx-auto mb-2",
                block.active ? `text-${block.color}-600` : "text-gray-400"
              )} />
              <p className="text-xs font-medium">{block.name}</p>
            </div>
          );
        })}
      </div>

      {/* Configuration Sections */}
      <div className="space-y-6 pt-4 border-t">
        <TradeConfigSection />
        <KeywordConfigSection onOpenKeywords={onOpenKeywords} />
      </div>
    </div>
  );
}

function TradeConfigSection() {
  return (
    <div className="space-y-4">
      <h4 className="font-medium">Limit open trades</h4>
      
      <div className="space-y-3">
        <div className="flex items-center space-x-3">
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
          <div className="flex-1 flex items-center justify-between">
            <span className="text-sm">Max. open trades:</span>
            <div className="flex items-center space-x-2">
              <Input className="w-16 h-8 text-sm" defaultValue="3" />
              <span className="text-sm text-muted-foreground">(for this provider only)</span>
              <HelpCircle className="w-4 h-4 text-muted-foreground" />
            </div>
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          <div className="w-3 h-3 rounded-full border-2 border-gray-300"></div>
          <div className="flex-1 flex items-center justify-between">
            <span className="text-sm">Max. open trades:</span>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-muted-foreground">(across all providers)</span>
              <HelpCircle className="w-4 h-4 text-muted-foreground" />
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <h4 className="font-medium">Limit open trades per pair</h4>
        
        <div className="space-y-3">
          <div className="flex items-center space-x-3">
            <div className="w-3 h-3 rounded-full border-2 border-gray-300"></div>
            <div className="flex-1 flex items-center justify-between">
              <span className="text-sm">Max. open trades per pair:</span>
              <div className="flex items-center space-x-2">
                <span className="text-sm text-muted-foreground">(for this provider only)</span>
                <HelpCircle className="w-4 h-4 text-muted-foreground" />
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <div className="w-3 h-3 rounded-full border-2 border-gray-300"></div>
            <div className="flex-1 flex items-center justify-between">
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
  );
}

function KeywordConfigSection({ onOpenKeywords }: { onOpenKeywords: () => void }) {
  return (
    <div className="space-y-4">
      <h4 className="font-medium">Conditions to execute signals</h4>
      
      <div className="space-y-3">
        <div className="flex items-center space-x-3">
          <div className="w-3 h-3 rounded-full border-2 border-gray-300"></div>
          <div className="flex-1 flex items-center justify-between">
            <span className="text-sm">Only enter signals if the text</span>
            <div className="flex items-center space-x-2">
              <Input 
                placeholder="keywords" 
                className="w-32 h-8 text-sm"
                onClick={onOpenKeywords}
                readOnly
              />
              <span className="text-sm">is detected in the message</span>
              <HelpCircle className="w-4 h-4 text-muted-foreground" />
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
  );
}

function OrderResumeConfiguration() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium flex items-center space-x-2">
          <span className="w-6 h-6 bg-blue-500 text-white rounded-full text-xs flex items-center justify-center">3.1</span>
          <span>Order Resume</span>
        </h3>
        <Button size="sm">
          <Plus className="w-4 h-4 mr-2" />
          Add a new Take Profit level
        </Button>
      </div>
      
      <div className="space-y-4 text-sm text-muted-foreground">
        <p>ONE order rising 100% will be inserted.</p>
        <p>When TP1 hits, 50% of the initial volume will be closed.</p>
        <p>When TP2 hits, 50% of the initial volume will be closed.</p>
        <p className="pt-2">
          For signals with less than 2 TP's, the leftover will still be the same as above, but will close fully once the final TP in the signal is reached.
        </p>
      </div>
    </div>
  );
}

function MessageTemplateConfiguration({ onOpenTemplate }: { onOpenTemplate: () => void }) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium flex items-center space-x-2">
          <span className="w-6 h-6 bg-blue-500 text-white rounded-full text-xs flex items-center justify-center">1</span>
          <span>Message Template</span>
        </h3>
        <HelpCircle className="w-4 h-4 text-muted-foreground" />
      </div>
      
      <Button size="sm" className="bg-blue-600 hover:bg-blue-700" onClick={onOpenTemplate}>
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
        <Button variant="outline" size="sm">Test Message</Button>
        <Button variant="outline" size="sm">Update Templates</Button>
      </div>
    </div>
  );
}

function TP2StrategyConfiguration() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium flex items-center space-x-2">
          <span className="w-6 h-6 bg-purple-500 text-white rounded-full text-xs flex items-center justify-center">TP2</span>
          <span>TP2 Strategy</span>
        </h3>
        <HelpCircle className="w-4 h-4 text-muted-foreground" />
      </div>
      
      <div className="space-y-4">
        <div className="flex items-center space-x-2">
          <input type="checkbox" className="rounded" defaultChecked />
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
      </div>
    </div>
  );
}

function TemplateConfigurationModal() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="font-medium flex items-center space-x-2">
              <span className="w-6 h-6 bg-purple-500 text-white rounded-full text-xs flex items-center justify-center">2</span>
              <span>Risk Management</span>
            </h4>
            <HelpCircle className="w-4 h-4 text-muted-foreground" />
          </div>
          
          <div className="text-sm space-y-2">
            <p>Possible risk management rules (values can be adjusted):</p>
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span>Use fixed lots 0.01</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span>Risk a fixed cash amount 5%</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span>Risk a % of your account balance 0.5%</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span>Calculate lotsize depending on a pip value 19 pip</span>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="font-medium flex items-center space-x-2">
              <span className="w-6 h-6 bg-purple-500 text-white rounded-full text-xs flex items-center justify-center">3</span>
              <span>Take Profit Levels</span>
            </h4>
            <Button size="sm">
              <HelpCircle className="w-4 h-4 mr-2" />
              Distribute % Equally
            </Button>
          </div>
          
          <div className="space-y-3">
            <div className="grid grid-cols-4 gap-2 text-xs font-medium">
              <span>TP #</span>
              <span>Percentage</span>
              <span>Strategy</span>
              <span></span>
            </div>
            
            {[
              { tp: 1, percentage: "60.0", strategy: "Set SL to ENTRY" },
              { tp: 2, percentage: "30.0", strategy: "Set SL to TP1" },
              { tp: 3, percentage: "10.0", strategy: "Set SL to TP2" }
            ].map((item) => (
              <div key={item.tp} className="grid grid-cols-4 gap-2 items-center text-sm">
                <span>TP {item.tp}</span>
                <span>{item.percentage}%</span>
                <span className="text-xs">{item.strategy}</span>
                <div className="flex items-center space-x-1">
                  <div className="w-4 h-4 bg-green-500 rounded text-xs text-white flex items-center justify-center">S</div>
                  <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                    <Copy className="w-3 h-3" />
                  </Button>
                  <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-500">
                    <Trash2 className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      
      <div className="flex justify-end space-x-3">
        <Button variant="outline">Close</Button>
        <Button>
          <Save className="w-4 h-4 mr-2" />
          Save
        </Button>
      </div>
    </div>
  );
}