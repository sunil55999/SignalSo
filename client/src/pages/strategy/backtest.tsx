import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { 
  TrendingUp, 
  Play, 
  Pause, 
  BarChart3, 
  Calendar, 
  Target, 
  DollarSign,
  TrendingDown,
  Activity,
  Download,
  Settings
} from 'lucide-react';

export function StrategyBacktest() {
  const [isRunning, setIsRunning] = useState(false);
  const [backtestResults, setBacktestResults] = useState<any>(null);
  const [settings, setSettings] = useState({
    startDate: '2024-01-01',
    endDate: '2024-12-31',
    initialBalance: 10000,
    riskPerTrade: 2,
    strategy: 'ai_parser',
    symbols: ['EURUSD', 'GBPUSD', 'XAUUSD'],
  });
  const { toast } = useToast();

  const handleRunBacktest = async () => {
    setIsRunning(true);
    setBacktestResults(null);

    try {
      // Simulate backtest process
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      // Mock backtest results
      const mockResults = {
        summary: {
          totalTrades: 156,
          winRate: 68.5,
          totalProfit: 2450.75,
          totalReturn: 24.51,
          maxDrawdown: -8.2,
          sharpeRatio: 1.45,
          avgWinAmount: 65.30,
          avgLossAmount: -42.80,
        },
        monthlyReturns: [
          { month: 'Jan', return: 180.50 },
          { month: 'Feb', return: 220.75 },
          { month: 'Mar', return: -120.25 },
          { month: 'Apr', return: 340.80 },
          { month: 'May', return: 190.40 },
          { month: 'Jun', return: 280.30 },
          { month: 'Jul', return: -80.15 },
          { month: 'Aug', return: 420.90 },
          { month: 'Sep', return: 150.60 },
          { month: 'Oct', return: 380.20 },
          { month: 'Nov', return: 240.70 },
          { month: 'Dec', return: 300.45 },
        ],
        equity: Array.from({ length: 30 }, (_, i) => ({
          day: i + 1,
          value: 10000 + (i * 82) + (Math.random() * 200 - 100),
        })),
      };

      setBacktestResults(mockResults);
      
      toast({
        title: 'Backtest completed',
        description: `Strategy tested with ${mockResults.summary.totalTrades} trades`,
      });
    } catch (error) {
      toast({
        title: 'Backtest failed',
        description: 'An error occurred during backtesting',
        variant: 'destructive',
      });
    } finally {
      setIsRunning(false);
    }
  };

  const handleExportResults = () => {
    if (!backtestResults) return;
    
    const csvContent = [
      ['Metric', 'Value'],
      ['Total Trades', backtestResults.summary.totalTrades],
      ['Win Rate', `${backtestResults.summary.winRate}%`],
      ['Total Profit', `$${backtestResults.summary.totalProfit}`],
      ['Total Return', `${backtestResults.summary.totalReturn}%`],
      ['Max Drawdown', `${backtestResults.summary.maxDrawdown}%`],
      ['Sharpe Ratio', backtestResults.summary.sharpeRatio],
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `backtest-results-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();

    toast({
      title: 'Results exported',
      description: 'Backtest results downloaded as CSV',
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Strategy Backtest</h1>
        <p className="text-gray-600 dark:text-gray-300">
          Test your trading strategies against historical data
        </p>
      </div>

      {/* Backtest Configuration */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Backtest Configuration
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Start Date
            </label>
            <input
              type="date"
              value={settings.startDate}
              onChange={(e) => setSettings({ ...settings, startDate: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              End Date
            </label>
            <input
              type="date"
              value={settings.endDate}
              onChange={(e) => setSettings({ ...settings, endDate: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Initial Balance ($)
            </label>
            <input
              type="number"
              value={settings.initialBalance}
              onChange={(e) => setSettings({ ...settings, initialBalance: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              min="1000"
              step="1000"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Risk per Trade (%)
            </label>
            <input
              type="number"
              value={settings.riskPerTrade}
              onChange={(e) => setSettings({ ...settings, riskPerTrade: parseFloat(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              min="0.1"
              max="10"
              step="0.1"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Strategy
            </label>
            <select
              value={settings.strategy}
              onChange={(e) => setSettings({ ...settings, strategy: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
            >
              <option value="ai_parser">AI Signal Parser</option>
              <option value="regex_parser">Regex Parser</option>
              <option value="ocr_parser">OCR Parser</option>
              <option value="combined">Combined Strategy</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Symbols
            </label>
            <select
              multiple
              value={settings.symbols}
              onChange={(e) => setSettings({ ...settings, symbols: Array.from(e.target.selectedOptions, option => option.value) })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
            >
              <option value="EURUSD">EUR/USD</option>
              <option value="GBPUSD">GBP/USD</option>
              <option value="USDJPY">USD/JPY</option>
              <option value="XAUUSD">XAU/USD (Gold)</option>
              <option value="XAGUSD">XAG/USD (Silver)</option>
              <option value="USOIL">US Oil</option>
            </select>
          </div>
        </div>

        <div className="mt-6 flex gap-2">
          <Button 
            onClick={handleRunBacktest}
            disabled={isRunning}
            className="flex-1 md:flex-none"
          >
            {isRunning ? (
              <>
                <Pause className="h-4 w-4 mr-2" />
                Running...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Run Backtest
              </>
            )}
          </Button>
          
          {backtestResults && (
            <Button 
              variant="outline"
              onClick={handleExportResults}
            >
              <Download className="h-4 w-4 mr-2" />
              Export Results
            </Button>
          )}
        </div>
      </div>

      {/* Backtest Results */}
      {backtestResults && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Total Trades</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {backtestResults.summary.totalTrades}
                  </p>
                </div>
                <Activity className="h-8 w-8 text-blue-600 dark:text-blue-400" />
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Win Rate</p>
                  <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                    {backtestResults.summary.winRate}%
                  </p>
                </div>
                <Target className="h-8 w-8 text-green-600 dark:text-green-400" />
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Total Profit</p>
                  <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                    ${backtestResults.summary.totalProfit}
                  </p>
                </div>
                <DollarSign className="h-8 w-8 text-green-600 dark:text-green-400" />
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Max Drawdown</p>
                  <p className="text-2xl font-bold text-red-600 dark:text-red-400">
                    {backtestResults.summary.maxDrawdown}%
                  </p>
                </div>
                <TrendingDown className="h-8 w-8 text-red-600 dark:text-red-400" />
              </div>
            </div>
          </div>

          {/* Performance Metrics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Performance Metrics
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Total Return</span>
                  <span className="font-medium text-green-600 dark:text-green-400">
                    {backtestResults.summary.totalReturn}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Sharpe Ratio</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {backtestResults.summary.sharpeRatio}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Avg Win Amount</span>
                  <span className="font-medium text-green-600 dark:text-green-400">
                    ${backtestResults.summary.avgWinAmount}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Avg Loss Amount</span>
                  <span className="font-medium text-red-600 dark:text-red-400">
                    ${backtestResults.summary.avgLossAmount}
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Monthly Returns
              </h3>
              <div className="space-y-2">
                {backtestResults.monthlyReturns.map((month: any) => (
                  <div key={month.month} className="flex justify-between items-center">
                    <span className="text-gray-600 dark:text-gray-400">{month.month}</span>
                    <span className={`font-medium ${
                      month.return >= 0 
                        ? 'text-green-600 dark:text-green-400' 
                        : 'text-red-600 dark:text-red-400'
                    }`}>
                      ${month.return}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Equity Curve */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Equity Curve
            </h3>
            <div className="h-64 flex items-end gap-1">
              {backtestResults.equity.map((point: any, index: number) => (
                <div
                  key={index}
                  className="bg-blue-500 rounded-t flex-1 min-w-0"
                  style={{ 
                    height: `${((point.value - 9000) / 4000) * 100}%`,
                    minHeight: '4px'
                  }}
                  title={`Day ${point.day}: $${point.value.toFixed(2)}`}
                />
              ))}
            </div>
            <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
              Portfolio value over time (hover for details)
            </div>
          </div>
        </>
      )}
    </div>
  );
}