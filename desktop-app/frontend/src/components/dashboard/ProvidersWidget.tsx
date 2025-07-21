import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Satellite,
  MessageSquare,
  Globe,
  Rss,
  Play,
  Pause,
  Settings,
  TestTube,
  Plus,
  MoreVertical,
  CheckCircle,
  AlertTriangle,
  Clock
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { formatRelativeTime } from '@/lib/utils'

interface Provider {
  id: string
  name: string
  type: 'telegram' | 'webhook' | 'api' | 'rss'
  status: 'active' | 'paused' | 'error' | 'configuring'
  lastSignal: Date | null
  signalsToday: number
  winRate: number
  isConnected: boolean
  performance: number
}

const mockProviders: Provider[] = [
  {
    id: '1',
    name: 'TradingBot Pro',
    type: 'telegram',
    status: 'active',
    lastSignal: new Date(Date.now() - 5 * 60 * 1000),
    signalsToday: 12,
    winRate: 78.5,
    isConnected: true,
    performance: 85
  },
  {
    id: '2',
    name: 'ForexSignals Elite',
    type: 'telegram',
    status: 'paused',
    lastSignal: new Date(Date.now() - 2 * 60 * 60 * 1000),
    signalsToday: 5,
    winRate: 65.2,
    isConnected: true,
    performance: 72
  },
  {
    id: '3',
    name: 'Alpha Trading API',
    type: 'api',
    status: 'error',
    lastSignal: null,
    signalsToday: 0,
    winRate: 0,
    isConnected: false,
    performance: 0
  },
  {
    id: '4',
    name: 'Market News Feed',
    type: 'rss',
    status: 'configuring',
    lastSignal: new Date(Date.now() - 30 * 60 * 1000),
    signalsToday: 3,
    winRate: 45.8,
    isConnected: true,
    performance: 55
  }
]

export function ProvidersWidget() {
  const [providers] = useState<Provider[]>(mockProviders)

  const getProviderIcon = (type: Provider['type']) => {
    switch (type) {
      case 'telegram':
        return <MessageSquare className="w-4 h-4" />
      case 'api':
        return <Globe className="w-4 h-4" />
      case 'webhook':
        return <Satellite className="w-4 h-4" />
      case 'rss':
        return <Rss className="w-4 h-4" />
      default:
        return <Satellite className="w-4 h-4" />
    }
  }

  const getStatusIcon = (status: Provider['status'], isConnected: boolean) => {
    if (!isConnected) return <AlertTriangle className="w-3 h-3 text-red-500" />
    
    switch (status) {
      case 'active':
        return <CheckCircle className="w-3 h-3 text-green-500" />
      case 'paused':
        return <Pause className="w-3 h-3 text-yellow-500" />
      case 'error':
        return <AlertTriangle className="w-3 h-3 text-red-500" />
      case 'configuring':
        return <Clock className="w-3 h-3 text-blue-500" />
      default:
        return <AlertTriangle className="w-3 h-3 text-gray-500" />
    }
  }

  const getStatusBadge = (status: Provider['status']) => {
    switch (status) {
      case 'active':
        return <Badge variant="success">Active</Badge>
      case 'paused':
        return <Badge variant="warning">Paused</Badge>
      case 'error':
        return <Badge variant="destructive">Error</Badge>
      case 'configuring':
        return <Badge variant="default">Setup</Badge>
      default:
        return <Badge variant="outline">Unknown</Badge>
    }
  }

  const activeProviders = providers.filter(p => p.status === 'active').length
  const totalSignals = providers.reduce((sum, p) => sum + p.signalsToday, 0)

  return (
    <Card className="h-full">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Satellite className="w-5 h-5 text-primary" />
              Signal Providers
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Connected sources and performance
            </p>
          </div>
          <Button size="sm" className="gap-2">
            <Plus className="w-4 h-4" />
            Add Provider
          </Button>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-4 mt-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-foreground">{activeProviders}</p>
            <p className="text-xs text-muted-foreground">Active</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-foreground">{totalSignals}</p>
            <p className="text-xs text-muted-foreground">Today</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-foreground">
              {providers.length > 0 ? 
                Math.round(providers.reduce((sum, p) => sum + p.winRate, 0) / providers.length) : 0}%
            </p>
            <p className="text-xs text-muted-foreground">Avg Win</p>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-3 max-h-64 overflow-y-auto custom-scrollbar">
          {providers.map((provider, index) => (
            <motion.div
              key={provider.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: index * 0.1 }}
              className="glass-panel p-3 hover:bg-card/90 transition-all duration-200 group"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    {getProviderIcon(provider.type)}
                    <span className="font-medium text-foreground">{provider.name}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    {getStatusIcon(provider.status, provider.isConnected)}
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  {getStatusBadge(provider.status)}
                  <Button variant="ghost" size="sm" className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100">
                    <MoreVertical className="w-3 h-3" />
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 mb-3 text-xs">
                <div>
                  <p className="text-muted-foreground">Last Signal</p>
                  <p className="font-medium text-foreground">
                    {provider.lastSignal ? formatRelativeTime(provider.lastSignal) : 'None'}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">Today</p>
                  <p className="font-medium text-foreground">{provider.signalsToday}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Win Rate</p>
                  <p className="font-medium text-foreground">{provider.winRate.toFixed(1)}%</p>
                </div>
              </div>

              {/* Performance Bar */}
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Performance</span>
                  <span className="text-foreground">{provider.performance}%</span>
                </div>
                <Progress value={provider.performance} className="h-1" />
              </div>

              {/* Quick Actions */}
              <div className="flex items-center justify-between mt-3 pt-3 border-t border-border/30">
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="sm" className="h-6 px-2 text-xs">
                    <TestTube className="w-3 h-3 mr-1" />
                    Test
                  </Button>
                  <Button variant="ghost" size="sm" className="h-6 px-2 text-xs">
                    <Settings className="w-3 h-3 mr-1" />
                    Edit
                  </Button>
                </div>
                
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs"
                  disabled={!provider.isConnected}
                >
                  {provider.status === 'active' ? (
                    <>
                      <Pause className="w-3 h-3 mr-1" />
                      Pause
                    </>
                  ) : (
                    <>
                      <Play className="w-3 h-3 mr-1" />
                      Resume
                    </>
                  )}
                </Button>
              </div>
            </motion.div>
          ))}

          {providers.length === 0 && (
            <div className="text-center py-8">
              <Satellite className="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground mb-3">
                No signal providers configured
              </p>
              <Button size="sm">
                <Plus className="w-4 h-4 mr-2" />
                Add Your First Provider
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}