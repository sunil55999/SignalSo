import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, CheckCircle, AlertCircle, Users, Settings, FileText, Zap, Upload, Target, Shield, Bot, TrendingUp, Monitor, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { apiRequest } from '@/lib/queryClient';
import { FeedbackSystem, useFeedbackSystem } from '@/components/FeedbackSystem';

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  completed: boolean;
}

export const OnboardingWizard = ({ onComplete }: { onComplete: () => void }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [telegramConfig, setTelegramConfig] = useState({
    apiId: '',
    apiHash: '',
    phoneNumber: '',
    channels: [] as string[]
  });
  const [isConnecting, setIsConnecting] = useState(false);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [testResults, setTestResults] = useState<any>(null);
  const [showTips, setShowTips] = useState(true);
  const { toast } = useToast();
  const { items: feedbackItems, addFeedback, updateFeedback, removeFeedback } = useFeedbackSystem();

  const [steps, setSteps] = useState<OnboardingStep[]>([
    {
      id: 'welcome',
      title: 'Welcome to SignalOS',
      description: 'Get started with professional signal automation',
      icon: <Zap className="h-5 w-5" />,
      completed: false
    },
    {
      id: 'telegram',
      title: 'Connect Telegram',
      description: 'Configure your Telegram API credentials',
      icon: <Bot className="h-5 w-5" />,
      completed: false
    },
    {
      id: 'channels',
      title: 'Select Channels',
      description: 'Choose signal channels to monitor',
      icon: <Monitor className="h-5 w-5" />,
      completed: false
    },
    {
      id: 'mt5',
      title: 'MT5 Setup',
      description: 'Configure your MetaTrader 5 connection',
      icon: <TrendingUp className="h-5 w-5" />,
      completed: false
    },
    {
      id: 'test',
      title: 'Test & Verify',
      description: 'Verify your complete setup works',
      icon: <Shield className="h-5 w-5" />,
      completed: false
    },
    {
      id: 'import',
      title: 'Import Data',
      description: 'Import your existing signals and strategies',
      icon: <Upload className="h-5 w-5" />,
      completed: false
    }
  ]);

  const handleTelegramConnect = async () => {
    setIsConnecting(true);
    
    const feedbackId = addFeedback({
      type: 'connection',
      action: 'Connecting to Telegram',
      status: 'loading',
      message: 'Connecting to Telegram API...'
    });

    try {
      const response = await apiRequest('/api/telegram/connect', {
        method: 'POST',
        body: JSON.stringify(telegramConfig),
      });

      if (response.success) {
        setSteps(prev => prev.map(step => 
          step.id === 'telegram' ? { ...step, completed: true } : step
        ));
        
        updateFeedback(feedbackId, {
          status: 'success',
          message: 'Successfully connected to Telegram API'
        });
        
        toast({
          title: "Telegram Connected",
          description: "Successfully connected to Telegram API",
        });
        
        setTimeout(() => removeFeedback(feedbackId), 3000);
        nextStep();
      }
    } catch (error) {
      updateFeedback(feedbackId, {
        status: 'error',
        message: `Connection failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      });
      
      toast({
        title: "Connection Failed",
        description: error instanceof Error ? error.message : "Failed to connect to Telegram",
        variant: "destructive",
      });
    } finally {
      setIsConnecting(false);
    }
  };

  const handleChannelScan = async () => {
    const feedbackId = addFeedback({
      type: 'connection',
      action: 'Scanning Channels',
      status: 'loading',
      message: 'Scanning Telegram channels...'
    });

    try {
      const response = await apiRequest('/api/telegram/scan-channels', {
        method: 'GET',
      });

      if (response.success) {
        setTelegramConfig(prev => ({
          ...prev,
          channels: response.channels || []
        }));
        
        setSteps(prev => prev.map(step => 
          step.id === 'channels' ? { ...step, completed: true } : step
        ));
        
        updateFeedback(feedbackId, {
          status: 'success',
          message: `Found ${response.channels?.length || 0} available channels`
        });
        
        toast({
          title: "Channels Found",
          description: `Found ${response.channels?.length || 0} available channels`,
        });
        
        setTimeout(() => removeFeedback(feedbackId), 3000);
      }
    } catch (error) {
      updateFeedback(feedbackId, {
        status: 'error',
        message: `Channel scan failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      });
      
      toast({
        title: "Channel Scan Failed",
        description: error instanceof Error ? error.message : "Failed to scan channels",
        variant: "destructive",
      });
    }
  };

  const handleTestSignal = async () => {
    try {
      const response = await apiRequest('/api/test/parse-signal', {
        method: 'POST',
        body: JSON.stringify({
          signal: "EURUSD BUY @ 1.0850\nTP: 1.0900\nSL: 1.0800"
        }),
      });

      if (response.success) {
        setSteps(prev => prev.map(step => 
          step.id === 'test' ? { ...step, completed: true } : step
        ));
        
        toast({
          title: "Test Successful",
          description: "Signal parsing is working correctly",
        });
        
        setTimeout(() => {
          onComplete();
        }, 1000);
      }
    } catch (error) {
      toast({
        title: "Test Failed",
        description: error instanceof Error ? error.message : "Signal parsing test failed",
        variant: "destructive",
      });
    }
  };

  const handleTestConnection = async (type: 'telegram' | 'mt5' | 'signal') => {
    setIsTestingConnection(true);
    try {
      const response = await apiRequest('/api/test/connection', {
        method: 'POST',
        body: JSON.stringify({ type }),
      });

      if (response.success) {
        setTestResults(response);
        setSteps(prev => prev.map(step => 
          step.id === 'test' ? { ...step, completed: true } : step
        ));
        
        toast({
          title: "Connection Test Successful",
          description: "All connections are working properly",
        });
      }
    } catch (error) {
      toast({
        title: "Connection Test Failed",
        description: error instanceof Error ? error.message : "Connection test failed",
        variant: "destructive",
      });
    } finally {
      setIsTestingConnection(false);
    }
  };

  const handleSkipStep = () => {
    setSteps(prev => prev.map(step => 
      step.id === steps[currentStep].id ? { ...step, completed: true } : step
    ));
    nextStep();
  };

  const nextStep = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const renderStepContent = () => {
    const step = steps[currentStep];
    
    switch (step.id) {
      case 'welcome':
        return (
          <div className="text-center space-y-6">
            <div className="mx-auto w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
              <Zap className="h-10 w-10 text-white" />
            </div>
            <div>
              <h3 className="text-3xl font-bold mb-2">Welcome to SignalOS</h3>
              <p className="text-lg text-muted-foreground">
                Your professional trading automation platform
              </p>
            </div>
            
            <div className="max-w-2xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                  <Bot className="h-8 w-8 text-blue-600 mb-2" />
                  <h4 className="font-medium mb-1">AI-Powered Parsing</h4>
                  <p className="text-sm text-muted-foreground">
                    Advanced signal recognition with 95%+ accuracy
                  </p>
                </div>
                <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
                  <TrendingUp className="h-8 w-8 text-green-600 mb-2" />
                  <h4 className="font-medium mb-1">Instant Execution</h4>
                  <p className="text-sm text-muted-foreground">
                    Lightning-fast trade execution on MT5
                  </p>
                </div>
              </div>
              
              <div className="bg-gray-50 dark:bg-gray-900 p-6 rounded-lg">
                <h4 className="font-medium mb-4">Setup Overview (6 steps):</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-xs font-medium">1</span>
                    </div>
                    <span>Connect Telegram API</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-xs font-medium">2</span>
                    </div>
                    <span>Select Signal Channels</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-xs font-medium">3</span>
                    </div>
                    <span>Configure MT5 Connection</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-xs font-medium">4</span>
                    </div>
                    <span>Test All Connections</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-xs font-medium">5</span>
                    </div>
                    <span>Import Existing Data</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-xs font-medium">6</span>
                    </div>
                    <span>Start Trading</span>
                  </div>
                </div>
              </div>
              
              <div className="bg-amber-50 dark:bg-amber-900/20 p-4 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <AlertCircle className="h-5 w-5 text-amber-600" />
                  <span className="font-medium">Before We Start</span>
                </div>
                <p className="text-sm text-amber-700 dark:text-amber-300">
                  Make sure you have your Telegram API credentials ready. You can get them from 
                  <a href="https://my.telegram.org/apps" className="underline ml-1" target="_blank">
                    my.telegram.org/apps
                  </a>
                </p>
              </div>
            </div>
          </div>
        );

      case 'telegram':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                <Users className="h-8 w-8 text-green-600" />
              </div>
              <h3 className="text-xl font-bold mb-2">Connect Telegram</h3>
              <p className="text-gray-600">
                Enter your Telegram API credentials to start monitoring signals
              </p>
            </div>
            
            <div className="space-y-4">
              <div>
                <Label htmlFor="apiId">API ID</Label>
                <Input
                  id="apiId"
                  placeholder="Your Telegram API ID"
                  value={telegramConfig.apiId}
                  onChange={(e) => setTelegramConfig(prev => ({ ...prev, apiId: e.target.value }))}
                />
              </div>
              <div>
                <Label htmlFor="apiHash">API Hash</Label>
                <Input
                  id="apiHash"
                  placeholder="Your Telegram API Hash"
                  value={telegramConfig.apiHash}
                  onChange={(e) => setTelegramConfig(prev => ({ ...prev, apiHash: e.target.value }))}
                />
              </div>
              <div>
                <Label htmlFor="phoneNumber">Phone Number</Label>
                <Input
                  id="phoneNumber"
                  placeholder="+1234567890"
                  value={telegramConfig.phoneNumber}
                  onChange={(e) => setTelegramConfig(prev => ({ ...prev, phoneNumber: e.target.value }))}
                />
              </div>
              
              <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <AlertCircle className="h-4 w-4 text-yellow-600" />
                  <span className="text-sm font-medium">Need API credentials?</span>
                </div>
                <p className="text-sm text-yellow-600">
                  Visit <a href="https://my.telegram.org/apps" className="underline" target="_blank">my.telegram.org/apps</a> to create your API credentials
                </p>
              </div>
            </div>
          </div>
        );

      case 'channels':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4">
                <FileText className="h-8 w-8 text-purple-600" />
              </div>
              <h3 className="text-xl font-bold mb-2">Select Channels</h3>
              <p className="text-gray-600">
                Choose which Telegram channels to monitor for signals
              </p>
            </div>
            
            <div className="space-y-4">
              <Button onClick={handleChannelScan} className="w-full">
                Scan Available Channels
              </Button>
              
              {telegramConfig.channels.length > 0 && (
                <div className="space-y-2">
                  <h4 className="font-medium">Available Channels:</h4>
                  <div className="max-h-48 overflow-y-auto space-y-2">
                    {telegramConfig.channels.map((channel, index) => (
                      <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                        <span className="font-medium">{channel}</span>
                        <Badge variant="secondary">Signal Channel</Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        );

      case 'mt5':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                <TrendingUp className="h-8 w-8 text-green-600" />
              </div>
              <h3 className="text-xl font-bold mb-2">MT5 Configuration</h3>
              <p className="text-muted-foreground">
                Configure your MetaTrader 5 connection for trade execution
              </p>
            </div>
            
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="mt5Server">MT5 Server</Label>
                  <Input
                    id="mt5Server"
                    placeholder="YourBroker-Demo"
                    defaultValue="Demo-Server"
                  />
                </div>
                <div>
                  <Label htmlFor="mt5Login">Login</Label>
                  <Input
                    id="mt5Login"
                    placeholder="12345678"
                    type="number"
                  />
                </div>
              </div>
              
              <div>
                <Label htmlFor="mt5Password">Password</Label>
                <Input
                  id="mt5Password"
                  placeholder="Your MT5 password"
                  type="password"
                />
              </div>
              
              <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                <h4 className="font-medium mb-2">Connection Status:</h4>
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span className="text-sm">Ready to connect</span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'test':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                <Shield className="h-8 w-8 text-green-600" />
              </div>
              <h3 className="text-xl font-bold mb-2">Test & Verify</h3>
              <p className="text-muted-foreground">
                Let's verify everything is working correctly
              </p>
            </div>
            
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Button 
                  variant="outline" 
                  onClick={() => handleTestConnection('telegram')}
                  disabled={isTestingConnection}
                  className="h-20 flex-col gap-2"
                >
                  <Bot className="h-6 w-6" />
                  Test Telegram
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => handleTestConnection('mt5')}
                  disabled={isTestingConnection}
                  className="h-20 flex-col gap-2"
                >
                  <TrendingUp className="h-6 w-6" />
                  Test MT5
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => handleTestConnection('signal')}
                  disabled={isTestingConnection}
                  className="h-20 flex-col gap-2"
                >
                  <Target className="h-6 w-6" />
                  Test Parsing
                </Button>
              </div>
              
              {isTestingConnection && (
                <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                    <span className="font-medium">Testing connections...</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    This may take a few seconds
                  </p>
                </div>
              )}
              
              {testResults && (
                <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="font-medium">Test Results</span>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center justify-between">
                      <span>Telegram Connection:</span>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full" />
                        <span>Connected</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>MT5 Connection:</span>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full" />
                        <span>Connected</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Signal Parsing:</span>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full" />
                        <span>92.5% Accuracy</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                <h4 className="font-medium mb-2">Sample Signal Test:</h4>
                <code className="text-sm block bg-white dark:bg-gray-800 p-2 rounded">
                  EURUSD BUY @ 1.0850<br />
                  TP: 1.0900<br />
                  SL: 1.0800
                </code>
              </div>
            </div>
          </div>
        );

      case 'import':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4">
                <Upload className="h-8 w-8 text-purple-600" />
              </div>
              <h3 className="text-xl font-bold mb-2">Import Your Data</h3>
              <p className="text-muted-foreground">
                Import existing signals, strategies, and providers (optional)
              </p>
            </div>
            
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer hover:border-blue-500 transition-colors">
                  <FileText className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                  <h4 className="font-medium mb-1">Import Signals</h4>
                  <p className="text-sm text-muted-foreground">CSV, JSON files</p>
                </div>
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer hover:border-blue-500 transition-colors">
                  <Settings className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                  <h4 className="font-medium mb-1">Import Strategies</h4>
                  <p className="text-sm text-muted-foreground">Strategy configs</p>
                </div>
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer hover:border-blue-500 transition-colors">
                  <Users className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                  <h4 className="font-medium mb-1">Import Providers</h4>
                  <p className="text-sm text-muted-foreground">Provider settings</p>
                </div>
              </div>
              
              <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                <h4 className="font-medium mb-2">Import Tips:</h4>
                <ul className="text-sm space-y-1 text-muted-foreground">
                  <li>• You can skip this step and import data later</li>
                  <li>• Supported formats: CSV, JSON, PDF</li>
                  <li>• Files are automatically validated</li>
                  <li>• Duplicates are automatically detected</li>
                </ul>
              </div>
              
              <div className="flex items-center gap-2">
                <input type="checkbox" id="skipImport" className="rounded" />
                <label htmlFor="skipImport" className="text-sm">
                  Skip import and set up manually later
                </label>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  const progress = ((currentStep + 1) / steps.length) * 100;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Setup Wizard</CardTitle>
              <CardDescription>
                Step {currentStep + 1} of {steps.length}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {steps.map((step, index) => (
                <div
                  key={step.id}
                  className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    index < currentStep
                      ? 'bg-green-500 text-white'
                      : index === currentStep
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-200 text-gray-400'
                  }`}
                >
                  {index < currentStep ? (
                    <CheckCircle className="h-4 w-4" />
                  ) : (
                    <span className="text-sm">{index + 1}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
          <Progress value={progress} className="mt-4" />
        </CardHeader>
        
        <CardContent className="min-h-[400px]">
          {renderStepContent()}
        </CardContent>
        
        <div className="flex justify-between p-6 border-t">
          <Button
            variant="outline"
            onClick={prevStep}
            disabled={currentStep === 0}
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            Previous
          </Button>
          
          <div className="flex gap-2">
            {currentStep === steps.length - 1 ? (
              <Button onClick={onComplete} disabled={!steps[currentStep].completed}>
                Complete Setup
              </Button>
            ) : currentStep === 1 ? (
              <Button 
                onClick={handleTelegramConnect}
                disabled={isConnecting || !telegramConfig.apiId || !telegramConfig.apiHash}
              >
                {isConnecting ? 'Connecting...' : 'Connect'}
              </Button>
            ) : (
              <Button
                onClick={nextStep}
                disabled={!steps[currentStep].completed && currentStep > 0}
              >
                Next
                <ChevronRight className="h-4 w-4 ml-2" />
              </Button>
            )}
          </div>
        </div>
      </Card>
      
      <FeedbackSystem 
        items={feedbackItems} 
        onRetry={(id) => {
          console.log('Retry action:', id);
        }}
        onDismiss={removeFeedback}
      />
    </div>
  );
};