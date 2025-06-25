import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { 
  Shield,
  HelpCircle,
  AlertTriangle,
  DollarSign,
  Percent,
  BarChart3,
  TrendingDown
} from "lucide-react";
import { cn } from "@/lib/utils";

interface RiskConfig {
  enabled: boolean;
  fixedLotSize: number;
  riskPercentage: number;
  accountBalance: number;
  calculateLotSize: boolean;
  maxDailyLoss: number;
  maxDrawdown: number;
  emergencyStop: boolean;
}

interface RiskManagementBlockProps {
  config: RiskConfig;
  onChange: (config: RiskConfig) => void;
}

export default function RiskManagementBlock({ config, onChange }: RiskManagementBlockProps) {
  const [riskMethod, setRiskMethod] = useState<"fixed" | "percentage">("percentage");

  const riskMethods = [
    {
      id: "fixed",
      name: "Fixed Lot Size",
      description: "Use same lot size for all trades",
      icon: DollarSign,
      color: "blue"
    },
    {
      id: "percentage", 
      name: "Risk % of Account",
      description: "Calculate lot based on risk percentage",
      icon: Percent,
      color: "green"
    }
  ];

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center space-x-2">
          <Shield className="w-5 h-5 text-amber-600" />
          <CardTitle>Risk Management</CardTitle>
          <HelpCircle className="w-4 h-4 text-muted-foreground" />
        </div>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Risk Method Selection */}
        <div>
          <Label className="text-sm font-medium mb-3 block">Risk Management Method</Label>
          <div className="grid grid-cols-2 gap-4">
            {riskMethods.map((method) => {
              const Icon = method.icon;
              const isActive = riskMethod === method.id;
              
              return (
                <div
                  key={method.id}
                  className={cn(
                    "p-4 rounded-lg border-2 cursor-pointer transition-all",
                    isActive 
                      ? `border-${method.color}-500 bg-${method.color}-50 dark:bg-${method.color}-950/20`
                      : "border-gray-200 hover:border-gray-300"
                  )}
                  onClick={() => setRiskMethod(method.id as "fixed" | "percentage")}
                >
                  <div className="flex items-center space-x-3">
                    <div className={cn(
                      "w-8 h-8 rounded-lg flex items-center justify-center",
                      isActive 
                        ? `bg-${method.color}-100 dark:bg-${method.color}-900/40`
                        : "bg-gray-100"
                    )}>
                      <Icon className={cn(
                        "w-4 h-4",
                        isActive ? `text-${method.color}-600` : "text-gray-400"
                      )} />
                    </div>
                    <div>
                      <p className="font-medium text-sm">{method.name}</p>
                      <p className="text-xs text-muted-foreground">{method.description}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Risk Configuration */}
        <div className="space-y-4">
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div className="bg-green-50 dark:bg-green-950/20 p-3 rounded-lg border border-green-200">
              <Label className="text-green-700 dark:text-green-300 font-medium">Use fixed lots</Label>
              <div className="flex items-center space-x-2 mt-2">
                <Input 
                  className="h-8 text-sm" 
                  defaultValue="0.01"
                  onChange={(e) => onChange({ ...config, fixedLotSize: parseFloat(e.target.value) || 0.01 })}
                />
              </div>
            </div>
            
            <div className="bg-green-50 dark:bg-green-950/20 p-3 rounded-lg border border-green-200">
              <Label className="text-green-700 dark:text-green-300 font-medium">Risk a fixed cash amount</Label>
              <div className="flex items-center space-x-2 mt-2">
                <Input className="h-8 text-sm" defaultValue="5%" />
              </div>
            </div>
            
            <div className="bg-green-50 dark:bg-green-950/20 p-3 rounded-lg border border-green-200">
              <Label className="text-green-700 dark:text-green-300 font-medium">Risk a % of your account balance</Label>
              <div className="flex items-center space-x-2 mt-2">
                <Input className="h-8 text-sm" defaultValue="0.5%" />
              </div>
            </div>
            
            <div className="bg-green-50 dark:bg-green-950/20 p-3 rounded-lg border border-green-200">
              <Label className="text-green-700 dark:text-green-300 font-medium">Calculate lotsize depending on a pip value</Label>
              <div className="flex items-center space-x-2 mt-2">
                <Input className="h-8 text-sm" defaultValue="19 pip" />
              </div>
            </div>
          </div>
        </div>

        {/* Take Profit Levels */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Label className="text-sm font-medium">3. Take Profit Levels</Label>
            <HelpCircle className="w-4 h-4 text-muted-foreground" />
          </div>
          
          <div className="space-y-3">
            <div className="grid grid-cols-4 gap-4">
              <div className="text-center">
                <Label className="text-xs text-muted-foreground">TP #</Label>
              </div>
              <div className="text-center">
                <Label className="text-xs text-muted-foreground">Percentage</Label>
              </div>
              <div className="text-center">
                <Label className="text-xs text-muted-foreground">Strategy</Label>
              </div>
              <div className="text-center">
                <Label className="text-xs text-muted-foreground">Distribute % Equally</Label>
              </div>
            </div>
            
            {[1, 2, 3].map((tp) => (
              <div key={tp} className="grid grid-cols-4 gap-4 items-center">
                <div className="text-center">
                  <span className="text-sm font-medium">TP {tp}</span>
                </div>
                <div className="text-center">
                  <span className="text-sm">{tp === 1 ? "60.0" : tp === 2 ? "30.0" : "10.0"}%</span>
                </div>
                <div className="text-center">
                  <Select defaultValue={`tp${tp}`}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={`tp${tp}`}>Set SL to {tp === 1 ? "ENTRY" : `TP${tp-1}`}</SelectItem>
                      <SelectItem value="hold">Hold Position</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center space-x-2">
                    <div className="w-4 h-4 bg-green-500 rounded flex items-center justify-center">
                      <span className="text-xs text-white font-bold">S</span>
                    </div>
                    <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                      <span className="text-xs">📋</span>
                    </Button>
                    <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-500">
                      <span className="text-xs">🗑️</span>
                    </Button>
                  </div>
                </div>
              </div>
            ))}
            
            <Button variant="outline" size="sm" className="text-xs">
              <HelpCircle className="w-3 h-3 mr-1" />
              Add a new Take Profit level
            </Button>
          </div>
        </div>

        {/* Signal Strategy */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Label className="text-sm font-medium">4. Signal Strategy</Label>
            <HelpCircle className="w-4 h-4 text-muted-foreground" />
          </div>
          
          <div className="flex items-center space-x-3">
            <Button variant="outline" size="sm">Strategy Templates</Button>
            <Button size="sm">
              <HelpCircle className="w-4 h-4 mr-2" />
              Add Custom Template
            </Button>
            <Button variant="outline" size="sm">Clear Strategy</Button>
          </div>
          
          <div className="relative">
            <Input placeholder="Search for a strategy..." className="pl-8" />
            <HelpCircle className="w-4 h-4 absolute left-2.5 top-3 text-muted-foreground" />
          </div>
          
          <div className="grid grid-cols-6 gap-3">
            {[
              { name: "Actions", icon: "⚡", active: true },
              { name: "Break Even", icon: "🎯", active: true },
              { name: "Manipulate Signal", icon: "🔄", active: true },
              { name: "Pending Orders", icon: "⏰", active: true },
              { name: "Filter Signals", icon: "🔍", active: true },
              { name: "Money Management", icon: "💰", active: true }
            ].map((block, index) => (
              <div
                key={index}
                className={cn(
                  "p-3 rounded-lg border-2 text-center cursor-pointer transition-all",
                  block.active ? "border-blue-200 bg-blue-50" : "border-gray-200 bg-gray-50"
                )}
              >
                <div className="text-lg mb-1">{block.icon}</div>
                <p className="text-xs font-medium">{block.name}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Emergency Controls */}
        <div className="space-y-3 pt-4 border-t">
          <div className="flex items-center justify-between">
            <Label htmlFor="emergency-stop" className="text-sm flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              <span>Emergency stop on max drawdown</span>
            </Label>
            <Switch
              id="emergency-stop"
              checked={config.emergencyStop}
              onCheckedChange={(checked) => 
                onChange({ ...config, emergencyStop: checked })
              }
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-xs text-muted-foreground">Max Daily Loss %</Label>
              <Input 
                className="h-8 text-sm mt-1" 
                defaultValue="5"
                onChange={(e) => onChange({ ...config, maxDailyLoss: parseFloat(e.target.value) || 5 })}
              />
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Max Drawdown %</Label>
              <Input 
                className="h-8 text-sm mt-1" 
                defaultValue="10"
                onChange={(e) => onChange({ ...config, maxDrawdown: parseFloat(e.target.value) || 10 })}
              />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}