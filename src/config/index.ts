import { SystemConfig, TelegramConfig, MT5Config, ParserConfig } from '@shared/schema';

export interface ConfigSyncResult {
  success: boolean;
  error?: string;
  conflicts?: string[];
}

export class ConfigManager {
  private config: SystemConfig = {
    telegram: {
      apiId: '',
      apiHash: '',
      phoneNumber: '',
      channelIds: []
    },
    mt5: {
      server: '',
      login: '',
      password: '',
      path: 'C:\\Program Files\\MetaTrader 5\\terminal64.exe'
    },
    parser: {
      aiModel: 'phi-3',
      confidenceThreshold: 0.7,
      fallbackEnabled: true,
      language: 'en'
    },
    riskManagement: {
      maxLotSize: 1.0,
      maxDrawdown: 0.1,
      maxDailyTrades: 10
    }
  };

  async loadConfig(): Promise<SystemConfig> {
    try {
      // Simulate loading from local storage or file
      await new Promise(resolve => setTimeout(resolve, 100));
      
      const stored = localStorage.getItem('signalos_config');
      if (stored) {
        this.config = { ...this.config, ...JSON.parse(stored) };
      }
      
      return this.config;
    } catch (error) {
      console.error('Failed to load config:', error);
      return this.config;
    }
  }

  async saveConfig(config: Partial<SystemConfig>): Promise<boolean> {
    try {
      this.config = { ...this.config, ...config };
      
      // Simulate saving to local storage
      await new Promise(resolve => setTimeout(resolve, 100));
      localStorage.setItem('signalos_config', JSON.stringify(this.config));
      
      return true;
    } catch (error) {
      console.error('Failed to save config:', error);
      return false;
    }
  }

  async syncWithCloud(): Promise<ConfigSyncResult> {
    try {
      // Simulate cloud sync
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Mock cloud config
      const cloudConfig = {
        parser: {
          aiModel: 'mistral-7b',
          confidenceThreshold: 0.8,
          fallbackEnabled: true,
          language: 'en'
        }
      };
      
      // Check for conflicts
      const conflicts = this.detectConflicts(cloudConfig);
      
      if (conflicts.length > 0) {
        return {
          success: false,
          conflicts,
          error: 'Configuration conflicts detected'
        };
      }
      
      // Merge cloud config
      this.config = { ...this.config, ...cloudConfig };
      await this.saveConfig(this.config);
      
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: `Cloud sync failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      };
    }
  }

  async exportConfig(): Promise<string> {
    return JSON.stringify(this.config, null, 2);
  }

  async importConfig(configJson: string): Promise<boolean> {
    try {
      const importedConfig = JSON.parse(configJson);
      
      // Validate config structure
      if (!this.validateConfig(importedConfig)) {
        throw new Error('Invalid configuration format');
      }
      
      this.config = importedConfig;
      await this.saveConfig(this.config);
      
      return true;
    } catch (error) {
      console.error('Failed to import config:', error);
      return false;
    }
  }

  getConfig(): SystemConfig {
    return { ...this.config };
  }

  getTelegramConfig(): TelegramConfig {
    return { ...this.config.telegram };
  }

  getMT5Config(): MT5Config {
    return { ...this.config.mt5 };
  }

  getParserConfig(): ParserConfig {
    return { ...this.config.parser };
  }

  updateTelegramConfig(config: Partial<TelegramConfig>): void {
    this.config.telegram = { ...this.config.telegram, ...config };
  }

  updateMT5Config(config: Partial<MT5Config>): void {
    this.config.mt5 = { ...this.config.mt5, ...config };
  }

  updateParserConfig(config: Partial<ParserConfig>): void {
    this.config.parser = { ...this.config.parser, ...config };
  }

  private detectConflicts(cloudConfig: any): string[] {
    const conflicts: string[] = [];
    
    // Check for model conflicts
    if (cloudConfig.parser?.aiModel !== this.config.parser.aiModel) {
      conflicts.push('AI Model version mismatch');
    }
    
    // Check for threshold conflicts
    if (cloudConfig.parser?.confidenceThreshold !== this.config.parser.confidenceThreshold) {
      conflicts.push('Confidence threshold mismatch');
    }
    
    return conflicts;
  }

  private validateConfig(config: any): boolean {
    return !!(
      config &&
      config.telegram &&
      config.mt5 &&
      config.parser &&
      config.riskManagement
    );
  }
}

// Export default instance
export const configManager = new ConfigManager();