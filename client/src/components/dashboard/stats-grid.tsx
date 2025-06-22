import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";

export default function StatsGrid() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["/api/dashboard/stats"],
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardContent className="p-6">
              <div className="h-20 bg-gray-200 rounded"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const statItems = [
    {
      title: "Active Trades",
      value: stats?.activeTrades || 0,
      change: "+12% from yesterday",
      changeType: "positive",
      icon: "fas fa-chart-line",
      bgColor: "bg-primary/10",
      iconColor: "text-primary"
    },
    {
      title: "Today's P&L",
      value: `$${stats?.todaysPnL || "0.00"}`,
      change: "+8.5% win rate",
      changeType: "positive",
      icon: "fas fa-dollar-sign",
      bgColor: "bg-secondary/10",
      iconColor: "text-secondary"
    },
    {
      title: "Signals Processed",
      value: stats?.signalsProcessed || 0,
      change: `${stats?.pendingSignals || 0} pending`,
      changeType: "neutral",
      icon: "fas fa-signal",
      bgColor: "bg-warning/10",
      iconColor: "text-warning"
    },
    {
      title: "Success Rate",
      value: `${stats?.successRate || "0.0"}%`,
      change: "Above target",
      changeType: "positive",
      icon: "fas fa-bullseye",
      bgColor: "bg-secondary/10",
      iconColor: "text-secondary"
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {statItems.map((stat, index) => (
        <Card key={index} className="shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted font-medium">{stat.title}</p>
                <p className="text-3xl font-bold text-dark mt-1">{stat.value}</p>
                <p className={`text-sm mt-1 ${
                  stat.changeType === 'positive' ? 'text-secondary' : 
                  stat.changeType === 'negative' ? 'text-destructive' : 'text-warning'
                }`}>
                  <i className={`fas ${stat.changeType === 'positive' ? 'fa-arrow-up' : 'fa-clock'}`}></i> {stat.change}
                </p>
              </div>
              <div className={`w-12 h-12 ${stat.bgColor} rounded-lg flex items-center justify-center`}>
                <i className={`${stat.icon} ${stat.iconColor}`}></i>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
