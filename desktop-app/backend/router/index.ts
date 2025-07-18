import { signalParser } from '../parser';
import { tradeExecutor } from '../executor';
import { telegramManager, TelegramMessage } from '../telegram';
import { logManager } from '../logs';
import { configManager } from '../config';
import { authManager } from '../auth';
import { ParsedSignalData } from '@shared/schema';

export interface SignalProcessingResult {
  success: boolean;
  signalId?: string;
  tradeId?: string;
  error?: string;
  confidence?: number;
}

export class SignalRouter {
  private isRunning = false;
  private retryQueue: Map<string, { signal: TelegramMessage; retries: number }> = new Map();
  private maxRetries = 3;
  private retryDelay = 5000; // 5 seconds

  async start(): Promise<void> {
    if (this.isRunning) {
      logManager.warning('Signal router already running', 'router');
      return;
    }

    // Check authentication
    if (!authManager.isAuthenticated()) {
      logManager.error('Authentication required to start signal router', 'router');
      throw new Error('Authentication required');
    }

    // Check license
    const license = await authManager.checkLicense();
    if (!license.isValid) {
      logManager.error('Invalid license - cannot start signal router', 'router');
      throw new Error('Invalid license');
    }

    // Connect to MT5
    const connected = await tradeExecutor.connect();
    if (!connected) {
      logManager.error('Failed to connect to MT5', 'router');
      throw new Error('MT5 connection failed');
    }

    // Set up Telegram message listener
    telegramManager.onMessage(this.handleTelegramMessage.bind(this));

    // Start monitoring configured channels
    const config = configManager.getConfig();
    if (config.telegram.channelIds.length > 0) {
      await telegramManager.startMonitoring(config.telegram.channelIds);
    }

    this.isRunning = true;
    logManager.info('Signal router started successfully', 'router');
  }

  async stop(): Promise<void> {
    if (!this.isRunning) {
      return;
    }

    // Stop Telegram monitoring
    await telegramManager.stopMonitoring();

    // Disconnect from MT5
    await tradeExecutor.disconnect();

    // Clear retry queue
    this.retryQueue.clear();

    this.isRunning = false;
    logManager.info('Signal router stopped', 'router');
  }

  async processSignal(message: TelegramMessage): Promise<SignalProcessingResult> {
    const signalId = `signal_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
    
    try {
      logManager.info(`Processing signal: ${message.text}`, 'router', {
        signalId,
        channelId: message.channelId,
        messageId: message.id
      });

      // Parse the signal
      const parseResult = await signalParser.parseSignal(message.text);
      
      if (!parseResult.success) {
        logManager.error(`Signal parsing failed: ${parseResult.error}`, 'router', {
          signalId,
          originalMessage: message.text,
          error: parseResult.error
        });

        // Check if we should retry
        const config = configManager.getConfig();
        if (config.parser.fallbackEnabled && this.shouldRetry(message.id)) {
          this.scheduleRetry(message);
        }

        return {
          success: false,
          signalId,
          error: parseResult.error,
          confidence: parseResult.confidence
        };
      }

      // Check confidence threshold
      const config = configManager.getConfig();
      if (parseResult.confidence < config.parser.confidenceThreshold) {
        logManager.warning(`Signal confidence below threshold: ${parseResult.confidence}`, 'router', {
          signalId,
          confidence: parseResult.confidence,
          threshold: config.parser.confidenceThreshold
        });

        return {
          success: false,
          signalId,
          error: 'Confidence below threshold',
          confidence: parseResult.confidence
        };
      }

      // Execute the trade
      const executionResult = await tradeExecutor.executeSignal(parseResult.data!);
      
      if (!executionResult.success) {
        logManager.error(`Trade execution failed: ${executionResult.error}`, 'router', {
          signalId,
          parsedData: parseResult.data,
          error: executionResult.error
        });

        return {
          success: false,
          signalId,
          error: executionResult.error,
          confidence: parseResult.confidence
        };
      }

      // Log successful execution
      logManager.info('Signal processed successfully', 'router', {
        signalId,
        tradeId: executionResult.trade?.id,
        ticket: executionResult.ticket,
        symbol: parseResult.data?.symbol,
        action: parseResult.data?.action,
        confidence: parseResult.confidence
      });

      // Remove from retry queue if it was there
      this.retryQueue.delete(message.id);

      return {
        success: true,
        signalId,
        tradeId: executionResult.trade?.id,
        confidence: parseResult.confidence
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      logManager.error(`Signal processing error: ${errorMessage}`, 'router', {
        signalId,
        originalMessage: message.text,
        error: errorMessage
      });

      return {
        success: false,
        signalId,
        error: errorMessage
      };
    }
  }

  getStatus(): {
    isRunning: boolean;
    retryQueueSize: number;
    mt5Connected: boolean;
    telegramConnected: boolean;
    monitoredChannels: string[];
  } {
    return {
      isRunning: this.isRunning,
      retryQueueSize: this.retryQueue.size,
      mt5Connected: tradeExecutor.getConnectionStatus().isConnected,
      telegramConnected: telegramManager.getSession().isLoggedIn,
      monitoredChannels: telegramManager.getMonitoredChannels()
    };
  }

  private async handleTelegramMessage(message: TelegramMessage): Promise<void> {
    if (!this.isRunning) {
      return;
    }

    // Process the signal
    await this.processSignal(message);
  }

  private shouldRetry(messageId: string): boolean {
    const entry = this.retryQueue.get(messageId);
    return !entry || entry.retries < this.maxRetries;
  }

  private scheduleRetry(message: TelegramMessage): void {
    const entry = this.retryQueue.get(message.id);
    const retries = entry ? entry.retries + 1 : 1;
    
    if (retries <= this.maxRetries) {
      this.retryQueue.set(message.id, { signal: message, retries });
      
      setTimeout(() => {
        if (this.retryQueue.has(message.id)) {
          logManager.info(`Retrying signal processing (attempt ${retries}/${this.maxRetries})`, 'router', {
            messageId: message.id,
            retries
          });
          
          this.processSignal(message);
        }
      }, this.retryDelay * retries); // Exponential backoff
    }
  }
}

// Export default instance
export const signalRouter = new SignalRouter();