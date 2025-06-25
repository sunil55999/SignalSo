import MainLayout from "@/layouts/MainLayout";
import ModernLiveTrades from "@/components/dashboard/ModernLiveTrades";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useQuery } from "@tanstack/react-query";
import { 
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  Filter,
  Download,
  RefreshCw
} from "lucide-react";

export default function TradesPage() {
  const { data: trades, isLoading, refetch } = useQuery({
    queryKey: ["/api/trades/live"],
    refetchInterval: 3000,
  });

  const { data: stats } = useQuery({
    queryKey: ["/api/dashboard/stats"],
    refetchInterval: 5000,
  });

  const tradesData = trades || [];
  const openTrades = tradesData.filter((t: any) => t.status === "open").length;
  const totalPnl = tradesData.reduce((sum: number, t: any) => sum + (t.pnl || 0), 0);

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Live Trades
            </h1>
            <p className="text-slate-600 dark:text-slate-400 mt-1">
              Monitor your active trading positions and performance
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <Button variant="outline" size="sm">
              <Filter className="w-4 h-4 mr-2" />
              Filter
            </Button>
            <Button variant="outline" size="sm">
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
            <Button onClick={() => refetch()} size="sm">
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card className="shadow-lg border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Active Trades</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {openTrades}
                  </p>
                </div>
                <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <Activity className="w-6 h-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Today's P&L</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    ${stats?.todaysPnL || "0.00"}
                  </p>
                </div>
                <div className="w-12 h-12 bg-gradient-to-r from-emerald-500 to-green-600 rounded-lg flex items-center justify-center">
                  <DollarSign className="w-6 h-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Success Rate</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {stats?.successRate || "0.0"}%
                  </p>
                </div>
                <div className="w-12 h-12 bg-gradient-to-r from-violet-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Portfolio Value</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    ${stats?.portfolioValue?.toLocaleString() || "0"}
                  </p>
                </div>
                <div className="w-12 h-12 bg-gradient-to-r from-orange-500 to-red-600 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Live Trades */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <ModernLiveTrades />
          
          <Card className="shadow-lg border-0">
            <CardHeader className="border-b border-slate-200 dark:border-slate-700">
              <CardTitle className="text-lg font-semibold">Trade History</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="text-center py-8">
                <Activity className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500 font-medium">Trade History</p>
                <p className="text-slate-400 text-sm">Recent closed trades will appear here</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
}