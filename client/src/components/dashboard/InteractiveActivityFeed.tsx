import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import { 
  Activity, 
  AlertCircle, 
  CheckCircle, 
  XCircle, 
  TrendingUp, 
  Bot, 
  Users, 
  Settings,
  Play,
  RotateCcw,
  Eye,
  Clock,
  Filter
} from 'lucide-react';
import { ActivityEvent } from '@shared/schema';
import { apiRequest } from '@/lib/queryClient';
import { useState } from 'react';

interface InteractiveActivityFeedProps {
  events?: ActivityEvent[];
  isLoading?: boolean;
  onEventAction?: (eventId: string, action: string) => void;
}

export function InteractiveActivityFeed({ events = [], isLoading, onEventAction }: InteractiveActivityFeedProps) {
  const { toast } = useToast();
  const [selectedEvent, setSelectedEvent] = useState<ActivityEvent | null>(null);
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [loadingActions, setLoadingActions] = useState<Set<string>>(new Set());

  const handleEventAction = async (eventId: string, actionType: string) => {
    setLoadingActions(prev => new Set(prev).add(`${eventId}-${actionType}`));
    
    try {
      const response = await apiRequest(`/api/events/${eventId}/actions`, {
        method: 'POST',
        body: JSON.stringify({ action: actionType }),
      });

      if (response.success) {
        toast({
          title: 'Success',
          description: `Action "${actionType}" executed successfully`,
        });
        
        if (onEventAction) {
          onEventAction(eventId, actionType);
        }
      } else {
        throw new Error(response.message || 'Action failed');
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Action failed',
        variant: 'destructive',
      });
    } finally {
      setLoadingActions(prev => {
        const newSet = new Set(prev);
        newSet.delete(`${eventId}-${actionType}`);
        return newSet;
      });
    }
  };

  const getEventIcon = (type: string, level: string) => {
    switch (type) {
      case 'trade':
        return <TrendingUp className="h-4 w-4 text-blue-600" />;
      case 'signal':
        return <Bot className="h-4 w-4 text-purple-600" />;
      case 'provider':
        return <Users className="h-4 w-4 text-green-600" />;
      case 'system':
        return <Settings className="h-4 w-4 text-gray-600" />;
      case 'strategy':
        return <Play className="h-4 w-4 text-orange-600" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-600" />;
      default:
        return <Activity className="h-4 w-4 text-gray-600" />;
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'success':
        return 'bg-green-100 text-green-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-blue-100 text-blue-800';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString();
    } catch {
      return 'Invalid date';
    }
  };

  const filteredEvents = events.filter(event => {
    if (activeFilter === 'all') return true;
    return event.type === activeFilter;
  });

  const eventCounts = {
    all: events.length,
    trade: events.filter(e => e.type === 'trade').length,
    signal: events.filter(e => e.type === 'signal').length,
    error: events.filter(e => e.type === 'error').length,
    system: events.filter(e => e.type === 'system').length,
    provider: events.filter(e => e.type === 'provider').length,
    strategy: events.filter(e => e.type === 'strategy').length,
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Activity className="h-5 w-5" />
            <span>Activity Feed</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center space-x-3 p-3 rounded-lg border">
                <div className="h-8 w-8 bg-gray-200 rounded-full animate-pulse"></div>
                <div className="flex-1">
                  <div className="h-4 bg-gray-200 rounded animate-pulse w-32 mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded animate-pulse w-48"></div>
                </div>
                <div className="h-6 bg-gray-200 rounded animate-pulse w-16"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Activity className="h-5 w-5" />
            <span>Activity Feed</span>
          </div>
          <div className="flex items-center space-x-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <Badge variant="outline">{filteredEvents.length} events</Badge>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs value={activeFilter} onValueChange={setActiveFilter}>
          <TabsList className="grid w-full grid-cols-7">
            <TabsTrigger value="all">All ({eventCounts.all})</TabsTrigger>
            <TabsTrigger value="trade">Trades ({eventCounts.trade})</TabsTrigger>
            <TabsTrigger value="signal">Signals ({eventCounts.signal})</TabsTrigger>
            <TabsTrigger value="error">Errors ({eventCounts.error})</TabsTrigger>
            <TabsTrigger value="system">System ({eventCounts.system})</TabsTrigger>
            <TabsTrigger value="provider">Providers ({eventCounts.provider})</TabsTrigger>
            <TabsTrigger value="strategy">Strategy ({eventCounts.strategy})</TabsTrigger>
          </TabsList>
          
          <TabsContent value={activeFilter} className="mt-4">
            <ScrollArea className="h-[400px]">
              <div className="space-y-3">
                {filteredEvents.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No events found</p>
                  </div>
                ) : (
                  filteredEvents.map((event) => (
                    <div
                      key={event.id}
                      className={`flex items-center space-x-3 p-3 rounded-lg border transition-colors hover:bg-gray-50 ${
                        event.resolved ? 'opacity-60' : ''
                      }`}
                    >
                      <div className="flex-shrink-0">
                        {getEventIcon(event.type, event.level)}
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <h4 className="text-sm font-medium truncate">{event.title}</h4>
                          <Badge variant="secondary" className={`text-xs ${getLevelColor(event.level)}`}>
                            {event.level}
                          </Badge>
                          {event.resolved && (
                            <Badge variant="outline" className="text-xs">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Resolved
                            </Badge>
                          )}
                        </div>
                        
                        <p className="text-xs text-muted-foreground truncate">{event.description}</p>
                        
                        <div className="flex items-center space-x-2 mt-2 text-xs text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          <span>{formatTimestamp(event.timestamp)}</span>
                          {event.provider && (
                            <>
                              <span>•</span>
                              <span>{event.provider}</span>
                            </>
                          )}
                          {event.symbol && (
                            <>
                              <span>•</span>
                              <span>{event.symbol}</span>
                            </>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Dialog>
                          <DialogTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedEvent(event)}
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                          </DialogTrigger>
                          <DialogContent className="max-w-2xl">
                            <DialogHeader>
                              <DialogTitle className="flex items-center space-x-2">
                                {getEventIcon(event.type, event.level)}
                                <span>{event.title}</span>
                              </DialogTitle>
                            </DialogHeader>
                            <div className="space-y-4">
                              <div>
                                <h4 className="font-medium mb-2">Description</h4>
                                <p className="text-sm text-muted-foreground">{event.description}</p>
                              </div>
                              
                              {event.details && (
                                <div>
                                  <h4 className="font-medium mb-2">Details</h4>
                                  <pre className="text-xs bg-gray-100 p-3 rounded overflow-auto">
                                    {JSON.stringify(event.details, null, 2)}
                                  </pre>
                                </div>
                              )}
                              
                              <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                  <span className="font-medium">Timestamp:</span>
                                  <p className="text-muted-foreground">{formatTimestamp(event.timestamp)}</p>
                                </div>
                                <div>
                                  <span className="font-medium">Type:</span>
                                  <p className="text-muted-foreground">{event.type}</p>
                                </div>
                                {event.provider && (
                                  <div>
                                    <span className="font-medium">Provider:</span>
                                    <p className="text-muted-foreground">{event.provider}</p>
                                  </div>
                                )}
                                {event.symbol && (
                                  <div>
                                    <span className="font-medium">Symbol:</span>
                                    <p className="text-muted-foreground">{event.symbol}</p>
                                  </div>
                                )}
                              </div>
                            </div>
                          </DialogContent>
                        </Dialog>
                        
                        {event.actions && event.actions.length > 0 && !event.resolved && (
                          <div className="flex space-x-1">
                            {event.actions.map((action) => (
                              <Button
                                key={action.id}
                                variant="outline"
                                size="sm"
                                onClick={() => handleEventAction(event.id, action.type)}
                                disabled={loadingActions.has(`${event.id}-${action.type}`)}
                                className="text-xs"
                              >
                                {action.type === 'retry' && <RotateCcw className="h-3 w-3 mr-1" />}
                                {action.type === 'acknowledge' && <CheckCircle className="h-3 w-3 mr-1" />}
                                {action.type === 'ignore' && <XCircle className="h-3 w-3 mr-1" />}
                                {action.type === 'fix' && <Settings className="h-3 w-3 mr-1" />}
                                {action.label}
                              </Button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}