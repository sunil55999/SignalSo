import { Routes, Route } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import { Layout } from '@/components/layout/Layout'
import { Dashboard } from '@/pages/Dashboard'
import { Providers } from '@/pages/Providers'
import { Strategies } from '@/pages/Strategies'
import { Trades } from '@/pages/Trades'
import { Backtest } from '@/pages/Backtest'
import { Logs } from '@/pages/Logs'
import { Settings } from '@/pages/Settings'
import { Help } from '@/pages/Help'

function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/providers" element={<Providers />} />
          <Route path="/strategies" element={<Strategies />} />
          <Route path="/trades" element={<Trades />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/help" element={<Help />} />
        </Routes>
      </Layout>
      <Toaster />
    </div>
  )
}

export default App