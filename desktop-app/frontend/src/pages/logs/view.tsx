import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function LogsView() {
  const { data: logs } = useQuery({
    queryKey: ['/api/logs'],
    refetchInterval: 5000,
  });

  const { data: stats } = useQuery({
    queryKey: ['/api/logs/stats'],
    refetchInterval: 10000,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">System Logs</h1>
      
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Total Logs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total || 0}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Info</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{stats?.byLevel?.info || 0}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Warnings</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{stats?.byLevel?.warning || 0}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Errors</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats?.byLevel?.error || 0}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Logs</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {logs?.map((log: any) => (
              <div key={log.id} className="flex items-center gap-3 p-2 rounded-lg border">
                <div className={`h-2 w-2 rounded-full ${
                  log.level === 'error' ? 'bg-red-500' : 
                  log.level === 'warning' ? 'bg-yellow-500' : 'bg-green-500'
                }`} />
                <span className="text-sm text-muted-foreground">
                  {new Date(log.timestamp).toLocaleString()}
                </span>
                <span className="text-sm font-medium">{log.component}</span>
                <span className="text-sm">{log.message}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}