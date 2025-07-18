"""
Tests for signal parsing module
"""

import pytest
import asyncio

from services.parser_ai import (
    SignalProcessor, AISignalParser, RegexFallbackParser,
    ParsedSignal, SignalType, ConfidenceLevel
)


class TestRegexFallbackParser:
    """Test regex fallback parser"""
    
    def setup_method(self):
        """Setup test environment"""
        self.parser = RegexFallbackParser()
    
    def test_parse_buy_signal(self):
        """Test parsing BUY signal"""
        text = "BUY EURUSD @ 1.1000 SL: 1.0950 TP: 1.1050"
        
        signal = self.parser.parse_signal(text)
        
        assert signal is not None
        assert signal.symbol == "EURUSD"
        assert signal.signal_type == SignalType.BUY
        assert signal.entry_price == 1.1000
        assert signal.stop_loss == 1.0950
        assert 1.1050 in signal.take_profit
        assert signal.confidence == ConfidenceLevel.MEDIUM
        assert signal.parsing_method == "regex_fallback"
    
    def test_parse_sell_signal(self):
        """Test parsing SELL signal"""
        text = "SELL GBP/USD Entry: 1.2500 Stop Loss: 1.2550 Take Profit: 1.2450"
        
        signal = self.parser.parse_signal(text)
        
        assert signal is not None
        assert signal.symbol == "GBP/USD"
        assert signal.signal_type == SignalType.SELL
        assert signal.entry_price == 1.2500
        assert signal.stop_loss == 1.2550
        assert 1.2450 in signal.take_profit
    
    def test_parse_signal_with_emojis(self):
        """Test parsing signal with emoji indicators"""
        text = "🔴 SELL XAU/USD @ 1850.50 🛑 SL: 1855.00 🎯 TP: 1845.00"
        
        signal = self.parser.parse_signal(text)
        
        assert signal is not None
        assert signal.symbol == "XAU/USD"
        assert signal.signal_type == SignalType.SELL
        assert signal.entry_price == 1850.50
    
    def test_parse_multiple_take_profits(self):
        """Test parsing signal with multiple take profit levels"""
        text = "BUY USDJPY Entry: 110.50 SL: 110.00 TP: 111.00 TP: 111.50 TP: 112.00"
        
        signal = self.parser.parse_signal(text)
        
        assert signal is not None
        assert len(signal.take_profit) == 3
        assert 111.00 in signal.take_profit
        assert 111.50 in signal.take_profit
        assert 112.00 in signal.take_profit
    
    def test_parse_invalid_signal(self):
        """Test parsing invalid signal returns None"""
        text = "This is just a regular message without trading information"
        
        signal = self.parser.parse_signal(text)
        
        assert signal is None
    
    def test_parse_signal_without_symbol(self):
        """Test parsing signal without symbol returns None"""
        text = "BUY at 1.1000 SL: 1.0950 TP: 1.1050"
        
        signal = self.parser.parse_signal(text)
        
        assert signal is None


class TestAISignalParser:
    """Test AI signal parser"""
    
    def setup_method(self):
        """Setup test environment"""
        self.parser = AISignalParser()
    
    @pytest.mark.asyncio
    async def test_ai_parse_signal(self):
        """Test AI signal parsing"""
        text = "Long EURUSD at market price, target 1.1100, stop at 1.0900"
        
        signal = await self.parser.parse_signal(text)
        
        assert signal is not None
        assert signal.symbol in ["EURUSD", "EUR/USD"]
        assert signal.signal_type == SignalType.BUY
        assert signal.parsing_method in ["ai_primary", "regex_fallback"]
    
    @pytest.mark.asyncio
    async def test_ai_parse_with_fallback(self):
        """Test AI parsing with fallback to regex"""
        # Simple signal that should be caught by either AI or regex
        text = "BUY GBPUSD @ 1.3000 SL 1.2950 TP 1.3050"
        
        signal = await self.parser.parse_signal(text)
        
        assert signal is not None
        assert signal.symbol in ["GBPUSD", "GBP/USD"]
        assert signal.signal_type == SignalType.BUY
    
    @pytest.mark.asyncio
    async def test_ai_parse_complex_signal(self):
        """Test AI parsing of complex signal"""
        text = """
        🔵 LONG EUR/USD
        📊 Entry Zone: 1.1050 - 1.1070
        🎯 Target 1: 1.1120
        🎯 Target 2: 1.1180
        🛑 Stop Loss: 1.1000
        💼 Risk: 2%
        """
        
        signal = await self.parser.parse_signal(text)
        
        assert signal is not None
        assert signal.signal_type == SignalType.BUY
        assert len(signal.take_profit) >= 1
    
    @pytest.mark.asyncio
    async def test_confidence_levels(self):
        """Test different confidence levels"""
        
        # High confidence signal (clear format)
        high_conf_text = "BUY EURUSD @ 1.1000 SL: 1.0950 TP: 1.1050"
        signal = await self.parser.parse_signal(high_conf_text)
        
        if signal:
            assert signal.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]
        
        # Low confidence signal (ambiguous)
        low_conf_text = "might be a good time to buy euro"
        signal = await self.parser.parse_signal(low_conf_text)
        
        if signal:
            assert signal.confidence in [ConfidenceLevel.LOW, ConfidenceLevel.UNCERTAIN]


class TestSignalProcessor:
    """Test signal processor"""
    
    def setup_method(self):
        """Setup test environment"""
        self.processor = SignalProcessor()
    
    @pytest.mark.asyncio
    async def test_process_valid_signal(self):
        """Test processing valid signal"""
        text = "BUY EURUSD @ 1.1000 SL: 1.0950 TP: 1.1050"
        
        signal = await self.processor.process_signal(text)
        
        assert signal is not None
        assert signal.symbol == "EURUSD"
        assert signal.signal_type == SignalType.BUY
        
        # Check stats
        stats = self.processor.get_processing_stats()
        assert stats["total_processed"] >= 1
        assert stats["successful_parses"] >= 1
    
    @pytest.mark.asyncio
    async def test_process_invalid_signal(self):
        """Test processing invalid signal"""
        text = "This is not a trading signal at all"
        
        signal = await self.processor.process_signal(text)
        
        # Should return None for invalid signal
        assert signal is None
        
        # Check stats
        stats = self.processor.get_processing_stats()
        assert stats["total_processed"] >= 1
        assert stats["failed_parses"] >= 1
    
    @pytest.mark.asyncio
    async def test_preprocess_input(self):
        """Test input preprocessing"""
        raw_input = "  BUY   EURUSD  @  1.1000   SL: 1.0950  "
        
        cleaned = self.processor._preprocess_input(raw_input)
        
        assert cleaned == "BUY EURUSD @ 1.1000 SL: 1.0950"
    
    @pytest.mark.asyncio
    async def test_multiple_signals_processing(self):
        """Test processing multiple signals"""
        signals_texts = [
            "BUY EURUSD @ 1.1000 SL: 1.0950 TP: 1.1050",
            "SELL GBPUSD @ 1.3000 SL: 1.3050 TP: 1.2950",
            "Invalid signal text",
            "BUY USDJPY @ 110.50 SL: 110.00 TP: 111.00"
        ]
        
        results = []
        for text in signals_texts:
            signal = await self.processor.process_signal(text)
            results.append(signal)
        
        # Should have 3 valid signals and 1 None
        valid_signals = [s for s in results if s is not None]
        assert len(valid_signals) == 3
        
        # Check final stats
        stats = self.processor.get_processing_stats()
        assert stats["total_processed"] == 4
        assert stats["successful_parses"] == 3
        assert stats["failed_parses"] == 1
        assert stats["success_rate"] == 0.75
    
    def test_get_processing_stats(self):
        """Test getting processing statistics"""
        stats = self.processor.get_processing_stats()
        
        assert isinstance(stats, dict)
        assert "total_processed" in stats
        assert "successful_parses" in stats
        assert "failed_parses" in stats
        assert "success_rate" in stats
        assert "ai_success_rate" in stats


@pytest.fixture
def sample_signal_texts():
    """Sample signal texts for testing"""
    return [
        "BUY EURUSD @ 1.1000 SL: 1.0950 TP: 1.1050",
        "SELL GBP/USD Entry: 1.2500 Stop: 1.2550 Target: 1.2450",
        "🔴 SHORT XAU/USD @ 1850.50 🛑 SL: 1855.00 🎯 TP: 1845.00",
        "Long bitcoin, entry around 45000, stop at 43000",
        "EUR/USD buy signal activated at 1.1025"
    ]


@pytest.mark.asyncio
async def test_end_to_end_parsing(sample_signal_texts):
    """End-to-end parsing test"""
    processor = SignalProcessor()
    
    parsed_signals = []
    for text in sample_signal_texts:
        signal = await processor.process_signal(text)
        if signal:
            parsed_signals.append(signal)
    
    # Should parse most signals successfully
    assert len(parsed_signals) >= 3
    
    # All parsed signals should have required fields
    for signal in parsed_signals:
        assert signal.symbol
        assert signal.signal_type in [SignalType.BUY, SignalType.SELL]
        assert signal.confidence in [
            ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, 
            ConfidenceLevel.LOW, ConfidenceLevel.UNCERTAIN
        ]
        assert signal.parsing_method in ["ai_primary", "regex_fallback"]
        assert signal.timestamp is not None


def test_parsed_signal_to_dict():
    """Test ParsedSignal to_dict conversion"""
    signal = ParsedSignal(
        symbol="EURUSD",
        signal_type=SignalType.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=[1.1050, 1.1100],
        confidence=ConfidenceLevel.HIGH,
        raw_text="BUY EURUSD @ 1.1000",
        parsing_method="test"
    )
    
    signal_dict = signal.to_dict()
    
    assert isinstance(signal_dict, dict)
    assert signal_dict["symbol"] == "EURUSD"
    assert signal_dict["signal_type"] == "BUY"
    assert signal_dict["confidence"] == "HIGH"
    assert signal_dict["take_profit"] == [1.1050, 1.1100]
    assert "timestamp" in signal_dict