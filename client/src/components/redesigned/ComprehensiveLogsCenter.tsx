import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  FileText, 
  Search, 
  Filter, 
  Download, 
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  Activity,
  TrendingUp,
  MessageSquare,
  Zap,
  Database,
  Settings,
  Eye,
  Trash2
} from 'lucide-react';

export function ComprehensiveLogsCenter() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLevel, setSelectedLevel] = useState<string>('all');
  const [selectedComponent, setSelectedComponent] = useState<string>('all');
  const [timeRange, setTimeRange] = useState<string>('24h');

  const { data: logs, refetch: refetchLogs } = useQuery({
    queryKey: ['/api/logs'],
    refetchInterval: 5000,
  });

  const { data: logStats } = useQuery({
    queryKey: ['/api/logs/stats'],
    refetchInterval: 10000,
  });

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
        return <Zap className="h-4 w-4 text-blue-600" />;
      case 'mt5':
        return <TrendingUp className="h-4 w-4 text-green-600" />;
      case 'telegram':
        return <MessageSquare className="h-4 w-4 text-purple-600" />;
      case 'system':
        return <Settings className="h-4 w-4 text-orange-600" />;
      default:
        return <Activity className="h-4 w-4 text-gray-600" />;
    }
  };

  const filteredLogs = logs?.filter(log => {
    const matchesSearch = log.message.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesLevel = selectedLevel === 'all' || log.level === selectedLevel;
    const matchesComponent = selectedComponent === 'all' || log.component === selectedComponent;
    return matchesSearch && matchesLevel && matchesComponent;
  }) || [];

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const handleExportLogs = () => {
    const exportData = filteredLogs.map(log => ({
      timestamp: log.timestamp,
      level: log.level,
      component: log.component,
      message: log.message
    }));
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const components = ['all', 'router', 'mt5', 'telegram', 'system'];
  const levels = ['all', 'info', 'warning', 'error'];
  const timeRanges = ['1h', '24h', '7d', '30d'];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Logs & Activity Center</h2>
          <p className="text-muted-foreground">
            Comprehensive system logs with filtering and analysis
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => refetchLogs()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={handleExportLogs}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-blue-600" />
              <div>
                <div className="text-2xl font-bold">{logStats?.total || 0}</div>
                <div className="text-sm text-muted-foreground">Total Logs</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <div>
                <div className="text-2xl font-bold text-green-600">{logStats?.byLevel?.info || 0}</div>
                <div className="text-sm text-muted-foreground">Info</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              <div>
                <div className="text-2xl font-bold text-yellow-600">{logStats?.byLevel?.warning || 0}</div>
                <div className="text-sm text-muted-foreground">Warnings</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <XCircle className="h-4 w-4 text-red-600" />
              <div>
                <div className="text-2xl font-bold text-red-600">{logStats?.byLevel?.error || 0}</div>
                <div className="text-sm text-muted-foreground">Errors</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters & Search
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <Label htmlFor="search">Search</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Search logs..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="level">Log Level</Label>
              <select
                id="level"
                value={selectedLevel}
                onChange={(e) => setSelectedLevel(e.target.value)}
                className="w-full p-2 border border-input rounded-md bg-background"
              >
                {levels.map(level => (
                  <option key={level} value={level}>
                    {level.charAt(0).toUpperCase() + level.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <Label htmlFor="component">Component</Label>
              <select
                id="component"
                value={selectedComponent}
                onChange={(e) => setSelectedComponent(e.target.value)}
                className="w-full p-2 border border-input rounded-md bg-background"
              >
                {components.map(component => (
                  <option key={component} value={component}>
                    {component.charAt(0).toUpperCase() + component.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <Label htmlFor="timeRange">Time Range</Label>
              <select
                id="timeRange"
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="w-full p-2 border border-input rounded-md bg-background"
              >
                {timeRanges.map(range => (
                  <option key={range} value={range}>
                    Last {range}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Log Tabs */}
      <Tabs defaultValue="timeline" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="timeline">Timeline View</TabsTrigger>
          <TabsTrigger value="grouped">Grouped by Component</TabsTrigger>
          <TabsTrigger value="analysis">Analysis</TabsTrigger>
        </TabsList>

        {/* Timeline View */}
        <TabsContent value="timeline">
          <Card>
            <CardHeader>
              <CardTitle>Live Log Timeline</CardTitle>
              <CardDescription>
                Real-time system activity in chronological order
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {filteredLogs.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No logs found matching your criteria</p>
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
                          <Badge variant="outline" className="text-xs">
                            {getComponentIcon(log.component)}
                            <span className="ml-1 capitalize">{log.component}</span>
                          </Badge>
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
        </TabsContent>

        {/* Grouped View */}
        <TabsContent value="grouped">
          <div className="grid gap-4">
            {components.filter(c => c !== 'all').map(component => {
              const componentLogs = filteredLogs.filter(log => log.component === component);
              if (componentLogs.length === 0) return null;
              
              return (
                <Card key={component}>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      {getComponentIcon(component)}
                      {component.charAt(0).toUpperCase() + component.slice(1)} Component
                      <Badge variant="secondary">{componentLogs.length}</Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {componentLogs.slice(0, 10).map((log, index) => (
                        <div key={index} className="flex items-center gap-2 p-2 rounded bg-muted/30">
                          {getLogIcon(log.level)}
                          <span className="text-sm flex-1">{log.message}</span>
                          <span className="text-xs text-muted-foreground">
                            {formatTimestamp(log.timestamp)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        {/* Analysis View */}
        <TabsContent value="analysis">
          <div className="grid gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Log Analysis</CardTitle>
                <CardDescription>
                  Insights and patterns from your system logs
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h3 className="font-medium mb-3">Activity by Component</h3>
                    <div className="space-y-2">
                      {logStats?.byComponent && Object.entries(logStats.byComponent).map(([component, count]) => (
                        <div key={component} className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            {getComponentIcon(component)}
                            <span className="text-sm capitalize">{component}</span>
                          </div>
                          <Badge variant="outline">{count}</Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  <div>
                    <h3 className="font-medium mb-3">Recent Error Patterns</h3>
                    <div className="space-y-2">
                      {filteredLogs.filter(log => log.level === 'error').slice(0, 5).map((log, index) => (
                        <div key={index} className="p-2 rounded bg-red-50 dark:bg-red-900/20 text-sm">
                          <div className="flex items-center gap-2">
                            <XCircle className="h-3 w-3 text-red-600" />
                            <span className="text-red-800 dark:text-red-200">{log.message}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}