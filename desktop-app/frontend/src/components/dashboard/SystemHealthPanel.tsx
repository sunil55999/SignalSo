import { motion } from 'framer-motion'
import {
  Database,
  Brain,
  Zap,
  MessageSquare,
  Store,
  Wifi,
  AlertTriangle,
  CheckCircle,
  Clock
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { SystemStatus } from '@/lib/api'

interface SystemHealthPanelProps {
  systemStatus?: SystemStatus
  isLoading?: boolean
}

interface ServiceStatus {
  name: string
  status: 'online' | 'offline' | 'warning' | 'configuring'
  icon: typeof Database
  description: string
  details?: string
  progress?: number
}

export function SystemHealthPanel({ systemStatus, isLoading }: SystemHealthPanelProps) {
  const services: ServiceStatus[] = [
    {
      name: 'Database',
      status: systemStatus?.components.database === 'connected' ? 'online' : 'offline',
      icon: Database,
      description: 'SQLite Local Storage',
      details: 'All data stored locally'
    },
    {
      name: 'AI Parser',
      status: systemStatus?.components.ai_parser === 'ready' ? 'online' : 'configuring',
      icon: Brain,
      description: 'Signal Processing Engine',
      details: 'LLM + Regex hybrid',
      progress: systemStatus?.components.ai_parser === 'ready' ? 100 : 75
    },
    {
      name: 'MT5 Bridge',
      status: systemStatus?.components.mt5_bridge === 'connected' ? 'online' : 'warning',
      icon: Zap,
      description: 'Trading Platform Connection',
      details: 'Desktop socket bridge',
      progress: 45
    },
    {
      name: 'Telegram API',
      status: systemStatus?.components.telegram === 'connected' ? 'online' : 'warning',
      icon: MessageSquare,
      description: 'Signal Source Integration',
      details: 'Multi-channel monitoring'
    },
    {
      name: 'Marketplace',
      status: 'configuring',
      icon: Store,
      description: 'Plugin & Strategy Store',
      details: 'Desktop plugin support'
    },
    {
      name: 'Network',
      status: 'online',
      icon: Wifi,
      description: 'API Connection',
      details: 'Replit backend connected'
    }
  ]

  const getStatusIcon = (status: ServiceStatus['status']) => {
    switch (status) {
      case 'online':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />
      case 'configuring':
        return <Clock className="w-4 h-4 text-blue-500" />
      default:
        return <AlertTriangle className="w-4 h-4 text-red-500" />
    }
  }

  const getStatusBadge = (status: ServiceStatus['status']) => {
    switch (status) {
      case 'online':
        return <Badge variant="success">Online</Badge>
      case 'warning':
        return <Badge variant="warning">Setup Required</Badge>
      case 'configuring':
        return <Badge variant="default">Configuring</Badge>
      default:
        return <Badge variant="destructive">Offline</Badge>
    }
  }

  if (isLoading) {
    return (
      <div className="glass-card p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-muted rounded mb-4 w-48"></div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-20 bg-muted rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const onlineCount = services.filter(s => s.status === 'online').length
  const totalServices = services.length
  const healthPercentage = Math.round((onlineCount / totalServices) * 100)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-6"
    >
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-foreground">System Health</h3>
          <p className="text-sm text-muted-foreground">
            Real-time service status monitoring
          </p>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-2xl font-bold text-foreground">{healthPercentage}%</div>
            <div className="text-xs text-muted-foreground">System Health</div>
          </div>
          <div className="w-16 h-16 relative">
            <svg className="w-16 h-16 transform -rotate-90" viewBox="0 0 36 36">
              <path
                className="text-muted stroke-current"
                strokeWidth="3"
                fill="transparent"
                d="M18 2.0845
                  a 15.9155 15.9155 0 0 1 0 31.831
                  a 15.9155 15.9155 0 0 1 0 -31.831"
              />
              <motion.path
                className="text-primary stroke-current"
                strokeWidth="3"
                strokeLinecap="round"
                fill="transparent"
                initial={{ strokeDasharray: "0 100" }}
                animate={{ strokeDasharray: `${healthPercentage} 100` }}
                transition={{ duration: 1, delay: 0.5 }}
                d="M18 2.0845
                  a 15.9155 15.9155 0 0 1 0 31.831
                  a 15.9155 15.9155 0 0 1 0 -31.831"
              />
            </svg>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {services.map((service, index) => (
          <motion.div
            key={service.name}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3, delay: index * 0.1 }}
            className="glass-panel p-4 hover:bg-card/90 transition-all duration-200 group cursor-pointer"
          >
            <div className="flex flex-col items-center text-center space-y-2">
              <div className="relative">
                <service.icon className="w-8 h-8 text-muted-foreground group-hover:text-foreground transition-colors" />
                <div className="absolute -bottom-1 -right-1">
                  {getStatusIcon(service.status)}
                </div>
                
                {service.status === 'online' && (
                  <motion.div
                    className="absolute inset-0 border-2 border-green-500/30 rounded-full"
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  />
                )}
              </div>
              
              <div className="space-y-1">
                <h4 className="text-sm font-medium text-foreground">{service.name}</h4>
                <p className="text-xs text-muted-foreground">{service.description}</p>
                {getStatusBadge(service.status)}
              </div>
              
              {service.progress !== undefined && (
                <div className="w-full mt-2">
                  <Progress value={service.progress} className="h-1" />
                  <p className="text-xs text-muted-foreground mt-1">
                    {service.progress}% configured
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        ))}
      </div>

      {/* System Summary */}
      <div className="mt-6 pt-4 border-t border-border/30 flex items-center justify-between text-sm">
        <div className="flex items-center gap-4 text-muted-foreground">
          <span>{onlineCount}/{totalServices} services online</span>
          <span>•</span>
          <span>Last updated: {new Date().toLocaleTimeString()}</span>
        </div>
        
        <motion.div
          className="flex items-center gap-2 text-green-500"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
          <span>Auto-monitoring active</span>
        </motion.div>
      </div>
    </motion.div>
  )
}