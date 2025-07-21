import { NavLink, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  BarChart3,
  Satellite,
  Layers3,
  TrendingUp,
  FlaskConical,
  ScrollText,
  Settings,
  HelpCircle,
  Zap
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navigationItems = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: BarChart3,
    description: 'Mission Control'
  },
  {
    name: 'Providers',
    href: '/providers',
    icon: Satellite,
    description: 'Signal Sources'
  },
  {
    name: 'Strategies',
    href: '/strategies',
    icon: Layers3,
    description: 'Trading Rules'
  },
  {
    name: 'Trades',
    href: '/trades',
    icon: TrendingUp,
    description: 'Active Positions'
  },
  {
    name: 'Backtest',
    href: '/backtest',
    icon: FlaskConical,
    description: 'Performance Testing'
  },
  {
    name: 'Logs',
    href: '/logs',
    icon: ScrollText,
    description: 'System Activity'
  },
  {
    name: 'Settings',
    href: '/settings',
    icon: Settings,
    description: 'Configuration'
  },
  {
    name: 'Help',
    href: '/help',
    icon: HelpCircle,
    description: 'Documentation'
  }
]

export function SidebarNav() {
  const location = useLocation()

  return (
    <div className="flex flex-col h-full p-4">
      {/* Logo & Brand */}
      <div className="flex items-center gap-3 mb-8 p-2">
        <div className="flex items-center justify-center w-10 h-10 bg-gradient-to-br from-primary to-accent rounded-lg">
          <Zap className="w-6 h-6 text-white" />
        </div>
        <div className="flex flex-col">
          <h1 className="text-xl font-bold text-foreground">SignalOS</h1>
          <p className="text-xs text-muted-foreground">Desktop Trading</p>
        </div>
      </div>

      {/* Navigation Items */}
      <nav className="flex flex-col gap-1 flex-1">
        {navigationItems.map((item) => {
          const isActive = location.pathname === item.href || 
                          (item.href === '/dashboard' && location.pathname === '/')
          
          return (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive: linkActive }) => cn(
                'sidebar-nav-item group relative',
                (isActive || linkActive) && 'active'
              )}
            >
              {({ isActive: linkActive }) => (
                <>
                  {(isActive || linkActive) && (
                    <motion.div
                      layoutId="sidebar-active-bg"
                      className="absolute inset-0 bg-primary/10 rounded-lg border border-primary/20"
                      initial={false}
                      transition={{ duration: 0.2 }}
                    />
                  )}
                  <item.icon className="w-5 h-5 transition-colors" />
                  <div className="flex flex-col flex-1 relative">
                    <span className="font-medium text-sm">{item.name}</span>
                    <span className="text-xs text-muted-foreground group-hover:text-muted-foreground/80">
                      {item.description}
                    </span>
                  </div>
                </>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* System Status */}
      <div className="mt-auto pt-4 border-t border-border/50">
        <div className="glass-card p-3">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse-soft"></div>
            <span className="text-sm font-medium text-foreground">System Active</span>
          </div>
          <div className="space-y-1 text-xs text-muted-foreground">
            <div className="flex justify-between">
              <span>API:</span>
              <span className="text-green-400">Connected</span>
            </div>
            <div className="flex justify-between">
              <span>Database:</span>
              <span className="text-green-400">Online</span>
            </div>
            <div className="flex justify-between">
              <span>MT5:</span>
              <span className="text-yellow-400">Configuring</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}