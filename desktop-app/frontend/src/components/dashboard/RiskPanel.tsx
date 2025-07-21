import { motion } from 'framer-motion'
import {
  Shield,
  AlertTriangle,
  TrendingDown,
  Target,
  DollarSign,
  BarChart3,
  Activity,
  Settings
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { formatCurrency, formatPercentage } from '@/lib/utils'

interface RiskMetric {
  label: string
  current: number
  limit: number
  status: 'safe' | 'warning' | 'critical'
  icon: typeof Shield
  format: 'currency' | 'percentage' | 'number'
}

export function RiskPanel() {
  // Mock risk data - in real app this would come from props or API
  const riskMetrics: RiskMetric[] = [
    {
      label: 'Account Drawdown',
      current: 5.2,
      limit: 15.0,
      status: 'safe',
      icon: TrendingDown,
      format: 'percentage'
    },
    {
      label: 'Daily Loss',
      current: 125.50,
      limit: 500.00,
      status: 'safe',
      icon: DollarSign,
      format: 'currency'
    },
    {
      label: 'Open Positions',
      current: 3,
      limit: 10,
      status: 'safe',
      icon: Target,
      format: 'number'
    },
    {
      label: 'Margin Usage',
      current: 25.8,
      limit: 80.0,
      status: 'safe',
      icon: BarChart3,
      format: 'percentage'
    }
  ]

  const complianceRules = [
    { rule: 'Max 5% risk per trade', status: 'active', violation: false },
    { rule: 'No overnight positions', status: 'active', violation: false },
    { rule: 'Daily loss limit $500', status: 'active', violation: false },
    { rule: 'Max 10 concurrent trades', status: 'active', violation: false }
  ]

  const formatValue = (value: number, format: 'currency' | 'percentage' | 'number') => {
    switch (format) {
      case 'currency':
        return formatCurrency(value)
      case 'percentage':
        return `${value.toFixed(1)}%`
      case 'number':
        return value.toString()
      default:
        return value.toString()
    }
  }

  const getStatusColor = (status: 'safe' | 'warning' | 'critical') => {
    switch (status) {
      case 'safe':
        return 'text-green-500'
      case 'warning':
        return 'text-yellow-500'
      case 'critical':
        return 'text-red-500'
      default:
        return 'text-muted-foreground'
    }
  }

  const getProgressColor = (status: 'safe' | 'warning' | 'critical') => {
    switch (status) {
      case 'safe':
        return 'bg-green-500'
      case 'warning':
        return 'bg-yellow-500'
      case 'critical':
        return 'bg-red-500'
      default:
        return 'bg-muted'
    }
  }

  const overallRiskScore = Math.round(
    riskMetrics.reduce((sum, metric) => sum + (metric.current / metric.limit) * 100, 0) / riskMetrics.length
  )

  const getRiskLevel = (score: number) => {
    if (score < 30) return { level: 'Conservative', color: 'text-green-500', badge: 'success' as const }
    if (score < 60) return { level: 'Moderate', color: 'text-yellow-500', badge: 'warning' as const }
    return { level: 'Aggressive', color: 'text-red-500', badge: 'destructive' as const }
  }

  const riskAssessment = getRiskLevel(overallRiskScore)

  return (
    <Card className="h-full">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-primary" />
              Risk & Compliance
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Live risk exposure monitoring
            </p>
          </div>
          <Button variant="ghost" size="sm">
            <Settings className="w-4 h-4" />
          </Button>
        </div>

        {/* Overall Risk Score */}
        <div className="mt-4 p-4 bg-background/50 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-muted-foreground">Risk Level</span>
            <Badge variant={riskAssessment.badge}>{riskAssessment.level}</Badge>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <Progress value={overallRiskScore} className="h-2" />
            </div>
            <span className={`text-lg font-bold ${riskAssessment.color}`}>
              {overallRiskScore}%
            </span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Risk Metrics */}
        <div className="space-y-4">
          <h4 className="font-semibold text-foreground">Risk Exposure</h4>
          {riskMetrics.map((metric, index) => (
            <motion.div
              key={metric.label}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
              className="space-y-2"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <metric.icon className={`w-4 h-4 ${getStatusColor(metric.status)}`} />
                  <span className="text-sm text-muted-foreground">{metric.label}</span>
                </div>
                <div className="text-right">
                  <span className={`text-sm font-medium ${getStatusColor(metric.status)}`}>
                    {formatValue(metric.current, metric.format)}
                  </span>
                  <span className="text-xs text-muted-foreground ml-1">
                    / {formatValue(metric.limit, metric.format)}
                  </span>
                </div>
              </div>
              <div className="relative">
                <Progress 
                  value={(metric.current / metric.limit) * 100} 
                  className="h-1"
                />
                {metric.status === 'warning' && (
                  <motion.div
                    className="absolute inset-0 bg-yellow-500/20 rounded-full"
                    animate={{ opacity: [0.3, 0.7, 0.3] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  />
                )}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Compliance Rules */}
        <div className="space-y-4">
          <h4 className="font-semibold text-foreground">Compliance Rules</h4>
          <div className="space-y-2">
            {complianceRules.map((rule, index) => (
              <motion.div
                key={rule.rule}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
                className="flex items-center justify-between p-2 bg-background/30 rounded-lg"
              >
                <div className="flex items-center gap-2">
                  {rule.violation ? (
                    <AlertTriangle className="w-3 h-3 text-red-500" />
                  ) : (
                    <Shield className="w-3 h-3 text-green-500" />
                  )}
                  <span className="text-xs text-foreground">{rule.rule}</span>
                </div>
                <Badge 
                  variant={rule.violation ? "destructive" : "success"} 
                  className="text-xs"
                >
                  {rule.violation ? 'Violated' : 'OK'}
                </Badge>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Risk Summary */}
        <div className="space-y-3 pt-4 border-t border-border/30">
          <h4 className="font-semibold text-foreground">Today's Summary</h4>
          
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="space-y-1">
              <p className="text-muted-foreground">Max Risk Used</p>
              <p className="font-medium text-foreground">2.1% / 5.0%</p>
            </div>
            <div className="space-y-1">
              <p className="text-muted-foreground">Violations</p>
              <p className="font-medium text-green-500">0</p>
            </div>
            <div className="space-y-1">
              <p className="text-muted-foreground">Alerts</p>
              <p className="font-medium text-yellow-500">1</p>
            </div>
            <div className="space-y-1">
              <p className="text-muted-foreground">Status</p>
              <p className="font-medium text-green-500">Compliant</p>
            </div>
          </div>
        </div>

        {/* Risk Alerts */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg"
        >
          <div className="flex items-start gap-2">
            <Activity className="w-4 h-4 text-yellow-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-foreground">
                Risk Advisory
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Monitor EURUSD volatility - consider reducing position size for news events
              </p>
            </div>
          </div>
        </motion.div>
      </CardContent>
    </Card>
  )
}