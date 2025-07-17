#!/usr/bin/env python3
"""
PDF Report Generator for SignalOS Desktop Application

Generates comprehensive PDF reports from backtesting results.
Includes summary, equity curve, statistics, and trade details.
"""

import os
import io
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import numpy as np

# Try to import reportlab
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.platypus import PageBreak, Image as ReportLabImage
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFReportGenerator:
    """
    Comprehensive PDF report generator for backtesting results
    """
    
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Report styling
        self.primary_color = colors.HexColor('#2E86AB')
        self.secondary_color = colors.HexColor('#A23B72')
        self.success_color = colors.HexColor('#2ECC71')
        self.danger_color = colors.HexColor('#E74C3C')
        self.warning_color = colors.HexColor('#F39C12')
        
        # Initialize matplotlib style
        plt.style.use('seaborn-v0_8')
        
        logger.info("PDFReportGenerator initialized")
    
    def generate_report(self, backtest_result, filename: str = None) -> str:
        """
        Generate comprehensive PDF report from backtest results
        """
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"SignalOS_Backtest_Report_{timestamp}.pdf"
            
            output_path = self.output_dir / filename
            
            if REPORTLAB_AVAILABLE:
                return self._generate_reportlab_pdf(backtest_result, output_path)
            else:
                return self._generate_matplotlib_pdf(backtest_result, output_path)
                
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}")
            return None
    
    def _generate_reportlab_pdf(self, result, output_path: Path) -> str:
        """Generate PDF using ReportLab"""
        try:
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            story = []
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=self.primary_color,
                alignment=TA_CENTER,
                spaceAfter=30
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=self.primary_color,
                spaceBefore=20,
                spaceAfter=10
            )
            
            # Title page
            story.append(Paragraph("SignalOS Backtest Report", title_style))
            story.append(Spacer(1, 20))
            
            # Executive Summary
            story.append(Paragraph("Executive Summary", heading_style))
            summary_data = [
                ['Metric', 'Value'],
                ['Initial Balance', f"${result.summary['initial_balance']:,.2f}"],
                ['Final Balance', f"${result.summary['final_balance']:,.2f}"],
                ['Total Return', f"{result.summary['total_return']:.2f}%"],
                ['Total Trades', f"{result.summary['total_trades']}"],
                ['Win Rate', f"{result.summary['win_rate']:.1f}%"],
                ['Profit Factor', f"{result.summary['profit_factor']:.2f}"],
                ['Max Drawdown', f"{result.summary['max_drawdown']:.2f}%"],
                ['Sharpe Ratio', f"{result.summary['sharpe_ratio']:.2f}"]
            ]
            
            summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 20))
            
            # Performance metrics
            story.append(Paragraph("Performance Metrics", heading_style))
            metrics_data = [
                ['Metric', 'Value'],
                ['Total Trades', f"{result.performance_metrics.get('total_trades', 0)}"],
                ['Winning Trades', f"{result.performance_metrics.get('winning_trades', 0)}"],
                ['Losing Trades', f"{result.performance_metrics.get('losing_trades', 0)}"],
                ['Average Trade P&L', f"${result.performance_metrics.get('avg_trade_pnl', 0):.2f}"],
                ['Average Win', f"${result.performance_metrics.get('avg_win', 0):.2f}"],
                ['Average Loss', f"${result.performance_metrics.get('avg_loss', 0):.2f}"],
                ['Avg Risk/Reward', f"{result.performance_metrics.get('avg_risk_reward', 0):.2f}"],
                ['Recovery Factor', f"{result.performance_metrics.get('recovery_factor', 0):.2f}"]
            ]
            
            metrics_table = Table(metrics_data, colWidths=[2*inch, 2*inch])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.secondary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(metrics_table)
            story.append(PageBreak())
            
            # Generate charts
            equity_chart = self._create_equity_chart(result.equity_curve)
            drawdown_chart = self._create_drawdown_chart(result.drawdown_curve)
            
            if equity_chart:
                story.append(Paragraph("Equity Curve", heading_style))
                story.append(ReportLabImage(equity_chart, width=6*inch, height=4*inch))
                story.append(Spacer(1, 20))
            
            if drawdown_chart:
                story.append(Paragraph("Drawdown Curve", heading_style))
                story.append(ReportLabImage(drawdown_chart, width=6*inch, height=4*inch))
                story.append(PageBreak())
            
            # Monthly returns
            if result.monthly_returns:
                story.append(Paragraph("Monthly Returns", heading_style))
                monthly_data = [['Month', 'Return', 'Trades', 'Win Rate']]
                for month_data in result.monthly_returns:
                    monthly_data.append([
                        month_data['month'],
                        f"${month_data['return']:.2f}",
                        f"{month_data['trades']}",
                        f"{month_data['win_rate']:.1f}%"
                    ])
                
                monthly_table = Table(monthly_data, colWidths=[1.5*inch, 1.5*inch, 1*inch, 1*inch])
                monthly_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(monthly_table)
                story.append(PageBreak())
            
            # Trade details (first 20 trades)
            story.append(Paragraph("Trade Details (First 20 Trades)", heading_style))
            trade_data = [['#', 'Symbol', 'Direction', 'Entry', 'Exit', 'P&L', 'Pips', 'Status']]
            
            for i, trade in enumerate(result.trades[:20]):
                trade_data.append([
                    f"{i+1}",
                    trade.symbol,
                    trade.direction,
                    f"{trade.entry_price:.5f}",
                    f"{trade.exit_price:.5f}" if trade.exit_price else "N/A",
                    f"${trade.pnl:.2f}" if trade.pnl else "N/A",
                    f"{trade.pnl_pips:.1f}" if trade.pnl_pips else "N/A",
                    trade.status
                ])
            
            trade_table = Table(trade_data, colWidths=[0.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.6*inch, 0.8*inch])
            trade_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8)
            ]))
            
            story.append(trade_table)
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"PDF report generated: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"ReportLab PDF generation failed: {e}")
            return None
    
    def _generate_matplotlib_pdf(self, result, output_path: Path) -> str:
        """Generate PDF using matplotlib (fallback)"""
        try:
            with PdfPages(str(output_path)) as pdf:
                # Page 1: Summary
                fig, ax = plt.subplots(figsize=(8.27, 11.69))  # A4 size
                ax.axis('off')
                
                # Title
                fig.suptitle('SignalOS Backtest Report', fontsize=20, fontweight='bold')
                
                # Summary table
                summary_text = f"""
                Executive Summary
                
                Initial Balance: ${result.summary['initial_balance']:,.2f}
                Final Balance: ${result.summary['final_balance']:,.2f}
                Total Return: {result.summary['total_return']:.2f}%
                Total Trades: {result.summary['total_trades']}
                Win Rate: {result.summary['win_rate']:.1f}%
                Profit Factor: {result.summary['profit_factor']:.2f}
                Max Drawdown: {result.summary['max_drawdown']:.2f}%
                Sharpe Ratio: {result.summary['sharpe_ratio']:.2f}
                
                Performance Metrics
                
                Total Trades: {result.performance_metrics.get('total_trades', 0)}
                Winning Trades: {result.performance_metrics.get('winning_trades', 0)}
                Losing Trades: {result.performance_metrics.get('losing_trades', 0)}
                Average Trade P&L: ${result.performance_metrics.get('avg_trade_pnl', 0):.2f}
                Average Win: ${result.performance_metrics.get('avg_win', 0):.2f}
                Average Loss: ${result.performance_metrics.get('avg_loss', 0):.2f}
                Average Risk/Reward: {result.performance_metrics.get('avg_risk_reward', 0):.2f}
                Recovery Factor: {result.performance_metrics.get('recovery_factor', 0):.2f}
                """
                
                ax.text(0.1, 0.9, summary_text, transform=ax.transAxes, fontsize=12,
                       verticalalignment='top', fontfamily='monospace')
                
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)
                
                # Page 2: Equity Curve
                if result.equity_curve:
                    fig, ax = plt.subplots(figsize=(8.27, 11.69))
                    
                    # Prepare data
                    timestamps = [datetime.fromisoformat(point['timestamp']) for point in result.equity_curve]
                    balances = [point['balance'] for point in result.equity_curve]
                    
                    # Plot equity curve
                    ax.plot(timestamps, balances, linewidth=2, color='blue')
                    ax.set_title('Equity Curve', fontsize=16, fontweight='bold')
                    ax.set_xlabel('Date')
                    ax.set_ylabel('Balance ($)')
                    ax.grid(True, alpha=0.3)
                    
                    # Format x-axis
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
                    
                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close(fig)
                
                # Page 3: Drawdown Chart
                if result.drawdown_curve:
                    fig, ax = plt.subplots(figsize=(8.27, 11.69))
                    
                    # Prepare data
                    timestamps = [datetime.fromisoformat(point['timestamp']) for point in result.drawdown_curve]
                    drawdowns = [point['drawdown'] for point in result.drawdown_curve]
                    
                    # Plot drawdown
                    ax.fill_between(timestamps, drawdowns, 0, alpha=0.3, color='red')
                    ax.plot(timestamps, drawdowns, linewidth=2, color='red')
                    ax.set_title('Drawdown Curve', fontsize=16, fontweight='bold')
                    ax.set_xlabel('Date')
                    ax.set_ylabel('Drawdown (%)')
                    ax.grid(True, alpha=0.3)
                    
                    # Format x-axis
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
                    
                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close(fig)
                
                # Page 4: Monthly Returns
                if result.monthly_returns:
                    fig, ax = plt.subplots(figsize=(8.27, 11.69))
                    
                    months = [data['month'] for data in result.monthly_returns]
                    returns = [data['return'] for data in result.monthly_returns]
                    
                    colors = ['green' if r > 0 else 'red' for r in returns]
                    
                    ax.bar(months, returns, color=colors, alpha=0.7)
                    ax.set_title('Monthly Returns', fontsize=16, fontweight='bold')
                    ax.set_xlabel('Month')
                    ax.set_ylabel('Return ($)')
                    ax.grid(True, alpha=0.3, axis='y')
                    
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
                    
                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close(fig)
            
            logger.info(f"Matplotlib PDF report generated: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Matplotlib PDF generation failed: {e}")
            return None
    
    def _create_equity_chart(self, equity_curve: List[Dict]) -> Optional[io.BytesIO]:
        """Create equity curve chart"""
        try:
            if not equity_curve:
                return None
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Prepare data
            timestamps = [datetime.fromisoformat(point['timestamp']) for point in equity_curve]
            balances = [point['balance'] for point in equity_curve]
            
            # Plot
            ax.plot(timestamps, balances, linewidth=2, color='#2E86AB')
            ax.set_title('Account Equity Curve', fontsize=14, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Balance ($)')
            ax.grid(True, alpha=0.3)
            
            # Format
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            # Save to BytesIO
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150)
            img_buffer.seek(0)
            plt.close(fig)
            
            return img_buffer
            
        except Exception as e:
            logger.error(f"Equity chart creation failed: {e}")
            return None
    
    def _create_drawdown_chart(self, drawdown_curve: List[Dict]) -> Optional[io.BytesIO]:
        """Create drawdown chart"""
        try:
            if not drawdown_curve:
                return None
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Prepare data
            timestamps = [datetime.fromisoformat(point['timestamp']) for point in drawdown_curve]
            drawdowns = [point['drawdown'] for point in drawdown_curve]
            
            # Plot
            ax.fill_between(timestamps, drawdowns, 0, alpha=0.3, color='#E74C3C')
            ax.plot(timestamps, drawdowns, linewidth=2, color='#E74C3C')
            ax.set_title('Account Drawdown', fontsize=14, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Drawdown (%)')
            ax.grid(True, alpha=0.3)
            
            # Format
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            # Save to BytesIO
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150)
            img_buffer.seek(0)
            plt.close(fig)
            
            return img_buffer
            
        except Exception as e:
            logger.error(f"Drawdown chart creation failed: {e}")
            return None
    
    def create_quick_report(self, result, filename: str = None) -> str:
        """Create a quick text-based report"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"SignalOS_Quick_Report_{timestamp}.txt"
            
            output_path = self.output_dir / filename
            
            with open(output_path, 'w') as f:
                f.write("=" * 60 + "\n")
                f.write("SIGNALOS BACKTEST REPORT\n")
                f.write("=" * 60 + "\n\n")
                
                f.write("EXECUTIVE SUMMARY\n")
                f.write("-" * 40 + "\n")
                f.write(f"Initial Balance: ${result.summary['initial_balance']:,.2f}\n")
                f.write(f"Final Balance: ${result.summary['final_balance']:,.2f}\n")
                f.write(f"Total Return: {result.summary['total_return']:.2f}%\n")
                f.write(f"Total Trades: {result.summary['total_trades']}\n")
                f.write(f"Win Rate: {result.summary['win_rate']:.1f}%\n")
                f.write(f"Profit Factor: {result.summary['profit_factor']:.2f}\n")
                f.write(f"Max Drawdown: {result.summary['max_drawdown']:.2f}%\n")
                f.write(f"Sharpe Ratio: {result.summary['sharpe_ratio']:.2f}\n\n")
                
                f.write("PERFORMANCE METRICS\n")
                f.write("-" * 40 + "\n")
                f.write(f"Total Trades: {result.performance_metrics.get('total_trades', 0)}\n")
                f.write(f"Winning Trades: {result.performance_metrics.get('winning_trades', 0)}\n")
                f.write(f"Losing Trades: {result.performance_metrics.get('losing_trades', 0)}\n")
                f.write(f"Average Trade P&L: ${result.performance_metrics.get('avg_trade_pnl', 0):.2f}\n")
                f.write(f"Average Win: ${result.performance_metrics.get('avg_win', 0):.2f}\n")
                f.write(f"Average Loss: ${result.performance_metrics.get('avg_loss', 0):.2f}\n")
                f.write(f"Average Risk/Reward: {result.performance_metrics.get('avg_risk_reward', 0):.2f}\n")
                f.write(f"Recovery Factor: {result.performance_metrics.get('recovery_factor', 0):.2f}\n\n")
                
                if result.monthly_returns:
                    f.write("MONTHLY RETURNS\n")
                    f.write("-" * 40 + "\n")
                    for month_data in result.monthly_returns:
                        f.write(f"{month_data['month']}: ${month_data['return']:.2f} "
                               f"({month_data['trades']} trades, {month_data['win_rate']:.1f}% win rate)\n")
                    f.write("\n")
                
                f.write("TRADE DETAILS (First 20 Trades)\n")
                f.write("-" * 40 + "\n")
                f.write(f"{'#':<3} {'Symbol':<8} {'Dir':<4} {'Entry':<8} {'Exit':<8} {'P&L':<8} {'Pips':<6} {'Status':<8}\n")
                f.write("-" * 60 + "\n")
                
                for i, trade in enumerate(result.trades[:20]):
                    f.write(f"{i+1:<3} {trade.symbol:<8} {trade.direction:<4} "
                           f"{trade.entry_price:<8.5f} "
                           f"{trade.exit_price or 0:<8.5f} "
                           f"{trade.pnl or 0:<8.2f} "
                           f"{trade.pnl_pips or 0:<6.1f} "
                           f"{trade.status:<8}\n")
                
                f.write("\n" + "=" * 60 + "\n")
                f.write(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n")
            
            logger.info(f"Quick report generated: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Quick report generation failed: {e}")
            return None


# Example usage
async def test_report_generator():
    """Test the report generator"""
    from desktop_app.backtest.engine import BacktestEngine
    
    # Create mock backtest result
    engine = BacktestEngine()
    signals = engine.generate_sample_signals(20)
    result = engine.run_backtest(signals)
    
    if result:
        # Generate reports
        generator = PDFReportGenerator()
        
        # PDF report
        pdf_path = generator.generate_report(result)
        if pdf_path:
            print(f"PDF report generated: {pdf_path}")
        
        # Quick text report
        txt_path = generator.create_quick_report(result)
        if txt_path:
            print(f"Text report generated: {txt_path}")
    else:
        print("Failed to generate backtest result")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_report_generator())