import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, CheckCircle, AlertCircle, Users, Settings, FileText, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { apiRequest } from '@/lib/queryClient';

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
  const { toast } = useToast();

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
      icon: <Users className="h-5 w-5" />,
      completed: false
    },
    {
      id: 'channels',
      title: 'Select Channels',
      description: 'Choose signal channels to monitor',
      icon: <FileText className="h-5 w-5" />,
      completed: false
    },
    {
      id: 'test',
      title: 'Test Setup',
      description: 'Verify your configuration works',
      icon: <CheckCircle className="h-5 w-5" />,
      completed: false
    }
  ]);

  const handleTelegramConnect = async () => {
    setIsConnecting(true);
    try {
      const response = await apiRequest('/api/telegram/connect', {
        method: 'POST',
        body: JSON.stringify(telegramConfig),
      });

      if (response.success) {
        setSteps(prev => prev.map(step => 
          step.id === 'telegram' ? { ...step, completed: true } : step
        ));
        toast({
          title: "Telegram Connected",
          description: "Successfully connected to Telegram API",
        });
        nextStep();
      }
    } catch (error) {
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
        
        toast({
          title: "Channels Found",
          description: `Found ${response.channels?.length || 0} available channels`,
        });
      }
    } catch (error) {
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
          <div className="text-center space-y-4">
            <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
              <Zap className="h-8 w-8 text-blue-600" />
            </div>
            <h3 className="text-2xl font-bold">Welcome to SignalOS</h3>
            <p className="text-gray-600 max-w-md mx-auto">
              This wizard will help you set up your trading automation system in just a few minutes.
            </p>
            <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
              <h4 className="font-medium mb-2">What you'll set up:</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Connect your Telegram account</li>
                <li>• Select signal channels to monitor</li>
                <li>• Test signal parsing</li>
                <li>• Configure basic settings</li>
              </ul>
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

      case 'test':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                <CheckCircle className="h-8 w-8 text-green-600" />
              </div>
              <h3 className="text-xl font-bold mb-2">Test Your Setup</h3>
              <p className="text-gray-600">
                Let's verify everything is working correctly
              </p>
            </div>
            
            <div className="space-y-4">
              <Button onClick={handleTestSignal} className="w-full">
                Test Signal Parsing
              </Button>
              
              <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                <h4 className="font-medium mb-2">Sample Signal:</h4>
                <code className="text-sm">
                  EURUSD BUY @ 1.0850<br />
                  TP: 1.0900<br />
                  SL: 1.0800
                </code>
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
    </div>
  );
};