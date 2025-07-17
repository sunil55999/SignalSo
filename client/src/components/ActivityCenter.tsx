import React, { useState } from 'react';
import { Bell, Clock, CheckCircle, AlertCircle, XCircle, Filter, Search, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface Activity {
  id: string;
  type: 'import' | 'export' | 'test' | 'error' | 'success';
  title: string;
  description: string;
  timestamp: Date;
  status: 'pending' | 'completed' | 'failed';
  details?: {
    fileName?: string;
    itemCount?: number;
    errors?: string[];
    warnings?: string[];
  };
}

const mockActivities: Activity[] = [
  {
    id: '1',
    type: 'import',
    title: 'Signals Import',
    description: 'Imported 25 signals from signals_batch_1.csv',
    timestamp: new Date(Date.now() - 2 * 60 * 1000),
    status: 'completed',
    details: {
      fileName: 'signals_batch_1.csv',
      itemCount: 25,
      warnings: ['2 duplicate signals ignored']
    }
  },
  {
    id: '2',
    type: 'test',
    title: 'Strategy Test',
    description: 'Backtested EUR/USD scalping strategy',
    timestamp: new Date(Date.now() - 15 * 60 * 1000),
    status: 'completed',
    details: {
      itemCount: 100
    }
  },
  {
    id: '3',
    type: 'error',
    title: 'Connection Failed',
    description: 'MT5 connection lost during trade execution',
    timestamp: new Date(Date.now() - 30 * 60 * 1000),
    status: 'failed',
    details: {
      errors: ['Connection timeout', 'Retry limit exceeded']
    }
  },
  {
    id: '4',
    type: 'export',
    title: 'Provider Export',
    description: 'Exported 8 provider configurations',
    timestamp: new Date(Date.now() - 60 * 60 * 1000),
    status: 'completed',
    details: {
      fileName: 'providers_backup.json',
      itemCount: 8
    }
  }
];

export const ActivityCenter = () => {
  const [activities, setActivities] = useState<Activity[]>(mockActivities);
  const [filter, setFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const filteredActivities = activities.filter(activity => {
    const matchesFilter = filter === 'all' || activity.type === filter;
    const matchesSearch = activity.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         activity.description.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const getActivityIcon = (type: Activity['type'], status: Activity['status']) => {
    if (status === 'pending') return <Clock className="h-4 w-4 text-yellow-500" />;
    if (status === 'failed') return <XCircle className="h-4 w-4 text-red-500" />;
    
    switch (type) {
      case 'import':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'export':
        return <CheckCircle className="h-4 w-4 text-blue-500" />;
      case 'test':
        return <CheckCircle className="h-4 w-4 text-purple-500" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      default:
        return <Bell className="h-4 w-4 text-gray-500" />;
    }
  };

  const getActivityBadge = (type: Activity['type']) => {
    const badges = {
      import: { label: 'Import', variant: 'secondary' as const },
      export: { label: 'Export', variant: 'outline' as const },
      test: { label: 'Test', variant: 'secondary' as const },
      error: { label: 'Error', variant: 'destructive' as const },
      success: { label: 'Success', variant: 'default' as const }
    };
    return badges[type] || { label: 'Unknown', variant: 'secondary' as const };
  };

  const handleRetry = (activityId: string) => {
    setActivities(prev => prev.map(activity => 
      activity.id === activityId 
        ? { ...activity, status: 'pending' as const }
        : activity
    ));
  };

  const handleUndo = (activityId: string) => {
    // Implement undo logic
    console.log('Undo activity:', activityId);
  };

  const formatTimeAgo = (timestamp: Date) => {
    const now = new Date();
    const diff = now.getTime() - timestamp.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'Just now';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bell className="h-5 w-5" />
          Activity Center
        </CardTitle>
        
        {/* Filters and Search */}
        <div className="flex items-center gap-4 mt-4">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-500" />
            <Select value={filter} onValueChange={setFilter}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Filter" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="import">Import</SelectItem>
                <SelectItem value="export">Export</SelectItem>
                <SelectItem value="test">Test</SelectItem>
                <SelectItem value="error">Error</SelectItem>
                <SelectItem value="success">Success</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div className="flex items-center gap-2 flex-1">
            <Search className="h-4 w-4 text-gray-500" />
            <Input
              placeholder="Search activities..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-sm"
            />
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="space-y-4 max-h-96 overflow-y-auto">
          {filteredActivities.map((activity) => (
            <div
              key={activity.id}
              className="flex items-start gap-3 p-3 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <div className="flex-shrink-0 mt-0.5">
                {getActivityIcon(activity.type, activity.status)}
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="font-medium text-sm">{activity.title}</h4>
                  <Badge variant={getActivityBadge(activity.type).variant} className="text-xs">
                    {getActivityBadge(activity.type).label}
                  </Badge>
                </div>
                
                <p className="text-sm text-gray-600 mb-2">{activity.description}</p>
                
                {activity.details && (
                  <div className="text-xs text-gray-500 space-y-1">
                    {activity.details.fileName && (
                      <div>File: {activity.details.fileName}</div>
                    )}
                    {activity.details.itemCount && (
                      <div>Items: {activity.details.itemCount}</div>
                    )}
                    {activity.details.errors && activity.details.errors.length > 0 && (
                      <div className="text-red-600">
                        Errors: {activity.details.errors.join(', ')}
                      </div>
                    )}
                    {activity.details.warnings && activity.details.warnings.length > 0 && (
                      <div className="text-yellow-600">
                        Warnings: {activity.details.warnings.join(', ')}
                      </div>
                    )}
                  </div>
                )}
                
                <div className="flex items-center justify-between mt-2">
                  <span className="text-xs text-gray-500">
                    {formatTimeAgo(activity.timestamp)}
                  </span>
                  
                  <div className="flex items-center gap-2">
                    {activity.status === 'failed' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRetry(activity.id)}
                        className="h-6 px-2 text-xs"
                      >
                        <RotateCcw className="h-3 w-3 mr-1" />
                        Retry
                      </Button>
                    )}
                    {activity.type === 'import' && activity.status === 'completed' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleUndo(activity.id)}
                        className="h-6 px-2 text-xs"
                      >
                        Undo
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
          
          {filteredActivities.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <Bell className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No activities found</p>
              <p className="text-sm">Try adjusting your filters or search term</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};