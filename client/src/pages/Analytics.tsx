import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import MainLayout from "@/layouts/MainLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import PerformanceChart from "@/components/charts/PerformanceChart";
import ProviderStatsCard from "@/components/providers/ProviderStatsCard";
import { 
  BarChart3, 
  TrendingUp, 
  Users, 
  Calendar,
  Download,
  Filter,
  RefreshCw
} from "lucide-react";

export default function Analytics() {
  const [timeframe, setTimeframe] = useState("30d");
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);

  const { data: analyticsData, isLoading, refetch } = useQuery({
    queryKey: ["/api/analytics", timeframe],
    refetchInterval: 60000,
  });

  const { data: providersData } = useQuery({
    queryKey: ["/api/providers/stats"],
    refetchInterval: 30000,
  });

  const mockProviders = [
    {
      id: "1",
      name: "ForexMaster Pro",
      status: "active" as const,
      totalSignals: 245,
      winRate: 78.5,
      avgPips: 85,
      profitFactor: 1.45,
      subscribers: 1250,
      trustScore: 85,
      lastSignal: "2 hours ago",
      monthlyPnL: 2450
    },
    {
      id: "2", 
      name: "TechAnalysis Elite",
      status: "active" as const,
      totalSignals: 189,
      winRate: 82.1,
      avgPips: 92,
      profitFactor: 1.62,
      subscribers: 980,
      trustScore: 91,
      lastSignal: "5 minutes ago",
      monthlyPnL: 3120
    },
    {
      id: "3",
      name: "SwingTrade Signals",
      status: "warning" as const,
      totalSignals: 156,
      winRate: 65.2,
      avgPips: 58,
      profitFactor: 1.18,
      subscribers: 750,
      trustScore: 72,
      lastSignal: "1 day ago",
      monthlyPnL: -450
    }
  ];

  const providers = providersData || mockProviders;

  const summaryStats = [
    {
      title: "Total Providers",
      value: providers.length,
      change: "+2 this month",
      icon: Users,
      color: "text-blue-600"
    },
    {
      title: "Avg Win Rate",
      value: `${(providers.reduce((acc, p) => acc + p.winRate, 0) / providers.length).toFixed(1)}%`,
      change: "+3.2% this month",
      icon: TrendingUp,
      color: "text-emerald-600"
    },
    {
      title: "Total Signals",
      value: providers.reduce((acc, p) => acc + p.totalSignals, 0),
      change: "+89 this week",
      icon: BarChart3,
      color: "text-purple-600"
    },
    {
      title: "Active Strategies",
      value: providers.filter(p => p.status === "active").length,
      change: "All systems operational",
      icon: Calendar,
      color: "text-orange-600"
    }
  ];

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Analytics Dashboard</h1>
            <p className="text-slate-600 mt-1">Comprehensive performance insights and provider analytics</p>
          </div>
          
          <div className="flex items-center space-x-3">
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            <Button variant="outline" size="sm">
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
            <Button variant="outline" size="sm">
              <Filter className="w-4 h-4 mr-2" />
              Filters
            </Button>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {summaryStats.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <Card key={index} className="border-0 shadow-lg">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-slate-600 mb-1">{stat.title}</p>
                      <p className="text-2xl font-bold text-slate-900">{stat.value}</p>
                      <p className="text-xs text-slate-500 mt-1">{stat.change}</p>
                    </div>
                    <div className={`w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center ${stat.color}`}>
                      <Icon className="w-6 h-6" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Performance Chart */}
        <PerformanceChart />

        {/* Provider Analytics */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-semibold text-slate-900">Provider Performance</h2>
            <div className="flex items-center space-x-2">
              <Badge variant="outline" className="text-emerald-700 border-emerald-200 bg-emerald-50">
                {providers.filter(p => p.status === "active").length} Active
              </Badge>
              <Badge variant="outline" className="text-amber-700 border-amber-200 bg-amber-50">
                {providers.filter(p => p.status === "warning").length} Warning
              </Badge>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {providers.map((provider) => (
              <ProviderStatsCard
                key={provider.id}
                provider={provider}
                onViewDetails={(id) => setSelectedProvider(id)}
                onToggleStatus={(id) => {
                  console.log("Toggle status for provider:", id);
                }}
              />
            ))}
          </div>
        </div>

        {/* Risk Metrics */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-r from-red-500 to-orange-600 rounded-lg flex items-center justify-center">
                <BarChart3 className="w-4 h-4 text-white" />
              </div>
              <span>Risk Management Overview</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="space-y-2">
                <div className="text-sm font-medium text-slate-600">Max Drawdown</div>
                <div className="text-2xl font-bold text-red-600">-5.2%</div>
                <div className="text-xs text-slate-500">Within acceptable limits</div>
              </div>
              
              <div className="space-y-2">
                <div className="text-sm font-medium text-slate-600">Risk Per Trade</div>
                <div className="text-2xl font-bold text-slate-900">2.5%</div>
                <div className="text-xs text-slate-500">Conservative approach</div>
              </div>
              
              <div className="space-y-2">
                <div className="text-sm font-medium text-slate-600">Sharpe Ratio</div>
                <div className="text-2xl font-bold text-emerald-600">1.85</div>
                <div className="text-xs text-slate-500">Excellent risk-adjusted returns</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}