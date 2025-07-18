import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Pin, 
  PinOff, 
  Eye, 
  EyeOff, 
  Settings, 
  Move, 
  Maximize2, 
  Minimize2,
  X
} from 'lucide-react';
import { DashboardWidget } from '@shared/schema';
import { useState } from 'react';

interface DashboardWidgetWrapperProps {
  widget: DashboardWidget;
  children: React.ReactNode;
  onPin?: (widgetId: string) => void;
  onHide?: (widgetId: string) => void;
  onSettings?: (widgetId: string) => void;
  onMove?: (widgetId: string, position: { x: number; y: number }) => void;
  onResize?: (widgetId: string, size: { width: number; height: number }) => void;
  isDragging?: boolean;
  isCustomizable?: boolean;
}

export function DashboardWidgetWrapper({
  widget,
  children,
  onPin,
  onHide,
  onSettings,
  onMove,
  onResize,
  isDragging = false,
  isCustomizable = true,
}: DashboardWidgetWrapperProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  const handlePin = () => {
    if (onPin) {
      onPin(widget.id);
    }
  };

  const handleHide = () => {
    if (onHide) {
      onHide(widget.id);
    }
  };

  const handleSettings = () => {
    if (onSettings) {
      onSettings(widget.id);
    }
  };

  const handleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  if (!widget.visible) {
    return null;
  }

  return (
    <div
      className={`relative transition-all duration-200 ${
        isDragging ? 'z-50 shadow-lg' : 'z-auto'
      } ${
        isExpanded ? 'fixed inset-4 z-50' : ''
      }`}
      style={{
        gridColumn: isExpanded ? 'unset' : `span ${widget.position.width}`,
        gridRow: isExpanded ? 'unset' : `span ${widget.position.height}`,
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <Card className={`h-full transition-all duration-200 ${
        widget.pinned ? 'ring-2 ring-blue-500' : ''
      } ${
        isDragging ? 'shadow-2xl rotate-1' : ''
      } ${
        isExpanded ? 'w-full h-full' : ''
      }`}>
        {/* Widget Header */}
        <div className={`flex items-center justify-between p-2 border-b transition-opacity duration-200 ${
          isCustomizable && (isHovered || widget.pinned) ? 'opacity-100' : 'opacity-0'
        }`}>
          <div className="flex items-center space-x-2">
            <div className="flex items-center space-x-1">
              {widget.pinned && (
                <Pin className="h-3 w-3 text-blue-600" />
              )}
              <span className="text-xs font-medium text-muted-foreground">
                {widget.title}
              </span>
            </div>
            <Badge variant="outline" className="text-xs">
              {widget.type}
            </Badge>
          </div>
          
          {isCustomizable && (
            <div className="flex items-center space-x-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleExpand}
                className="h-6 w-6 p-0"
              >
                {isExpanded ? (
                  <Minimize2 className="h-3 w-3" />
                ) : (
                  <Maximize2 className="h-3 w-3" />
                )}
              </Button>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={handlePin}
                className="h-6 w-6 p-0"
              >
                {widget.pinned ? (
                  <PinOff className="h-3 w-3" />
                ) : (
                  <Pin className="h-3 w-3" />
                )}
              </Button>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={handleSettings}
                className="h-6 w-6 p-0"
              >
                <Settings className="h-3 w-3" />
              </Button>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={handleHide}
                className="h-6 w-6 p-0"
              >
                <EyeOff className="h-3 w-3" />
              </Button>
            </div>
          )}
        </div>

        {/* Widget Content */}
        <div className={`${isExpanded ? 'h-full overflow-auto' : ''}`}>
          {children}
        </div>

        {/* Drag Handle */}
        {isCustomizable && (isHovered || isDragging) && (
          <div className="absolute top-1 left-1/2 transform -translate-x-1/2 cursor-move">
            <Move className="h-4 w-4 text-muted-foreground" />
          </div>
        )}

        {/* Resize Handle */}
        {isCustomizable && !isExpanded && (isHovered || isDragging) && (
          <div className="absolute bottom-1 right-1 cursor-se-resize">
            <div className="w-3 h-3 bg-muted-foreground opacity-50 rounded-sm"></div>
          </div>
        )}
      </Card>

      {/* Expanded Overlay */}
      {isExpanded && (
        <div 
          className="fixed inset-0 bg-black/50 z-40"
          onClick={handleExpand}
        />
      )}
    </div>
  );
}