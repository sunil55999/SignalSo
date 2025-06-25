import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { 
  TrendingUp,
  HelpCircle,
  Target,
  Activity,
  BarChart3
} from "lucide-react";
import { cn } from "@/lib/utils";

interface TrailingStopConfig {
  enabled: boolean;
  triggerType: "pips" | "percentage" | "ratio";
  triggerValue: number;
  trailDistance: number;
  onlyAfterBreakeven: boolean;
  moveToEntry: boolean;
  moveToTP: number;
}

interface TrailingStopBlockProps {
  config: TrailingStopConfig;
  onChange: (config: TrailingStopConfig) => void;
}

export default function TrailingStopBlock({ config, onChange }: TrailingStopBlockProps) {
  const [activeStrategy, setActiveStrategy] = useState<"trail" | "move">("trail");

  const trailStrategies = [
    {
      id: "trail",
      name: "Trailing SL",
      description: "Move SL following price movement",
      icon: TrendingUp,
      color: "emerald"
    },
    {
      id: "move",
      name: "Move SL",
      description: "Move SL to specific levels",
      icon: Target,
      color: "blue"
    }
  ];

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center space-x-2">
          <TrendingUp className="w-5 h-5 text-emerald-600" />
          <CardTitle>Trailing SL Configuration</CardTitle>
          <HelpCircle className="w-4 h-4 text-muted-foreground" />
        </div>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Strategy Selection */}
        <div className="grid grid-cols-2 gap-4">
          {trailStrategies.map((strategy) => {
            const Icon = strategy.icon;
            const isActive = activeStrategy === strategy.id;
            
            return (
              <div
                key={strategy.id}
                className={cn(
                  "p-4 rounded-lg border-2 cursor-pointer transition-all",
                  isActive 
                    ? `border-${strategy.color}-500 bg-${strategy.color}-50 dark:bg-${strategy.color}-950/20`
                    : "border-gray-200 hover:border-gray-300"
                )}
                onClick={() => setActiveStrategy(strategy.id as "trail" | "move")}
              >
                <div className="flex items-center space-x-3">
                  <div className={cn(
                    "w-8 h-8 rounded-lg flex items-center justify-center",
                    isActive 
                      ? `bg-${strategy.color}-100 dark:bg-${strategy.color}-900/40`
                      : "bg-gray-100"
                  )}>
                    <Icon className={cn(
                      "w-4 h-4",
                      isActive ? `text-${strategy.color}-600` : "text-gray-400"
                    )} />
                  </div>
                  <div>
                    <p className="font-medium text-sm">{strategy.name}</p>
                    <p className="text-xs text-muted-foreground">{strategy.description}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {activeStrategy === "trail" && (
          <div className="space-y-4">
            <div className="space-y-3">
              <Label className="text-sm font-medium">TRAIL Add</Label>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <span className="text-sm">pips to SL every</span>
                    <Input className="w-16 h-8 text-sm" defaultValue="0" />
                    <span className="text-sm">pips in profit - Only after break-even</span>
                    <HelpCircle className="w-4 h-4 text-muted-foreground" />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm">R:R in profit - Only after break-even</span>
                    <HelpCircle className="w-4 h-4 text-muted-foreground" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeStrategy === "move" && (
          <div className="space-y-4">
            <div className="space-y-3">
              <Label className="text-sm font-medium">When in profit</Label>
              
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 rounded-full bg-green-500"></div>
                  <span className="text-sm">Move SL to ENTRYPOINT +</span>
                  <Input className="w-16 h-8 text-sm" defaultValue="0" />
                  <span className="text-sm">pips when the signal is</span>
                  <Input className="w-16 h-8 text-sm" defaultValue="0" />
                  <span className="text-sm">pips in profit</span>
                </div>
                
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 rounded-full border-2 border-gray-300"></div>
                  <span className="text-sm">Move SL to ENTRYPOINT +</span>
                  <Input className="w-16 h-8 text-sm" />
                  <span className="text-sm">pips, when signal reaches</span>
                  <span className="text-sm">% profit (account balance)</span>
                </div>
                
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 rounded-full border-2 border-gray-300"></div>
                  <span className="text-sm">Move SL to ENTRYPOINT +</span>
                  <Input className="w-16 h-8 text-sm" />
                  <span className="text-sm">pips, when signal reaches</span>
                  <span className="text-sm">% of Take Profit level</span>
                </div>
                
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 rounded-full border-2 border-gray-300"></div>
                  <span className="text-sm">Move SL to</span>
                  <span className="text-sm">% of Take Profit level, when the signal reaches</span>
                  <span className="text-sm">% of Take Profit level</span>
                  <HelpCircle className="w-4 h-4 text-muted-foreground" />
                </div>
                
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 rounded-full border-2 border-gray-300"></div>
                  <span className="text-sm">Move SL to</span>
                  <span className="text-sm">% of Take Profit level, when the signal reaches</span>
                  <span className="text-sm">% of Take Profit level</span>
                  <HelpCircle className="w-4 h-4 text-muted-foreground" />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Advanced Options */}
        <div className="space-y-3 pt-4 border-t">
          <div className="flex items-center justify-between">
            <Label htmlFor="breakeven-only" className="text-sm">
              Only activate after break-even
            </Label>
            <Switch
              id="breakeven-only"
              checked={config.onlyAfterBreakeven}
              onCheckedChange={(checked) => 
                onChange({ ...config, onlyAfterBreakeven: checked })
              }
            />
          </div>
          
          <div className="flex items-center justify-between">
            <Label htmlFor="move-entry" className="text-sm">
              Move SL to entry when profitable
            </Label>
            <Switch
              id="move-entry"
              checked={config.moveToEntry}
              onCheckedChange={(checked) => 
                onChange({ ...config, moveToEntry: checked })
              }
            />
          </div>
        </div>

        {/* Trail Distance Slider */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">Trail Distance (pips)</Label>
          <div className="px-2">
            <Slider
              value={[config.trailDistance]}
              onValueChange={([value]) => onChange({ ...config, trailDistance: value })}
              max={100}
              min={1}
              step={1}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground mt-1">
              <span>1 pip</span>
              <span>{config.trailDistance} pips</span>
              <span>100 pips</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}