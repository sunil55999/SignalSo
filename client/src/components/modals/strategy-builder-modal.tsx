import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { insertStrategySchema } from "@shared/schema";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { z } from "zod";

interface StrategyBuilderModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const strategyFormSchema = insertStrategySchema.extend({
  name: z.string().min(1, "Strategy name is required"),
});

type StrategyForm = z.infer<typeof strategyFormSchema>;

interface StrategyRule {
  id: string;
  name: string;
  condition: {
    type: string;
    parameters: Record<string, any>;
  };
  action: {
    type: string;
    parameters: Record<string, any>;
  };
  enabled: boolean;
  priority: number;
}

export default function StrategyBuilderModal({ isOpen, onClose }: StrategyBuilderModalProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("builder");
  const [rules, setRules] = useState<StrategyRule[]>([]);
  const [selectedRule, setSelectedRule] = useState<StrategyRule | null>(null);

  // Fetch existing strategies
  const { data: strategies } = useQuery({
    queryKey: ["/api/strategies"],
    enabled: isOpen,
  });

  const strategyForm = useForm<StrategyForm>({
    resolver: zodResolver(strategyFormSchema),
    defaultValues: {
      name: "",
      config: {},
      isActive: true,
    },
  });

  const createStrategyMutation = useMutation({
    mutationFn: async (data: StrategyForm) => {
      const strategyConfig = {
        id: `strategy_${Date.now()}`,
        name: data.name,
        description: "Strategy created with visual builder",
        rules: rules,
        global_settings: {
          max_concurrent_trades: 5,
          default_lot_size: 0.01,
          emergency_stop: false
        },
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };

      const res = await apiRequest("POST", "/api/strategies", {
        ...data,
        config: strategyConfig
      });
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/strategies"] });
      toast({
        title: "Strategy created",
        description: "Your trading strategy has been successfully created",
      });
      onClose();
      strategyForm.reset();
      setRules([]);
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const addRule = () => {
    const newRule: StrategyRule = {
      id: `rule_${Date.now()}`,
      name: "New Rule",
      condition: {
        type: "confidence_threshold",
        parameters: { min_confidence: 70 }
      },
      action: {
        type: "execute_normal",
        parameters: {}
      },
      enabled: true,
      priority: rules.length + 1
    };
    setRules([...rules, newRule]);
    setSelectedRule(newRule);
  };

  const updateRule = (updatedRule: StrategyRule) => {
    setRules(rules.map(rule => rule.id === updatedRule.id ? updatedRule : rule));
    setSelectedRule(updatedRule);
  };

  const deleteRule = (ruleId: string) => {
    setRules(rules.filter(rule => rule.id !== ruleId));
    if (selectedRule?.id === ruleId) {
      setSelectedRule(null);
    }
  };

  const onSubmit = (data: StrategyForm) => {
    createStrategyMutation.mutate(data);
  };

  const predefinedTemplates = [
    {
      name: "Conservative Strategy",
      description: "Low risk, steady gains",
      rules: [
        {
          id: "conf_filter",
          name: "Confidence Filter",
          condition: { type: "confidence_threshold", parameters: { min_confidence: 80 } },
          action: { type: "skip_trade", parameters: { reason: "Low confidence" } },
          enabled: true,
          priority: 100
        },
        {
          id: "risk_mgmt",
          name: "Risk Management",
          condition: { type: "risk_management", parameters: { max_risk_percent: 1.5 } },
          action: { type: "scale_lot_size", parameters: { scale_factor: 0.5 } },
          enabled: true,
          priority: 90
        }
      ]
    },
    {
      name: "Aggressive Strategy",
      description: "Higher risk, higher reward",
      rules: [
        {
          id: "conf_filter",
          name: "Confidence Filter",
          condition: { type: "confidence_threshold", parameters: { min_confidence: 60 } },
          action: { type: "skip_trade", parameters: { reason: "Low confidence" } },
          enabled: true,
          priority: 100
        },
        {
          id: "tp1_move",
          name: "Move SL on TP1",
          condition: { type: "tp_hit_action", parameters: { tp_level: 1 } },
          action: { type: "move_sl_to_entry", parameters: {} },
          enabled: true,
          priority: 80
        }
      ]
    }
  ];

  const applyTemplate = (template: any) => {
    setRules(template.rules);
    strategyForm.setValue("name", template.name);
    setActiveTab("builder");
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold text-dark">
            Strategy Builder
          </DialogTitle>
        </DialogHeader>
        
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="templates">Templates</TabsTrigger>
            <TabsTrigger value="builder">Visual Builder</TabsTrigger>
            <TabsTrigger value="config">Configuration</TabsTrigger>
          </TabsList>

          <TabsContent value="templates" className="h-96 overflow-y-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {predefinedTemplates.map((template, index) => (
                <Card key={index} className="cursor-pointer hover:border-primary">
                  <CardHeader>
                    <CardTitle className="text-lg">{template.name}</CardTitle>
                    <p className="text-sm text-muted">{template.description}</p>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <p className="text-sm font-medium">Rules:</p>
                      {template.rules.map((rule, ruleIndex) => (
                        <Badge key={ruleIndex} variant="outline" className="mr-2">
                          {rule.name}
                        </Badge>
                      ))}
                    </div>
                    <Button 
                      className="w-full mt-4" 
                      onClick={() => applyTemplate(template)}
                    >
                      Use Template
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="builder" className="h-96">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 h-full">
              {/* Rules List */}
              <div className="border rounded-lg p-4">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-semibold">Strategy Rules</h3>
                  <Button size="sm" onClick={addRule}>
                    <i className="fas fa-plus mr-2"></i>
                    Add Rule
                  </Button>
                </div>
                <div className="space-y-2">
                  {rules.map((rule) => (
                    <div
                      key={rule.id}
                      className={`p-3 border rounded cursor-pointer transition-colors ${
                        selectedRule?.id === rule.id ? 'border-primary bg-primary/5' : 'hover:bg-gray-50'
                      }`}
                      onClick={() => setSelectedRule(rule)}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-medium text-sm">{rule.name}</p>
                          <p className="text-xs text-muted">
                            {rule.condition.type} → {rule.action.type}
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteRule(rule.id);
                          }}
                        >
                          <i className="fas fa-trash text-destructive"></i>
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Rule Editor */}
              <div className="col-span-2 border rounded-lg p-4">
                {selectedRule ? (
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <h3 className="font-semibold">Edit Rule: {selectedRule.name}</h3>
                      <div className="flex items-center space-x-2">
                        <Switch
                          checked={selectedRule.enabled}
                          onCheckedChange={(enabled) => 
                            updateRule({ ...selectedRule, enabled })
                          }
                        />
                        <Label>Enabled</Label>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>Rule Name</Label>
                        <Input
                          value={selectedRule.name}
                          onChange={(e) => 
                            updateRule({ ...selectedRule, name: e.target.value })
                          }
                        />
                      </div>
                      <div>
                        <Label>Priority</Label>
                        <Input
                          type="number"
                          value={selectedRule.priority}
                          onChange={(e) => 
                            updateRule({ ...selectedRule, priority: parseInt(e.target.value) })
                          }
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>Condition Type</Label>
                        <Select
                          value={selectedRule.condition.type}
                          onValueChange={(value) =>
                            updateRule({
                              ...selectedRule,
                              condition: { ...selectedRule.condition, type: value }
                            })
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="confidence_threshold">Confidence Threshold</SelectItem>
                            <SelectItem value="time_filter">Time Filter</SelectItem>
                            <SelectItem value="symbol_filter">Symbol Filter</SelectItem>
                            <SelectItem value="risk_management">Risk Management</SelectItem>
                            <SelectItem value="market_condition">Market Condition</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div>
                        <Label>Action Type</Label>
                        <Select
                          value={selectedRule.action.type}
                          onValueChange={(value) =>
                            updateRule({
                              ...selectedRule,
                              action: { ...selectedRule.action, type: value }
                            })
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="execute_normal">Execute Normal</SelectItem>
                            <SelectItem value="skip_trade">Skip Trade</SelectItem>
                            <SelectItem value="scale_lot_size">Scale Lot Size</SelectItem>
                            <SelectItem value="move_sl_to_entry">Move SL to Entry</SelectItem>
                            <SelectItem value="send_alert">Send Alert</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    {/* Condition Parameters */}
                    {selectedRule.condition.type === "confidence_threshold" && (
                      <div>
                        <Label>Minimum Confidence (%)</Label>
                        <Input
                          type="number"
                          value={selectedRule.condition.parameters.min_confidence || 70}
                          onChange={(e) =>
                            updateRule({
                              ...selectedRule,
                              condition: {
                                ...selectedRule.condition,
                                parameters: {
                                  ...selectedRule.condition.parameters,
                                  min_confidence: parseFloat(e.target.value)
                                }
                              }
                            })
                          }
                        />
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <i className="fas fa-mouse-pointer text-4xl text-gray-400 mb-4"></i>
                      <p className="text-gray-500">Select a rule to edit</p>
                      <p className="text-sm text-gray-400">or add a new rule to get started</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="config" className="h-96">
            <Form {...strategyForm}>
              <form onSubmit={strategyForm.handleSubmit(onSubmit)} className="space-y-4">
                <FormField
                  control={strategyForm.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Strategy Name</FormLabel>
                      <FormControl>
                        <Input placeholder="Enter strategy name" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={strategyForm.control}
                    name="isActive"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                          <FormLabel className="text-base">Active Strategy</FormLabel>
                          <div className="text-sm text-muted">
                            Activate this strategy for live trading
                          </div>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                </div>

                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold mb-2">Strategy Summary</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>Total Rules:</span>
                      <span>{rules.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Active Rules:</span>
                      <span>{rules.filter(r => r.enabled).length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Strategy Type:</span>
                      <span>
                        {rules.some(r => r.condition.parameters?.min_confidence > 75) 
                          ? "Conservative" 
                          : "Balanced"}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end space-x-2">
                  <Button type="button" variant="outline" onClick={onClose}>
                    Cancel
                  </Button>
                  <Button 
                    type="submit" 
                    disabled={createStrategyMutation.isPending || rules.length === 0}
                  >
                    Create Strategy
                  </Button>
                </div>
              </form>
            </Form>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
