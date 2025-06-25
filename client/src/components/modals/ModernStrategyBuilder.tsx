import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { 
  X, 
  Plus, 
  Layers, 
  Clock, 
  Target, 
  Filter,
  Shield,
  Zap,
  Save,
  Play
} from "lucide-react";
import { cn } from "@/lib/utils";

interface StrategyBlock {
  id: string;
  type: "timeWindow" | "riskReward" | "keywordFilter" | "marginFilter" | "providerFilter";
  name: string;
  icon: React.ElementType;
  configured: boolean;
  active: boolean;
}

interface ModernStrategyBuilderProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ModernStrategyBuilder({ isOpen, onClose }: ModernStrategyBuilderProps) {
  const [strategyName, setStrategyName] = useState("");
  const [selectedBlocks, setSelectedBlocks] = useState<StrategyBlock[]>([]);

  const availableBlocks: StrategyBlock[] = [
    {
      id: "time-window",
      type: "timeWindow",
      name: "Time Window",
      icon: Clock,
      configured: false,
      active: true
    },
    {
      id: "risk-reward",
      type: "riskReward", 
      name: "Risk/Reward",
      icon: Target,
      configured: false,
      active: true
    },
    {
      id: "keyword-filter",
      type: "keywordFilter",
      name: "Keyword Filter",
      icon: Filter,
      configured: false,
      active: true
    },
    {
      id: "margin-filter",
      type: "marginFilter",
      name: "Margin Filter",
      icon: Shield,
      configured: false,
      active: true
    }
  ];

  const addBlock = (block: StrategyBlock) => {
    if (!selectedBlocks.find(b => b.id === block.id)) {
      setSelectedBlocks([...selectedBlocks, { ...block, configured: false }]);
    }
  };

  const removeBlock = (blockId: string) => {
    setSelectedBlocks(selectedBlocks.filter(b => b.id !== blockId));
  };

  const toggleBlockActive = (blockId: string) => {
    setSelectedBlocks(selectedBlocks.map(block => 
      block.id === blockId ? { ...block, active: !block.active } : block
    ));
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 p-6 text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
                <Layers className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-2xl font-bold">Strategy Builder</h2>
                <p className="text-blue-100">Create advanced trading automation rules</p>
              </div>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose} className="text-white hover:bg-white/20">
              <X className="w-6 h-6" />
            </Button>
          </div>
        </div>

        <div className="flex h-[calc(90vh-120px)]">
          {/* Left Panel - Available Blocks */}
          <div className="w-80 border-r border-slate-200 p-6 overflow-y-auto">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">Available Blocks</h3>
            <div className="space-y-3">
              {availableBlocks.map((block) => {
                const Icon = block.icon;
                const isSelected = selectedBlocks.find(b => b.id === block.id);
                
                return (
                  <Card 
                    key={block.id} 
                    className={cn(
                      "cursor-pointer transition-all duration-200 hover:shadow-md",
                      isSelected ? "ring-2 ring-blue-500 bg-blue-50" : ""
                    )}
                    onClick={() => addBlock(block)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
                          <Icon className="w-5 h-5 text-slate-600" />
                        </div>
                        <div className="flex-1">
                          <div className="font-medium text-slate-900">{block.name}</div>
                          <div className="text-xs text-slate-500">
                            {block.type === "timeWindow" && "Control trading hours"}
                            {block.type === "riskReward" && "Set R:R ratios"}
                            {block.type === "keywordFilter" && "Filter by keywords"}
                            {block.type === "marginFilter" && "Check margin requirements"}
                          </div>
                        </div>
                        {isSelected && (
                          <Badge variant="outline" className="text-blue-600 border-blue-200 bg-blue-50">
                            Added
                          </Badge>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>

          {/* Right Panel - Strategy Builder */}
          <div className="flex-1 p-6 overflow-y-auto">
            <div className="max-w-3xl mx-auto space-y-6">
              {/* Strategy Name */}
              <Card className="border-0 shadow-lg">
                <CardHeader>
                  <CardTitle className="text-lg">Strategy Configuration</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <label className="text-sm font-medium text-slate-700 mb-2 block">
                        Strategy Name
                      </label>
                      <Input
                        placeholder="Enter strategy name..."
                        value={strategyName}
                        onChange={(e) => setStrategyName(e.target.value)}
                        className="w-full"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Selected Blocks */}
              <Card className="border-0 shadow-lg">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center justify-between">
                    <span>Strategy Blocks ({selectedBlocks.length})</span>
                    {selectedBlocks.length > 0 && (
                      <Badge variant="outline" className="text-emerald-600 border-emerald-200 bg-emerald-50">
                        {selectedBlocks.filter(b => b.active).length} Active
                      </Badge>
                    )}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {selectedBlocks.length === 0 ? (
                    <div className="text-center py-12 border-2 border-dashed border-slate-200 rounded-lg">
                      <Layers className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                      <p className="text-slate-500 font-medium">No blocks added yet</p>
                      <p className="text-slate-400 text-sm">Add blocks from the left panel to build your strategy</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {selectedBlocks.map((block, index) => {
                        const Icon = block.icon;
                        
                        return (
                          <Card key={block.id} className="border border-slate-200">
                            <CardContent className="p-4">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center space-x-3">
                                  <div className="text-sm font-medium text-slate-500">
                                    {index + 1}
                                  </div>
                                  <div className={cn(
                                    "w-10 h-10 rounded-lg flex items-center justify-center",
                                    block.active ? "bg-blue-100" : "bg-slate-100"
                                  )}>
                                    <Icon className={cn(
                                      "w-5 h-5",
                                      block.active ? "text-blue-600" : "text-slate-400"
                                    )} />
                                  </div>
                                  <div>
                                    <div className="font-medium text-slate-900">{block.name}</div>
                                    <div className="text-xs text-slate-500">
                                      {block.configured ? "Configured" : "Not configured"}
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="flex items-center space-x-2">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => toggleBlockActive(block.id)}
                                    className={cn(
                                      "text-xs",
                                      block.active 
                                        ? "text-emerald-600 border-emerald-200 bg-emerald-50" 
                                        : "text-slate-600"
                                    )}
                                  >
                                    {block.active ? "Active" : "Inactive"}
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => removeBlock(block.id)}
                                    className="text-red-500 hover:text-red-700 hover:bg-red-50"
                                  >
                                    <X className="w-4 h-4" />
                                  </Button>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-slate-200 p-6 bg-slate-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-sm text-slate-600">
              <Zap className="w-4 h-4" />
              <span>{selectedBlocks.filter(b => b.active).length} active blocks</span>
            </div>
            
            <div className="flex items-center space-x-3">
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button 
                variant="outline"
                disabled={!strategyName || selectedBlocks.length === 0}
                className="text-blue-600 border-blue-200 hover:bg-blue-50"
              >
                <Save className="w-4 h-4 mr-2" />
                Save Draft
              </Button>
              <Button 
                disabled={!strategyName || selectedBlocks.length === 0}
                className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700"
              >
                <Play className="w-4 h-4 mr-2" />
                Deploy Strategy
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}