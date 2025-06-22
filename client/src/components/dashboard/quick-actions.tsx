import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";

export default function QuickActions() {
  const { toast } = useToast();
  const [stealthMode, setStealthMode] = useState(false);
  const [tradingPaused, setTradingPaused] = useState(false);

  const toggleStealth = () => {
    setStealthMode(!stealthMode);
    toast({
      title: `Stealth Mode ${!stealthMode ? 'Enabled' : 'Disabled'}`,
      description: `SL/TP will ${!stealthMode ? 'be hidden from' : 'be visible in'} MT5`,
    });
  };

  const pauseTrading = () => {
    setTradingPaused(!tradingPaused);
    toast({
      title: `Trading ${!tradingPaused ? 'Paused' : 'Resumed'}`,
      description: `New signal execution is ${!tradingPaused ? 'stopped' : 'active'}`,
      variant: !tradingPaused ? "destructive" : "default",
    });
  };

  const syncStrategy = () => {
    toast({
      title: "Strategy Sync Initiated",
      description: "Updating configuration from server",
    });
  };

  const actions = [
    {
      title: "Toggle Stealth Mode",
      description: "Hide SL/TP from MT5",
      icon: "fas fa-eye-slash",
      bgColor: "bg-primary/10",
      iconColor: "text-primary",
      onClick: toggleStealth,
      active: stealthMode
    },
    {
      title: "Pause Trading",
      description: "Stop new signal execution",
      icon: "fas fa-pause",
      bgColor: "bg-warning/10",
      iconColor: "text-warning",
      onClick: pauseTrading,
      active: tradingPaused
    },
    {
      title: "Sync Strategy",
      description: "Update configuration",
      icon: "fas fa-sync",
      bgColor: "bg-secondary/10",
      iconColor: "text-secondary",
      onClick: syncStrategy,
      active: false
    }
  ];

  return (
    <div className="mt-8">
      <Card className="shadow-sm">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-lg font-semibold text-dark">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {actions.map((action, index) => (
              <Button
                key={index}
                variant="ghost"
                onClick={action.onClick}
                className={`flex items-center space-x-3 p-4 h-auto border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors ${
                  action.active ? 'bg-gray-100 border-gray-300' : ''
                }`}
              >
                <div className={`w-10 h-10 ${action.bgColor} rounded-lg flex items-center justify-center`}>
                  <i className={`${action.icon} ${action.iconColor}`}></i>
                </div>
                <div className="text-left flex-1">
                  <p className="font-medium text-dark">{action.title}</p>
                  <p className="text-sm text-muted">{action.description}</p>
                </div>
                {action.active && (
                  <div className="w-2 h-2 bg-secondary rounded-full"></div>
                )}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
