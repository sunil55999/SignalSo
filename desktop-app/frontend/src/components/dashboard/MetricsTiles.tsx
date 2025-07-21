import { motion } from 'framer-motion'
import {
  Trophy,
  Target,
  DollarSign,
  Activity,
  Zap,
  TrendingUp,
  BarChart3,
  Clock
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { formatCurrency, formatPercentage } from '@/lib/utils'
import { SystemStatus } from '@/lib/api'

interface MetricsTilesProps {
  systemStatus?: SystemStatus
}

interface MetricTile {
  title: string
  value: string | number
  change?: number
  trend?: 'up' | 'down' | 'neutral'
  icon: typeof Trophy
  description: string
  color: string
  format?: 'currency' | 'percentage' | 'number' | 'time'
  badge?: string
}

export function MetricsTiles({ systemStatus }: MetricsTilesProps) {
  const stats = systemStatus?.stats

  const metrics: MetricTile[] = [
    {
      title: 'Win Rate',
      value: stats?.win_rate || 0,
      change: 5.2,
      trend: 'up',
      icon: Trophy,
      description: 'Trading success rate',
      color: 'text-yellow-500',
      format: 'percentage'
    },
    {
      title: 'Trades Executed',
      value: stats?.active_trades || 0,
      change: 12,
      trend: 'up',
      icon: Target,
      description: 'Total completed trades',
      color: 'text-blue-500',
      format: 'number',
      badge: 'Today'
    },
    {
      title: "Today's PnL",
      value: stats?.total_profit || 0,
      change: 15.8,
      trend: 'up',
      icon: DollarSign,
      description: 'Profit and loss today',
      color: 'text-green-500',
      format: 'currency'
    },
    {
      title: 'Signal Parsing',
      value: 98.5,
      change: -1.2,
      trend: 'down',
      icon: Activity,
      description: 'AI processing accuracy',
      color: 'text-purple-500',
      format: 'percentage'
    },
    {
      title: 'Execution Speed',
      value: 245,
      change: -15,
      trend: 'up',
      icon: Zap,
      description: 'Average order latency',
      color: 'text-orange-500',
      format: 'time',
      badge: 'ms'
    },
    {
      title: 'Active Signals',
      value: stats?.signals_today || 0,
      change: 8,
      trend: 'up',
      icon: BarChart3,
      description: 'Signals processed today',
      color: 'text-cyan-500',
      format: 'number'
    }
  ]

  const formatValue = (value: string | number, format?: string, badge?: string) => {
    const numValue = typeof value === 'string' ? parseFloat(value) : value

    switch (format) {
      case 'currency':
        return formatCurrency(numValue)
      case 'percentage':
        return `${numValue.toFixed(1)}%`
      case 'time':
        return `${numValue}${badge || 'ms'}`
      case 'number':
        return numValue.toLocaleString()
      default:
        return value.toString()
    }
  }

  const getTrendIcon = (trend?: 'up' | 'down' | 'neutral') => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-3 h-3 text-green-500" />
      case 'down':
        return <TrendingUp className="w-3 h-3 text-red-500 rotate-180" />
      default:
        return <Clock className="w-3 h-3 text-muted-foreground" />
    }
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
      {metrics.map((metric, index) => (
        <motion.div
          key={metric.title}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: index * 0.1 }}
        >
          <Card className="metric-card group">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-3">
                <div className={`p-2 rounded-lg bg-background/50 ${metric.color}`}>
                  <metric.icon className="w-5 h-5" />
                </div>
                {metric.badge && (
                  <Badge variant="outline" className="text-xs">
                    {metric.badge}
                  </Badge>
                )}
              </div>

              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">{metric.title}</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-bold text-foreground">
                    {formatValue(metric.value, metric.format, metric.badge)}
                  </span>
                </div>
                
                {metric.change !== undefined && (
                  <div className="flex items-center gap-1">
                    {getTrendIcon(metric.trend)}
                    <span
                      className={`text-xs font-medium ${
                        metric.trend === 'up' ? 'text-green-500' : 
                        metric.trend === 'down' ? 'text-red-500' : 
                        'text-muted-foreground'
                      }`}
                    >
                      {Math.abs(metric.change)}%
                    </span>
                  </div>
                )}
              </div>

              <div className="mt-3 pt-3 border-t border-border/30">
                <p className="text-xs text-muted-foreground">
                  {metric.description}
                </p>
              </div>

              {/* Mini chart placeholder - would be actual chart in real implementation */}
              <div className="mt-2 h-8 flex items-end space-x-1 opacity-30 group-hover:opacity-70 transition-opacity">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div
                    key={i}
                    className={`w-2 bg-gradient-to-t rounded-sm ${metric.color.replace('text-', 'from-')} to-transparent`}
                    style={{
                      height: `${Math.random() * 100}%`,
                      minHeight: '4px'
                    }}
                  />
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </div>
  )
}