"""
Tests for analytics engine
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from core.analytics import AnalyticsEngine, AnalyticsTimeframe, TradeMetrics, AnalyticsSummary
from services.report_pdf import get_pdf_builder


class TestAnalyticsEngine:
    """Test cases for analytics engine"""
    
    @pytest.fixture
    def analytics_engine(self):
        """Create analytics engine instance"""
        return AnalyticsEngine()
    
    @pytest.fixture
    def sample_trades(self):
        """Create sample trade data"""
        return [
            TradeMetrics(
                trade_id="T001",
                symbol="XAUUSD",
                entry_price=1950.0,
                exit_price=1965.0,
                volume=0.1,
                profit_loss=150.0,
                profit_loss_percentage=0.77,
                duration_seconds=3600,
                signal_provider="provider_1",
                entry_time=datetime.utcnow() - timedelta(hours=2),
                exit_time=datetime.utcnow() - timedelta(hours=1)
            ),
            TradeMetrics(
                trade_id="T002",
                symbol="EURUSD",
                entry_price=1.0850,
                exit_price=1.0825,
                volume=0.2,
                profit_loss=-50.0,
                profit_loss_percentage=-0.23,
                duration_seconds=1800,
                signal_provider="provider_2",
                entry_time=datetime.utcnow() - timedelta(hours=3),
                exit_time=datetime.utcnow() - timedelta(hours=2)
            )
        ]
    
    @pytest.mark.asyncio
    async def test_get_summary_analytics(self, analytics_engine, sample_trades):
        """Test getting summary analytics"""
        # Mock the data retrieval
        with patch.object(analytics_engine, '_get_trades_data', return_value=sample_trades):
            summary = await analytics_engine.get_summary_analytics()
            
            assert isinstance(summary, AnalyticsSummary)
            assert summary.total_trades == 2
            assert summary.winning_trades == 1
            assert summary.losing_trades == 1
            assert summary.win_rate == 50.0
            assert summary.total_pnl == 100.0
            assert summary.profit_factor > 0
    
    @pytest.mark.asyncio
    async def test_get_provider_analytics(self, analytics_engine):
        """Test getting provider analytics"""
        sample_providers = [
            {
                "id": "provider_1",
                "name": "Gold Signals Pro",
                "signals": [{"symbol": "XAUUSD", "created_at": datetime.utcnow().isoformat()}],
                "executed_signals": [{"symbol": "XAUUSD", "profit_loss": 150.0}]
            }
        ]
        
        with patch.object(analytics_engine, '_get_provider_data', return_value=sample_providers):
            providers = await analytics_engine.get_provider_analytics()
            
            assert len(providers) == 1
            assert providers[0].provider_name == "Gold Signals Pro"
            assert providers[0].total_signals == 1
            assert providers[0].executed_signals == 1
    
    @pytest.mark.asyncio
    async def test_get_symbol_analytics(self, analytics_engine, sample_trades):
        """Test getting symbol analytics"""
        filtered_trades = [t for t in sample_trades if t.symbol == "XAUUSD"]
        
        with patch.object(analytics_engine, '_get_symbol_trades', return_value=filtered_trades):
            analytics = await analytics_engine.get_symbol_analytics("XAUUSD")
            
            assert analytics["symbol"] == "XAUUSD"
            assert analytics["total_trades"] == 1
            assert analytics["winning_trades"] == 1
            assert analytics["win_rate"] == 100.0
    
    @pytest.mark.asyncio
    async def test_get_performance_chart_data(self, analytics_engine, sample_trades):
        """Test getting performance chart data"""
        with patch.object(analytics_engine, '_get_trades_data', return_value=sample_trades):
            chart_data = await analytics_engine.get_performance_chart_data()
            
            assert "labels" in chart_data
            assert "datasets" in chart_data
            assert len(chart_data["datasets"]) == 2  # Cumulative and daily P&L
    
    def test_calculate_summary_metrics(self, analytics_engine, sample_trades):
        """Test summary metrics calculation"""
        summary = analytics_engine._calculate_summary_metrics(sample_trades)
        
        assert summary.total_trades == 2
        assert summary.winning_trades == 1
        assert summary.losing_trades == 1
        assert summary.win_rate == 50.0
        assert summary.total_pnl == 100.0
        assert summary.average_win == 150.0
        assert summary.average_loss == -50.0
        assert summary.profit_factor == 3.0
    
    def test_calculate_drawdown(self, analytics_engine, sample_trades):
        """Test drawdown calculation"""
        max_drawdown, max_drawdown_percentage = analytics_engine._calculate_drawdown(sample_trades)
        
        assert max_drawdown >= 0
        assert max_drawdown_percentage >= 0
    
    def test_calculate_sharpe_ratio(self, analytics_engine, sample_trades):
        """Test Sharpe ratio calculation"""
        sharpe_ratio = analytics_engine._calculate_sharpe_ratio(sample_trades)
        
        assert isinstance(sharpe_ratio, float)
    
    def test_calculate_consecutive_stats(self, analytics_engine, sample_trades):
        """Test consecutive wins/losses calculation"""
        wins, losses = analytics_engine._calculate_consecutive_stats(sample_trades)
        
        assert wins >= 0
        assert losses >= 0
    
    def test_cache_functionality(self, analytics_engine):
        """Test cache functionality"""
        cache_key = "test_cache"
        test_data = {"test": "data"}
        
        # Test cache miss
        assert analytics_engine._should_update_cache(cache_key) is True
        
        # Update cache
        analytics_engine._update_cache(cache_key, test_data)
        
        # Test cache hit
        assert analytics_engine._should_update_cache(cache_key) is False
        assert analytics_engine.cache[cache_key] == test_data
    
    def test_empty_data_handling(self, analytics_engine):
        """Test handling of empty data"""
        empty_summary = analytics_engine._get_empty_summary()
        
        assert empty_summary.total_trades == 0
        assert empty_summary.win_rate == 0.0
        assert empty_summary.total_pnl == 0.0
        
        empty_symbol = analytics_engine._get_empty_symbol_analytics("XAUUSD")
        
        assert empty_symbol["symbol"] == "XAUUSD"
        assert empty_symbol["total_trades"] == 0
        assert empty_symbol["win_rate"] == 0.0


class TestPDFReportBuilder:
    """Test cases for PDF report builder"""
    
    @pytest.fixture
    def pdf_builder(self):
        """Create PDF builder instance"""
        return get_pdf_builder()
    
    @pytest.fixture
    def sample_summary(self):
        """Create sample analytics summary"""
        return AnalyticsSummary(
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=60.0,
            total_pnl=500.0,
            total_pnl_percentage=5.0,
            average_win=125.0,
            average_loss=-62.5,
            profit_factor=2.0,
            max_drawdown=100.0,
            max_drawdown_percentage=10.0,
            sharpe_ratio=1.5,
            average_trade_duration=1800,
            best_trade=200.0,
            worst_trade=-100.0,
            consecutive_wins=3,
            consecutive_losses=2,
            total_volume=5.0,
            average_latency_ms=85.5
        )
    
    def test_generate_analytics_report(self, pdf_builder, sample_summary):
        """Test PDF report generation"""
        pdf_bytes = pdf_builder.generate_analytics_report(sample_summary)
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF')  # PDF header
    
    def test_save_report_to_file(self, pdf_builder, sample_summary):
        """Test saving report to file"""
        pdf_bytes = pdf_builder.generate_analytics_report(sample_summary)
        
        file_path = pdf_builder.save_report_to_file(pdf_bytes, "test_report.pdf")
        
        assert file_path.endswith("test_report.pdf")
        
        # Clean up test file
        import os
        if os.path.exists(file_path):
            os.remove(file_path)
    
    def test_custom_styles(self, pdf_builder):
        """Test custom styles creation"""
        assert 'Title' in pdf_builder.custom_styles
        assert 'Subtitle' in pdf_builder.custom_styles
        assert 'SectionHeader' in pdf_builder.custom_styles
        assert 'Body' in pdf_builder.custom_styles
        assert 'Metric' in pdf_builder.custom_styles
    
    def test_brand_colors(self, pdf_builder):
        """Test brand colors configuration"""
        assert 'primary' in pdf_builder.brand_colors
        assert 'secondary' in pdf_builder.brand_colors
        assert 'success' in pdf_builder.brand_colors
        assert 'danger' in pdf_builder.brand_colors
    
    def test_build_header(self, pdf_builder):
        """Test header building"""
        header_elements = pdf_builder._build_header("Test User")
        
        assert len(header_elements) > 0
        # Check that header contains title and subtitle
        assert any("Trading Analytics Report" in str(elem) for elem in header_elements)
    
    def test_build_executive_summary(self, pdf_builder, sample_summary):
        """Test executive summary building"""
        summary_elements = pdf_builder._build_executive_summary(sample_summary)
        
        assert len(summary_elements) > 0
        # Check that summary contains key metrics
        assert any("Executive Summary" in str(elem) for elem in summary_elements)
    
    def test_build_performance_metrics(self, pdf_builder, sample_summary):
        """Test performance metrics building"""
        metrics_elements = pdf_builder._build_performance_metrics(sample_summary)
        
        assert len(metrics_elements) > 0
        # Check that metrics contains performance data
        assert any("Performance Metrics" in str(elem) for elem in metrics_elements)
    
    def test_build_recommendations(self, pdf_builder, sample_summary):
        """Test recommendations building"""
        recommendations = pdf_builder._build_recommendations(sample_summary)
        
        assert len(recommendations) > 0
        # Check that recommendations are generated
        assert any("Recommendations" in str(elem) for elem in recommendations)
    
    def test_status_color_functions(self, pdf_builder):
        """Test status color functions"""
        # Test good status
        assert pdf_builder._get_status_color(60.0, 50.0) == "Good"
        
        # Test fair status
        assert pdf_builder._get_status_color(45.0, 50.0) == "Fair"
        
        # Test poor status
        assert pdf_builder._get_status_color(30.0, 50.0) == "Poor"
        
        # Test PnL colors
        assert pdf_builder._get_pnl_color(100.0) == "Profit"
        assert pdf_builder._get_pnl_color(-100.0) == "Loss"
        assert pdf_builder._get_pnl_color(0.0) == "Neutral"
        
        # Test drawdown colors
        assert pdf_builder._get_drawdown_color(5.0) == "Good"
        assert pdf_builder._get_drawdown_color(15.0) == "Fair"
        assert pdf_builder._get_drawdown_color(25.0) == "High"


if __name__ == "__main__":
    pytest.main([__file__])