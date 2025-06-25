import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useWebSocket } from "@/lib/websocket";
import { useToast } from "@/hooks/use-toast";
import { 
  Send, 
  TestTube,
  Wifi,
  MessageSquare,
  AlertCircle
} from "lucide-react";

export default function WebSocketTester() {
  const { isConnected, sendMessage, connectionState } = useWebSocket();
  const { toast } = useToast();
  const [testMessage, setTestMessage] = useState("");
  const [messageType, setMessageType] = useState("test_message");

  const sendTestMessage = () => {
    if (!testMessage.trim()) {
      toast({
        title: "Message Required",
        description: "Please enter a test message",
        variant: "destructive",
      });
      return;
    }

    sendMessage(messageType, { 
      message: testMessage,
      timestamp: new Date().toISOString()
    });

    toast({
      title: "Test Message Sent",
      description: `Sent "${messageType}" message via WebSocket`,
    });

    setTestMessage("");
  };

  const testEmergencyStop = () => {
    sendMessage("emergency_stop_test", {
      testMode: true,
      timestamp: new Date().toISOString()
    });

    toast({
      title: "Emergency Stop Test",
      description: "Test emergency stop signal sent",
      variant: "destructive",
    });
  };

  const testTradeUpdate = () => {
    sendMessage("trade_update", {
      tradeId: "test_123",
      symbol: "EURUSD",
      action: "BUY",
      pnl: 25.50,
      status: "open",
      timestamp: new Date().toISOString()
    });

    toast({
      title: "Trade Update Test",
      description: "Test trade update sent",
    });
  };

  const testSignalCreated = () => {
    sendMessage("signal_created", {
      signalId: "test_signal_456",
      symbol: "GBPUSD",
      action: "SELL",
      entry: 1.2650,
      provider: "Test Provider",
      timestamp: new Date().toISOString()
    });

    toast({
      title: "Signal Created Test",
      description: "Test signal creation sent",
    });
  };

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <TestTube className="w-5 h-5" />
          <span>WebSocket Connection Tester</span>
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Connection Status */}
        <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div className="flex items-center space-x-2">
            <Wifi className={`w-5 h-5 ${isConnected ? 'text-green-500' : 'text-red-500'}`} />
            <span className="font-medium">Connection Status:</span>
          </div>
          <Badge variant={isConnected ? "default" : "destructive"}>
            {connectionState.toUpperCase()}
          </Badge>
        </div>

        {/* Custom Message Test */}
        <div className="space-y-3">
          <Label>Custom Message Test</Label>
          <div className="flex space-x-2">
            <Input
              placeholder="Enter test message..."
              value={testMessage}
              onChange={(e) => setTestMessage(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && sendTestMessage()}
              className="flex-1"
            />
            <Button 
              onClick={sendTestMessage}
              disabled={!isConnected || !testMessage.trim()}
            >
              <Send className="w-4 h-4 mr-2" />
              Send
            </Button>
          </div>
        </div>

        {/* Predefined Tests */}
        <div className="space-y-3">
          <Label>Predefined Message Tests</Label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Button
              variant="outline"
              onClick={testEmergencyStop}
              disabled={!isConnected}
              className="flex items-center space-x-2"
            >
              <AlertCircle className="w-4 h-4 text-red-500" />
              <span>Emergency Stop</span>
            </Button>
            
            <Button
              variant="outline"
              onClick={testTradeUpdate}
              disabled={!isConnected}
              className="flex items-center space-x-2"
            >
              <MessageSquare className="w-4 h-4 text-blue-500" />
              <span>Trade Update</span>
            </Button>
            
            <Button
              variant="outline"
              onClick={testSignalCreated}
              disabled={!isConnected}
              className="flex items-center space-x-2"
            >
              <MessageSquare className="w-4 h-4 text-green-500" />
              <span>Signal Created</span>
            </Button>
          </div>
        </div>

        {!isConnected && (
          <div className="p-4 bg-yellow-50 dark:bg-yellow-950/20 border border-yellow-200 rounded-lg">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-yellow-600" />
              <span className="text-sm text-yellow-800 dark:text-yellow-200">
                WebSocket is not connected. Tests will be queued until connection is restored.
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}