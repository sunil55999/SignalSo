import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import { 
  Layout, 
  Settings, 
  HelpCircle, 
  Sun, 
  Moon, 
  MoreHorizontal,
  Grid,
  List,
  Eye,
  EyeOff
} from 'lucide-react';

// Import all dashboard components
import { AccountSummaryCard } from './AccountSummaryCard';
import { SystemHealthIndicators } from './SystemHealthIndicators';
import { QuickActionsBar } from './QuickActionsBar';
import { PerformanceMetricsTiles } from './PerformanceMetricsTiles';
import { InteractiveActivityFeed } from './InteractiveActivityFeed';
import { ProvidersPanel } from './ProvidersPanel';
import { StrategiesPanel } from './StrategiesPanel';
import { RiskPanel } from './RiskPanel';
import { NotificationCenter } from './NotificationCenter';
import { DashboardWidgetWrapper } from './DashboardWidgetWrapper';

// Mock data for development (as requested in the guide)
const mockData = {
  account: {
    id: '1',
    balance: 10000,
    equity: 10025,
    margin: 150,
    marginFree: 9875,
    marginLevel: 668.33,
    profit: 25,
    currency: 'USD',
    server: 'MetaQuotes-Demo',
    leverage: 100,
    name: 'Demo Account',
    company: 'MetaQuotes',
    tradeAllowed: true,
    tradeExpert: true,
    limitOrders: 200,
    marginSoMode: 0,
    marginSoCall: 50,
    marginSoSo: 30,
    marginInitial: 0,
    marginMaintenance: 0,
    assetsBalance: 10000,
    assetsCredit: 0,
    assetsEquity: 10025,
    assetsProfit: 25,
  },
  license: {
    id: '1',
    tier: 'pro' as const,
    status: 'active' as const,
    validUntil: '2025-12-31',
    features: ['unlimited_providers', 'advanced_strategies', 'risk_management'],
    limits: {
      providers: 50,
      strategies: 20,
      trades: 1000,
      signals: 10000,
    },
    deviceId: 'desktop-001',
    userId: 'user-123',
    companyName: 'SignalOS Pro',
  },
  systemHealth: {
    aiParser: {
      status: 'online' as const,
      lastActivity: new Date().toISOString(),
      successRate: 98.5,
      message: 'Operating normally',
    },
    mt5Bridge: {
      status: 'connected' as const,
      lastActivity: new Date().toISOString(),
      latency: 45,
      message: 'Connected to MetaQuotes-Demo',
    },
    telegramLink: {
      status: 'active' as const,
      lastActivity: new Date().toISOString(),
      channelsConnected: 3,
      message: '3 channels monitoring',
    },
    marketplace: {
      status: 'online' as const,
      lastUpdate: new Date().toISOString(),
      message: 'All services operational',
    },
    notifications: {
      status: 'enabled' as const,
      queueSize: 2,
      message: '2 pending notifications',
    },
  },
  tradingMetrics: {
    todaysPnL: 125.50,
    winRate: 78.5,
    tradesExecuted: 15,
    parsingSuccessRate: 98.5,
    executionSpeed: 245,
    totalTrades: 150,
    totalProfit: 2450.75,
    totalLoss: -890.25,
    averageWin: 65.50,
    averageLoss: -32.25,
    maxDrawdown: 5.2,
    sharpeRatio: 1.85,
    profitFactor: 2.75,
  },
  providers: [
    {
      id: '1',
      name: 'Gold Signals Pro',
      type: 'telegram' as const,
      status: 'active' as const,
      connected: true,
      channelId: '@goldsignalspro',
      channelName: 'Gold Signals Pro',
      lastActivity: new Date().toISOString(),
      performance: {
        totalSignals: 245,
        successfulParsing: 98,
        executedTrades: 42,
        winRate: 85.5,
        profit: 1250.75,
        latency: 125,
      },
    },
    {
      id: '2',
      name: 'Forex Elite',
      type: 'telegram' as const,
      status: 'active' as const,
      connected: true,
      channelId: '@forexelite',
      channelName: 'Forex Elite Signals',
      lastActivity: new Date().toISOString(),
      performance: {
        totalSignals: 189,
        successfulParsing: 95,
        executedTrades: 38,
        winRate: 72.5,
        profit: 850.25,
        latency: 98,
      },
    },
  ],
  strategies: [
    {
      id: '1',
      name: 'Scalping Strategy',
      description: 'High-frequency scalping with risk management',
      status: 'active' as const,
      type: 'scalping' as const,
      providers: ['1', '2'],
      rules: [
        {
          id: '1',
          condition: 'Signal type == BUY',
          action: 'Execute with 0.1 lot',
          parameters: { lotSize: 0.1, stopLoss: 20 },
        },
        {
          id: '2',
          condition: 'Profit > 10 pips',
          action: 'Close 50% position',
          parameters: { percentage: 50 },
        },
      ],
      riskManagement: {
        maxLotSize: 0.5,
        maxRiskPerTrade: 2,
        maxDailyLoss: 5,
        stopLossPoints: 20,
        takeProfitPoints: 30,
      },
      performance: {
        totalTrades: 125,
        winRate: 78.5,
        profit: 1450.75,
        drawdown: 3.2,
        lastExecuted: new Date().toISOString(),
      },
    },
  ],
  activityEvents: [
    {
      id: '1',
      timestamp: new Date().toISOString(),
      type: 'trade' as const,
      level: 'success' as const,
      title: 'Trade Executed',
      description: 'EURUSD BUY 0.1 lot executed at 1.0850',
      provider: 'Gold Signals Pro',
      symbol: 'EURUSD',
      resolved: false,
      actions: [
        {
          id: '1',
          label: 'View Details',
          type: 'acknowledge' as const,
        },
      ],
    },
    {
      id: '2',
      timestamp: new Date(Date.now() - 300000).toISOString(),
      type: 'signal' as const,
      level: 'info' as const,
      title: 'Signal Parsed',
      description: 'Successfully parsed GBPUSD signal from Forex Elite',
      provider: 'Forex Elite',
      symbol: 'GBPUSD',
      resolved: true,
    },
  ],
  riskExposures: [
    {
      symbol: 'EURUSD',
      exposure: 2500,
      margin: 250,
      unrealizedPnL: 45.50,
      trades: 3,
      providers: ['Gold Signals Pro'],
      maxExposure: 5000,
      riskLevel: 'low' as const,
    },
    {
      symbol: 'GBPUSD',
      exposure: 1800,
      margin: 180,
      unrealizedPnL: -15.25,
      trades: 2,
      providers: ['Forex Elite'],
      maxExposure: 3000,
      riskLevel: 'medium' as const,
    },
  ],
  notifications: [
    {
      id: '1',
      type: 'warning' as const,
      title: 'High Exposure Warning',
      message: 'EURUSD exposure approaching 60% of maximum limit',
      timestamp: new Date().toISOString(),
      read: false,
      dismissed: false,
      category: 'risk' as const,
      priority: 'high' as const,
      actions: [
        {
          id: '1',
          label: 'Reduce Exposure',
          type: 'fix' as const,
        },
      ],
    },
    {
      id: '2',
      type: 'info' as const,
      title: 'Strategy Performance',
      message: 'Scalping Strategy achieved 78.5% win rate today',
      timestamp: new Date(Date.now() - 600000).toISOString(),
      read: false,
      dismissed: false,
      category: 'trading' as const,
      priority: 'medium' as const,
    },
  ],
};

export function SignalOSDashboard() {
  const { toast } = useToast();
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isAutomationRunning, setIsAutomationRunning] = useState(true);
  const [dashboardLayout, setDashboardLayout] = useState<'grid' | 'list'>('grid');
  const [activeTab, setActiveTab] = useState('overview');
  const [hiddenWidgets, setHiddenWidgets] = useState<Set<string>>(new Set());

  // Real-time data queries (using mock data as requested)
  const { data: accountData, isLoading: accountLoading } = useQuery({
    queryKey: ['/api/account'],
    queryFn: () => Promise.resolve(mockData.account),
    refetchInterval: 5000,
  });

  const { data: systemHealthData, isLoading: healthLoading } = useQuery({
    queryKey: ['/api/system/health'],
    queryFn: () => Promise.resolve(mockData.systemHealth),
    refetchInterval: 2000,
  });

  const { data: metricsData, isLoading: metricsLoading } = useQuery({
    queryKey: ['/api/metrics'],
    queryFn: () => Promise.resolve(mockData.tradingMetrics),
    refetchInterval: 5000,
  });

  const { data: providersData, isLoading: providersLoading } = useQuery({
    queryKey: ['/api/providers'],
    queryFn: () => Promise.resolve(mockData.providers),
    refetchInterval: 10000,
  });

  const { data: strategiesData, isLoading: strategiesLoading } = useQuery({
    queryKey: ['/api/strategies'],
    queryFn: () => Promise.resolve(mockData.strategies),
    refetchInterval: 10000,
  });

  const { data: activityData, isLoading: activityLoading } = useQuery({
    queryKey: ['/api/activity'],
    queryFn: () => Promise.resolve(mockData.activityEvents),
    refetchInterval: 3000,
  });

  const { data: riskData, isLoading: riskLoading } = useQuery({
    queryKey: ['/api/risk'],
    queryFn: () => Promise.resolve(mockData.riskExposures),
    refetchInterval: 5000,
  });

  const { data: notificationsData, isLoading: notificationsLoading } = useQuery({
    queryKey: ['/api/notifications'],
    queryFn: () => Promise.resolve(mockData.notifications),
    refetchInterval: 10000,
  });

  const handleWidgetToggle = (widgetId: string) => {
    setHiddenWidgets(prev => {
      const newSet = new Set(prev);
      if (newSet.has(widgetId)) {
        newSet.delete(widgetId);
      } else {
        newSet.add(widgetId);
      }
      return newSet;
    });
  };

  const handleThemeToggle = () => {
    setIsDarkMode(!isDarkMode);
    document.documentElement.classList.toggle('dark');
  };

  const handleModalOpen = (type: string, id?: string) => {
    toast({
      title: `${type} Modal`,
      description: `Opening ${type} ${id ? `for ${id}` : ''}...`,
    });
  };

  return (
    <div className={`min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 ${isDarkMode ? 'dark' : ''}`}>
      {/* Top Header */}
      <div className="bg-white dark:bg-gray-900 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
                  <Layout className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900 dark:text-white">SignalOS</h1>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Professional Trading Dashboard</p>
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                <Badge variant={isAutomationRunning ? 'default' : 'secondary'} className="animate-pulse">
                  {isAutomationRunning ? 'Live Trading' : 'Paused'}
                </Badge>
                <Badge variant="outline" className="bg-green-50 text-green-700">
                  {mockData.license.tier.toUpperCase()} License
                </Badge>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setDashboardLayout(dashboardLayout === 'grid' ? 'list' : 'grid')}
              >
                {dashboardLayout === 'grid' ? <List className="h-4 w-4" /> : <Grid className="h-4 w-4" />}
              </Button>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={handleThemeToggle}
              >
                {isDarkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </Button>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleModalOpen('Help')}
              >
                <HelpCircle className="h-4 w-4" />
              </Button>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleModalOpen('Settings')}
              >
                <Settings className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Quick Actions Bar */}
        <QuickActionsBar
          isAutomationRunning={isAutomationRunning}
          onImportSignals={() => handleModalOpen('Import')}
          onOpenBacktest={() => handleModalOpen('Backtest')}
          onOpenProvider={() => handleModalOpen('Provider')}
          onOpenSettings={() => handleModalOpen('Settings')}
          onOpenHelp={() => handleModalOpen('Help')}
        />

        {/* Dashboard Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="trading">Trading</TabsTrigger>
            <TabsTrigger value="risk">Risk & Compliance</TabsTrigger>
            <TabsTrigger value="activity">Activity & Logs</TabsTrigger>
          </TabsList>
          
          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            {/* Top Row - Account & Health */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <AccountSummaryCard
                account={accountData}
                license={mockData.license}
                isLoading={accountLoading}
              />
              <SystemHealthIndicators
                systemHealth={systemHealthData}
                isLoading={healthLoading}
              />
              <NotificationCenter
                notifications={notificationsData}
                isLoading={notificationsLoading}
              />
            </div>

            {/* Performance Metrics */}
            <PerformanceMetricsTiles
              metrics={metricsData}
              isLoading={metricsLoading}
            />

            {/* Providers & Strategies */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ProvidersPanel
                providers={providersData}
                isLoading={providersLoading}
                onAddProvider={() => handleModalOpen('Provider')}
                onEditProvider={(id) => handleModalOpen('Provider', id)}
              />
              <StrategiesPanel
                strategies={strategiesData}
                isLoading={strategiesLoading}
                onAddStrategy={() => handleModalOpen('Strategy')}
                onEditStrategy={(id) => handleModalOpen('Strategy', id)}
                onBacktestStrategy={(id) => handleModalOpen('Backtest', id)}
              />
            </div>
          </TabsContent>

          {/* Trading Tab */}
          <TabsContent value="trading" className="space-y-6">
            <PerformanceMetricsTiles
              metrics={metricsData}
              isLoading={metricsLoading}
            />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ProvidersPanel
                providers={providersData}
                isLoading={providersLoading}
                onAddProvider={() => handleModalOpen('Provider')}
                onEditProvider={(id) => handleModalOpen('Provider', id)}
              />
              <StrategiesPanel
                strategies={strategiesData}
                isLoading={strategiesLoading}
                onAddStrategy={() => handleModalOpen('Strategy')}
                onEditStrategy={(id) => handleModalOpen('Strategy', id)}
                onBacktestStrategy={(id) => handleModalOpen('Backtest', id)}
              />
            </div>
          </TabsContent>

          {/* Risk & Compliance Tab */}
          <TabsContent value="risk" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <AccountSummaryCard
                account={accountData}
                license={mockData.license}
                isLoading={accountLoading}
              />
              <SystemHealthIndicators
                systemHealth={systemHealthData}
                isLoading={healthLoading}
              />
              <NotificationCenter
                notifications={notificationsData}
                isLoading={notificationsLoading}
              />
            </div>
            <RiskPanel
              riskExposures={riskData}
              marginLevel={accountData?.marginLevel}
              totalExposure={riskData?.reduce((sum, r) => sum + r.exposure, 0) || 0}
              isLoading={riskLoading}
            />
          </TabsContent>

          {/* Activity & Logs Tab */}
          <TabsContent value="activity" className="space-y-6">
            <InteractiveActivityFeed
              events={activityData}
              isLoading={activityLoading}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}