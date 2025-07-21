import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { apiService } from '@/lib/api'
import { DashboardHeader } from '@/components/dashboard/DashboardHeader'
import { QuickActionsBar } from '@/components/dashboard/QuickActionsBar'
import { SystemHealthPanel } from '@/components/dashboard/SystemHealthPanel'
import { AccountSummaryCard } from '@/components/dashboard/AccountSummaryCard'
import { MetricsTiles } from '@/components/dashboard/MetricsTiles'
import { ActivityFeed } from '@/components/dashboard/ActivityFeed'
import { ProvidersWidget } from '@/components/dashboard/ProvidersWidget'
import { StrategyCards } from '@/components/dashboard/StrategyCards'
import { RiskPanel } from '@/components/dashboard/RiskPanel'

export function Dashboard() {
  // Fetch dashboard data
  const { data: systemStatus, isLoading: statusLoading } = useQuery({
    queryKey: ['system-status'],
    queryFn: () => apiService.getSystemStatus().then(res => res.data),
    refetchInterval: 5000 // Refresh every 5 seconds
  })

  const { data: activityData } = useQuery({
    queryKey: ['activity-feed'],
    queryFn: () => apiService.getActivity(10).then(res => res.data),
    refetchInterval: 2000 // Refresh every 2 seconds
  })

  return (
    <div className="space-y-6">
      {/* Quick Actions Bar */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <QuickActionsBar />
      </motion.div>

      {/* System Health Panel */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="col-span-12"
      >
        <SystemHealthPanel systemStatus={systemStatus} isLoading={statusLoading} />
      </motion.div>

      {/* Account Overview */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.2 }}
        className="col-span-12 lg:col-span-8"
      >
        <AccountSummaryCard />
      </motion.div>

      {/* Performance Metrics Grid */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.3 }}
        className="col-span-12"
      >
        <MetricsTiles systemStatus={systemStatus} />
      </motion.div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-12 gap-6">
        {/* Activity Feed */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: 0.4 }}
          className="col-span-12 lg:col-span-8"
        >
          <ActivityFeed activities={activityData?.events || []} />
        </motion.div>

        {/* Risk Panel */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: 0.5 }}
          className="col-span-12 lg:col-span-4"
        >
          <RiskPanel />
        </motion.div>
      </div>

      {/* Providers and Strategies */}
      <div className="grid grid-cols-12 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.6 }}
          className="col-span-12 lg:col-span-6"
        >
          <ProvidersWidget />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.7 }}
          className="col-span-12 lg:col-span-6"
        >
          <StrategyCards />
        </motion.div>
      </div>
    </div>
  )
}