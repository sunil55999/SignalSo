import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  Activity, 
  Filter, 
  Search,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  TrendingUp,
  MessageSquare,
  Zap,
  RefreshCw
} from 'lucide-react';

interface SignalActivityFeedProps {
  logs: any[];
}

export function SignalActivityFeed({ logs }: SignalActivityFeedProps) {
  const [filter, setFilter] = useState<'all' | 'success' | 'error' | 'warning'>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const getLogIcon = (level: string) => {
    switch (level) {
      case 'info':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-600" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      default:
        return <Activity className="h-4 w-4 text-blue-600" />;
    }
  };

  const getComponentIcon = (component: string) => {
    switch (component) {
      case 'router':
        return <Zap className="h-3 w-3" />;
      case 'mt5':
        return <TrendingUp className="h-3 w-3" />;
      case 'telegram':
        return <MessageSquare className="h-3 w-3" />;
      default:
        return <Activity className="h-3 w-3" />;
    }
  };

  const filteredLogs = logs?.filter(log => {
    const matchesFilter = filter === 'all' || log.level === filter;
    const matchesSearch = log.message.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  }) || [];

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <Card className="h-96">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          Signal Activity Feed
        </CardTitle>
        <CardDescription>
          Real-time log of signal processing, trades, and system events
        </CardDescription>
        
        {/* Filter Controls */}
        <div className="flex items-center gap-2 pt-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search activity..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
          <div className="flex gap-1">
            {['all', 'success', 'error', 'warning'].map((filterType) => (
              <Button
                key={filterType}
                variant={filter === filterType ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilter(filterType as any)}
                className="capitalize"
              >
                {filterType === 'success' ? 'info' : filterType}
              </Button>
            ))}
          </div>
          <Button variant="outline" size="sm">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {filteredLogs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No activity found matching your criteria</p>
            </div>
          ) : (
            filteredLogs.map((log, index) => (
              <div key={log.id || index} className="flex items-start gap-3 p-3 rounded-lg bg-muted/50 hover:bg-muted/70 transition-colors">
                <div className="flex-shrink-0 mt-0.5">
                  {getLogIcon(log.level)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="text-sm font-medium text-foreground">{log.message}</p>
                    {log.component && (
                      <Badge variant="outline" className="text-xs">
                        {getComponentIcon(log.component)}
                        <span className="ml-1 capitalize">{log.component}</span>
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {formatTimestamp(log.timestamp)}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}