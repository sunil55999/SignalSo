import MainLayout from "@/layouts/MainLayout";
// import ProviderStatsCard from "@/components/dashboard/ProviderStatsCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useQuery } from "@tanstack/react-query";
import { 
  Users,
  Plus,
  Settings,
  TrendingUp,
  RefreshCw
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export default function ProvidersPage() {
  const { data: providers, refetch } = useQuery({
    queryKey: ["/api/providers/stats"],
    refetchInterval: 10000,
  });

  const { toast } = useToast();
  const providersData = providers || [];

  const handleAddProvider = () => {
    toast({
      title: "Add Provider",
      description: "Provider setup dialog would open here"
    });
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Signal Providers
            </h1>
            <p className="text-slate-600 dark:text-slate-400 mt-1">
              Manage and monitor your trading signal sources
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            <Button size="sm" onClick={handleAddProvider}>
              <Plus className="w-4 h-4 mr-2" />
              Add Provider
            </Button>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card className="shadow-lg border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Total Providers</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {providersData.length}
                  </p>
                </div>
                <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <Users className="w-6 h-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Active Providers</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {providersData.filter((p: any) => p.status === "active").length}
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
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Avg Success Rate</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {providersData.length > 0 
                      ? (providersData.reduce((sum: number, p: any) => sum + (p.successRate || 0), 0) / providersData.length).toFixed(1)
                      : 0
                    }%
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
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Total Signals</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {providersData.reduce((sum: number, p: any) => sum + (p.totalSignals || 0), 0)}
                  </p>
                </div>
                <div className="w-12 h-12 bg-gradient-to-r from-orange-500 to-red-600 rounded-lg flex items-center justify-center">
                  <Settings className="w-6 h-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Providers Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {providersData.length > 0 ? (
            providersData.map((provider: any, index: number) => (
              <Card key={index} className="shadow-lg border-0">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-slate-900">{provider.name}</h3>
                    <Badge variant="outline" className="text-xs">
                      {provider.status}
                    </Badge>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600">Success Rate</span>
                      <span className="font-medium">{provider.successRate}%</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600">Total Signals</span>
                      <span className="font-medium">{provider.totalSignals}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          ) : (
            <Card className="shadow-lg border-0 lg:col-span-2 xl:col-span-3">
              <CardContent className="p-12">
                <div className="text-center">
                  <Users className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
                    No Providers Found
                  </h3>
                  <p className="text-slate-600 dark:text-slate-400 mb-6">
                    Start by adding your first signal provider to begin receiving trading signals
                  </p>
                  <Button onClick={handleAddProvider}>
                    <Plus className="w-4 h-4 mr-2" />
                    Add Your First Provider
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Provider Management */}
        <Card className="shadow-lg border-0">
          <CardHeader className="border-b border-slate-200 dark:border-slate-700">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg font-semibold">Provider Management</CardTitle>
              <Badge variant="outline" className="text-xs">
                Advanced Settings
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center p-6 border border-dashed border-slate-300 dark:border-slate-600 rounded-lg hover:border-blue-500 transition-colors cursor-pointer">
                <Plus className="w-8 h-8 text-slate-400 mx-auto mb-3" />
                <h4 className="font-medium text-slate-900 dark:text-slate-100 mb-1">Add Telegram Channel</h4>
                <p className="text-sm text-slate-600 dark:text-slate-400">Connect a new Telegram signal channel</p>
              </div>
              
              <div className="text-center p-6 border border-dashed border-slate-300 dark:border-slate-600 rounded-lg hover:border-blue-500 transition-colors cursor-pointer">
                <Settings className="w-8 h-8 text-slate-400 mx-auto mb-3" />
                <h4 className="font-medium text-slate-900 dark:text-slate-100 mb-1">Configure Filters</h4>
                <p className="text-sm text-slate-600 dark:text-slate-400">Set up signal filtering rules</p>
              </div>
              
              <div className="text-center p-6 border border-dashed border-slate-300 dark:border-slate-600 rounded-lg hover:border-blue-500 transition-colors cursor-pointer">
                <TrendingUp className="w-8 h-8 text-slate-400 mx-auto mb-3" />
                <h4 className="font-medium text-slate-900 dark:text-slate-100 mb-1">Performance Analysis</h4>
                <p className="text-sm text-slate-600 dark:text-slate-400">Deep dive into provider metrics</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}