import MainLayout from "@/layouts/MainLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Shield,
  AlertTriangle,
  Settings,
  TrendingDown
} from "lucide-react";

export default function RiskPage() {
  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Risk Control
            </h1>
            <p className="text-slate-600 dark:text-slate-400 mt-1">
              Manage risk limits and safety controls for your trading
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <Button size="sm">
              <Settings className="w-4 h-4 mr-2" />
              Configure Limits
            </Button>
          </div>
        </div>

        {/* Risk Controls */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="shadow-lg border-0">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Shield className="w-5 h-5 text-emerald-500" />
                <span>Risk Management</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Max Daily Loss</span>
                  <Badge variant="outline">$500</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Max Position Size</span>
                  <Badge variant="outline">2%</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Max Open Positions</span>
                  <Badge variant="outline">5</Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <span>Safety Alerts</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <Shield className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500 font-medium">All Systems Secure</p>
                <p className="text-slate-400 text-sm">No risk alerts at this time</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
}