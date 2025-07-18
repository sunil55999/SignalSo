import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Filter, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Info,
  Clock,
  RefreshCw
} from 'lucide-react';

interface LogEvent {
  id: string;
  level: 'info' | 'warning' | 'error' | 'success';
  message: string;
  timestamp: string;
  component: string;
  resolved?: boolean;
}

export function EventTimeline() {
  const [filter, setFilter] = useState<'all' | 'errors' | 'warnings' | 'info'>('all');
  
  const { data: logs, refetch } = useQuery({
    queryKey: ['/api/logs'],
    refetchInterval: 5000,
  });

  const getEventIcon = (level: string) => {
    switch (level) {
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      default:
        return <Info className="h-4 w-4 text-blue-500" />;
    }
  };

  const getEventBadge = (level: string) => {
    switch (level) {
      case 'error':
        return <Badge variant="destructive">Error</Badge>;
      case 'warning':
        return <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100">Warning</Badge>;
      case 'success':
        return <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Success</Badge>;
      default:
        return <Badge variant="outline">Info</Badge>;
    }
  };

  const getTimeAgo = (timestamp: string) => {
    const now = new Date();
    const eventTime = new Date(timestamp);
    const diffMs = now.getTime() - eventTime.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return `${Math.floor(diffMins / 1440)}d ago`;
  };

  const filteredLogs = logs?.filter((log: LogEvent) => {
    if (filter === 'all') return true;
    return log.level === filter;
  }) || [];

  const unresolvedCount = filteredLogs.filter((log: LogEvent) => 
    (log.level === 'error' || log.level === 'warning') && !log.resolved
  ).length;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-lg font-semibold">Event Timeline</CardTitle>
            {unresolvedCount > 0 && (
              <Badge variant="destructive" className="text-xs">
                {unresolvedCount} unresolved
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              <Button
                variant={filter === 'all' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilter('all')}
              >
                All
              </Button>
              <Button
                variant={filter === 'errors' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilter('errors')}
              >
                Errors
              </Button>
              <Button
                variant={filter === 'warnings' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilter('warnings')}
              >
                Warnings
              </Button>
              <Button
                variant={filter === 'info' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilter('info')}
              >
                Info
              </Button>
            </div>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {filteredLogs.slice(0, 20).map((log: LogEvent) => (
            <div key={log.id} className="flex items-start gap-3 p-3 border rounded-lg hover:bg-muted/50 transition-colors">
              <div className="flex-shrink-0 mt-0.5">
                {getEventIcon(log.level)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-sm">{log.component}</span>
                  {getEventBadge(log.level)}
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {getTimeAgo(log.timestamp)}
                  </div>
                </div>
                <p className="text-sm text-muted-foreground">{log.message}</p>
                {(log.level === 'error' || log.level === 'warning') && !log.resolved && (
                  <Button variant="link" size="sm" className="h-auto p-0 mt-1">
                    Mark as resolved
                  </Button>
                )}
              </div>
            </div>
          ))}
          {filteredLogs.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <Info className="h-8 w-8 mx-auto mb-2" />
              <p>No events found for the selected filter</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}