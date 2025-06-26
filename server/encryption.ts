/**
 * Encryption Utilities for SignalOS
 * Addresses missing encryption for sensitive data (Issue #28)
 */

import crypto from 'crypto';

const ALGORITHM = 'aes-256-gcm';
const KEY_LENGTH = 32; // 256 bits
const IV_LENGTH = 16; // 128 bits
const TAG_LENGTH = 16; // 128 bits

class EncryptionService {
  private encryptionKey: Buffer;

  constructor() {
    const keyString = process.env.ENCRYPTION_KEY;
    if (!keyString) {
      throw new Error('ENCRYPTION_KEY environment variable is required');
    }
    
    // Derive key from environment variable
    this.encryptionKey = crypto.scryptSync(keyString, 'salt', KEY_LENGTH);
  }

  /**
   * Encrypt sensitive data
   */
  encrypt(plaintext: string): string {
    try {
      const iv = crypto.randomBytes(IV_LENGTH);
      const cipher = crypto.createCipher(ALGORITHM, this.encryptionKey);
      cipher.setAAD(Buffer.from('SignalOS', 'utf8')); // Additional authenticated data
      
      let ciphertext = cipher.update(plaintext, 'utf8', 'hex');
      ciphertext += cipher.final('hex');
      
      const tag = cipher.getAuthTag();
      
      // Combine IV + tag + ciphertext
      return iv.toString('hex') + tag.toString('hex') + ciphertext;
    } catch (error) {
      throw new Error('Encryption failed');
    }
  }

  /**
   * Decrypt sensitive data
   */
  decrypt(encryptedData: string): string {
    try {
      // Extract IV, tag, and ciphertext
      const iv = Buffer.from(encryptedData.slice(0, IV_LENGTH * 2), 'hex');
      const tag = Buffer.from(encryptedData.slice(IV_LENGTH * 2, (IV_LENGTH + TAG_LENGTH) * 2), 'hex');
      const ciphertext = encryptedData.slice((IV_LENGTH + TAG_LENGTH) * 2);
      
      const decipher = crypto.createDecipher(ALGORITHM, this.encryptionKey);
      decipher.setAAD(Buffer.from('SignalOS', 'utf8'));
      decipher.setAuthTag(tag);
      
      let plaintext = decipher.update(ciphertext, 'hex', 'utf8');
      plaintext += decipher.final('utf8');
      
      return plaintext;
    } catch (error) {
      throw new Error('Decryption failed');
    }
  }

  /**
   * Hash sensitive data (one-way)
   */
  hash(data: string): string {
    return crypto.createHash('sha256').update(data).digest('hex');
  }

  /**
   * Generate secure random token
   */
  generateToken(length: number = 32): string {
    return crypto.randomBytes(length).toString('hex');
  }
}

// Global encryption service instance
let encryptionService: EncryptionService | null = null;

export function getEncryptionService(): EncryptionService {
  if (!encryptionService) {
    encryptionService = new EncryptionService();
  }
  return encryptionService;
}

// Utility functions for common encryption tasks
export function encryptSensitiveData(data: string): string {
  return getEncryptionService().encrypt(data);
}

export function decryptSensitiveData(encryptedData: string): string {
  return getEncryptionService().decrypt(encryptedData);
}

export function hashSensitiveData(data: string): string {
  return getEncryptionService().hash(data);
}

export function generateSecureToken(length?: number): string {
  return getEncryptionService().generateToken(length);
}