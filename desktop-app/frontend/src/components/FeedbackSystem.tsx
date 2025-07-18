import React, { useState, useEffect } from 'react';
import { CheckCircle, XCircle, AlertCircle, Clock, Zap, TrendingUp, Shield, Upload, Download } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';

interface FeedbackItem {
  id: string;
  type: 'import' | 'export' | 'test' | 'connection' | 'strategy' | 'provider';
  action: string;
  status: 'pending' | 'loading' | 'success' | 'error';
  message: string;
  progress?: number;
  details?: any;
  timestamp: Date;
  duration?: number;
}

interface FeedbackSystemProps {
  items: FeedbackItem[];
  onRetry?: (id: string) => void;
  onDismiss?: (id: string) => void;
}

export const FeedbackSystem: React.FC<FeedbackSystemProps> = ({
  items,
  onRetry,
  onDismiss
}) => {
  const [visibleItems, setVisibleItems] = useState<FeedbackItem[]>([]);

  useEffect(() => {
    // Show latest 5 items
    const sortedItems = [...items].sort((a, b) => 
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    ).slice(0, 5);
    setVisibleItems(sortedItems);
  }, [items]);

  const getTypeIcon = (type: FeedbackItem['type']) => {
    switch (type) {
      case 'import':
        return <Upload className="h-4 w-4" />;
      case 'export':
        return <Download className="h-4 w-4" />;
      case 'test':
        return <Zap className="h-4 w-4" />;
      case 'connection':
        return <Shield className="h-4 w-4" />;
      case 'strategy':
        return <TrendingUp className="h-4 w-4" />;
      case 'provider':
        return <Shield className="h-4 w-4" />;
      default:
        return <AlertCircle className="h-4 w-4" />;
    }
  };

  const getStatusIcon = (status: FeedbackItem['status']) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-4 w-4 text-gray-500" />;
      case 'loading':
        return <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />;
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: FeedbackItem['status']) => {
    switch (status) {
      case 'pending':
        return 'border-gray-200 bg-gray-50';
      case 'loading':
        return 'border-blue-200 bg-blue-50';
      case 'success':
        return 'border-green-200 bg-green-50';
      case 'error':
        return 'border-red-200 bg-red-50';
      default:
        return 'border-gray-200 bg-gray-50';
    }
  };

  const formatTimeAgo = (timestamp: Date) => {
    const now = new Date();
    const diff = now.getTime() - timestamp.getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    if (seconds > 0) return `${seconds}s ago`;
    return 'Just now';
  };

  const formatDuration = (duration?: number) => {
    if (!duration) return '';
    if (duration < 1000) return `${duration}ms`;
    return `${(duration / 1000).toFixed(1)}s`;
  };

  if (visibleItems.length === 0) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-md">
      <div className="space-y-2">
        {visibleItems.map((item) => (
          <Card key={item.id} className={`${getStatusColor(item.status)} border-l-4 shadow-lg`}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3 flex-1">
                  <div className="flex-shrink-0">
                    {getTypeIcon(item.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {getStatusIcon(item.status)}
                      <span className="font-medium text-sm">{item.action}</span>
                    </div>
                    <p className="text-xs text-gray-600 mb-1">{item.message}</p>
                    
                    {item.progress !== undefined && item.status === 'loading' && (
                      <div className="mb-2">
                        <Progress value={item.progress} className="h-1" />
                        <span className="text-xs text-gray-500">{item.progress}%</span>
                      </div>
                    )}
                    
                    {item.details && (
                      <div className="text-xs text-gray-500 mb-2">
                        {item.details.items && `${item.details.items} items processed`}
                        {item.details.errors && item.details.errors.length > 0 && (
                          <span className="text-red-600 ml-2">
                            {item.details.errors.length} errors
                          </span>
                        )}
                        {item.details.warnings && item.details.warnings.length > 0 && (
                          <span className="text-yellow-600 ml-2">
                            {item.details.warnings.length} warnings
                          </span>
                        )}
                      </div>
                    )}
                    
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span>{formatTimeAgo(item.timestamp)}</span>
                      {item.duration && (
                        <span>took {formatDuration(item.duration)}</span>
                      )}
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-1 ml-2">
                  {item.status === 'error' && onRetry && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onRetry(item.id)}
                      className="h-6 w-6 p-0"
                    >
                      <TrendingUp className="h-3 w-3" />
                    </Button>
                  )}
                  {onDismiss && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDismiss(item.id)}
                      className="h-6 w-6 p-0"
                    >
                      <XCircle className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

// Hook to manage feedback items
export const useFeedbackSystem = () => {
  const [items, setItems] = useState<FeedbackItem[]>([]);

  const addFeedback = (feedback: Omit<FeedbackItem, 'id' | 'timestamp'>) => {
    const newItem: FeedbackItem = {
      ...feedback,
      id: Date.now().toString(),
      timestamp: new Date()
    };
    setItems(prev => [...prev, newItem]);
    return newItem.id;
  };

  const updateFeedback = (id: string, updates: Partial<FeedbackItem>) => {
    setItems(prev => prev.map(item => 
      item.id === id ? { ...item, ...updates } : item
    ));
  };

  const removeFeedback = (id: string) => {
    setItems(prev => prev.filter(item => item.id !== id));
  };

  const clearAll = () => {
    setItems([]);
  };

  return {
    items,
    addFeedback,
    updateFeedback,
    removeFeedback,
    clearAll
  };
};