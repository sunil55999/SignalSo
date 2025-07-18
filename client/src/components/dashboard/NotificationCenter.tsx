import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/hooks/use-toast';
import { 
  Bell, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Info, 
  X,
  Settings,
  RotateCcw,
  ExternalLink,
  Clock,
  Filter
} from 'lucide-react';
import { Notification } from '@shared/schema';
import { apiRequest } from '@/lib/queryClient';
import { useState } from 'react';

interface NotificationCenterProps {
  notifications?: Notification[];
  isLoading?: boolean;
  onNotificationAction?: (notificationId: string, action: string) => void;
}

export function NotificationCenter({ 
  notifications = [], 
  isLoading, 
  onNotificationAction 
}: NotificationCenterProps) {
  const { toast } = useToast();
  const [loadingActions, setLoadingActions] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<'all' | 'unread' | 'high' | 'urgent'>('all');

  const handleNotificationAction = async (notificationId: string, actionType: string) => {
    const actionKey = `${notificationId}-${actionType}`;
    setLoadingActions(prev => new Set(prev).add(actionKey));
    
    try {
      let endpoint = '';
      let method = 'POST';
      let successMessage = '';

      switch (actionType) {
        case 'dismiss':
          endpoint = `/api/notifications/${notificationId}/dismiss`;
          successMessage = 'Notification dismissed';
          break;
        case 'resolve':
          endpoint = `/api/notifications/${notificationId}/resolve`;
          successMessage = 'Notification resolved';
          break;
        case 'retry':
          endpoint = `/api/notifications/${notificationId}/retry`;
          successMessage = 'Action retried';
          break;
        case 'fix':
          endpoint = `/api/notifications/${notificationId}/fix`;
          successMessage = 'Fix action initiated';
          break;
        default:
          throw new Error('Unknown action');
      }

      const response = await apiRequest(endpoint, { method });
      
      if (response.success) {
        toast({
          title: 'Success',
          description: successMessage,
        });
        
        if (onNotificationAction) {
          onNotificationAction(notificationId, actionType);
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
        newSet.delete(actionKey);
        return newSet;
      });
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-600" />;
      default:
        return <Info className="h-4 w-4 text-blue-600" />;
    }
  };

  const getNotificationColor = (type: string) => {
    switch (type) {
      case 'success':
        return 'bg-green-50 border-green-200';
      case 'warning':
        return 'bg-yellow-50 border-yellow-200';
      case 'error':
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-blue-50 border-blue-200';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diff = now.getTime() - date.getTime();
      
      if (diff < 60000) return 'Just now';
      if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
      if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
      return `${Math.floor(diff / 86400000)}d ago`;
    } catch {
      return 'Unknown';
    }
  };

  const filteredNotifications = notifications.filter(notification => {
    switch (filter) {
      case 'unread':
        return !notification.read;
      case 'high':
        return notification.priority === 'high';
      case 'urgent':
        return notification.priority === 'urgent';
      default:
        return true;
    }
  });

  const unreadCount = notifications.filter(n => !n.read).length;
  const urgentCount = notifications.filter(n => n.priority === 'urgent').length;

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Bell className="h-5 w-5" />
            <span>Notifications</span>
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
            <Bell className="h-5 w-5" />
            <span>Notifications</span>
            {unreadCount > 0 && (
              <Badge variant="destructive" className="text-xs">
                {unreadCount}
              </Badge>
            )}
            {urgentCount > 0 && (
              <Badge variant="destructive" className="text-xs animate-pulse">
                {urgentCount} urgent
              </Badge>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as any)}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="all">All ({notifications.length})</option>
              <option value="unread">Unread ({unreadCount})</option>
              <option value="high">High Priority</option>
              <option value="urgent">Urgent</option>
            </select>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px]">
          <div className="space-y-3">
            {filteredNotifications.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No notifications</p>
              </div>
            ) : (
              filteredNotifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`p-3 rounded-lg border transition-colors ${
                    getNotificationColor(notification.type)
                  } ${
                    !notification.read ? 'shadow-sm' : 'opacity-75'
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 mt-1">
                      {getNotificationIcon(notification.type)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <h4 className="text-sm font-medium truncate">
                          {notification.title}
                        </h4>
                        <Badge variant="outline" className={`text-xs ${getPriorityColor(notification.priority)}`}>
                          {notification.priority}
                        </Badge>
                        {!notification.read && (
                          <div className="h-2 w-2 bg-blue-600 rounded-full"></div>
                        )}
                      </div>
                      
                      <p className="text-sm text-gray-700 mb-2">
                        {notification.message}
                      </p>
                      
                      <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        <span>{formatTimestamp(notification.timestamp)}</span>
                        <span>•</span>
                        <span>{notification.category}</span>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-1">
                      {!notification.dismissed && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleNotificationAction(notification.id, 'dismiss')}
                          disabled={loadingActions.has(`${notification.id}-dismiss`)}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </div>
                  
                  {/* Action Buttons */}
                  {notification.actions && notification.actions.length > 0 && (
                    <div className="flex items-center space-x-2 mt-3 pt-3 border-t">
                      {notification.actions.map((action) => (
                        <Button
                          key={action.id}
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            if (action.url) {
                              window.open(action.url, '_blank');
                            } else {
                              handleNotificationAction(notification.id, action.type);
                            }
                          }}
                          disabled={loadingActions.has(`${notification.id}-${action.type}`)}
                          className="text-xs"
                        >
                          {action.type === 'resolve' && <CheckCircle className="h-3 w-3 mr-1" />}
                          {action.type === 'fix' && <Settings className="h-3 w-3 mr-1" />}
                          {action.type === 'retry' && <RotateCcw className="h-3 w-3 mr-1" />}
                          {action.type === 'dismiss' && <X className="h-3 w-3 mr-1" />}
                          {action.url && <ExternalLink className="h-3 w-3 mr-1" />}
                          {action.label}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}