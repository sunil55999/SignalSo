/**
 * Email Reporter Utility for SignalOS
 * Generates and sends comprehensive trading performance reports via email
 */

import nodemailer from 'nodemailer';
import fs from 'fs/promises';
import path from 'path';
import { storage } from '../storage';

export interface EmailConfig {
  smtpHost?: string;
  smtpPort?: number;
  smtpUser?: string;
  smtpPassword?: string;
  fromEmail: string;
  fromName?: string;
  provider: 'smtp' | 'sendgrid' | 'mailgun';
  apiKey?: string;
  apiUrl?: string;
}

export interface ReportData {
  totalTrades: number;
  totalSignals: number;
  winRate: number;
  averageRR: number;
  totalPnL: number;
  topProviders: Array<{
    name: string;
    winRate: number;
    totalSignals: number;
    pnl: number;
  }>;
  errorCount: number;
  blockedSignals: number;
  executedSignals: number;
  dateRange: {
    from: string;
    to: string;
  };
  activeUsers: number;
  mt5ConnectionStatus: string;
}

export interface EmailReport {
  subject: string;
  htmlContent: string;
  textContent: string;
  recipientEmail: string;
  recipientName?: string;
  reportType: 'daily' | 'weekly' | 'monthly' | 'custom';
  userId?: number;
}

export class EmailReporter {
  private config: EmailConfig;
  private transporter: nodemailer.Transporter | null = null;
  private templatesPath: string;
  private logPath: string;

  constructor(config: EmailConfig) {
    this.config = config;
    this.templatesPath = path.join(__dirname, '../templates');
    this.logPath = path.join(__dirname, '../../logs/email_reports.log');
    this.initializeTransporter();
  }

  private async initializeTransporter(): Promise<void> {
    try {
      if (this.config.provider === 'smtp') {
        this.transporter = nodemailer.createTransporter({
          host: this.config.smtpHost,
          port: this.config.smtpPort || 587,
          secure: this.config.smtpPort === 465,
          auth: {
            user: this.config.smtpUser,
            pass: this.config.smtpPassword,
          },
          tls: {
            rejectUnauthorized: false,
          },
        });
      } else if (this.config.provider === 'sendgrid') {
        this.transporter = nodemailer.createTransporter({
          service: 'SendGrid',
          auth: {
            user: 'apikey',
            pass: this.config.apiKey,
          },
        });
      } else if (this.config.provider === 'mailgun') {
        const mg = require('nodemailer-mailgun-transport');
        this.transporter = nodemailer.createTransporter(
          mg({
            auth: {
              api_key: this.config.apiKey,
              domain: this.config.apiUrl,
            },
          })
        );
      }

      if (this.transporter) {
        await this.transporter.verify();
        await this.logMessage('Email transporter initialized successfully');
      }
    } catch (error) {
      await this.logMessage(`Failed to initialize email transporter: ${error.message}`, 'error');
      throw new Error(`Email configuration error: ${error.message}`);
    }
  }

  private async logMessage(message: string, level: 'info' | 'error' | 'warn' = 'info'): Promise<void> {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [${level.toUpperCase()}] ${message}\n`;
    
    try {
      await fs.appendFile(this.logPath, logEntry);
    } catch (error) {
      console.error('Failed to write to email log:', error);
    }
  }

  private async loadTemplate(templateName: string): Promise<string> {
    try {
      const templatePath = path.join(this.templatesPath, `${templateName}.html`);
      return await fs.readFile(templatePath, 'utf-8');
    } catch (error) {
      await this.logMessage(`Failed to load template ${templateName}: ${error.message}`, 'error');
      throw new Error(`Template not found: ${templateName}`);
    }
  }

  private async generateReportData(
    userId?: number,
    dateFrom?: Date,
    dateTo?: Date
  ): Promise<ReportData> {
    try {
      const from = dateFrom || new Date(Date.now() - 24 * 60 * 60 * 1000); // Yesterday
      const to = dateTo || new Date();

      // Fetch data from storage
      const signals = await storage.getSignals(1000);
      const trades = userId ? await storage.getUserTrades(userId, 1000) : [];
      const mt5Status = userId ? await storage.getMt5Status(userId) : null;

      // Filter by date range
      const filteredSignals = signals.filter(signal => {
        const signalDate = new Date(signal.createdAt || 0);
        return signalDate >= from && signalDate <= to;
      });

      const filteredTrades = trades.filter(trade => {
        const tradeDate = new Date(trade.openTime || 0);
        return tradeDate >= from && tradeDate <= to;
      });

      // Calculate metrics
      const totalTrades = filteredTrades.length;
      const totalSignals = filteredSignals.length;
      const executedSignals = filteredSignals.filter(s => s.status === 'executed').length;
      const blockedSignals = filteredSignals.filter(s => s.status === 'blocked').length;
      const errorCount = filteredSignals.filter(s => s.status === 'failed').length;

      const profitableTrades = filteredTrades.filter(t => parseFloat(t.profit || '0') > 0);
      const winRate = totalTrades > 0 ? (profitableTrades.length / totalTrades) * 100 : 0;

      const totalPnL = filteredTrades.reduce((sum, trade) => sum + parseFloat(trade.profit || '0'), 0);

      // Calculate average R:R ratio
      let totalRR = 0;
      let rrCount = 0;
      filteredTrades.forEach(trade => {
        const profit = parseFloat(trade.profit || '0');
        const entry = parseFloat(trade.entryPrice || '0');
        const sl = parseFloat(trade.stopLoss || '0');
        
        if (profit !== 0 && entry > 0 && sl > 0) {
          const risk = Math.abs(entry - sl);
          const reward = Math.abs(profit / parseFloat(trade.lotSize || '0.01'));
          if (risk > 0) {
            totalRR += reward / risk;
            rrCount++;
          }
        }
      });
      const averageRR = rrCount > 0 ? totalRR / rrCount : 0;

      // Calculate top providers
      const providerMap = new Map();
      filteredSignals.forEach(signal => {
        const providerId = signal.channelId || signal.id;
        const providerName = signal.channelName || `Channel ${signal.id}`;
        
        if (!providerMap.has(providerId)) {
          providerMap.set(providerId, {
            name: providerName,
            signals: [],
            trades: []
          });
        }
        providerMap.get(providerId).signals.push(signal);
      });

      // Add trades to providers
      filteredTrades.forEach(trade => {
        if (trade.signalId) {
          const signal = filteredSignals.find(s => s.id === trade.signalId);
          if (signal) {
            const providerId = signal.channelId || signal.id;
            if (providerMap.has(providerId)) {
              providerMap.get(providerId).trades.push(trade);
            }
          }
        }
      });

      const topProviders = Array.from(providerMap.values())
        .map(provider => {
          const signals = provider.signals;
          const trades = provider.trades;
          const pnl = trades.reduce((sum: number, trade: any) => sum + parseFloat(trade.profit || '0'), 0);
          const executedCount = signals.filter((s: any) => s.status === 'executed').length;
          const successfulTrades = trades.filter((t: any) => parseFloat(t.profit || '0') > 0);
          const winRate = executedCount > 0 ? (successfulTrades.length / executedCount) * 100 : 0;

          return {
            name: provider.name,
            winRate: Number(winRate.toFixed(1)),
            totalSignals: signals.length,
            pnl: Number(pnl.toFixed(2))
          };
        })
        .sort((a, b) => b.winRate - a.winRate)
        .slice(0, 5);

      return {
        totalTrades,
        totalSignals,
        winRate: Number(winRate.toFixed(1)),
        averageRR: Number(averageRR.toFixed(2)),
        totalPnL: Number(totalPnL.toFixed(2)),
        topProviders,
        errorCount,
        blockedSignals,
        executedSignals,
        dateRange: {
          from: from.toISOString().split('T')[0],
          to: to.toISOString().split('T')[0]
        },
        activeUsers: userId ? 1 : 0,
        mt5ConnectionStatus: mt5Status?.isConnected ? 'Connected' : 'Disconnected'
      };
    } catch (error) {
      await this.logMessage(`Failed to generate report data: ${error.message}`, 'error');
      throw error;
    }
  }

  private async renderTemplate(templateName: string, data: ReportData): Promise<{ html: string; text: string }> {
    try {
      const htmlTemplate = await this.loadTemplate(templateName);
      
      // Replace template variables
      let htmlContent = htmlTemplate
        .replace(/{{totalTrades}}/g, data.totalTrades.toString())
        .replace(/{{totalSignals}}/g, data.totalSignals.toString())
        .replace(/{{winRate}}/g, data.winRate.toString())
        .replace(/{{averageRR}}/g, data.averageRR.toString())
        .replace(/{{totalPnL}}/g, data.totalPnL >= 0 ? `+$${data.totalPnL}` : `-$${Math.abs(data.totalPnL)}`)
        .replace(/{{executedSignals}}/g, data.executedSignals.toString())
        .replace(/{{blockedSignals}}/g, data.blockedSignals.toString())
        .replace(/{{errorCount}}/g, data.errorCount.toString())
        .replace(/{{dateFrom}}/g, data.dateRange.from)
        .replace(/{{dateTo}}/g, data.dateRange.to)
        .replace(/{{mt5Status}}/g, data.mt5ConnectionStatus);

      // Generate top providers table
      const providersTable = data.topProviders
        .map(provider => `
          <tr>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">${provider.name}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: center;">${provider.winRate}%</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: center;">${provider.totalSignals}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: center; color: ${provider.pnl >= 0 ? '#22c55e' : '#ef4444'};">
              ${provider.pnl >= 0 ? '+' : ''}$${provider.pnl}
            </td>
          </tr>`)
        .join('');

      htmlContent = htmlContent.replace(/{{topProviders}}/g, providersTable);

      // Generate plain text version
      const textContent = `
SignalOS Trading Report (${data.dateRange.from} to ${data.dateRange.to})

PERFORMANCE SUMMARY:
- Total Trades: ${data.totalTrades}
- Total Signals: ${data.totalSignals}
- Win Rate: ${data.winRate}%
- Average R:R: ${data.averageRR}
- Total P&L: ${data.totalPnL >= 0 ? '+' : ''}$${data.totalPnL}

SIGNAL EXECUTION:
- Executed: ${data.executedSignals}
- Blocked: ${data.blockedSignals}
- Errors: ${data.errorCount}

TOP PERFORMING PROVIDERS:
${data.topProviders.map((p, i) => `${i + 1}. ${p.name} - ${p.winRate}% win rate, ${p.totalSignals} signals, $${p.pnl} P&L`).join('\n')}

MT5 Status: ${data.mt5ConnectionStatus}

Generated by SignalOS at ${new Date().toISOString()}
      `.trim();

      return { html: htmlContent, text: textContent };
    } catch (error) {
      await this.logMessage(`Failed to render template: ${error.message}`, 'error');
      throw error;
    }
  }

  public async generateDailyReport(userId?: number): Promise<EmailReport> {
    try {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      yesterday.setHours(0, 0, 0, 0);
      
      const today = new Date();
      today.setHours(23, 59, 59, 999);

      const reportData = await this.generateReportData(userId, yesterday, today);
      const { html, text } = await this.renderTemplate('daily_report', reportData);

      return {
        subject: `SignalOS Daily Report - ${reportData.dateRange.from}`,
        htmlContent: html,
        textContent: text,
        recipientEmail: '', // To be set by caller
        reportType: 'daily',
        userId
      };
    } catch (error) {
      await this.logMessage(`Failed to generate daily report: ${error.message}`, 'error');
      throw error;
    }
  }

  public async generateWeeklyReport(userId?: number): Promise<EmailReport> {
    try {
      const lastWeek = new Date();
      lastWeek.setDate(lastWeek.getDate() - 7);
      lastWeek.setHours(0, 0, 0, 0);
      
      const today = new Date();
      today.setHours(23, 59, 59, 999);

      const reportData = await this.generateReportData(userId, lastWeek, today);
      const { html, text } = await this.renderTemplate('weekly_report', reportData);

      return {
        subject: `SignalOS Weekly Report - Week of ${reportData.dateRange.from}`,
        htmlContent: html,
        textContent: text,
        recipientEmail: '', // To be set by caller
        reportType: 'weekly',
        userId
      };
    } catch (error) {
      await this.logMessage(`Failed to generate weekly report: ${error.message}`, 'error');
      throw error;
    }
  }

  public async generateCustomReport(
    userId?: number,
    dateFrom?: Date,
    dateTo?: Date
  ): Promise<EmailReport> {
    try {
      const reportData = await this.generateReportData(userId, dateFrom, dateTo);
      const { html, text } = await this.renderTemplate('custom_report', reportData);

      return {
        subject: `SignalOS Custom Report - ${reportData.dateRange.from} to ${reportData.dateRange.to}`,
        htmlContent: html,
        textContent: text,
        recipientEmail: '', // To be set by caller
        reportType: 'custom',
        userId
      };
    } catch (error) {
      await this.logMessage(`Failed to generate custom report: ${error.message}`, 'error');
      throw error;
    }
  }

  public async sendReport(report: EmailReport): Promise<boolean> {
    try {
      if (!this.transporter) {
        throw new Error('Email transporter not initialized');
      }

      if (!report.recipientEmail) {
        throw new Error('Recipient email is required');
      }

      const mailOptions = {
        from: `${this.config.fromName || 'SignalOS'} <${this.config.fromEmail}>`,
        to: report.recipientEmail,
        subject: report.subject,
        text: report.textContent,
        html: report.htmlContent,
      };

      const result = await this.transporter.sendMail(mailOptions);
      
      await this.logMessage(
        `Report sent successfully to ${report.recipientEmail} (${report.reportType}) - MessageId: ${result.messageId}`
      );

      return true;
    } catch (error) {
      await this.logMessage(
        `Failed to send report to ${report.recipientEmail}: ${error.message}`,
        'error'
      );
      return false;
    }
  }

  public async sendDailyReport(recipientEmail: string, userId?: number): Promise<boolean> {
    try {
      const report = await this.generateDailyReport(userId);
      report.recipientEmail = recipientEmail;
      return await this.sendReport(report);
    } catch (error) {
      await this.logMessage(`Failed to send daily report: ${error.message}`, 'error');
      return false;
    }
  }

  public async sendWeeklyReport(recipientEmail: string, userId?: number): Promise<boolean> {
    try {
      const report = await this.generateWeeklyReport(userId);
      report.recipientEmail = recipientEmail;
      return await this.sendReport(report);
    } catch (error) {
      await this.logMessage(`Failed to send weekly report: ${error.message}`, 'error');
      return false;
    }
  }

  public async testConnection(): Promise<boolean> {
    try {
      if (!this.transporter) {
        return false;
      }
      await this.transporter.verify();
      await this.logMessage('Email connection test successful');
      return true;
    } catch (error) {
      await this.logMessage(`Email connection test failed: ${error.message}`, 'error');
      return false;
    }
  }

  public async getReportLogs(limit: number = 50): Promise<string[]> {
    try {
      const logContent = await fs.readFile(this.logPath, 'utf-8');
      const lines = logContent.split('\n').filter(line => line.trim());
      return lines.slice(-limit);
    } catch (error) {
      await this.logMessage(`Failed to read report logs: ${error.message}`, 'error');
      return [];
    }
  }
}

// Default export for easy importing
export default EmailReporter;