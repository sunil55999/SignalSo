import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Upload,
  Plus,
  FlaskConical,
  Pause,
  Play,
  HelpCircle,
  Download,
  Settings
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/hooks/use-toast'

export function QuickActionsBar() {
  const [isSystemPaused, setIsSystemPaused] = useState(false)
  const [isLoading, setIsLoading] = useState<string | null>(null)
  const { toast } = useToast()

  const handleImportSignals = () => {
    setIsLoading('import')
    // Simulate file dialog and import process
    setTimeout(() => {
      setIsLoading(null)
      toast({
        title: "Import Signals",
        description: "File import dialog would open here",
      })
    }, 1000)
  }

  const handleAddProvider = () => {
    toast({
      title: "Add Provider",
      description: "Provider setup modal would open here",
    })
  }

  const handleRunBacktest = () => {
    setIsLoading('backtest')
    setTimeout(() => {
      setIsLoading(null)
      toast({
        title: "Run Backtest",
        description: "Backtest configuration would start here",
      })
    }, 1500)
  }

  const toggleSystem = () => {
    setIsLoading('system')
    setTimeout(() => {
      setIsSystemPaused(!isSystemPaused)
      setIsLoading(null)
      toast({
        title: isSystemPaused ? "System Resumed" : "System Paused",
        description: `Trading automation is now ${isSystemPaused ? 'active' : 'paused'}`,
        variant: isSystemPaused ? "default" : "destructive"
      })
    }, 800)
  }

  const actions = [
    {
      id: 'import',
      label: 'Import Signals',
      icon: Upload,
      onClick: handleImportSignals,
      variant: 'outline' as const,
      description: 'Import signal files'
    },
    {
      id: 'provider',
      label: 'Add Provider',
      icon: Plus,
      onClick: handleAddProvider,
      variant: 'outline' as const,
      description: 'Connect new signal source'
    },
    {
      id: 'backtest',
      label: 'Run Backtest',
      icon: FlaskConical,
      onClick: handleRunBacktest,
      variant: 'outline' as const,
      description: 'Test strategy performance'
    },
    {
      id: 'system',
      label: isSystemPaused ? 'Resume' : 'Pause',
      icon: isSystemPaused ? Play : Pause,
      onClick: toggleSystem,
      variant: isSystemPaused ? 'default' : 'destructive' as const,
      description: 'Toggle system automation',
      priority: true
    }
  ]

  return (
    <div className="glass-card p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Quick Actions</h3>
          <p className="text-sm text-muted-foreground">Desktop trading controls</p>
        </div>
        
        <div className="flex items-center gap-2">
          <Badge variant={isSystemPaused ? "destructive" : "success"}>
            System {isSystemPaused ? 'Paused' : 'Active'}
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {actions.map((action, index) => (
          <motion.div
            key={action.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.1 }}
          >
            <Button
              variant={action.variant}
              onClick={action.onClick}
              disabled={isLoading === action.id}
              className={`w-full h-16 flex flex-col gap-1 relative transition-all duration-200 hover:scale-105 ${
                action.priority ? 'ring-2 ring-primary/50' : ''
              }`}
            >
              <action.icon className={`w-5 h-5 ${
                isLoading === action.id ? 'animate-spin' : ''
              }`} />
              <span className="text-xs font-medium">{action.label}</span>
              
              {action.priority && !isSystemPaused && (
                <motion.div
                  className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full"
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              )}
            </Button>
          </motion.div>
        ))}
      </div>

      {/* Secondary Actions */}
      <div className="flex items-center justify-between mt-4 pt-4 border-t border-border/30">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Export Data
          </Button>
          <Button variant="ghost" size="sm">
            <Settings className="w-4 h-4 mr-2" />
            Quick Setup
          </Button>
        </div>
        
        <Button variant="ghost" size="sm">
          <HelpCircle className="w-4 h-4 mr-2" />
          Help & Docs
        </Button>
      </div>
    </div>
  )
}