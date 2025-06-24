/**
 * Unit Tests for PairMapper
 * Tests symbol mapping, user overrides, and configuration management
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { PairMapper, mapSymbol, mapSymbols, defaultPairMapper } from '../utils/pair_mapper';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    }
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

describe('PairMapper', () => {
  let mapper: PairMapper;

  beforeEach(() => {
    localStorageMock.clear();
    mapper = new PairMapper();
  });

  afterEach(() => {
    localStorageMock.clear();
  });

  describe('Basic Symbol Mapping', () => {
    it('should map known aliases correctly', () => {
      expect(mapper.mapSymbol('GOLD')).toBe('XAUUSD');
      expect(mapper.mapSymbol('BTC')).toBe('BTCUSD');
      expect(mapper.mapSymbol('US30')).toBe('US30.cash');
      expect(mapper.mapSymbol('GER40')).toBe('DAX40.cash');
      expect(mapper.mapSymbol('DAX')).toBe('DAX40.cash');
    });

    it('should handle case-insensitive matching by default', () => {
      expect(mapper.mapSymbol('gold')).toBe('XAUUSD');
      expect(mapper.mapSymbol('Gold')).toBe('XAUUSD');
      expect(mapper.mapSymbol('GOLD')).toBe('XAUUSD');
      expect(mapper.mapSymbol('btc')).toBe('BTCUSD');
    });

    it('should return fallback when symbol not found', () => {
      expect(mapper.mapSymbol('UNKNOWN')).toBe('UNKNOWN');
      expect(mapper.mapSymbol('CUSTOM_PAIR')).toBe('CUSTOM_PAIR');
    });

    it('should handle empty and invalid inputs', () => {
      expect(mapper.mapSymbol('')).toBe('');
      expect(mapper.mapSymbol(null as any)).toBe(null);
      expect(mapper.mapSymbol(undefined as any)).toBe(undefined);
    });

    it('should recognize already valid MT5 pairs', () => {
      expect(mapper.mapSymbol('XAUUSD')).toBe('XAUUSD');
      expect(mapper.mapSymbol('EURUSD')).toBe('EURUSD');
      expect(mapper.mapSymbol('DAX40.cash')).toBe('DAX40.cash');
    });
  });

  describe('Multiple Symbol Mapping', () => {
    it('should map multiple symbols correctly', () => {
      const input = ['GOLD', 'BTC', 'US30', 'UNKNOWN'];
      const expected = ['XAUUSD', 'BTCUSD', 'US30.cash', 'UNKNOWN'];
      expect(mapper.mapSymbols(input)).toEqual(expected);
    });

    it('should handle empty array', () => {
      expect(mapper.mapSymbols([])).toEqual([]);
    });
  });

  describe('User Override Configuration', () => {
    it('should apply user overrides correctly', () => {
      mapper.addUserOverrides({
        'CUSTOM': 'CUSTOM.mt5',
        'GOLD': 'XAUUSD_CUSTOM'
      });

      expect(mapper.mapSymbol('CUSTOM')).toBe('CUSTOM.mt5');
      expect(mapper.mapSymbol('GOLD')).toBe('XAUUSD_CUSTOM'); // Override default
    });

    it('should persist user overrides to localStorage', () => {
      mapper.addUserOverrides({
        'TEST': 'TEST.mt5'
      });

      // Create new mapper instance to test persistence
      const newMapper = new PairMapper();
      expect(newMapper.mapSymbol('TEST')).toBe('TEST.mt5');
    });

    it('should remove user overrides', () => {
      mapper.addUserOverrides({
        'TEMP': 'TEMP.mt5'
      });
      expect(mapper.mapSymbol('TEMP')).toBe('TEMP.mt5');

      mapper.removeUserOverride('TEMP');
      expect(mapper.mapSymbol('TEMP')).toBe('TEMP'); // Falls back to input
    });

    it('should clear all user overrides', () => {
      mapper.addUserOverrides({
        'TEMP1': 'TEMP1.mt5',
        'TEMP2': 'TEMP2.mt5'
      });

      mapper.clearUserOverrides();
      expect(mapper.mapSymbol('TEMP1')).toBe('TEMP1');
      expect(mapper.mapSymbol('TEMP2')).toBe('TEMP2');
    });
  });

  describe('Configuration Management', () => {
    it('should export and import configuration', () => {
      mapper.addUserOverrides({
        'EXPORT_TEST': 'EXPORT.mt5'
      });

      const exported = mapper.exportConfig();
      const newMapper = new PairMapper();
      newMapper.importConfig(exported);

      expect(newMapper.mapSymbol('EXPORT_TEST')).toBe('EXPORT.mt5');
    });

    it('should handle case sensitivity configuration', () => {
      const caseSensitiveMapper = new PairMapper({ caseSensitive: true });
      caseSensitiveMapper.addUserOverrides({
        'CasE': 'CASE.mt5'
      });

      expect(caseSensitiveMapper.mapSymbol('CasE')).toBe('CASE.mt5');
      expect(caseSensitiveMapper.mapSymbol('case')).toBe('case'); // No match, fallback
    });

    it('should handle fallback configuration', () => {
      const noFallbackMapper = new PairMapper({ fallbackToInput: false });
      expect(noFallbackMapper.mapSymbol('UNKNOWN')).toBe('');
    });
  });

  describe('Utility Functions', () => {
    it('should check if mapping exists', () => {
      expect(mapper.hasMapping('GOLD')).toBe(true);
      expect(mapper.hasMapping('UNKNOWN')).toBe(false);
    });

    it('should get all mappings', () => {
      const mappings = mapper.getAllMappings();
      expect(mappings.GOLD).toBe('XAUUSD');
      expect(mappings.BTC).toBe('BTCUSD');
    });

    it('should get user overrides only', () => {
      mapper.addUserOverrides({
        'USER1': 'USER1.mt5'
      });

      const overrides = mapper.getUserOverrides();
      expect(overrides.USER1).toBe('USER1.mt5');
      expect(overrides.GOLD).toBeUndefined(); // Should not include defaults
    });

    it('should get reverse mappings', () => {
      const goldMappings = mapper.getReverseMappings('XAUUSD');
      expect(goldMappings).toContain('GOLD');
      expect(goldMappings).toContain('XAUUSD');
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('should handle localStorage errors gracefully', () => {
      // Mock localStorage to throw error
      const originalSetItem = Storage.prototype.setItem;
      Storage.prototype.setItem = () => {
        throw new Error('LocalStorage error');
      };

      // Should not throw error
      expect(() => {
        mapper.addUserOverrides({ 'TEST': 'TEST.mt5' });
      }).not.toThrow();

      // Restore original method
      Storage.prototype.setItem = originalSetItem;
    });

    it('should handle malformed localStorage data', () => {
      localStorageMock.setItem('signalos_pair_overrides', 'invalid json');
      
      // Should create new mapper without throwing
      expect(() => {
        new PairMapper();
      }).not.toThrow();
    });
  });

  describe('Convenience Functions', () => {
    it('should use default mapper instance', () => {
      expect(mapSymbol('GOLD')).toBe('XAUUSD');
      expect(mapSymbols(['GOLD', 'BTC'])).toEqual(['XAUUSD', 'BTCUSD']);
    });
  });

  describe('Integration Scenarios', () => {
    it('should handle complex signal provider scenarios', () => {
      // Simulate real-world provider mappings
      const providerSignals = [
        'GOLD', 'US30', 'BTC', 'NASDAQ', 'DAX', 'FTSE', 'NIKKEI',
        'OIL', 'SILVER', 'EURUSD', 'GBPUSD', 'UNKNOWN_PAIR'
      ];

      const expectedMappings = [
        'XAUUSD', 'US30.cash', 'BTCUSD', 'NAS100.cash', 'DAX40.cash',
        'UK100.cash', 'JPN225.cash', 'WTI.cash', 'XAGUSD', 'EURUSD',
        'GBPUSD', 'UNKNOWN_PAIR'
      ];

      expect(mapper.mapSymbols(providerSignals)).toEqual(expectedMappings);
    });

    it('should handle user customization for specific broker', () => {
      // User has different broker with different naming
      mapper.addUserOverrides({
        'US30': 'YM', // Different broker naming
        'GOLD': 'GC',
        'OIL': 'CL'
      });

      expect(mapper.mapSymbol('US30')).toBe('YM');
      expect(mapper.mapSymbol('GOLD')).toBe('GC');
      expect(mapper.mapSymbol('OIL')).toBe('CL');
    });
  });
});