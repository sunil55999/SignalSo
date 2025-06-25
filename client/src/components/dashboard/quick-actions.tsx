import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { 
  AlertTriangle, 
  Pause, 
  Play, 
  EyeOff, 
  Eye, 
  RefreshCw,
  Square,
  Loader2
} from "lucide-react";

export default function QuickActions() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [stealthMode, setStealthMode] = useState(false);
  const [tradingPaused, setTradingPaused] = useState(false);

  const emergencyStopMutation = useMutation({
    mutationFn: async () => {
      return apiRequest("/api/trading/emergency-stop", {
        method: "POST",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/mt5-status"] });
      queryClient.invalidateQueries({ queryKey: ["/api/trades/live"] });
      toast({
        title: "Emergency Stop Activated",
        description: "All trading has been stopped immediately",
        variant: "destructive",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Emergency Stop Failed",
        description: error.message || "Failed to activate emergency stop",
        variant: "destructive",
      });
    },
  });

  const pauseTradingMutation = useMutation({
    mutationFn: async () => {
      const endpoint = tradingPaused ? "/api/trading/resume" : "/api/trading/pause";
      return apiRequest(endpoint, {
        method: "POST",
      });
    },
    onSuccess: () => {
      setTradingPaused(!tradingPaused);
      queryClient.invalidateQueries({ queryKey: ["/api/mt5-status"] });
      toast({
        title: `Trading ${!tradingPaused ? 'Paused' : 'Resumed'}`,
        description: `Signal processing is now ${!tradingPaused ? 'stopped' : 'active'}`,
        variant: !tradingPaused ? "destructive" : "default",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Operation Failed",
        description: error.message || "Failed to change trading state",
        variant: "destructive",
      });
    },
  });

  const stealthModeMutation = useMutation({
    mutationFn: async () => {
      return apiRequest("/api/trading/stealth-toggle", {
        method: "POST",
        body: JSON.stringify({ stealthMode: !stealthMode }),
      });
    },
    onSuccess: () => {
      setStealthMode(!stealthMode);
      toast({
        title: `Stealth Mode ${!stealthMode ? 'Enabled' : 'Disabled'}`,
        description: `SL/TP will ${!stealthMode ? 'be hidden from' : 'be visible in'} MT5`,
      });
    },
    onError: (error: any) => {
      toast({
        title: "Stealth Mode Failed",
        description: error.message || "Failed to toggle stealth mode",
        variant: "destructive",
      });
    },
  });

  const syncDesktopMutation = useMutation({
    mutationFn: async () => {
      return apiRequest("/api/firebridge/force-sync", {
        method: "POST",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/mt5-status"] });
      queryClient.invalidateQueries({ queryKey: ["/api/trades/live"] });
      queryClient.invalidateQueries({ queryKey: ["/api/dashboard/stats"] });
      toast({
        title: "Desktop Sync Initiated",
        description: "Synchronizing with desktop application",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Sync Failed",
        description: error.message || "Failed to sync with desktop app",
        variant: "destructive",
      });
    },
  });

  return (
    <div className="mt-8">
      <Card className="shadow-sm">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-lg font-semibold text-dark">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-4">
            {/* Emergency Stop */}
            <Button
              variant="outline"
              onClick={() => emergencyStopMutation.mutate()}
              disabled={emergencyStopMutation.isPending}
              className="flex items-center space-x-3 p-4 h-auto border-red-200 hover:bg-red-50 hover:border-red-300 transition-colors"
            >
              <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
                {emergencyStopMutation.isPending ? (
                  <Loader2 className="w-5 h-5 text-red-600 animate-spin" />
                ) : (
                  <Square className="w-5 h-5 text-red-600" />
                )}
              </div>
              <div className="text-left flex-1">
                <p className="font-medium text-red-700">Emergency Stop</p>
                <p className="text-sm text-red-600">Stop all trading immediately</p>
              </div>
            </Button>

            {/* Pause/Resume Trading */}
            <Button
              variant="outline"
              onClick={() => pauseTradingMutation.mutate()}
              disabled={pauseTradingMutation.isPending}
              className={`flex items-center space-x-3 p-4 h-auto transition-colors ${
                tradingPaused 
                  ? 'border-green-200 hover:bg-green-50 hover:border-green-300' 
                  : 'border-amber-200 hover:bg-amber-50 hover:border-amber-300'
              }`}
            >
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                tradingPaused ? 'bg-green-100' : 'bg-amber-100'
              }`}>
                {pauseTradingMutation.isPending ? (
                  <Loader2 className={`w-5 h-5 animate-spin ${
                    tradingPaused ? 'text-green-600' : 'text-amber-600'
                  }`} />
                ) : tradingPaused ? (
                  <Play className="w-5 h-5 text-green-600" />
                ) : (
                  <Pause className="w-5 h-5 text-amber-600" />
                )}
              </div>
              <div className="text-left flex-1">
                <p className={`font-medium ${
                  tradingPaused ? 'text-green-700' : 'text-amber-700'
                }`}>
                  {tradingPaused ? 'Resume Trading' : 'Pause Trading'}
                </p>
                <p className={`text-sm ${
                  tradingPaused ? 'text-green-600' : 'text-amber-600'
                }`}>
                  {tradingPaused ? 'Activate signal processing' : 'Stop new signal execution'}
                </p>
              </div>
              {tradingPaused && (
                <div className="w-2 h-2 bg-amber-500 rounded-full"></div>
              )}
            </Button>

            {/* Stealth Mode */}
            <Button
              variant="outline"
              onClick={() => stealthModeMutation.mutate()}
              disabled={stealthModeMutation.isPending}
              className={`flex items-center space-x-3 p-4 h-auto transition-colors ${
                stealthMode 
                  ? 'border-purple-200 bg-purple-50 hover:border-purple-300' 
                  : 'border-gray-200 hover:bg-gray-50 hover:border-gray-300'
              }`}
            >
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                stealthMode ? 'bg-purple-100' : 'bg-gray-100'
              }`}>
                {stealthModeMutation.isPending ? (
                  <Loader2 className={`w-5 h-5 animate-spin ${
                    stealthMode ? 'text-purple-600' : 'text-gray-600'
                  }`} />
                ) : stealthMode ? (
                  <EyeOff className="w-5 h-5 text-purple-600" />
                ) : (
                  <Eye className="w-5 h-5 text-gray-600" />
                )}
              </div>
              <div className="text-left flex-1">
                <p className={`font-medium ${
                  stealthMode ? 'text-purple-700' : 'text-gray-700'
                }`}>
                  Stealth Mode
                </p>
                <p className={`text-sm ${
                  stealthMode ? 'text-purple-600' : 'text-gray-600'
                }`}>
                  {stealthMode ? 'SL/TP hidden from MT5' : 'SL/TP visible in MT5'}
                </p>
              </div>
              {stealthMode && (
                <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
              )}
            </Button>

            {/* Sync Desktop */}
            <Button
              variant="outline"
              onClick={() => syncDesktopMutation.mutate()}
              disabled={syncDesktopMutation.isPending}
              className="flex items-center space-x-3 p-4 h-auto border-blue-200 hover:bg-blue-50 hover:border-blue-300 transition-colors"
            >
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                {syncDesktopMutation.isPending ? (
                  <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
                ) : (
                  <RefreshCw className="w-5 h-5 text-blue-600" />
                )}
              </div>
              <div className="text-left flex-1">
                <p className="font-medium text-blue-700">Sync Desktop</p>
                <p className="text-sm text-blue-600">Force sync with desktop app</p>
              </div>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
