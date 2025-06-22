import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

export default function RecentSignals() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  const { data: signals, isLoading } = useQuery({
    queryKey: ["/api/signals", { limit: 10 }],
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  const replayMutation = useMutation({
    mutationFn: async (signalId: number) => {
      const res = await apiRequest("POST", `/api/signals/${signalId}/replay`);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/signals"] });
      toast({
        title: "Signal Replayed",
        description: "Signal has been queued for re-execution",
      });
    },
    onError: (error) => {
      toast({
        title: "Replay Failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Recent Signals</CardTitle>
            <Button variant="ghost" size="sm">Signal History</Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="animate-pulse flex items-center justify-between py-3 border-b border-gray-100">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-gray-200 rounded-full"></div>
                  <div>
                    <div className="h-4 bg-gray-200 rounded w-32 mb-1"></div>
                    <div className="h-3 bg-gray-200 rounded w-24"></div>
                  </div>
                </div>
                <div className="w-16 h-6 bg-gray-200 rounded"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'executed':
        return 'bg-secondary/10 text-secondary';
      case 'pending':
        return 'bg-warning/10 text-warning';
      case 'failed':
        return 'bg-destructive/10 text-destructive';
      case 'skipped':
        return 'bg-gray-100 text-gray-600';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  const getStatusDot = (status: string) => {
    switch (status) {
      case 'executed':
        return 'bg-secondary';
      case 'pending':
        return 'bg-warning';
      case 'failed':
        return 'bg-destructive';
      case 'skipped':
        return 'bg-gray-400';
      default:
        return 'bg-gray-400';
    }
  };

  return (
    <Card className="shadow-sm">
      <CardHeader className="border-b border-gray-200">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold text-dark">Recent Signals</CardTitle>
          <Button variant="ghost" size="sm" className="text-primary hover:text-primary/80">
            Signal History
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-6">
        {!signals || signals.length === 0 ? (
          <div className="text-center py-8">
            <i className="fas fa-signal text-4xl text-gray-400 mb-4"></i>
            <p className="text-gray-500 font-medium">No Recent Signals</p>
            <p className="text-sm text-gray-400">Telegram signals will appear here when received</p>
          </div>
        ) : (
          <div className="space-y-4">
            {signals.map((signal, index) => (
              <div 
                key={signal.id} 
                className={`flex items-center justify-between py-3 ${
                  index !== signals.length - 1 ? 'border-b border-gray-100' : ''
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div className={`w-2 h-2 ${getStatusDot(signal.status || 'pending')} rounded-full`}></div>
                  <div>
                    <p className="font-medium text-dark">
                      {signal.symbol} {signal.action} Signal
                    </p>
                    <p className="text-sm text-muted">
                      Entry: {signal.entry} • {new Date(signal.createdAt!).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Badge className={getStatusColor(signal.status || 'pending')}>
                    {signal.status || 'pending'}
                  </Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => replayMutation.mutate(signal.id)}
                    disabled={replayMutation.isPending}
                    className="text-primary hover:text-primary/80"
                  >
                    <i className="fas fa-redo text-sm"></i>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
