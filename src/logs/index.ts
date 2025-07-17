import { Log, InsertLog } from '@shared/schema';

export type LogLevel = 'info' | 'warning' | 'error';
export type LogComponent = 'parser' | 'executor' | 'telegram' | 'auth' | 'config' | 'router' | 'updater';

export interface LogEntry {
  id: string;
  level: LogLevel;
  message: string;
  component: LogComponent;
  data?: any;
  timestamp: Date;
}

export class LogManager {
  private logs: Map<string, LogEntry> = new Map();
  private listeners: Set<(entry: LogEntry) => void> = new Set();
  private maxLogs = 1000;

  log(level: LogLevel, message: string, component: LogComponent, data?: any): void {
    const entry: LogEntry = {
      id: this.generateId(),
      level,
      message,
      component,
      data,
      timestamp: new Date()
    };

    this.logs.set(entry.id, entry);
    this.trimLogs();
    
    // Notify listeners
    this.listeners.forEach(listener => {
      try {
        listener(entry);
      } catch (error) {
        console.error('Error in log listener:', error);
      }
    });

    // Also log to console for development
    const consoleMethod = level === 'error' ? 'error' : level === 'warning' ? 'warn' : 'log';
    console[consoleMethod](`[${component.toUpperCase()}] ${message}`, data || '');
  }

  info(message: string, component: LogComponent, data?: any): void {
    this.log('info', message, component, data);
  }

  warning(message: string, component: LogComponent, data?: any): void {
    this.log('warning', message, component, data);
  }

  error(message: string, component: LogComponent, data?: any): void {
    this.log('error', message, component, data);
  }

  getLogs(options?: {
    level?: LogLevel;
    component?: LogComponent;
    limit?: number;
    since?: Date;
  }): LogEntry[] {
    let logs = Array.from(this.logs.values());

    if (options?.level) {
      logs = logs.filter(log => log.level === options.level);
    }

    if (options?.component) {
      logs = logs.filter(log => log.component === options.component);
    }

    if (options?.since) {
      logs = logs.filter(log => log.timestamp >= options.since!);
    }

    // Sort by timestamp (newest first)
    logs.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());

    if (options?.limit) {
      logs = logs.slice(0, options.limit);
    }

    return logs;
  }

  getLogById(id: string): LogEntry | null {
    return this.logs.get(id) || null;
  }

  clearLogs(options?: {
    level?: LogLevel;
    component?: LogComponent;
    before?: Date;
  }): number {
    let deletedCount = 0;

    for (const [id, log] of this.logs.entries()) {
      let shouldDelete = true;

      if (options?.level && log.level !== options.level) {
        shouldDelete = false;
      }

      if (options?.component && log.component !== options.component) {
        shouldDelete = false;
      }

      if (options?.before && log.timestamp >= options.before) {
        shouldDelete = false;
      }

      if (shouldDelete) {
        this.logs.delete(id);
        deletedCount++;
      }
    }

    return deletedCount;
  }

  onLog(listener: (entry: LogEntry) => void): () => void {
    this.listeners.add(listener);
    
    return () => {
      this.listeners.delete(listener);
    };
  }

  exportLogs(format: 'json' | 'csv' = 'json'): string {
    const logs = this.getLogs();
    
    if (format === 'csv') {
      const headers = ['Timestamp', 'Level', 'Component', 'Message', 'Data'];
      const rows = logs.map(log => [
        log.timestamp.toISOString(),
        log.level,
        log.component,
        log.message,
        log.data ? JSON.stringify(log.data) : ''
      ]);
      
      return [headers, ...rows].map(row => row.join(',')).join('\n');
    }

    return JSON.stringify(logs, null, 2);
  }

  getStats(): {
    total: number;
    byLevel: Record<LogLevel, number>;
    byComponent: Record<LogComponent, number>;
    recentErrors: LogEntry[];
  } {
    const logs = Array.from(this.logs.values());
    const stats = {
      total: logs.length,
      byLevel: { info: 0, warning: 0, error: 0 } as Record<LogLevel, number>,
      byComponent: {} as Record<LogComponent, number>,
      recentErrors: logs
        .filter(log => log.level === 'error')
        .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
        .slice(0, 10)
    };

    logs.forEach(log => {
      stats.byLevel[log.level]++;
      stats.byComponent[log.component] = (stats.byComponent[log.component] || 0) + 1;
    });

    return stats;
  }

  private trimLogs(): void {
    if (this.logs.size > this.maxLogs) {
      const entries = Array.from(this.logs.entries());
      entries.sort((a, b) => a[1].timestamp.getTime() - b[1].timestamp.getTime());
      
      const toDelete = entries.slice(0, this.logs.size - this.maxLogs);
      toDelete.forEach(([id]) => this.logs.delete(id));
    }
  }

  private generateId(): string {
    return `log_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
  }
}

// Export default instance
export const logManager = new LogManager();