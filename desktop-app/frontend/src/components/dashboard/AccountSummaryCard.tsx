import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CreditCard,
  TrendingUp,
  TrendingDown,
  Shield,
  ChevronDown,
  ChevronUp,
  Zap,
  Award,
  Eye,
  EyeOff
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { formatCurrency, formatPercentage } from '@/lib/utils'

export function AccountSummaryCard() {
  const [isExpanded, setIsExpanded] = useState(false)
  const [showBalances, setShowBalances] = useState(true)

  // Mock account data - in real app this would come from props or API
  const accountData = {
    accountName: 'Trading Account Pro',
    accountNumber: '****7842',
    licenseType: 'Desktop Premium',
    broker: 'IC Markets',
    server: 'ICMarkets-Live01',
    balance: 10000.00,
    equity: 10250.75,
    margin: 1250.30,
    freeMargin: 8999.45,
    marginLevel: 820.45,
    openPnL: 250.75,
    todaysPnL: 125.50,
    totalPnL: 2547.89,
    isActive: true,
    riskLevel: 'Conservative',
    maxDrawdown: 15.5,
    usedMargin: 12.5
  }

  const getMarginLevelColor = (level: number) => {
    if (level > 500) return 'text-green-500'
    if (level > 200) return 'text-yellow-500'
    return 'text-red-500'
  }

  const getMarginLevelBadge = (level: number) => {
    if (level > 500) return <Badge variant="success">Safe</Badge>
    if (level > 200) return <Badge variant="warning">Caution</Badge>
    return <Badge variant="destructive">Critical</Badge>
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-12 h-12 bg-gradient-to-br from-primary to-accent rounded-xl">
              <CreditCard className="w-6 h-6 text-white" />
            </div>
            <div>
              <CardTitle className="text-xl font-bold">Account & License Overview</CardTitle>
              <p className="text-sm text-muted-foreground">Desktop trading account status</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <Badge variant={accountData.isActive ? "success" : "destructive"}>
              {accountData.isActive ? "Desktop-Activated" : "Inactive"}
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Account Summary */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">Balance</p>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowBalances(!showBalances)}
                className="h-6 w-6 p-0"
              >
                {showBalances ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
              </Button>
            </div>
            <p className="text-2xl font-bold text-foreground">
              {showBalances ? formatCurrency(accountData.balance) : '••••••'}
            </p>
          </div>

          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">Equity</p>
            <p className="text-2xl font-bold text-foreground">
              {showBalances ? formatCurrency(accountData.equity) : '••••••'}
            </p>
            <div className="flex items-center gap-1">
              {accountData.openPnL >= 0 ? (
                <TrendingUp className="w-3 h-3 text-green-500" />
              ) : (
                <TrendingDown className="w-3 h-3 text-red-500" />
              )}
              <span className={`text-xs ${accountData.openPnL >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {showBalances ? formatCurrency(accountData.openPnL) : '•••'}
              </span>
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">Margin Level</p>
            <p className={`text-2xl font-bold ${getMarginLevelColor(accountData.marginLevel)}`}>
              {accountData.marginLevel.toFixed(1)}%
            </p>
            {getMarginLevelBadge(accountData.marginLevel)}
          </div>

          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">Free Margin</p>
            <p className="text-2xl font-bold text-foreground">
              {showBalances ? formatCurrency(accountData.freeMargin) : '••••••'}
            </p>
          </div>
        </div>

        {/* License & Risk Information */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="glass-panel p-4">
            <div className="flex items-center gap-3 mb-3">
              <Award className="w-5 h-5 text-primary" />
              <h4 className="font-semibold">License Information</h4>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Type:</span>
                <span className="font-medium">{accountData.licenseType}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Account:</span>
                <span className="font-medium">{accountData.accountNumber}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Broker:</span>
                <span className="font-medium">{accountData.broker}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Server:</span>
                <span className="font-medium">{accountData.server}</span>
              </div>
            </div>
          </div>

          <div className="glass-panel p-4">
            <div className="flex items-center gap-3 mb-3">
              <Shield className="w-5 h-5 text-green-500" />
              <h4 className="font-semibold">Risk Management</h4>
            </div>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-muted-foreground">Margin Used</span>
                  <span className="font-medium">{accountData.usedMargin}%</span>
                </div>
                <Progress value={accountData.usedMargin} className="h-2" />
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Risk Level:</span>
                <Badge variant="success">{accountData.riskLevel}</Badge>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Max Drawdown:</span>
                <span className="font-medium">{accountData.maxDrawdown}%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Expanded Details */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
              className="space-y-4 pt-4 border-t border-border/30"
            >
              <h4 className="font-semibold flex items-center gap-2">
                <Zap className="w-4 h-4 text-primary" />
                Desktop Configuration
              </h4>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div className="space-y-2">
                  <p className="text-muted-foreground">Local Storage Path:</p>
                  <p className="font-mono text-xs bg-muted p-2 rounded">
                    ~/SignalOS/data/
                  </p>
                </div>
                <div className="space-y-2">
                  <p className="text-muted-foreground">Config File:</p>
                  <p className="font-mono text-xs bg-muted p-2 rounded">
                    config.json
                  </p>
                </div>
                <div className="space-y-2">
                  <p className="text-muted-foreground">Last Sync:</p>
                  <p className="font-medium">
                    {new Date().toLocaleString()}
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse-soft"></div>
                  <span>Desktop app active and monitoring</span>
                </div>
                <Button variant="outline" size="sm">
                  Open Local Config
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </CardContent>
    </Card>
  )
}