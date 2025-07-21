import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Activity,
  TrendingUp,
  AlertTriangle,
  Info,
  CheckCircle,
  X,
  Filter,
  ExternalLink,
  MoreHorizontal,
  Clock,
  Maximize2
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatRelativeTime } from '@/lib/utils'
import { ActivityEvent } from '@/lib/api'

interface ActivityFeedProps {
  activities: ActivityEvent[]
}

type FilterType = 'all' | 'signals' | 'trades' | 'errors' | 'system'

const mockActivities: ActivityEvent[] = [
  {
    id: '1',
    type: 'signal',
    message: 'New EURUSD signal received from TradingBot Pro',
    timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    severity: 'info',
    data: { symbol: 'EURUSD', type: 'BUY', confidence: 0.85 }
  },
  {
    id: '2',
    type: 'trade',
    message: 'Trade executed: GBPJPY BUY 0.01 lots at 189.45',
    timestamp: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
    severity: 'success',
    data: { symbol: 'GBPJPY', profit: 15.50 }
  },
  {
    id: '3',
    type: 'system',
    message: 'AI Parser model updated to version 2.1.3',
    timestamp: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
    severity: 'info'
  },
  {
    id: '4',
    type: 'error',
    message: 'MT5 connection temporarily lost, retrying...',
    timestamp: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
    severity: 'warning',
    data: { retry_count: 2 }
  },
  {
    id: '5',
    type: 'trade',
    message: 'Stop loss triggered for USDJPY position',
    timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
    severity: 'error',
    data: { symbol: 'USDJPY', loss: -25.30 }
  }
]

export function ActivityFeed({ activities }: ActivityFeedProps) {
  const [filter, setFilter] = useState<FilterType>('all')
  const [isExpanded, setIsExpanded] = useState(false)
  
  // Use mock data if no activities provided
  const displayActivities = activities.length > 0 ? activities : mockActivities

  const getActivityIcon = (type: ActivityEvent['type'], severity: ActivityEvent['severity']) => {
    switch (type) {
      case 'signal':
        return <Activity className="w-4 h-4 text-blue-500" />
      case 'trade':
        return severity === 'success' ? 
          <CheckCircle className="w-4 h-4 text-green-500" /> :
          <TrendingUp className="w-4 h-4 text-orange-500" />
      case 'error':
        return <AlertTriangle className="w-4 h-4 text-red-500" />
      case 'system':
        return <Info className="w-4 h-4 text-cyan-500" />
      default:
        return <Clock className="w-4 h-4 text-muted-foreground" />
    }
  }

  const getSeverityBadge = (severity: ActivityEvent['severity']) => {
    switch (severity) {
      case 'success':
        return <Badge variant="success">Success</Badge>
      case 'warning':
        return <Badge variant="warning">Warning</Badge>
      case 'error':
        return <Badge variant="destructive">Error</Badge>
      default:
        return <Badge variant="default">Info</Badge>
    }
  }

  const filteredActivities = displayActivities.filter(activity => {
    if (filter === 'all') return true
    return activity.type === filter || (filter === 'errors' && activity.severity === 'error')
  })

  const filters: { type: FilterType; label: string; count: number }[] = [
    { type: 'all', label: 'All', count: displayActivities.length },
    { type: 'signals', label: 'Signals', count: displayActivities.filter(a => a.type === 'signal').length },
    { type: 'trades', label: 'Trades', count: displayActivities.filter(a => a.type === 'trade').length },
    { type: 'errors', label: 'Errors', count: displayActivities.filter(a => a.severity === 'error').length },
    { type: 'system', label: 'System', count: displayActivities.filter(a => a.type === 'system').length }
  ]

  return (
    <Card className="h-full">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary" />
              Live Activity Feed
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Real-time system events and trading activity
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              <Maximize2 className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-2 mt-4">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <div className="flex gap-1">
            {filters.map((filterOption) => (
              <Button
                key={filterOption.type}
                variant={filter === filterOption.type ? "default" : "ghost"}
                size="sm"
                onClick={() => setFilter(filterOption.type)}
                className="h-8"
              >
                {filterOption.label}
                {filterOption.count > 0 && (
                  <Badge variant="secondary" className="ml-2 text-xs">
                    {filterOption.count}
                  </Badge>
                )}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className={`space-y-3 ${isExpanded ? 'max-h-none' : 'max-h-96'} overflow-y-auto custom-scrollbar`}>
          <AnimatePresence mode="popLayout">
            {filteredActivities.map((activity, index) => (
              <motion.div
                key={activity.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2, delay: index * 0.05 }}
                className="glass-panel p-4 hover:bg-card/90 transition-all duration-200 cursor-pointer group"
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-0.5">
                    {getActivityIcon(activity.type, activity.severity)}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-foreground leading-5">
                          {activity.message}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          <time className="text-xs text-muted-foreground">
                            {formatRelativeTime(new Date(activity.timestamp))}
                          </time>
                          {getSeverityBadge(activity.severity)}
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                          <ExternalLink className="w-3 h-3" />
                        </Button>
                        <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                          <MoreHorizontal className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>

                    {/* Additional Data */}
                    {activity.data && (
                      <div className="mt-3 pt-3 border-t border-border/30">
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          {Object.entries(activity.data).map(([key, value]) => (
                            <div key={key} className="flex justify-between">
                              <span className="text-muted-foreground capitalize">
                                {key.replace('_', ' ')}:
                              </span>
                              <span className="font-mono text-foreground">
                                {typeof value === 'number' ? 
                                  (key.includes('profit') || key.includes('loss') ? 
                                    `$${value.toFixed(2)}` : value.toString()
                                  ) : value?.toString()
                                }
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {filteredActivities.length === 0 && (
            <div className="text-center py-8">
              <Activity className="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">
                No {filter === 'all' ? '' : filter} activities found
              </p>
            </div>
          )}
        </div>

        {/* Auto-refresh indicator */}
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-border/30 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <motion.div
              className="w-2 h-2 bg-green-500 rounded-full"
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
            <span>Auto-refreshing</span>
          </div>
          <span>{filteredActivities.length} events shown</span>
        </div>
      </CardContent>
    </Card>
  )
}