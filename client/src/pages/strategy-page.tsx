import MainLayout from "@/layouts/MainLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Layers,
  Plus,
  Play,
  Pause,
  Settings,
  TrendingUp
} from "lucide-react";

export default function StrategyPage() {
  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Strategy Builder
            </h1>
            <p className="text-slate-600 dark:text-slate-400 mt-1">
              Create and manage your automated trading strategies
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <Button size="sm">
              <Plus className="w-4 h-4 mr-2" />
              New Strategy
            </Button>
          </div>
        </div>

        {/* Strategy Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          <Card className="shadow-lg border-0">
            <CardContent className="p-6">
              <div className="text-center">
                <Layers className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
                  Strategy Builder
                </h3>
                <p className="text-slate-600 dark:text-slate-400 mb-6">
                  Create custom trading strategies with visual blocks
                </p>
                <Button>
                  <Plus className="w-4 h-4 mr-2" />
                  Build Strategy
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
}