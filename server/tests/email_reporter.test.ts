/**
 * Unit Tests for Email Reporter
 * Tests email formatting, delivery, error handling, and template processing
 */

import { describe, it, expect, beforeEach, afterEach, vi, Mock } from 'vitest';
import fs from 'fs/promises';
import path from 'path';
import { EmailReporter, type EmailConfig } from '../utils/email_reporter';

// Mock nodemailer
const mockSendMail = vi.fn();
const mockVerify = vi.fn();
const mockCreateTransporter = vi.fn(() => ({
  sendMail: mockSendMail,
  verify: mockVerify,
}));

vi.mock('nodemailer', () => ({
  default: {
    createTransporter: mockCreateTransporter,
  },
}));

// Mock storage
const mockStorage = {
  getSignals: vi.fn(),
  getUserTrades: vi.fn(),
  getMt5Status: vi.fn(),
};

vi.mock('../storage', () => ({
  storage: mockStorage,
}));

// Mock file system operations
vi.mock('fs/promises');
const mockFs = fs as any;

describe('EmailReporter', () => {
  let emailReporter: EmailReporter;
  let mockConfig: EmailConfig;

  beforeEach(() => {
    vi.clearAllMocks();
    
    mockConfig = {
      provider: 'smtp',
      smtpHost: 'smtp.test.com',
      smtpPort: 587,
      smtpUser: 'test@test.com',
      smtpPassword: 'password',
      fromEmail: 'noreply@signalos.com',
      fromName: 'SignalOS',
    };

    mockVerify.mockResolvedValue(true);
    mockSendMail.mockResolvedValue({ messageId: 'test-message-id' });
    mockFs.appendFile = vi.fn().mockResolvedValue(undefined);
    mockFs.readFile = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Initialization', () => {
    it('should initialize with SMTP configuration', async () => {
      emailReporter = new EmailReporter(mockConfig);
      
      // Wait for async initialization
      await new Promise(resolve => setTimeout(resolve, 100));
      
      expect(mockCreateTransporter).toHaveBeenCalledWith({
        host: 'smtp.test.com',
        port: 587,
        secure: false,
        auth: {
          user: 'test@test.com',
          pass: 'password',
        },
        tls: {
          rejectUnauthorized: false,
        },
      });
      expect(mockVerify).toHaveBeenCalled();
    });

    it('should initialize with SendGrid configuration', async () => {
      const sendGridConfig: EmailConfig = {
        ...mockConfig,
        provider: 'sendgrid',
        apiKey: 'sg-test-key',
      };

      emailReporter = new EmailReporter(sendGridConfig);
      
      await new Promise(resolve => setTimeout(resolve, 100));
      
      expect(mockCreateTransporter).toHaveBeenCalledWith({
        service: 'SendGrid',
        auth: {
          user: 'apikey',
          pass: 'sg-test-key',
        },
      });
    });

    it('should handle initialization errors gracefully', async () => {
      mockVerify.mockRejectedValue(new Error('Connection failed'));
      
      await expect(async () => {
        emailReporter = new EmailReporter(mockConfig);
        await new Promise(resolve => setTimeout(resolve, 100));
      }).rejects.toThrow('Email configuration error: Connection failed');
    });
  });

  describe('Report Data Generation', () => {
    beforeEach(() => {
      emailReporter = new EmailReporter(mockConfig);
      
      // Mock storage responses
      mockStorage.getSignals.mockResolvedValue([
        {
          id: 1,
          channelId: 'channel-1',
          channelName: 'Test Provider',
          status: 'executed',
          createdAt: new Date().toISOString(),
        },
        {
          id: 2,
          channelId: 'channel-2',
          channelName: 'Another Provider',
          status: 'failed',
          createdAt: new Date().toISOString(),
        },
      ]);

      mockStorage.getUserTrades.mockResolvedValue([
        {
          id: 1,
          signalId: 1,
          profit: '100.50',
          entryPrice: '1.1000',
          stopLoss: '1.0950',
          lotSize: '0.01',
          openTime: new Date().toISOString(),
        },
        {
          id: 2,
          signalId: 1,
          profit: '-50.25',
          entryPrice: '1.2000',
          stopLoss: '1.2050',
          lotSize: '0.01',
          openTime: new Date().toISOString(),
        },
      ]);

      mockStorage.getMt5Status.mockResolvedValue({
        isConnected: true,
      });
    });

    it('should calculate correct win rate', async () => {
      const report = await emailReporter.generateDailyReport(1);
      
      expect(report.subject).toContain('SignalOS Daily Report');
      expect(report.htmlContent).toContain('50.0'); // 50% win rate (1 win out of 2 trades)
      expect(report.textContent).toContain('50.0%');
    });

    it('should calculate correct total P&L', async () => {
      const report = await emailReporter.generateDailyReport(1);
      
      expect(report.htmlContent).toContain('50.25'); // 100.50 - 50.25
      expect(report.textContent).toContain('$50.25');
    });

    it('should handle empty data gracefully', async () => {
      mockStorage.getSignals.mockResolvedValue([]);
      mockStorage.getUserTrades.mockResolvedValue([]);
      
      const report = await emailReporter.generateDailyReport(1);
      
      expect(report.htmlContent).toContain('0'); // Zero trades
      expect(report.textContent).toContain('0 trades');
    });
  });

  describe('Template Rendering', () => {
    beforeEach(() => {
      emailReporter = new EmailReporter(mockConfig);
      
      const mockTemplate = `
        <h1>Daily Report</h1>
        <p>Total Trades: {{totalTrades}}</p>
        <p>Win Rate: {{winRate}}%</p>
        <p>Total P&L: {{totalPnL}}</p>
        <p>Status: {{mt5Status}}</p>
        <table>{{topProviders}}</table>
      `;
      
      mockFs.readFile.mockResolvedValue(mockTemplate);
    });

    it('should load and render templates correctly', async () => {
      // Mock minimal storage data
      mockStorage.getSignals.mockResolvedValue([]);
      mockStorage.getUserTrades.mockResolvedValue([]);
      mockStorage.getMt5Status.mockResolvedValue({ isConnected: true });
      
      const report = await emailReporter.generateDailyReport(1);
      
      expect(mockFs.readFile).toHaveBeenCalledWith(
        expect.stringContaining('daily_report.html'),
        'utf-8'
      );
      expect(report.htmlContent).toContain('<h1>Daily Report</h1>');
      expect(report.htmlContent).toContain('Total Trades: 0');
      expect(report.htmlContent).toContain('Status: Connected');
    });

    it('should handle template loading errors', async () => {
      mockFs.readFile.mockRejectedValue(new Error('Template not found'));
      
      await expect(emailReporter.generateDailyReport(1)).rejects.toThrow(
        'Template not found: daily_report'
      );
    });

    it('should render provider table correctly', async () => {
      mockStorage.getSignals.mockResolvedValue([
        {
          id: 1,
          channelId: 'provider-1',
          channelName: 'Best Provider',
          status: 'executed',
          createdAt: new Date().toISOString(),
        },
      ]);

      mockStorage.getUserTrades.mockResolvedValue([
        {
          id: 1,
          signalId: 1,
          profit: '200.00',
          entryPrice: '1.1000',
          stopLoss: '1.0950',
          lotSize: '0.01',
          openTime: new Date().toISOString(),
        },
      ]);

      const report = await emailReporter.generateDailyReport(1);
      
      expect(report.htmlContent).toContain('Best Provider');
      expect(report.htmlContent).toContain('100.0%'); // 100% win rate
      expect(report.htmlContent).toContain('$200');
    });
  });

  describe('Email Sending', () => {
    beforeEach(() => {
      emailReporter = new EmailReporter(mockConfig);
      mockStorage.getSignals.mockResolvedValue([]);
      mockStorage.getUserTrades.mockResolvedValue([]);
      mockStorage.getMt5Status.mockResolvedValue({ isConnected: true });
      mockFs.readFile.mockResolvedValue('<html>Test Template {{totalTrades}}</html>');
    });

    it('should send email successfully', async () => {
      const result = await emailReporter.sendDailyReport('test@example.com', 1);
      
      expect(result).toBe(true);
      expect(mockSendMail).toHaveBeenCalledWith({
        from: 'SignalOS <noreply@signalos.com>',
        to: 'test@example.com',
        subject: expect.stringContaining('SignalOS Daily Report'),
        text: expect.any(String),
        html: expect.stringContaining('<html>'),
      });
    });

    it('should handle email sending failures', async () => {
      mockSendMail.mockRejectedValue(new Error('SMTP Error'));
      
      const result = await emailReporter.sendDailyReport('test@example.com', 1);
      
      expect(result).toBe(false);
      expect(mockFs.appendFile).toHaveBeenCalledWith(
        expect.stringContaining('email_reports.log'),
        expect.stringContaining('Failed to send report')
      );
    });

    it('should validate recipient email', async () => {
      const report = await emailReporter.generateDailyReport(1);
      report.recipientEmail = '';
      
      const result = await emailReporter.sendReport(report);
      
      expect(result).toBe(false);
      expect(mockSendMail).not.toHaveBeenCalled();
    });
  });

  describe('Weekly and Custom Reports', () => {
    beforeEach(() => {
      emailReporter = new EmailReporter(mockConfig);
      mockStorage.getSignals.mockResolvedValue([]);
      mockStorage.getUserTrades.mockResolvedValue([]);
      mockStorage.getMt5Status.mockResolvedValue({ isConnected: true });
      mockFs.readFile.mockResolvedValue('<html>{{reportType}} Template</html>');
    });

    it('should generate weekly reports', async () => {
      const report = await emailReporter.generateWeeklyReport(1);
      
      expect(report.subject).toContain('SignalOS Weekly Report');
      expect(report.reportType).toBe('weekly');
    });

    it('should generate custom reports with date range', async () => {
      const fromDate = new Date('2024-01-01');
      const toDate = new Date('2024-01-31');
      
      const report = await emailReporter.generateCustomReport(1, fromDate, toDate);
      
      expect(report.subject).toContain('SignalOS Custom Report');
      expect(report.subject).toContain('2024-01-01 to 2024-01-31');
      expect(report.reportType).toBe('custom');
    });
  });

  describe('Connection Testing', () => {
    beforeEach(() => {
      emailReporter = new EmailReporter(mockConfig);
    });

    it('should test connection successfully', async () => {
      mockVerify.mockResolvedValue(true);
      
      const result = await emailReporter.testConnection();
      
      expect(result).toBe(true);
      expect(mockVerify).toHaveBeenCalled();
    });

    it('should handle connection test failures', async () => {
      mockVerify.mockRejectedValue(new Error('Connection timeout'));
      
      const result = await emailReporter.testConnection();
      
      expect(result).toBe(false);
    });
  });

  describe('Logging', () => {
    beforeEach(() => {
      emailReporter = new EmailReporter(mockConfig);
    });

    it('should write logs correctly', async () => {
      mockStorage.getSignals.mockResolvedValue([]);
      mockStorage.getUserTrades.mockResolvedValue([]);
      mockStorage.getMt5Status.mockResolvedValue({ isConnected: true });
      mockFs.readFile.mockResolvedValue('<html>Test</html>');
      
      await emailReporter.sendDailyReport('test@example.com', 1);
      
      expect(mockFs.appendFile).toHaveBeenCalledWith(
        expect.stringContaining('email_reports.log'),
        expect.stringContaining('[INFO] Report sent successfully')
      );
    });

    it('should retrieve log entries', async () => {
      const mockLogContent = 'Log line 1\nLog line 2\nLog line 3\n';
      mockFs.readFile.mockResolvedValue(mockLogContent);
      
      const logs = await emailReporter.getReportLogs(2);
      
      expect(logs).toEqual(['Log line 2', 'Log line 3']);
    });

    it('should handle log reading errors', async () => {
      mockFs.readFile.mockRejectedValue(new Error('Log file not found'));
      
      const logs = await emailReporter.getReportLogs();
      
      expect(logs).toEqual([]);
    });
  });

  describe('Error Handling', () => {
    beforeEach(() => {
      emailReporter = new EmailReporter(mockConfig);
    });

    it('should handle storage errors gracefully', async () => {
      mockStorage.getSignals.mockRejectedValue(new Error('Database error'));
      
      await expect(emailReporter.generateDailyReport(1)).rejects.toThrow('Database error');
    });

    it('should handle template rendering errors', async () => {
      mockStorage.getSignals.mockResolvedValue([]);
      mockStorage.getUserTrades.mockResolvedValue([]);
      mockStorage.getMt5Status.mockResolvedValue({ isConnected: true });
      
      mockFs.readFile.mockResolvedValue('{{invalidTemplate}}');
      
      // Should not throw but handle gracefully
      const report = await emailReporter.generateDailyReport(1);
      expect(report.htmlContent).toContain('{{invalidTemplate}}');
    });
  });
});