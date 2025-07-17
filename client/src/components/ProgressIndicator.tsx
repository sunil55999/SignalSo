import React from 'react';
import { CheckCircle, Clock, AlertCircle } from 'lucide-react';

interface ProgressIndicatorProps {
  status: 'pending' | 'loading' | 'success' | 'error';
  message: string;
  progress?: number;
  details?: string;
}

export const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  status,
  message,
  progress,
  details
}) => {
  const getStatusIcon = () => {
    switch (status) {
      case 'pending':
        return <Clock className="h-4 w-4 text-gray-500" />;
      case 'loading':
        return <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />;
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'pending':
        return 'text-gray-600';
      case 'loading':
        return 'text-blue-600';
      case 'success':
        return 'text-green-600';
      case 'error':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 rounded-lg border">
      <div className="flex-shrink-0">
        {getStatusIcon()}
      </div>
      <div className="flex-1">
        <div className={`font-medium ${getStatusColor()}`}>
          {message}
        </div>
        {details && (
          <div className="text-sm text-gray-500 mt-1">
            {details}
          </div>
        )}
        {progress !== undefined && status === 'loading' && (
          <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>
    </div>
  );
};