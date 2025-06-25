import MainLayout from "@/layouts/MainLayout";
import SignalTable from "@/components/tables/SignalTable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useQuery } from "@tanstack/react-query";
import { 
  TrendingUp,
  Filter,
  Download,
  RefreshCw,
  Activity
} from "lucide-react";
import { useToastActions } from "@/hooks/use-toast-actions";

export default function SignalsPage() {
  const { data: signals, isLoading, refetch } = useQuery({
    queryKey: ["/api/signals"],
    refetchInterval: 5000,
  });

  const { handleFilter, handleExport, handleRefresh } = useToastActions();

  const signalsData = signals || [];
  const activeSignals = signalsData.filter((s: any) => s.status === "pending").length;
  const executedSignals = signalsData.filter((s: any) => s.status === "executed").length;

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Trading Signals
            </h1>
            <p className="text-slate-600 dark:text-slate-400 mt-1">
              Monitor and manage your trading signals in real-time
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <Button variant="outline" size="sm" onClick={handleFilter}>
              <Filter className="w-4 h-4 mr-2" />
              Filter
            </Button>
            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
            <Button onClick={() => { refetch(); handleRefresh(); }} size="sm">
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
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Total Signals</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {signalsData.length}
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
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Active Signals</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {activeSignals}
                  </p>
                </div>
                <div className="w-12 h-12 bg-gradient-to-r from-orange-500 to-red-600 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Executed</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {executedSignals}
                  </p>
                </div>
                <div className="w-12 h-12 bg-gradient-to-r from-emerald-500 to-green-600 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-white" />
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
                    {signalsData.length > 0 ? ((executedSignals / signalsData.length) * 100).toFixed(1) : 0}%
                  </p>
                </div>
                <div className="w-12 h-12 bg-gradient-to-r from-violet-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <Activity className="w-6 h-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Signals Table */}
        <Card className="shadow-lg border-0">
          <CardHeader className="border-b border-slate-200 dark:border-slate-700">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg font-semibold">All Trading Signals</CardTitle>
              <div className="flex items-center space-x-2">
                <Badge variant="outline" className="text-xs">
                  Live Data
                </Badge>
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <SignalTable />
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}