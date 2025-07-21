import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Bell,
  User,
  Moon,
  Sun,
  Settings,
  LogOut,
  Maximize2,
  Minimize2
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

const pageTitles: Record<string, string> = {
  '/': 'Dashboard – Mission Control',
  '/dashboard': 'Dashboard – Mission Control',
  '/providers': 'Providers – Signal Sources',
  '/strategies': 'Strategies – Trading Rules',
  '/trades': 'Trades – Active Positions',
  '/backtest': 'Backtest – Performance Testing',
  '/logs': 'Logs – System Activity',
  '/settings': 'Settings – Configuration',
  '/help': 'Help – Documentation'
}

export function DashboardHeader() {
  const location = useLocation()
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isDarkMode, setIsDarkMode] = useState(true)
  const [notifications] = useState([
    { id: 1, type: 'info', message: 'System initialized successfully' },
    { id: 2, type: 'warning', message: 'MT5 connection pending setup' }
  ])

  const pageTitle = pageTitles[location.pathname] || 'SignalOS Desktop'
  const hasUnreadNotifications = notifications.length > 0

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen()
      setIsFullscreen(true)
    } else {
      document.exitFullscreen()
      setIsFullscreen(false)
    }
  }

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode)
    document.documentElement.classList.toggle('dark')
  }

  return (
    <header className="glass-panel border-b border-border/50 px-6 py-4">
      <div className="flex items-center justify-between">
        {/* Page Title */}
        <div className="flex items-center gap-4">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
          >
            <h1 className="text-2xl font-semibold text-foreground">
              {pageTitle}
            </h1>
          </motion.div>
        </div>

        {/* Header Actions */}
        <div className="flex items-center gap-3">
          {/* Notifications */}
          <div className="relative">
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="w-5 h-5" />
              <AnimatePresence>
                {hasUnreadNotifications && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    exit={{ scale: 0 }}
                    className="absolute -top-1 -right-1"
                  >
                    <Badge variant="destructive" className="w-5 h-5 p-0 flex items-center justify-center text-xs">
                      {notifications.length}
                    </Badge>
                  </motion.div>
                )}
              </AnimatePresence>
            </Button>
          </div>

          {/* Theme Toggle */}
          <Button 
            variant="ghost" 
            size="icon"
            onClick={toggleTheme}
            className="transition-transform hover:scale-110"
          >
            <AnimatePresence mode="wait">
              <motion.div
                key={isDarkMode ? 'dark' : 'light'}
                initial={{ rotate: -90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: 90, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                {isDarkMode ? (
                  <Moon className="w-5 h-5" />
                ) : (
                  <Sun className="w-5 h-5" />
                )}
              </motion.div>
            </AnimatePresence>
          </Button>

          {/* Fullscreen Toggle */}
          <Button 
            variant="ghost" 
            size="icon"
            onClick={toggleFullscreen}
            className="transition-transform hover:scale-110"
          >
            {isFullscreen ? (
              <Minimize2 className="w-5 h-5" />
            ) : (
              <Maximize2 className="w-5 h-5" />
            )}
          </Button>

          {/* Divider */}
          <div className="w-px h-6 bg-border/50 mx-2" />

          {/* User Profile */}
          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium text-foreground">Trading User</p>
              <p className="text-xs text-muted-foreground">Desktop License</p>
            </div>
            
            <div className="relative">
              <Button variant="ghost" size="icon" className="relative">
                <div className="w-8 h-8 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center">
                  <User className="w-4 h-4 text-white" />
                </div>
                <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 border-2 border-background rounded-full"></div>
              </Button>
            </div>
          </div>

          {/* Settings */}
          <Button variant="ghost" size="icon">
            <Settings className="w-5 h-5" />
          </Button>
        </div>
      </div>

      {/* Desktop App Status Bar */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-border/30">
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse-soft"></div>
            <span>Desktop App Connected</span>
          </div>
          <span>•</span>
          <span>Version 1.0.0</span>
          <span>•</span>
          <span>Replit Environment</span>
        </div>
        
        <div className="flex items-center gap-2">
          <Badge variant="success" className="text-xs">
            Production Ready
          </Badge>
        </div>
      </div>
    </header>
  )
}