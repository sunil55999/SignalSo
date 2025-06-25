import MainLayout from "@/layouts/MainLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Bot,
  MessageSquare,
  Zap,
  Settings
} from "lucide-react";

export default function CopilotPage() {
  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              AI Copilot
            </h1>
            <p className="text-slate-600 dark:text-slate-400 mt-1">
              Your intelligent trading assistant powered by AI
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <Button size="sm">
              <Settings className="w-4 h-4 mr-2" />
              Configure
            </Button>
          </div>
        </div>

        {/* Copilot Interface */}
        <Card className="shadow-lg border-0">
          <CardContent className="p-12">
            <div className="text-center">
              <Bot className="w-20 h-20 text-slate-300 mx-auto mb-6" />
              <h3 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 mb-4">
                AI Copilot Assistant
              </h3>
              <p className="text-slate-600 dark:text-slate-400 mb-8 max-w-md mx-auto">
                Get intelligent insights, automated analysis, and smart recommendations for your trading strategies
              </p>
              <div className="flex justify-center space-x-4">
                <Button>
                  <MessageSquare className="w-4 h-4 mr-2" />
                  Start Chat
                </Button>
                <Button variant="outline">
                  <Zap className="w-4 h-4 mr-2" />
                  Quick Analysis
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}