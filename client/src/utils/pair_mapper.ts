/**
 * Pair Mapper Utility
 * Maps signal provider symbols to broker MT5-compatible pair names
 * Supports static config, dynamic overrides, and case-insensitive matching
 */

export interface PairMapping {
  [key: string]: string;
}

export interface PairMapperConfig {
  defaultMappings: PairMapping;
  userOverrides?: PairMapping;
  fallbackToInput?: boolean;
  caseSensitive?: boolean;
}

/**
 * Default symbol mappings from signal providers to MT5 broker pairs
 */
const DEFAULT_MAPPINGS: PairMapping = {
  // Precious Metals
  'GOLD': 'XAUUSD',
  'SILVER': 'XAGUSD',
  'XAUUSD': 'XAUUSD',
  'XAGUSD': 'XAGUSD',
  
  // Cryptocurrencies
  'BTC': 'BTCUSD',
  'BITCOIN': 'BTCUSD',
  'ETH': 'ETHUSD',
  'ETHEREUM': 'ETHUSD',
  'LTC': 'LTCUSD',
  'LITECOIN': 'LTCUSD',
  
  // Indices
  'US30': 'US30.cash',
  'DOW': 'US30.cash',
  'DOWJONES': 'US30.cash',
  'SPX500': 'SPX500.cash',
  'SP500': 'SPX500.cash',
  'NAS100': 'NAS100.cash',
  'NASDAQ': 'NAS100.cash',
  'GER40': 'DAX40.cash',
  'DAX': 'DAX40.cash',
  'UK100': 'UK100.cash',
  'FTSE': 'UK100.cash',
  'JPN225': 'JPN225.cash',
  'NIKKEI': 'JPN225.cash',
  
  // Major Forex Pairs
  'EURUSD': 'EURUSD',
  'GBPUSD': 'GBPUSD',
  'USDJPY': 'USDJPY',
  'USDCHF': 'USDCHF',
  'AUDUSD': 'AUDUSD',
  'USDCAD': 'USDCAD',
  'NZDUSD': 'NZDUSD',
  
  // Cross Pairs
  'EURJPY': 'EURJPY',
  'GBPJPY': 'GBPJPY',
  'EURGBP': 'EURGBP',
  'EURAUD': 'EURAUD',
  'EURCAD': 'EURCAD',
  'GBPAUD': 'GBPAUD',
  'GBPCAD': 'GBPCAD',
  'AUDCAD': 'AUDCAD',
  'AUDJPY': 'AUDJPY',
  'CADJPY': 'CADJPY',
  'CHFJPY': 'CHFJPY',
  'NZDJPY': 'NZDJPY',
  
  // Commodities
  'OIL': 'WTI.cash',
  'CRUDE': 'WTI.cash',
  'WTI': 'WTI.cash',
  'BRENT': 'BRENT.cash',
  'NATGAS': 'NATGAS.cash',
  'GAS': 'NATGAS.cash'
};

/**
 * Storage keys for localStorage persistence
 */
const STORAGE_KEYS = {
  USER_OVERRIDES: 'signalos_pair_overrides',
  CONFIG: 'signalos_pair_config'
} as const;

export class PairMapper {
  private config: PairMapperConfig;
  private combinedMappings: PairMapping;

  constructor(config?: Partial<PairMapperConfig>) {
    this.config = {
      defaultMappings: DEFAULT_MAPPINGS,
      fallbackToInput: true,
      caseSensitive: false,
      ...config
    };

    // Load user overrides from localStorage
    this.loadUserOverrides();
    this.updateCombinedMappings();
  }

  /**
   * Map a symbol to its MT5 pair equivalent
   * @param symbol - The input symbol to map
   * @returns The mapped MT5 pair name or fallback value
   */
  mapSymbol(symbol: string): string {
    if (!symbol) return symbol;

    const searchKey = this.config.caseSensitive ? symbol : symbol.toUpperCase();
    const mapped = this.combinedMappings[searchKey];

    if (mapped) {
      return mapped;
    }

    // Check if input is already a valid MT5 pair
    const isValidMT5 = Object.values(this.combinedMappings).includes(symbol);
    if (isValidMT5) {
      return symbol;
    }

    // Fallback to input if no mapping found
    return this.config.fallbackToInput ? symbol : '';
  }

  /**
   * Map multiple symbols at once
   * @param symbols - Array of symbols to map
   * @returns Array of mapped symbols
   */
  mapSymbols(symbols: string[]): string[] {
    return symbols.map(symbol => this.mapSymbol(symbol));
  }

  /**
   * Add or update user override mappings
   * @param overrides - Object containing symbol mappings to add/update
   */
  addUserOverrides(overrides: PairMapping): void {
    if (!this.config.userOverrides) {
      this.config.userOverrides = {};
    }

    // Normalize keys to uppercase if case-insensitive
    const normalizedOverrides: PairMapping = {};
    Object.entries(overrides).forEach(([key, value]) => {
      const normalizedKey = this.config.caseSensitive ? key : key.toUpperCase();
      normalizedOverrides[normalizedKey] = value;
    });

    Object.assign(this.config.userOverrides, normalizedOverrides);
    this.saveUserOverrides();
    this.updateCombinedMappings();
  }

  /**
   * Remove user override for a specific symbol
   * @param symbol - Symbol to remove override for
   */
  removeUserOverride(symbol: string): void {
    if (!this.config.userOverrides) return;

    const key = this.config.caseSensitive ? symbol : symbol.toUpperCase();
    delete this.config.userOverrides[key];
    this.saveUserOverrides();
    this.updateCombinedMappings();
  }

  /**
   * Clear all user overrides
   */
  clearUserOverrides(): void {
    this.config.userOverrides = {};
    this.saveUserOverrides();
    this.updateCombinedMappings();
  }

  /**
   * Get all current mappings (default + user overrides)
   * @returns Combined mapping object
   */
  getAllMappings(): PairMapping {
    return { ...this.combinedMappings };
  }

  /**
   * Get only user override mappings
   * @returns User override mappings
   */
  getUserOverrides(): PairMapping {
    return { ...(this.config.userOverrides || {}) };
  }

  /**
   * Check if a symbol has a mapping
   * @param symbol - Symbol to check
   * @returns True if mapping exists
   */
  hasMapping(symbol: string): boolean {
    const key = this.config.caseSensitive ? symbol : symbol.toUpperCase();
    return key in this.combinedMappings;
  }

  /**
   * Get reverse mapping (MT5 pair to original symbol)
   * @param mt5Pair - MT5 pair to find original symbol for
   * @returns Array of original symbols that map to this MT5 pair
   */
  getReverseMappings(mt5Pair: string): string[] {
    const results: string[] = [];
    Object.entries(this.combinedMappings).forEach(([symbol, pair]) => {
      if (pair === mt5Pair) {
        results.push(symbol);
      }
    });
    return results;
  }

  /**
   * Export configuration for backup/sharing
   * @returns Serializable configuration object
   */
  exportConfig(): PairMapperConfig {
    return {
      ...this.config,
      userOverrides: { ...(this.config.userOverrides || {}) }
    };
  }

  /**
   * Import configuration from backup/sharing
   * @param config - Configuration to import
   */
  importConfig(config: PairMapperConfig): void {
    this.config = { ...config };
    this.saveUserOverrides();
    this.updateCombinedMappings();
  }

  /**
   * Load user overrides from localStorage
   */
  private loadUserOverrides(): void {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.USER_OVERRIDES);
      if (stored) {
        this.config.userOverrides = JSON.parse(stored);
      }
    } catch (error) {
      console.warn('Failed to load user overrides from localStorage:', error);
      this.config.userOverrides = {};
    }
  }

  /**
   * Save user overrides to localStorage
   */
  private saveUserOverrides(): void {
    try {
      localStorage.setItem(
        STORAGE_KEYS.USER_OVERRIDES,
        JSON.stringify(this.config.userOverrides || {})
      );
    } catch (error) {
      console.warn('Failed to save user overrides to localStorage:', error);
    }
  }

  /**
   * Update the combined mappings object
   */
  private updateCombinedMappings(): void {
    // Start with default mappings
    this.combinedMappings = { ...this.config.defaultMappings };

    // Apply case normalization if needed
    if (!this.config.caseSensitive) {
      const normalizedDefaults: PairMapping = {};
      Object.entries(this.config.defaultMappings).forEach(([key, value]) => {
        normalizedDefaults[key.toUpperCase()] = value;
      });
      this.combinedMappings = normalizedDefaults;
    }

    // Apply user overrides
    if (this.config.userOverrides) {
      Object.assign(this.combinedMappings, this.config.userOverrides);
    }
  }
}

/**
 * Default singleton instance for easy usage
 */
export const defaultPairMapper = new PairMapper();

/**
 * Convenience function for quick symbol mapping
 * @param symbol - Symbol to map
 * @returns Mapped MT5 pair
 */
export function mapSymbol(symbol: string): string {
  return defaultPairMapper.mapSymbol(symbol);
}

/**
 * Convenience function for mapping multiple symbols
 * @param symbols - Array of symbols to map
 * @returns Array of mapped MT5 pairs
 */
export function mapSymbols(symbols: string[]): string[] {
  return defaultPairMapper.mapSymbols(symbols);
}