import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Layers3,
  TrendingUp,
  Play,
  Pause,
  Settings,
  FlaskConical,
  Plus,
  BarChart3,
  Target,
  Clock,
  AlertTriangle,
  CheckCircle
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { formatCurrency, formatRelativeTime } from '@/lib/utils'

interface Strategy {
  id: string
  name: string
  description: string
  status: 'active' | 'paused' | 'testing' | 'inactive'
  providers: string[]
  rules: {
    riskPerTrade: number
    maxDrawdown: number
    profitTarget: number
    stopLoss: number
  }
  performance: {
    totalTrades: number
    winRate: number
    profit: number
    maxDrawdown: number
  }
  lastBacktest: Date | null
  isRunning: boolean
}

const mockStrategies: Strategy[] = [
  {
    id: '1',
    name: 'Scalping Master',
    description: 'Fast scalping with tight stops',
    status: 'active',
    providers: ['TradingBot Pro', 'Alpha Trading'],
    rules: {
      riskPerTrade: 1.0,
      maxDrawdown: 10,
      profitTarget: 50,
      stopLoss: 25
    },
    performance: {
      totalTrades: 145,
      winRate: 78.5,
      profit: 1250.75,
      maxDrawdown: 5.2
    },
    lastBacktest: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
    isRunning: true
  },
  {
    id: '2',
    name: 'Swing Trading Pro',
    description: 'Medium-term swing positions',
    status: 'paused',
    providers: ['ForexSignals Elite'],
    rules: {
      riskPerTrade: 2.0,
      maxDrawdown: 15,
      profitTarget: 100,
      stopLoss: 50
    },
    performance: {
      totalTrades: 45,
      winRate: 65.5,
      profit: 789.50,
      maxDrawdown: 8.9
    },
    lastBacktest: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
    isRunning: false
  },
  {
    id: '3',
    name: 'News Trading',
    description: 'High-impact news events',
    status: 'testing',
    providers: ['Market News Feed'],
    rules: {
      riskPerTrade: 0.5,
      maxDrawdown: 5,
      profitTarget: 25,
      stopLoss: 15
    },
    performance: {
      totalTrades: 12,
      winRate: 83.3,
      profit: 156.25,
      maxDrawdown: 2.1
    },
    lastBacktest: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
    isRunning: false
  }
]

export function StrategyCards() {
  const [strategies] = useState<Strategy[]>(mockStrategies)

  const getStatusIcon = (status: Strategy['status']) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'paused':
        return <Pause className="w-4 h-4 text-yellow-500" />
      case 'testing':
        return <FlaskConical className="w-4 h-4 text-blue-500" />
      case 'inactive':
        return <AlertTriangle className="w-4 h-4 text-gray-500" />
      default:
        return <Clock className="w-4 h-4 text-muted-foreground" />
    }
  }

  const getStatusBadge = (status: Strategy['status']) => {
    switch (status) {
      case 'active':
        return <Badge variant="success">Active</Badge>
      case 'paused':
        return <Badge variant="warning">Paused</Badge>
      case 'testing':
        return <Badge variant="default">Testing</Badge>
      case 'inactive':
        return <Badge variant="outline">Inactive</Badge>
      default:
        return <Badge variant="outline">Unknown</Badge>
    }
  }

  const activeStrategies = strategies.filter(s => s.status === 'active').length

  return (
    <Card className="h-full">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Layers3 className="w-5 h-5 text-primary" />
              Trading Strategies
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Active rules and backtesting
            </p>
          </div>
          <Button size="sm" className="gap-2">
            <Plus className="w-4 h-4" />
            New Strategy
          </Button>
        </div>

        {/* Summary */}
        <div className="flex items-center gap-4 mt-4 p-3 bg-background/50 rounded-lg">
          <div className="text-center">
            <p className="text-lg font-bold text-foreground">{activeStrategies}</p>
            <p className="text-xs text-muted-foreground">Active</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-foreground">
              {strategies.reduce((sum, s) => sum + s.performance.totalTrades, 0)}
            </p>
            <p className="text-xs text-muted-foreground">Total Trades</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-green-500">
              {formatCurrency(strategies.reduce((sum, s) => sum + s.performance.profit, 0))}
            </p>
            <p className="text-xs text-muted-foreground">Total Profit</p>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-4 max-h-64 overflow-y-auto custom-scrollbar">
          {strategies.map((strategy, index) => (
            <motion.div
              key={strategy.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: index * 0.1 }}
              className="glass-panel p-4 hover:bg-card/90 transition-all duration-200 group"
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(strategy.status)}
                    <h4 className="font-semibold text-foreground">{strategy.name}</h4>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusBadge(strategy.status)}
                </div>
              </div>

              <p className="text-sm text-muted-foreground mb-3">
                {strategy.description}
              </p>

              {/* Providers */}
              <div className="mb-3">
                <p className="text-xs text-muted-foreground mb-1">Connected Providers:</p>
                <div className="flex flex-wrap gap-1">
                  {strategy.providers.map((provider) => (
                    <Badge key={provider} variant="outline" className="text-xs">
                      {provider}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Performance Grid */}
              <div className="grid grid-cols-2 gap-3 mb-3 text-xs">
                <div>
                  <p className="text-muted-foreground">Win Rate</p>
                  <p className="font-medium text-foreground">
                    {strategy.performance.winRate.toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">Profit</p>
                  <p className={`font-medium ${
                    strategy.performance.profit >= 0 ? 'text-green-500' : 'text-red-500'
                  }`}>
                    {formatCurrency(strategy.performance.profit)}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">Trades</p>
                  <p className="font-medium text-foreground">
                    {strategy.performance.totalTrades}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">Max DD</p>
                  <p className="font-medium text-foreground">
                    {strategy.performance.maxDrawdown.toFixed(1)}%
                  </p>
                </div>
              </div>

              {/* Risk Progress Bar */}
              <div className="space-y-2 mb-3">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Risk Usage</span>
                  <span className="text-foreground">
                    {strategy.performance.maxDrawdown.toFixed(1)}% / {strategy.rules.maxDrawdown}%
                  </span>
                </div>
                <Progress 
                  value={(strategy.performance.maxDrawdown / strategy.rules.maxDrawdown) * 100} 
                  className="h-1"
                />
              </div>

              {/* Last Backtest */}
              <div className="flex items-center justify-between text-xs text-muted-foreground mb-3">
                <span>Last backtest:</span>
                <span>
                  {strategy.lastBacktest ? 
                    formatRelativeTime(strategy.lastBacktest) : 
                    'Never'
                  }
                </span>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-between pt-3 border-t border-border/30">
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="sm" className="h-6 px-2 text-xs">
                    <Settings className="w-3 h-3 mr-1" />
                    Edit
                  </Button>
                  <Button variant="ghost" size="sm" className="h-6 px-2 text-xs">
                    <FlaskConical className="w-3 h-3 mr-1" />
                    Backtest
                  </Button>
                  <Button variant="ghost" size="sm" className="h-6 px-2 text-xs">
                    <BarChart3 className="w-3 h-3 mr-1" />
                    Stats
                  </Button>
                </div>
                
                <div className="flex items-center gap-1">
                  {strategy.isRunning && (
                    <motion.div
                      className="w-2 h-2 bg-green-500 rounded-full mr-2"
                      animate={{ scale: [1, 1.2, 1] }}
                      transition={{ duration: 2, repeat: Infinity }}
                    />
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-xs"
                  >
                    {strategy.status === 'active' ? (
                      <>
                        <Pause className="w-3 h-3 mr-1" />
                        Pause
                      </>
                    ) : (
                      <>
                        <Play className="w-3 h-3 mr-1" />
                        Start
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </motion.div>
          ))}

          {strategies.length === 0 && (
            <div className="text-center py-8">
              <Layers3 className="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground mb-3">
                No trading strategies configured
              </p>
              <Button size="sm">
                <Plus className="w-4 h-4 mr-2" />
                Create Your First Strategy
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}