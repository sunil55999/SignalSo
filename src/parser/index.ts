import { ParsedSignalData } from '@shared/schema';

export interface ParseResult {
  success: boolean;
  data?: ParsedSignalData;
  error?: string;
  confidence: number;
  method: 'ai' | 'regex' | 'fallback';
}

export interface ParserEngine {
  parse(message: string): Promise<ParseResult>;
  name: string;
  priority: number;
}

// AI Parser Engine
export class AIParserEngine implements ParserEngine {
  name = 'AI Parser';
  priority = 1;

  async parse(message: string): Promise<ParseResult> {
    try {
      // Simulate AI parsing with timeout protection
      const timeoutMs = 5000;
      const parsePromise = this.performAIParsing(message);
      
      const result = await Promise.race([
        parsePromise,
        new Promise<ParseResult>((_, reject) => 
          setTimeout(() => reject(new Error('AI parsing timeout')), timeoutMs)
        )
      ]);
      
      return result;
    } catch (error) {
      return {
        success: false,
        error: `AI parsing failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        confidence: 0,
        method: 'ai'
      };
    }
  }

  private async performAIParsing(message: string): Promise<ParseResult> {
    // Simulate AI model processing delay
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Basic AI-like parsing logic
    const symbolMatch = message.match(/(?:GOLD|XAUUSD|EURUSD|GBPUSD|USDJPY|USDCAD|AUDUSD|NZDUSD|EURJPY|GBPJPY)/i);
    const actionMatch = message.match(/(?:BUY|SELL|LONG|SHORT)/i);
    const entryMatch = message.match(/(?:Entry|@|at)\s*:?\s*(\d+\.?\d*)/i);
    const slMatch = message.match(/(?:SL|Stop Loss|Stop)\s*:?\s*(\d+\.?\d*)/i);
    const tpMatch = message.match(/(?:TP|Take Profit|Target)\s*:?\s*(\d+\.?\d*)/i);
    
    if (!symbolMatch || !actionMatch) {
      return {
        success: false,
        error: 'Could not identify symbol or action',
        confidence: 0,
        method: 'ai'
      };
    }
    
    const symbol = symbolMatch[0].toUpperCase();
    const action = actionMatch[0].toUpperCase() as 'BUY' | 'SELL';
    const entryPrice = entryMatch ? parseFloat(entryMatch[1]) : 0;
    const stopLoss = slMatch ? parseFloat(slMatch[1]) : 0;
    const takeProfit = tpMatch ? [parseFloat(tpMatch[1])] : [];
    
    return {
      success: true,
      data: {
        symbol,
        action,
        entryPrice,
        stopLoss,
        takeProfit,
        confidence: 0.85,
        metadata: { source: 'ai', timestamp: new Date().toISOString() }
      },
      confidence: 0.85,
      method: 'ai'
    };
  }
}

// Regex Parser Engine (fallback)
export class RegexParserEngine implements ParserEngine {
  name = 'Regex Parser';
  priority = 2;

  async parse(message: string): Promise<ParseResult> {
    try {
      const patterns = [
        // Pattern 1: Standard format
        /(?<symbol>GOLD|XAUUSD|EURUSD|GBPUSD|USDJPY|USDCAD|AUDUSD|NZDUSD|EURJPY|GBPJPY)\s*(?<action>BUY|SELL|LONG|SHORT)\s*(?:@|at|entry)?\s*(?<entry>\d+\.?\d*)\s*(?:SL|Stop Loss|Stop)\s*(?<sl>\d+\.?\d*)\s*(?:TP|Take Profit|Target)\s*(?<tp>\d+\.?\d*)/i,
        
        // Pattern 2: Alternative format
        /(?<action>BUY|SELL|LONG|SHORT)\s*(?<symbol>GOLD|XAUUSD|EURUSD|GBPUSD|USDJPY|USDCAD|AUDUSD|NZDUSD|EURJPY|GBPJPY)\s*(?<entry>\d+\.?\d*)\s*(?<sl>\d+\.?\d*)\s*(?<tp>\d+\.?\d*)/i
      ];
      
      for (const pattern of patterns) {
        const match = message.match(pattern);
        if (match && match.groups) {
          const { symbol, action, entry, sl, tp } = match.groups;
          
          return {
            success: true,
            data: {
              symbol: symbol.toUpperCase(),
              action: action.toUpperCase() as 'BUY' | 'SELL',
              entryPrice: parseFloat(entry),
              stopLoss: parseFloat(sl),
              takeProfit: [parseFloat(tp)],
              confidence: 0.7,
              metadata: { source: 'regex', pattern: pattern.source }
            },
            confidence: 0.7,
            method: 'regex'
          };
        }
      }
      
      return {
        success: false,
        error: 'No regex pattern matched',
        confidence: 0,
        method: 'regex'
      };
    } catch (error) {
      return {
        success: false,
        error: `Regex parsing failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        confidence: 0,
        method: 'regex'
      };
    }
  }
}

// Main Parser with fallback chain
export class SignalParser {
  private engines: ParserEngine[] = [
    new AIParserEngine(),
    new RegexParserEngine()
  ];
  
  async parseSignal(message: string): Promise<ParseResult> {
    const sanitizedMessage = this.sanitizeMessage(message);
    
    for (const engine of this.engines) {
      try {
        const result = await engine.parse(sanitizedMessage);
        if (result.success) {
          return result;
        }
      } catch (error) {
        console.error(`Parser engine ${engine.name} failed:`, error);
      }
    }
    
    // Final fallback with reasonable defaults
    return {
      success: false,
      error: 'All parsing engines failed',
      confidence: 0,
      method: 'fallback'
    };
  }
  
  private sanitizeMessage(message: string): string {
    // Remove emojis and special characters
    return message
      .replace(/[\u{1F600}-\u{1F64F}]/gu, '')
      .replace(/[\u{1F300}-\u{1F5FF}]/gu, '')
      .replace(/[\u{1F680}-\u{1F6FF}]/gu, '')
      .replace(/[^\w\s\.\-@:]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }
}

// Export default instance
export const signalParser = new SignalParser();