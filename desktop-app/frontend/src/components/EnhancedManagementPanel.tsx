import React, { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Upload, Download, Play, Pause, Plus, Edit, Trash2, Copy, 
  CheckCircle, XCircle, AlertCircle, Clock, FileText, Users, 
  Settings, Zap, Search, Filter, RefreshCw, Target, TrendingUp,
  Bot, Shield, Activity, Signal, BarChart3, Monitor
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import { apiRequest } from '@/lib/queryClient';
import { FeedbackSystem, useFeedbackSystem } from '@/components/FeedbackSystem';

interface Provider {
  id: string;
  name: string;
  status: 'active' | 'paused' | 'stopped';
  accuracy: number;
  totalSignals: number;
}

interface Strategy {
  id: string;
  name: string;
  riskLevel: 'Low' | 'Medium' | 'High';
  winRate: number;
  status: 'active' | 'paused' | 'stopped';
}

interface TestResult {
  winRate?: number;
  totalTrades?: number;
  profit?: number;
  maxDrawdown?: number;
  connections?: {
    telegram: boolean;
    mt5: boolean;
    internet: boolean;
  };
  parsed?: {
    symbol: string;
    action: string;
    entryPrice: number;
    stopLoss: number;
    takeProfit: number[];
    confidence: number;
  };
}

export const EnhancedManagementPanel = () => {
  const [activeTab, setActiveTab] = useState<'signals' | 'strategies' | 'providers'>('signals');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAction, setSelectedAction] = useState<string>('');
  const [isImporting, setIsImporting] = useState(false);
  const [importProgress, setImportProgress] = useState(0);
  const [testResults, setTestResults] = useState<TestResult | null>(null);
  const [isRunningTest, setIsRunningTest] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { items: feedbackItems, addFeedback, updateFeedback, removeFeedback } = useFeedbackSystem();

  // Fetch data for all tabs
  const { data: providers, isLoading: providersLoading } = useQuery({
    queryKey: ['/api/providers'],
    refetchInterval: 5000,
  });

  const { data: strategies, isLoading: strategiesLoading } = useQuery({
    queryKey: ['/api/strategies'],
    refetchInterval: 5000,
  });

  const { data: signals, isLoading: signalsLoading } = useQuery({
    queryKey: ['/api/signals'],
    refetchInterval: 3000,
  });

  // Mutations for various actions
  const importMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiRequest('/api/import', { method: 'POST', body: formData });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/providers'] });
      queryClient.invalidateQueries({ queryKey: ['/api/strategies'] });
      queryClient.invalidateQueries({ queryKey: ['/api/signals'] });
      toast({ title: 'Import Successful', description: 'Data imported successfully' });
    },
    onError: (error) => {
      toast({ title: 'Import Failed', description: error.message, variant: 'destructive' });
    }
  });

  const testMutation = useMutation({
    mutationFn: async (testType: 'strategy' | 'connection' | 'parse-signal') => {
      return apiRequest(`/api/test/${testType}`, { method: 'POST' });
    },
    onSuccess: (data) => {
      setTestResults(data);
      toast({ title: 'Test Completed', description: 'Test completed successfully' });
    },
    onError: (error) => {
      toast({ title: 'Test Failed', description: error.message, variant: 'destructive' });
    }
  });

  const handleFileUpload = async (files: FileList) => {
    if (files.length === 0) return;
    
    setIsImporting(true);
    setImportProgress(0);

    const feedbackId = addFeedback({
      type: 'import',
      action: 'Importing Files',
      status: 'loading',
      message: `Importing ${files.length} file(s)...`,
      progress: 0
    });

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const progress = (i / files.length) * 100;
        setImportProgress(progress);
        
        updateFeedback(feedbackId, {
          progress,
          message: `Importing ${file.name}... (${i + 1}/${files.length})`
        });
        
        await importMutation.mutateAsync(file);
      }
      setImportProgress(100);
      
      updateFeedback(feedbackId, {
        status: 'success',
        message: `Successfully imported ${files.length} file(s)`,
        progress: 100
      });
      
      setTimeout(() => removeFeedback(feedbackId), 3000);
    } catch (error) {
      updateFeedback(feedbackId, {
        status: 'error',
        message: `Import failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      });
    } finally {
      setIsImporting(false);
    }
  };

  const handleQuickTest = async (testType: 'strategy' | 'connection' | 'parse-signal') => {
    setIsRunningTest(true);
    setTestResults(null);
    
    const feedbackId = addFeedback({
      type: 'test',
      action: 'Running Test',
      status: 'loading',
      message: `Testing ${testType}...`
    });
    
    try {
      await testMutation.mutateAsync(testType);
      
      updateFeedback(feedbackId, {
        status: 'success',
        message: `${testType} test completed successfully`
      });
      
      setTimeout(() => removeFeedback(feedbackId), 3000);
    } catch (error) {
      updateFeedback(feedbackId, {
        status: 'error',
        message: `Test failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      });
    } finally {
      setIsRunningTest(false);
    }
  };

  const handleExport = async (type: 'signals' | 'strategies' | 'providers') => {
    const feedbackId = addFeedback({
      type: 'export',
      action: 'Exporting Data',
      status: 'loading',
      message: `Exporting ${type} data...`
    });
    
    try {
      const response = await apiRequest(`/api/export/${type}`, { method: 'GET' });
      
      // Create and download file
      const blob = new Blob([JSON.stringify(response, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${type}_export_${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      updateFeedback(feedbackId, {
        status: 'success',
        message: `Successfully exported ${type} data`
      });
      
      toast({ title: 'Export Complete', description: `${type} exported successfully` });
      setTimeout(() => removeFeedback(feedbackId), 3000);
    } catch (error) {
      updateFeedback(feedbackId, {
        status: 'error',
        message: `Export failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      });
      toast({ title: 'Export Failed', description: error instanceof Error ? error.message : 'Unknown error', variant: 'destructive' });
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge variant="default" className="bg-green-500">Active</Badge>;
      case 'paused':
        return <Badge variant="secondary">Paused</Badge>;
      case 'stopped':
        return <Badge variant="destructive">Stopped</Badge>;
      default:
        return <Badge variant="outline">Unknown</Badge>;
    }
  };

  const renderQuickActions = () => (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="h-5 w-5" />
          Quick Actions
        </CardTitle>
        <CardDescription>
          Common tasks with instant feedback
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            disabled={isImporting}
            className="h-20 flex-col gap-2"
          >
            <Upload className="h-6 w-6" />
            {isImporting ? 'Importing...' : 'Import Data'}
          </Button>
          
          <Button
            variant="outline"
            onClick={() => handleExport(activeTab)}
            className="h-20 flex-col gap-2"
          >
            <Download className="h-6 w-6" />
            Export {activeTab}
          </Button>
          
          <Button
            variant="outline"
            onClick={() => handleQuickTest('strategy')}
            disabled={isRunningTest}
            className="h-20 flex-col gap-2"
          >
            <Target className="h-6 w-6" />
            {isRunningTest ? 'Testing...' : 'Test Strategy'}
          </Button>
          
          <Button
            variant="outline"
            onClick={() => handleQuickTest('connection')}
            disabled={isRunningTest}
            className="h-20 flex-col gap-2"
          >
            <Shield className="h-6 w-6" />
            Test Connection
          </Button>
        </div>

        {/* Import Progress */}
        {isImporting && (
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Importing files...</span>
              <span className="text-sm text-muted-foreground">{Math.round(importProgress)}%</span>
            </div>
            <Progress value={importProgress} className="w-full" />
          </div>
        )}

        {/* Test Results */}
        {testResults && (
          <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
            <h4 className="font-medium mb-2 flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-600" />
              Test Results
            </h4>
            {testResults.winRate && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Win Rate:</span>
                  <span className="font-medium ml-2">{testResults.winRate}%</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Total Trades:</span>
                  <span className="font-medium ml-2">{testResults.totalTrades}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Profit:</span>
                  <span className="font-medium ml-2 text-green-600">${testResults.profit}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Max Drawdown:</span>
                  <span className="font-medium ml-2">{testResults.maxDrawdown}%</span>
                </div>
              </div>
            )}
            {testResults.connections && (
              <div className="flex gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${testResults.connections.telegram ? 'bg-green-500' : 'bg-red-500'}`} />
                  Telegram
                </div>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${testResults.connections.mt5 ? 'bg-green-500' : 'bg-red-500'}`} />
                  MT5
                </div>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${testResults.connections.internet ? 'bg-green-500' : 'bg-red-500'}`} />
                  Internet
                </div>
              </div>
            )}
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".csv,.json,.pdf"
          onChange={(e) => e.target.files && handleFileUpload(e.target.files)}
          className="hidden"
        />
      </CardContent>
    </Card>
  );

  const renderProviders = () => (
    <div className="space-y-4">
      {providers?.map((provider: Provider) => (
        <Card key={provider.id} className="hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <Users className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-medium">{provider.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    {provider.totalSignals} signals • {provider.accuracy}% accuracy
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {getStatusBadge(provider.status)}
                <Button variant="ghost" size="sm">
                  <Edit className="h-4 w-4" />
                </Button>
              </div>
            </div>
            
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Accuracy:</span>
                <div className="font-medium">{provider.accuracy}%</div>
              </div>
              <div>
                <span className="text-muted-foreground">Total Signals:</span>
                <div className="font-medium">{provider.totalSignals}</div>
              </div>
              <div>
                <span className="text-muted-foreground">Status:</span>
                <div className="font-medium">{provider.status}</div>
              </div>
            </div>
            
            <div className="flex gap-2 mt-4">
              <Button size="sm" variant="outline">
                <Play className="h-4 w-4 mr-2" />
                Start
              </Button>
              <Button size="sm" variant="outline">
                <Pause className="h-4 w-4 mr-2" />
                Pause
              </Button>
              <Button size="sm" variant="outline">
                <BarChart3 className="h-4 w-4 mr-2" />
                Analytics
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );

  const renderStrategies = () => (
    <div className="space-y-4">
      {strategies?.map((strategy: Strategy) => (
        <Card key={strategy.id} className="hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
                  <Settings className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <h3 className="font-medium">{strategy.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    {strategy.riskLevel} Risk • {strategy.winRate}% Win Rate
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {getStatusBadge(strategy.status)}
                <Button variant="ghost" size="sm">
                  <Edit className="h-4 w-4" />
                </Button>
              </div>
            </div>
            
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Win Rate:</span>
                <div className="font-medium">{strategy.winRate}%</div>
              </div>
              <div>
                <span className="text-muted-foreground">Risk Level:</span>
                <div className="font-medium">{strategy.riskLevel}</div>
              </div>
              <div>
                <span className="text-muted-foreground">Status:</span>
                <div className="font-medium">{strategy.status}</div>
              </div>
            </div>
            
            <div className="flex gap-2 mt-4">
              <Button size="sm" variant="outline">
                <Play className="h-4 w-4 mr-2" />
                Deploy
              </Button>
              <Button size="sm" variant="outline">
                <Target className="h-4 w-4 mr-2" />
                Backtest
              </Button>
              <Button size="sm" variant="outline">
                <Copy className="h-4 w-4 mr-2" />
                Clone
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );

  const renderSignals = () => (
    <div className="space-y-4">
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-medium">Live Signal Feed</h3>
              <p className="text-sm text-muted-foreground">Real-time signal monitoring</p>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-sm">Live</span>
            </div>
          </div>
          
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                    <Signal className="h-4 w-4 text-green-600" />
                  </div>
                  <div>
                    <div className="font-medium">EUR/USD BUY</div>
                    <div className="text-sm text-muted-foreground">Entry: 1.0850 • SL: 1.0800</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-medium">92.5%</div>
                  <div className="text-xs text-muted-foreground">Confidence</div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Management Center</h2>
          <p className="text-muted-foreground">
            Import, export, and manage your trading automation
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button size="sm">
            <Plus className="h-4 w-4 mr-2" />
            Add New
          </Button>
        </div>
      </div>

      {renderQuickActions()}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Data Management</CardTitle>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 w-64"
                />
              </div>
              <Select value={selectedAction} onValueChange={setSelectedAction}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Actions" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="start">Start All</SelectItem>
                  <SelectItem value="pause">Pause All</SelectItem>
                  <SelectItem value="export">Export All</SelectItem>
                  <SelectItem value="backup">Backup</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as any)}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="signals" className="flex items-center gap-2">
                <Signal className="h-4 w-4" />
                Signals
              </TabsTrigger>
              <TabsTrigger value="strategies" className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Strategies
              </TabsTrigger>
              <TabsTrigger value="providers" className="flex items-center gap-2">
                <Users className="h-4 w-4" />
                Providers
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="signals" className="mt-6">
              {signalsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-6 w-6 animate-spin" />
                </div>
              ) : (
                renderSignals()
              )}
            </TabsContent>
            
            <TabsContent value="strategies" className="mt-6">
              {strategiesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-6 w-6 animate-spin" />
                </div>
              ) : (
                renderStrategies()
              )}
            </TabsContent>
            
            <TabsContent value="providers" className="mt-6">
              {providersLoading ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-6 w-6 animate-spin" />
                </div>
              ) : (
                renderProviders()
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
      
      <FeedbackSystem 
        items={feedbackItems} 
        onRetry={(id) => {
          // TODO: Implement retry logic
          console.log('Retry:', id);
        }}
        onDismiss={removeFeedback}
      />
    </div>
  );
};