import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { 
  TestTube, 
  Play, 
  Copy, 
  Check, 
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Target,
  Shield,
  Clock,
  BarChart3
} from 'lucide-react';

export function SignalValidator() {
  const [testMessage, setTestMessage] = useState('GOLD BUY @ 1950.50 SL 1945.00 TP 1960.00');
  const [parseResult, setParseResult] = useState<any>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [copied, setCopied] = useState(false);
  const { toast } = useToast();

  const sampleSignals = [
    'GOLD BUY @ 1950.50 SL 1945.00 TP 1960.00',
    'EURUSD SELL @ 1.0850 SL 1.0900 TP 1.0800',
    'GBPUSD BUY @ 1.2650 SL 1.2600 TP 1.2750',
    'XAUUSD SELL @ 1955.20 SL 1962.00 TP 1945.00',
    'USDJPY BUY @ 148.50 SL 147.80 TP 149.50',
  ];

  const handleValidateSignal = async () => {
    if (!testMessage.trim()) return;

    setIsProcessing(true);
    setParseResult(null);

    try {
      // Simulate signal parsing
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Mock parsing result
      const mockResult = {
        success: true,
        confidence: 0.85,
        method: 'ai',
        data: {
          symbol: 'GOLD',
          action: 'BUY',
          entryPrice: 1950.50,
          stopLoss: 1945.00,
          takeProfit: [1960.00],
          confidence: 0.85,
          metadata: {
            source: 'ai',
            timestamp: new Date().toISOString(),
            processingTime: '125ms'
          }
        }
      };

      setParseResult(mockResult);
      
      if (mockResult.success) {
        toast({
          title: 'Signal validated successfully',
          description: `Parsed with ${(mockResult.confidence * 100).toFixed(1)}% confidence`,
        });
      } else {
        toast({
          title: 'Signal validation failed',
          description: 'The signal could not be parsed',
          variant: 'destructive',
        });
      }
    } catch (error) {
      toast({
        title: 'Validation error',
        description: 'An error occurred while validating the signal',
        variant: 'destructive',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      toast({
        title: 'Copied to clipboard',
        description: 'Signal has been copied to your clipboard',
      });
    } catch (error) {
      toast({
        title: 'Copy failed',
        description: 'Failed to copy signal to clipboard',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Signal Validator</h1>
        <p className="text-gray-600 dark:text-gray-300">
          Test and validate trading signals with our AI parser
        </p>
      </div>

      {/* Test Input */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Test Signal Parser
        </h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Signal Message
            </label>
            <textarea
              value={testMessage}
              onChange={(e) => setTestMessage(e.target.value)}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white font-mono"
              placeholder="Enter your trading signal here..."
            />
          </div>

          <div className="flex gap-2">
            <Button 
              onClick={handleValidateSignal}
              disabled={isProcessing || !testMessage.trim()}
              className="flex-1 md:flex-none"
            >
              {isProcessing ? (
                <>
                  <TestTube className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Validate Signal
                </>
              )}
            </Button>
            
            <Button 
              variant="outline"
              onClick={() => copyToClipboard(testMessage)}
              disabled={!testMessage.trim()}
            >
              {copied ? (
                <Check className="h-4 w-4" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Parse Result */}
      {parseResult && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            Parse Result
          </h2>
          
          <div className="space-y-4">
            {/* Status */}
            <div className={`flex items-center gap-2 p-3 rounded-lg ${
              parseResult.success 
                ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800' 
                : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
            }`}>
              {parseResult.success ? (
                <Check className="h-5 w-5 text-green-600 dark:text-green-400" />
              ) : (
                <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
              )}
              <span className={`font-medium ${
                parseResult.success 
                  ? 'text-green-800 dark:text-green-200' 
                  : 'text-red-800 dark:text-red-200'
              }`}>
                {parseResult.success ? 'Signal parsed successfully' : 'Signal parsing failed'}
              </span>
            </div>

            {parseResult.success && parseResult.data && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <BarChart3 className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Symbol</span>
                  </div>
                  <p className="text-lg font-bold text-gray-900 dark:text-white">
                    {parseResult.data.symbol}
                  </p>
                </div>

                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    {parseResult.data.action === 'BUY' ? (
                      <TrendingUp className="h-4 w-4 text-green-600 dark:text-green-400" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-red-600 dark:text-red-400" />
                    )}
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Action</span>
                  </div>
                  <p className={`text-lg font-bold ${
                    parseResult.data.action === 'BUY' 
                      ? 'text-green-600 dark:text-green-400' 
                      : 'text-red-600 dark:text-red-400'
                  }`}>
                    {parseResult.data.action}
                  </p>
                </div>

                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Target className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Entry Price</span>
                  </div>
                  <p className="text-lg font-bold text-gray-900 dark:text-white">
                    {parseResult.data.entryPrice}
                  </p>
                </div>

                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Shield className="h-4 w-4 text-red-600 dark:text-red-400" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Stop Loss</span>
                  </div>
                  <p className="text-lg font-bold text-gray-900 dark:text-white">
                    {parseResult.data.stopLoss}
                  </p>
                </div>

                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Target className="h-4 w-4 text-green-600 dark:text-green-400" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Take Profit</span>
                  </div>
                  <p className="text-lg font-bold text-gray-900 dark:text-white">
                    {parseResult.data.takeProfit.join(', ')}
                  </p>
                </div>

                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Confidence</span>
                  </div>
                  <p className="text-lg font-bold text-gray-900 dark:text-white">
                    {(parseResult.data.confidence * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
            )}

            {/* Metadata */}
            {parseResult.data?.metadata && (
              <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <h3 className="font-medium text-gray-900 dark:text-white mb-2">Processing Details</h3>
                <div className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
                  <p>Method: {parseResult.method}</p>
                  <p>Processing Time: {parseResult.data.metadata.processingTime}</p>
                  <p>Timestamp: {new Date(parseResult.data.metadata.timestamp).toLocaleString()}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Sample Signals */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Sample Signals
        </h2>
        
        <div className="space-y-2">
          {sampleSignals.map((signal, index) => (
            <div 
              key={index}
              className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 cursor-pointer"
              onClick={() => setTestMessage(signal)}
            >
              <code className="text-sm font-mono text-gray-900 dark:text-white">
                {signal}
              </code>
              <Button 
                variant="ghost" 
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  copyToClipboard(signal);
                }}
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}