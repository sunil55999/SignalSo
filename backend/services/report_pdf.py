"""
PDF Report Builder Service
"""

import io
import os
import tempfile
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
# from reportlab.platypus.charts import VerticalBarChart, HorizontalLineChart  # Charts module not available in base reportlab
# from reportlab.lib.charts import Drawing  # Charts module not available in base reportlab
# from reportlab.graphics.shapes import String
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from core.analytics import AnalyticsSummary, ProviderAnalytics, TradeMetrics
from utils.logging_config import get_logger

logger = get_logger("report_pdf")


class PDFReportBuilder:
    """PDF report builder for trading analytics"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.custom_styles = self._create_custom_styles()
        self.brand_colors = {
            'primary': HexColor('#2563eb'),
            'secondary': HexColor('#64748b'),
            'success': HexColor('#10b981'),
            'danger': HexColor('#ef4444'),
            'warning': HexColor('#f59e0b'),
            'light': HexColor('#f8fafc'),
            'dark': HexColor('#1e293b')
        }
    
    def _create_custom_styles(self) -> Dict[str, ParagraphStyle]:
        """Create custom paragraph styles"""
        styles = {}
        
        # Title style
        styles['Title'] = ParagraphStyle(
            'Title',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=HexColor('#1e293b'),
            alignment=TA_CENTER
        )
        
        # Subtitle style
        styles['Subtitle'] = ParagraphStyle(
            'Subtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            textColor=HexColor('#475569'),
            alignment=TA_LEFT
        )
        
        # Section header style
        styles['SectionHeader'] = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceAfter=15,
            textColor=HexColor('#2563eb'),
            alignment=TA_LEFT
        )
        
        # Body text style
        styles['Body'] = ParagraphStyle(
            'Body',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=10,
            textColor=HexColor('#374151'),
            alignment=TA_LEFT
        )
        
        # Metric style
        styles['Metric'] = ParagraphStyle(
            'Metric',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=5,
            textColor=HexColor('#1f2937'),
            alignment=TA_LEFT
        )
        
        return styles
    
    def generate_analytics_report(self, summary: AnalyticsSummary, 
                                trades: List[TradeMetrics] = None,
                                providers: List[ProviderAnalytics] = None,
                                chart_data: Dict[str, Any] = None,
                                user_name: str = "User") -> bytes:
        """Generate comprehensive analytics PDF report"""
        try:
            # Create PDF buffer
            buffer = io.BytesIO()
            
            # Create document
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Build report content
            story = []
            
            # Header
            story.extend(self._build_header(user_name))
            
            # Executive Summary
            story.extend(self._build_executive_summary(summary))
            
            # Performance Metrics
            story.extend(self._build_performance_metrics(summary))
            
            # Trade Analysis
            if trades:
                story.extend(self._build_trade_analysis(trades))
            
            # Provider Analysis
            if providers:
                story.extend(self._build_provider_analysis(providers))
            
            # Charts and Visualizations
            if chart_data:
                story.extend(self._build_charts(chart_data))
            
            # Recommendations
            story.extend(self._build_recommendations(summary))
            
            # Footer
            story.extend(self._build_footer())
            
            # Build PDF
            doc.build(story)
            
            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            logger.info("PDF report generated successfully")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Error generating PDF report: {e}")
            raise
    
    def _build_header(self, user_name: str) -> List:
        """Build report header"""
        story = []
        
        # Title
        title = Paragraph("Trading Analytics Report", self.custom_styles['Title'])
        story.append(title)
        
        # Subtitle with user and date
        subtitle_text = f"Report for {user_name} | Generated on {datetime.now().strftime('%B %d, %Y')}"
        subtitle = Paragraph(subtitle_text, self.custom_styles['Subtitle'])
        story.append(subtitle)
        
        story.append(Spacer(1, 20))
        
        return story
    
    def _build_executive_summary(self, summary: AnalyticsSummary) -> List:
        """Build executive summary section"""
        story = []
        
        # Section header
        header = Paragraph("Executive Summary", self.custom_styles['SectionHeader'])
        story.append(header)
        
        # Key metrics table
        key_metrics = [
            ['Total Trades', str(summary.total_trades)],
            ['Win Rate', f"{summary.win_rate:.1f}%"],
            ['Total P&L', f"${summary.total_pnl:.2f}"],
            ['Profit Factor', f"{summary.profit_factor:.2f}"],
            ['Max Drawdown', f"{summary.max_drawdown_percentage:.1f}%"],
            ['Sharpe Ratio', f"{summary.sharpe_ratio:.2f}"]
        ]
        
        table = Table(key_metrics, colWidths=[2*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.brand_colors['light']),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.brand_colors['dark']),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, self.brand_colors['secondary'])
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _build_performance_metrics(self, summary: AnalyticsSummary) -> List:
        """Build performance metrics section"""
        story = []
        
        # Section header
        header = Paragraph("Performance Metrics", self.custom_styles['SectionHeader'])
        story.append(header)
        
        # Detailed metrics table
        metrics = [
            ['Metric', 'Value', 'Status'],
            ['Total Trades', str(summary.total_trades), ''],
            ['Winning Trades', str(summary.winning_trades), ''],
            ['Losing Trades', str(summary.losing_trades), ''],
            ['Win Rate', f"{summary.win_rate:.1f}%", self._get_status_color(summary.win_rate, 50)],
            ['Total P&L', f"${summary.total_pnl:.2f}", self._get_pnl_color(summary.total_pnl)],
            ['Average Win', f"${summary.average_win:.2f}", ''],
            ['Average Loss', f"${summary.average_loss:.2f}", ''],
            ['Profit Factor', f"{summary.profit_factor:.2f}", self._get_status_color(summary.profit_factor, 1.0)],
            ['Max Drawdown', f"{summary.max_drawdown_percentage:.1f}%", self._get_drawdown_color(summary.max_drawdown_percentage)],
            ['Sharpe Ratio', f"{summary.sharpe_ratio:.2f}", self._get_status_color(summary.sharpe_ratio, 1.0)],
            ['Best Trade', f"${summary.best_trade:.2f}", ''],
            ['Worst Trade', f"${summary.worst_trade:.2f}", ''],
            ['Total Volume', f"{summary.total_volume:.2f}", ''],
            ['Avg Latency', f"{summary.average_latency_ms:.1f}ms", '']
        ]
        
        table = Table(metrics, colWidths=[2*inch, 1.5*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.brand_colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, self.brand_colors['secondary'])
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _build_trade_analysis(self, trades: List[TradeMetrics]) -> List:
        """Build trade analysis section"""
        story = []
        
        # Section header
        header = Paragraph("Trade Analysis", self.custom_styles['SectionHeader'])
        story.append(header)
        
        # Recent trades table (last 10)
        recent_trades = sorted(trades, key=lambda t: t.entry_time, reverse=True)[:10]
        
        trade_data = [['Symbol', 'Type', 'P&L', 'Duration', 'Entry Time']]
        
        for trade in recent_trades:
            trade_type = "BUY" if trade.profit_loss > 0 else "SELL"  # Simplified
            duration = f"{trade.duration_seconds // 3600}h {(trade.duration_seconds % 3600) // 60}m"
            entry_time = trade.entry_time.strftime('%m/%d %H:%M')
            
            trade_data.append([
                trade.symbol,
                trade_type,
                f"${trade.profit_loss:.2f}",
                duration,
                entry_time
            ])
        
        table = Table(trade_data, colWidths=[1*inch, 0.8*inch, 1*inch, 1*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.brand_colors['secondary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, self.brand_colors['secondary'])
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _build_provider_analysis(self, providers: List[ProviderAnalytics]) -> List:
        """Build provider analysis section"""
        story = []
        
        # Section header
        header = Paragraph("Signal Provider Analysis", self.custom_styles['SectionHeader'])
        story.append(header)
        
        # Provider performance table
        provider_data = [['Provider', 'Signals', 'Executed', 'Win Rate', 'Avg P&L']]
        
        for provider in providers:
            provider_data.append([
                provider.provider_name,
                str(provider.total_signals),
                str(provider.executed_signals),
                f"{provider.win_rate:.1f}%",
                f"${provider.average_pnl:.2f}"
            ])
        
        table = Table(provider_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.brand_colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, self.brand_colors['secondary'])
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _build_charts(self, chart_data: Dict[str, Any]) -> List:
        """Build charts section"""
        story = []
        
        # Section header
        header = Paragraph("Performance Charts", self.custom_styles['SectionHeader'])
        story.append(header)
        
        # Add chart placeholder (ReportLab charts are complex, simplified here)
        chart_text = "Performance charts would be rendered here in a full implementation."
        chart_paragraph = Paragraph(chart_text, self.custom_styles['Body'])
        story.append(chart_paragraph)
        
        story.append(Spacer(1, 20))
        
        return story
    
    def _build_recommendations(self, summary: AnalyticsSummary) -> List:
        """Build recommendations section"""
        story = []
        
        # Section header
        header = Paragraph("Recommendations", self.custom_styles['SectionHeader'])
        story.append(header)
        
        # Generate recommendations based on metrics
        recommendations = []
        
        if summary.win_rate < 50:
            recommendations.append("• Consider reviewing your trading strategy as win rate is below 50%")
        
        if summary.profit_factor < 1.0:
            recommendations.append("• Focus on risk management - profit factor is below 1.0")
        
        if summary.max_drawdown_percentage > 20:
            recommendations.append("• Reduce position sizes to limit drawdown exposure")
        
        if summary.sharpe_ratio < 1.0:
            recommendations.append("• Improve risk-adjusted returns by optimizing entry/exit timing")
        
        if not recommendations:
            recommendations.append("• Excellent performance! Continue following your current strategy")
        
        for recommendation in recommendations:
            rec_paragraph = Paragraph(recommendation, self.custom_styles['Body'])
            story.append(rec_paragraph)
        
        story.append(Spacer(1, 20))
        
        return story
    
    def _build_footer(self) -> List:
        """Build report footer"""
        story = []
        
        # Disclaimer
        disclaimer = (
            "This report is generated by SignalOS Analytics Engine. "
            "Past performance does not guarantee future results. "
            "Trading involves risk and may result in loss of capital."
        )
        
        footer_paragraph = Paragraph(disclaimer, self.custom_styles['Body'])
        story.append(footer_paragraph)
        
        return story
    
    def _get_status_color(self, value: float, threshold: float) -> str:
        """Get status color based on value and threshold"""
        if value >= threshold:
            return "Good"
        elif value >= threshold * 0.8:
            return "Fair"
        else:
            return "Poor"
    
    def _get_pnl_color(self, pnl: float) -> str:
        """Get color based on P&L"""
        if pnl > 0:
            return "Profit"
        elif pnl < 0:
            return "Loss"
        else:
            return "Neutral"
    
    def _get_drawdown_color(self, drawdown: float) -> str:
        """Get color based on drawdown percentage"""
        if drawdown < 10:
            return "Good"
        elif drawdown < 20:
            return "Fair"
        else:
            return "High"
    
    def save_report_to_file(self, report_bytes: bytes, filename: str = None) -> str:
        """Save report to file and return path"""
        try:
            if filename is None:
                filename = f"trading_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            # Create reports directory if it doesn't exist
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            
            # Save file
            file_path = reports_dir / filename
            with open(file_path, 'wb') as f:
                f.write(report_bytes)
            
            logger.info(f"Report saved to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error saving report to file: {e}")
            raise


# Global PDF builder instance
_pdf_builder = None


def get_pdf_builder() -> PDFReportBuilder:
    """Get global PDF builder instance"""
    global _pdf_builder
    if _pdf_builder is None:
        _pdf_builder = PDFReportBuilder()
    return _pdf_builder