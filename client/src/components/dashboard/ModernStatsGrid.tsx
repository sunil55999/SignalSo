import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Activity, DollarSign, Target, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCard {
  title: string;
  value: string | number;
  change: string;
  changeValue: number;
  icon: React.ElementType;
  gradient: string;
  textColor: string;
}

export default function ModernStatsGrid() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["/api/dashboard/stats"],
    refetchInterval: 10000,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="animate-pulse border-0 shadow-lg">
            <CardContent className="p-6">
              <div className="h-24 bg-gradient-to-br from-slate-100 to-slate-200 rounded-lg"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const statCards: StatCard[] = [
    {
      title: "Portfolio Value",
      value: `$${(stats?.portfolioValue || 12450).toLocaleString()}`,
      change: "from yesterday",
      changeValue: stats?.portfolioChange || 2.4,
      icon: DollarSign,
      gradient: "from-emerald-500 to-teal-600",
      textColor: "text-emerald-600"
    },
    {
      title: "Active Trades",
      value: stats?.activeTrades || 8,
      change: "positions open",
      changeValue: stats?.tradesChange || 12,
      icon: Activity,
      gradient: "from-blue-500 to-indigo-600",
      textColor: "text-blue-600"
    },
    {
      title: "Success Rate",
      value: `${stats?.successRate || 78.5}%`,
      change: "win rate",
      changeValue: stats?.successChange || 5.2,
      icon: Target,
      gradient: "from-purple-500 to-pink-600",
      textColor: "text-purple-600"
    },
    {
      title: "Signals Today",
      value: stats?.signalsToday || 24,
      change: "processed",
      changeValue: stats?.signalsChange || 18,
      icon: Zap,
      gradient: "from-orange-500 to-red-600",
      textColor: "text-orange-600"
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {statCards.map((stat, index) => {
        const Icon = stat.icon;
        const isPositive = stat.changeValue >= 0;
        
        return (
          <Card key={index} className="border-0 shadow-lg hover:shadow-xl transition-all duration-300 group">
            <CardContent className="p-6 relative overflow-hidden">
              {/* Background Gradient */}
              <div className={cn(
                "absolute top-0 right-0 w-20 h-20 rounded-full blur-2xl opacity-20 group-hover:opacity-30 transition-opacity",
                `bg-gradient-to-br ${stat.gradient}`
              )}></div>
              
              <div className="relative z-10">
                <div className="flex items-center justify-between mb-4">
                  <div className={cn(
                    "w-12 h-12 rounded-xl flex items-center justify-center shadow-lg",
                    `bg-gradient-to-br ${stat.gradient}`
                  )}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  
                  <div className="flex items-center space-x-1">
                    {isPositive ? (
                      <TrendingUp className="w-4 h-4 text-emerald-500" />
                    ) : (
                      <TrendingDown className="w-4 h-4 text-red-500" />
                    )}
                    <span className={cn(
                      "text-sm font-medium",
                      isPositive ? "text-emerald-600" : "text-red-600"
                    )}>
                      {isPositive ? "+" : ""}{stat.changeValue}%
                    </span>
                  </div>
                </div>

                <div>
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">
                    {stat.title}
                  </p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-1">
                    {stat.value}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {stat.change}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}