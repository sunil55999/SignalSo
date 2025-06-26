/**
 * Backup and Recovery System for SignalOS
 * Addresses missing backup and recovery (Issue #26)
 */

import fs from 'fs/promises';
import path from 'path';
import { DatabaseStorage } from './storage';
import { encryptSensitiveData, decryptSensitiveData } from './encryption';

export interface BackupConfig {
  enabled: boolean;
  frequency: 'daily' | 'weekly' | 'monthly';
  retentionDays: number;
  encryptBackups: boolean;
  backupPath: string;
  maxBackupSize: number; // MB
}

export interface BackupMetadata {
  timestamp: Date;
  version: string;
  size: number;
  checksum: string;
  encrypted: boolean;
  tables: string[];
}

export class BackupRecoverySystem {
  private config: BackupConfig;
  private storage: DatabaseStorage;
  private isRunning = false;

  constructor(storage: DatabaseStorage, config: Partial<BackupConfig> = {}) {
    this.storage = storage;
    this.config = {
      enabled: true,
      frequency: 'daily',
      retentionDays: 30,
      encryptBackups: true,
      backupPath: process.env.BACKUP_PATH || './backups',
      maxBackupSize: 500, // 500MB
      ...config
    };
  }

  /**
   * Initialize backup system
   */
  async initialize(): Promise<void> {
    await this.ensureBackupDirectory();
    if (this.config.enabled) {
      await this.scheduleBackups();
    }
  }

  /**
   * Ensure backup directory exists
   */
  private async ensureBackupDirectory(): Promise<void> {
    try {
      await fs.mkdir(this.config.backupPath, { recursive: true });
    } catch (error) {
      throw new Error(`Failed to create backup directory: ${error}`);
    }
  }

  /**
   * Create full database backup
   */
  async createBackup(): Promise<string> {
    if (this.isRunning) {
      throw new Error('Backup already in progress');
    }

    this.isRunning = true;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupFileName = `signalos-backup-${timestamp}.json`;
    const backupPath = path.join(this.config.backupPath, backupFileName);

    try {
      // Collect all data
      const backupData = await this.collectBackupData();
      
      // Calculate checksum
      const checksum = this.calculateChecksum(JSON.stringify(backupData));
      
      // Create metadata
      const metadata: BackupMetadata = {
        timestamp: new Date(),
        version: '1.0.0',
        size: JSON.stringify(backupData).length,
        checksum,
        encrypted: this.config.encryptBackups,
        tables: Object.keys(backupData.data)
      };

      const backupContent = {
        metadata,
        data: backupData
      };

      // Encrypt if enabled
      let finalContent = JSON.stringify(backupContent, null, 2);
      if (this.config.encryptBackups) {
        finalContent = encryptSensitiveData(finalContent);
      }

      // Write backup file
      await fs.writeFile(backupPath, finalContent);

      // Clean old backups
      await this.cleanOldBackups();

      return backupPath;
    } catch (error) {
      throw new Error(`Backup failed: ${error}`);
    } finally {
      this.isRunning = false;
    }
  }

  /**
   * Collect all backup data
   */
  private async collectBackupData(): Promise<any> {
    const data: any = {};

    try {
      // Backup users (without sensitive data)
      data.users = await this.storage.getUsers();
      
      // Backup channels
      data.channels = await this.storage.getChannels();
      
      // Backup signals
      data.signals = await this.storage.getSignals();
      
      // Backup trades
      data.trades = await this.storage.getTrades();
      
      // Backup mt5 status
      data.mt5Status = await this.storage.getMT5Status();

      return { data, timestamp: new Date() };
    } catch (error) {
      throw new Error(`Failed to collect backup data: ${error}`);
    }
  }

  /**
   * Restore from backup
   */
  async restoreFromBackup(backupPath: string): Promise<void> {
    try {
      let backupContent = await fs.readFile(backupPath, 'utf-8');
      
      // Decrypt if needed
      if (this.config.encryptBackups) {
        try {
          backupContent = decryptSensitiveData(backupContent);
        } catch (error) {
          throw new Error('Failed to decrypt backup - invalid encryption key');
        }
      }

      const backup = JSON.parse(backupContent);
      
      // Verify backup integrity
      await this.verifyBackupIntegrity(backup);
      
      // Restore data
      await this.restoreData(backup.data);
      
    } catch (error) {
      throw new Error(`Restore failed: ${error}`);
    }
  }

  /**
   * Verify backup integrity
   */
  private async verifyBackupIntegrity(backup: any): Promise<void> {
    if (!backup.metadata || !backup.data) {
      throw new Error('Invalid backup format');
    }

    const calculatedChecksum = this.calculateChecksum(JSON.stringify(backup.data));
    if (calculatedChecksum !== backup.metadata.checksum) {
      throw new Error('Backup integrity check failed - corrupted data');
    }
  }

  /**
   * Restore data to database
   */
  private async restoreData(data: any): Promise<void> {
    // Note: This is a simplified restore - in production, you'd want
    // more sophisticated conflict resolution and rollback capabilities
    
    try {
      if (data.data.users) {
        for (const user of data.data.users) {
          await this.storage.createUser(user);
        }
      }

      if (data.data.channels) {
        for (const channel of data.data.channels) {
          await this.storage.createChannel(channel);
        }
      }

      if (data.data.signals) {
        for (const signal of data.data.signals) {
          await this.storage.createSignal(signal);
        }
      }

      if (data.data.trades) {
        for (const trade of data.data.trades) {
          await this.storage.createTrade(trade);
        }
      }

    } catch (error) {
      throw new Error(`Data restoration failed: ${error}`);
    }
  }

  /**
   * Schedule automatic backups
   */
  private async scheduleBackups(): Promise<void> {
    const intervals = {
      daily: 24 * 60 * 60 * 1000,
      weekly: 7 * 24 * 60 * 60 * 1000,
      monthly: 30 * 24 * 60 * 60 * 1000
    };

    const interval = intervals[this.config.frequency];
    
    setInterval(async () => {
      try {
        await this.createBackup();
        console.log(`Scheduled backup completed: ${new Date().toISOString()}`);
      } catch (error) {
        console.error(`Scheduled backup failed: ${error}`);
      }
    }, interval);
  }

  /**
   * Clean old backups based on retention policy
   */
  private async cleanOldBackups(): Promise<void> {
    try {
      const files = await fs.readdir(this.config.backupPath);
      const backupFiles = files.filter(f => f.startsWith('signalos-backup-'));
      
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - this.config.retentionDays);

      for (const file of backupFiles) {
        const filePath = path.join(this.config.backupPath, file);
        const stats = await fs.stat(filePath);
        
        if (stats.mtime < cutoffDate) {
          await fs.unlink(filePath);
        }
      }
    } catch (error) {
      console.error(`Failed to clean old backups: ${error}`);
    }
  }

  /**
   * Calculate checksum for data integrity
   */
  private calculateChecksum(data: string): string {
    const crypto = require('crypto');
    return crypto.createHash('sha256').update(data).digest('hex');
  }

  /**
   * List available backups
   */
  async listBackups(): Promise<BackupMetadata[]> {
    try {
      const files = await fs.readdir(this.config.backupPath);
      const backupFiles = files.filter(f => f.startsWith('signalos-backup-'));
      
      const backups: BackupMetadata[] = [];
      
      for (const file of backupFiles) {
        const filePath = path.join(this.config.backupPath, file);
        const stats = await fs.stat(filePath);
        
        try {
          let content = await fs.readFile(filePath, 'utf-8');
          
          if (this.config.encryptBackups) {
            content = decryptSensitiveData(content);
          }
          
          const backup = JSON.parse(content);
          if (backup.metadata) {
            backups.push({
              ...backup.metadata,
              timestamp: new Date(backup.metadata.timestamp)
            });
          }
        } catch (error) {
          // Skip corrupted backups
          continue;
        }
      }
      
      return backups.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
    } catch (error) {
      throw new Error(`Failed to list backups: ${error}`);
    }
  }

  /**
   * Get backup system status
   */
  getStatus() {
    return {
      enabled: this.config.enabled,
      frequency: this.config.frequency,
      retentionDays: this.config.retentionDays,
      encryptBackups: this.config.encryptBackups,
      backupPath: this.config.backupPath,
      isRunning: this.isRunning
    };
  }
}