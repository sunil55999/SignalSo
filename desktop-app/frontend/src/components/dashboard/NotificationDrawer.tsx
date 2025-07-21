import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Bell,
  X,
  Info,
  AlertTriangle,
  CheckCircle,
  Zap,
  BookOpen,
  Settings,
  ExternalLink,
  Trash2
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatRelativeTime } from '@/lib/utils'

interface Notification {
  id: string
  type: 'info' | 'warning' | 'error' | 'success' | 'onboarding'
  title: string
  message: string
  timestamp: Date
  isRead: boolean
  actionLabel?: string
  actionUrl?: string
  dismissible: boolean
}

const mockNotifications: Notification[] = [
  {
    id: '1',
    type: 'onboarding',
    title: 'Welcome to SignalOS Desktop!',
    message: 'Complete your setup by connecting your first signal provider.',
    timestamp: new Date(Date.now() - 5 * 60 * 1000),
    isRead: false,
    actionLabel: 'Get Started',
    actionUrl: '/providers',
    dismissible: true
  },
  {
    id: '2',
    type: 'warning',
    title: 'MT5 Setup Required',
    message: 'Connect your MT5 terminal to enable automated trading.',
    timestamp: new Date(Date.now() - 15 * 60 * 1000),
    isRead: false,
    actionLabel: 'Configure MT5',
    actionUrl: '/settings',
    dismissible: true
  },
  {
    id: '3',
    type: 'success',
    title: 'Database Connected',
    message: 'Your local database is successfully initialized and ready.',
    timestamp: new Date(Date.now() - 30 * 60 * 1000),
    isRead: true,
    dismissible: true
  },
  {
    id: '4',
    type: 'info',
    title: 'New Feature Available',
    message: 'Risk management tools are now available in the dashboard.',
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
    isRead: false,
    actionLabel: 'Learn More',
    actionUrl: '/help',
    dismissible: true
  }
]

interface NotificationDrawerProps {
  isOpen: boolean
  onClose: () => void
}

export function NotificationDrawer({ isOpen, onClose }: NotificationDrawerProps) {
  const [notifications, setNotifications] = useState<Notification[]>(mockNotifications)

  const getNotificationIcon = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />
      case 'error':
        return <AlertTriangle className="w-4 h-4 text-red-500" />
      case 'onboarding':
        return <BookOpen className="w-4 h-4 text-blue-500" />
      default:
        return <Info className="w-4 h-4 text-cyan-500" />
    }
  }

  const markAsRead = (id: string) => {
    setNotifications(prev => 
      prev.map(n => n.id === id ? { ...n, isRead: true } : n)
    )
  }

  const dismissNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }

  const markAllAsRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, isRead: true })))
  }

  const clearAll = () => {
    setNotifications(prev => prev.filter(n => !n.dismissible))
  }

  const unreadCount = notifications.filter(n => !n.isRead).length

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40"
            onClick={onClose}
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 h-full w-96 bg-card border-l border-border shadow-2xl z-50 flex flex-col"
          >
            <Card className="h-full border-0 rounded-none shadow-none">
              <CardHeader className="border-b border-border">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Bell className="w-5 h-5 text-primary" />
                      Notifications
                      {unreadCount > 0 && (
                        <Badge variant="destructive" className="text-xs">
                          {unreadCount}
                        </Badge>
                      )}
                    </CardTitle>
                    <p className="text-sm text-muted-foreground mt-1">
                      System alerts and onboarding
                    </p>
                  </div>
                  <Button variant="ghost" size="sm" onClick={onClose}>
                    <X className="w-4 h-4" />
                  </Button>
                </div>

                {/* Action Buttons */}
                {notifications.length > 0 && (
                  <div className="flex items-center gap-2 mt-4">
                    <Button variant="ghost" size="sm" onClick={markAllAsRead}>
                      Mark All Read
                    </Button>
                    <Button variant="ghost" size="sm" onClick={clearAll}>
                      <Trash2 className="w-3 h-3 mr-1" />
                      Clear All
                    </Button>
                  </div>
                )}
              </CardHeader>

              <CardContent className="flex-1 p-0 overflow-y-auto custom-scrollbar">
                {notifications.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center px-6">
                    <Bell className="w-12 h-12 text-muted-foreground/50 mb-3" />
                    <p className="text-sm text-muted-foreground mb-2">
                      You're all caught up!
                    </p>
                    <p className="text-xs text-muted-foreground">
                      No new notifications at this time.
                    </p>
                  </div>
                ) : (
                  <div className="divide-y divide-border">
                    {notifications.map((notification, index) => (
                      <motion.div
                        key={notification.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.2, delay: index * 0.05 }}
                        className={`p-4 hover:bg-muted/30 transition-colors cursor-pointer ${
                          !notification.isRead ? 'bg-primary/5 border-l-2 border-l-primary' : ''
                        }`}
                        onClick={() => markAsRead(notification.id)}
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex-shrink-0 mt-1">
                            {getNotificationIcon(notification.type)}
                          </div>

                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-2">
                              <h4 className="text-sm font-medium text-foreground">
                                {notification.title}
                              </h4>
                              {notification.dismissible && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    dismissNotification(notification.id)
                                  }}
                                >
                                  <X className="w-3 h-3" />
                                </Button>
                              )}
                            </div>

                            <p className="text-sm text-muted-foreground mt-1 leading-relaxed">
                              {notification.message}
                            </p>

                            <div className="flex items-center justify-between mt-3">
                              <time className="text-xs text-muted-foreground">
                                {formatRelativeTime(notification.timestamp)}
                              </time>
                              
                              {notification.actionLabel && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 text-xs"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    // Navigate to action URL
                                    window.location.href = notification.actionUrl || '#'
                                  }}
                                >
                                  {notification.actionLabel}
                                  <ExternalLink className="w-3 h-3 ml-1" />
                                </Button>
                              )}
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}