"""
Analytics System - PnL, WinRate, DD, Latency calculations
"""

import asyncio
import json
import statistics
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import math

from utils.logging_config import get_logger
# from db.models import Trade, Signal, User  # Will be used in production

logger = get_logger("analytics")


class AnalyticsTimeframe(Enum):
    """Analytics timeframe options"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    ALL_TIME = "all_time"


@dataclass
class TradeMetrics:
    """Individual trade metrics"""
    trade_id: str
    symbol: str
    entry_price: float
    exit_price: float
    volume: float
    profit_loss: float
    profit_loss_percentage: float
    duration_seconds: int
    signal_provider: Optional[str]
    entry_time: datetime
    exit_time: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['entry_time'] = self.entry_time.isoformat()
        data['exit_time'] = self.exit_time.isoformat()
        return data


@dataclass
class AnalyticsSummary:
    """Analytics summary data"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_percentage: float
    average_win: float
    average_loss: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_percentage: float
    sharpe_ratio: float
    average_trade_duration: int
    best_trade: float
    worst_trade: float
    consecutive_wins: int
    consecutive_losses: int
    total_volume: float
    average_latency_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class ProviderAnalytics:
    """Analytics for signal providers"""
    provider_id: str
    provider_name: str
    total_signals: int
    executed_signals: int
    execution_rate: float
    win_rate: float
    average_pnl: float
    best_performing_symbol: str
    worst_performing_symbol: str
    average_signal_latency_ms: float
    last_signal_time: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['last_signal_time'] = self.last_signal_time.isoformat()
        return data


class AnalyticsEngine:
    """Main analytics calculation engine"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
        self.last_cache_update = {}
    
    def _should_update_cache(self, cache_key: str) -> bool:
        """Check if cache should be updated"""
        if cache_key not in self.last_cache_update:
            return True
        
        last_update = self.last_cache_update[cache_key]
        return (datetime.utcnow() - last_update).seconds > self.cache_timeout
    
    def _update_cache(self, cache_key: str, data: Any):
        """Update cache with new data"""
        self.cache[cache_key] = data
        self.last_cache_update[cache_key] = datetime.utcnow()
    
    async def get_summary_analytics(self, user_id: str = None, 
                                   timeframe: AnalyticsTimeframe = AnalyticsTimeframe.ALL_TIME) -> AnalyticsSummary:
        """Get summary analytics for user or all users"""
        try:
            cache_key = f"summary_{user_id or 'all'}_{timeframe.value}"
            
            if not self._should_update_cache(cache_key):
                return self.cache[cache_key]
            
            # Get trade data (in production, query from database)
            trades = await self._get_trades_data(user_id, timeframe)
            
            if not trades:
                return self._get_empty_summary()
            
            # Calculate metrics
            summary = self._calculate_summary_metrics(trades)
            
            # Update cache
            self._update_cache(cache_key, summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error calculating summary analytics: {e}")
            return self._get_empty_summary()
    
    async def get_provider_analytics(self, provider_id: str = None) -> List[ProviderAnalytics]:
        """Get analytics for signal providers"""
        try:
            cache_key = f"provider_{provider_id or 'all'}"
            
            if not self._should_update_cache(cache_key):
                return self.cache[cache_key]
            
            # Get provider data (in production, query from database)
            providers_data = await self._get_provider_data(provider_id)
            
            analytics = []
            for provider_data in providers_data:
                provider_analytics = self._calculate_provider_metrics(provider_data)
                analytics.append(provider_analytics)
            
            # Update cache
            self._update_cache(cache_key, analytics)
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error calculating provider analytics: {e}")
            return []
    
    async def get_symbol_analytics(self, symbol: str, user_id: str = None) -> Dict[str, Any]:
        """Get analytics for specific symbol"""
        try:
            cache_key = f"symbol_{symbol}_{user_id or 'all'}"
            
            if not self._should_update_cache(cache_key):
                return self.cache[cache_key]
            
            # Get symbol trades data
            trades = await self._get_symbol_trades(symbol, user_id)
            
            if not trades:
                return self._get_empty_symbol_analytics(symbol)
            
            # Calculate symbol-specific metrics
            analytics = self._calculate_symbol_metrics(trades, symbol)
            
            # Update cache
            self._update_cache(cache_key, analytics)
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error calculating symbol analytics: {e}")
            return self._get_empty_symbol_analytics(symbol)
    
    async def get_performance_chart_data(self, user_id: str = None, 
                                       timeframe: AnalyticsTimeframe = AnalyticsTimeframe.MONTHLY) -> Dict[str, Any]:
        """Get performance chart data"""
        try:
            cache_key = f"chart_{user_id or 'all'}_{timeframe.value}"
            
            if not self._should_update_cache(cache_key):
                return self.cache[cache_key]
            
            # Get trade data
            trades = await self._get_trades_data(user_id, timeframe)
            
            # Calculate time series data
            chart_data = self._calculate_chart_data(trades, timeframe)
            
            # Update cache
            self._update_cache(cache_key, chart_data)
            
            return chart_data
            
        except Exception as e:
            logger.error(f"Error calculating chart data: {e}")
            return {"labels": [], "datasets": []}
    
    def _calculate_summary_metrics(self, trades: List[TradeMetrics]) -> AnalyticsSummary:
        """Calculate summary metrics from trades"""
        if not trades:
            return self._get_empty_summary()
        
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.profit_loss > 0])
        losing_trades = len([t for t in trades if t.profit_loss < 0])
        
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        total_pnl = sum(t.profit_loss for t in trades)
        total_pnl_percentage = sum(t.profit_loss_percentage for t in trades)
        
        wins = [t.profit_loss for t in trades if t.profit_loss > 0]
        losses = [t.profit_loss for t in trades if t.profit_loss < 0]
        
        average_win = statistics.mean(wins) if wins else 0
        average_loss = statistics.mean(losses) if losses else 0
        
        profit_factor = (sum(wins) / abs(sum(losses))) if losses else float('inf')
        
        # Calculate drawdown
        max_drawdown, max_drawdown_percentage = self._calculate_drawdown(trades)
        
        # Calculate Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio(trades)
        
        # Calculate duration statistics
        durations = [t.duration_seconds for t in trades]
        average_trade_duration = statistics.mean(durations) if durations else 0
        
        # Best and worst trades
        best_trade = max(t.profit_loss for t in trades) if trades else 0
        worst_trade = min(t.profit_loss for t in trades) if trades else 0
        
        # Consecutive wins/losses
        consecutive_wins, consecutive_losses = self._calculate_consecutive_stats(trades)
        
        # Total volume
        total_volume = sum(t.volume for t in trades)
        
        # Average latency (simulated for now)
        average_latency_ms = 85.5  # Simulated average latency
        
        return AnalyticsSummary(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_percentage=total_pnl_percentage,
            average_win=average_win,
            average_loss=average_loss,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_drawdown_percentage=max_drawdown_percentage,
            sharpe_ratio=sharpe_ratio,
            average_trade_duration=int(average_trade_duration),
            best_trade=best_trade,
            worst_trade=worst_trade,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
            total_volume=total_volume,
            average_latency_ms=average_latency_ms
        )
    
    def _calculate_drawdown(self, trades: List[TradeMetrics]) -> Tuple[float, float]:
        """Calculate maximum drawdown"""
        if not trades:
            return 0.0, 0.0
        
        # Sort trades by time
        sorted_trades = sorted(trades, key=lambda t: t.entry_time)
        
        # Calculate running P&L
        running_pnl = 0
        peak_pnl = 0
        max_drawdown = 0
        max_drawdown_percentage = 0
        
        for trade in sorted_trades:
            running_pnl += trade.profit_loss
            
            if running_pnl > peak_pnl:
                peak_pnl = running_pnl
            
            drawdown = peak_pnl - running_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                
                if peak_pnl > 0:
                    max_drawdown_percentage = (drawdown / peak_pnl) * 100
        
        return max_drawdown, max_drawdown_percentage
    
    def _calculate_sharpe_ratio(self, trades: List[TradeMetrics]) -> float:
        """Calculate Sharpe ratio"""
        if not trades or len(trades) < 2:
            return 0.0
        
        returns = [t.profit_loss_percentage for t in trades]
        
        if not returns:
            return 0.0
        
        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns) if len(returns) > 1 else 0
        
        if std_return == 0:
            return 0.0
        
        # Risk-free rate (assumed 2% annually, converted to per-trade)
        risk_free_rate = 0.02 / 252  # Daily risk-free rate
        
        sharpe_ratio = (mean_return - risk_free_rate) / std_return
        
        return sharpe_ratio
    
    def _calculate_consecutive_stats(self, trades: List[TradeMetrics]) -> Tuple[int, int]:
        """Calculate consecutive wins and losses"""
        if not trades:
            return 0, 0
        
        # Sort trades by time
        sorted_trades = sorted(trades, key=lambda t: t.entry_time)
        
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_consecutive_wins = 0
        current_consecutive_losses = 0
        
        for trade in sorted_trades:
            if trade.profit_loss > 0:
                current_consecutive_wins += 1
                current_consecutive_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_consecutive_wins)
            else:
                current_consecutive_losses += 1
                current_consecutive_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_consecutive_losses)
        
        return max_consecutive_wins, max_consecutive_losses
    
    def _calculate_provider_metrics(self, provider_data: Dict[str, Any]) -> ProviderAnalytics:
        """Calculate metrics for signal provider"""
        signals = provider_data.get('signals', [])
        executed_signals = provider_data.get('executed_signals', [])
        
        total_signals = len(signals)
        executed_count = len(executed_signals)
        execution_rate = (executed_count / total_signals) * 100 if total_signals > 0 else 0
        
        # Calculate win rate from executed signals
        winning_signals = [s for s in executed_signals if s.get('profit_loss', 0) > 0]
        win_rate = (len(winning_signals) / executed_count) * 100 if executed_count > 0 else 0
        
        # Average PnL
        average_pnl = statistics.mean([s.get('profit_loss', 0) for s in executed_signals]) if executed_signals else 0
        
        # Best and worst performing symbols
        symbol_performance = {}
        for signal in executed_signals:
            symbol = signal.get('symbol', 'UNKNOWN')
            pnl = signal.get('profit_loss', 0)
            
            if symbol not in symbol_performance:
                symbol_performance[symbol] = []
            symbol_performance[symbol].append(pnl)
        
        best_performing_symbol = "N/A"
        worst_performing_symbol = "N/A"
        
        if symbol_performance:
            symbol_averages = {symbol: statistics.mean(pnls) for symbol, pnls in symbol_performance.items()}
            best_performing_symbol = max(symbol_averages, key=symbol_averages.get)
            worst_performing_symbol = min(symbol_averages, key=symbol_averages.get)
        
        # Average signal latency (simulated)
        average_signal_latency_ms = 120.0  # Simulated
        
        # Last signal time
        last_signal_time = datetime.utcnow()
        if signals:
            last_signal_time = max(datetime.fromisoformat(s.get('created_at', datetime.utcnow().isoformat())) for s in signals)
        
        return ProviderAnalytics(
            provider_id=provider_data.get('id', 'unknown'),
            provider_name=provider_data.get('name', 'Unknown Provider'),
            total_signals=total_signals,
            executed_signals=executed_count,
            execution_rate=execution_rate,
            win_rate=win_rate,
            average_pnl=average_pnl,
            best_performing_symbol=best_performing_symbol,
            worst_performing_symbol=worst_performing_symbol,
            average_signal_latency_ms=average_signal_latency_ms,
            last_signal_time=last_signal_time
        )
    
    def _calculate_symbol_metrics(self, trades: List[TradeMetrics], symbol: str) -> Dict[str, Any]:
        """Calculate metrics for specific symbol"""
        if not trades:
            return self._get_empty_symbol_analytics(symbol)
        
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.profit_loss > 0])
        
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        total_pnl = sum(t.profit_loss for t in trades)
        average_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        # Best and worst trades
        best_trade = max(t.profit_loss for t in trades) if trades else 0
        worst_trade = min(t.profit_loss for t in trades) if trades else 0
        
        # Average duration
        avg_duration = statistics.mean([t.duration_seconds for t in trades]) if trades else 0
        
        # Volume statistics
        total_volume = sum(t.volume for t in trades)
        avg_volume = total_volume / total_trades if total_trades > 0 else 0
        
        return {
            "symbol": symbol,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": total_trades - winning_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "average_pnl": average_pnl,
            "best_trade": best_trade,
            "worst_trade": worst_trade,
            "average_duration_seconds": int(avg_duration),
            "total_volume": total_volume,
            "average_volume": avg_volume
        }
    
    def _calculate_chart_data(self, trades: List[TradeMetrics], timeframe: AnalyticsTimeframe) -> Dict[str, Any]:
        """Calculate time series chart data"""
        if not trades:
            return {"labels": [], "datasets": []}
        
        # Sort trades by time
        sorted_trades = sorted(trades, key=lambda t: t.entry_time)
        
        # Group trades by time period
        time_groups = {}
        for trade in sorted_trades:
            time_key = self._get_time_key(trade.entry_time, timeframe)
            if time_key not in time_groups:
                time_groups[time_key] = []
            time_groups[time_key].append(trade)
        
        # Calculate cumulative P&L
        labels = []
        cumulative_pnl = []
        daily_pnl = []
        
        running_pnl = 0
        for time_key in sorted(time_groups.keys()):
            trades_in_period = time_groups[time_key]
            period_pnl = sum(t.profit_loss for t in trades_in_period)
            
            running_pnl += period_pnl
            
            labels.append(time_key)
            cumulative_pnl.append(running_pnl)
            daily_pnl.append(period_pnl)
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Cumulative P&L",
                    "data": cumulative_pnl,
                    "type": "line"
                },
                {
                    "label": "Daily P&L",
                    "data": daily_pnl,
                    "type": "bar"
                }
            ]
        }
    
    def _get_time_key(self, dt: datetime, timeframe: AnalyticsTimeframe) -> str:
        """Get time key for grouping"""
        if timeframe == AnalyticsTimeframe.DAILY:
            return dt.strftime('%Y-%m-%d')
        elif timeframe == AnalyticsTimeframe.WEEKLY:
            return dt.strftime('%Y-W%U')
        elif timeframe == AnalyticsTimeframe.MONTHLY:
            return dt.strftime('%Y-%m')
        elif timeframe == AnalyticsTimeframe.YEARLY:
            return dt.strftime('%Y')
        else:
            return dt.strftime('%Y-%m-%d')
    
    def _get_empty_summary(self) -> AnalyticsSummary:
        """Get empty analytics summary"""
        return AnalyticsSummary(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            total_pnl_percentage=0.0,
            average_win=0.0,
            average_loss=0.0,
            profit_factor=0.0,
            max_drawdown=0.0,
            max_drawdown_percentage=0.0,
            sharpe_ratio=0.0,
            average_trade_duration=0,
            best_trade=0.0,
            worst_trade=0.0,
            consecutive_wins=0,
            consecutive_losses=0,
            total_volume=0.0,
            average_latency_ms=0.0
        )
    
    def _get_empty_symbol_analytics(self, symbol: str) -> Dict[str, Any]:
        """Get empty symbol analytics"""
        return {
            "symbol": symbol,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "average_pnl": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "average_duration_seconds": 0,
            "total_volume": 0.0,
            "average_volume": 0.0
        }
    
    async def _get_trades_data(self, user_id: str = None, 
                             timeframe: AnalyticsTimeframe = AnalyticsTimeframe.ALL_TIME) -> List[TradeMetrics]:
        """Get trade data from database (simulated for now)"""
        # In production, this would query the database
        # For now, return sample data
        
        sample_trades = [
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
        
        return sample_trades
    
    async def _get_provider_data(self, provider_id: str = None) -> List[Dict[str, Any]]:
        """Get provider data from database (simulated for now)"""
        # In production, this would query the database
        # For now, return sample data
        
        sample_providers = [
            {
                "id": "provider_1",
                "name": "Gold Signals Pro",
                "signals": [
                    {"symbol": "XAUUSD", "created_at": datetime.utcnow().isoformat()},
                    {"symbol": "XAUUSD", "created_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()}
                ],
                "executed_signals": [
                    {"symbol": "XAUUSD", "profit_loss": 150.0}
                ]
            },
            {
                "id": "provider_2",
                "name": "Forex Master",
                "signals": [
                    {"symbol": "EURUSD", "created_at": datetime.utcnow().isoformat()}
                ],
                "executed_signals": [
                    {"symbol": "EURUSD", "profit_loss": -50.0}
                ]
            }
        ]
        
        if provider_id:
            return [p for p in sample_providers if p["id"] == provider_id]
        
        return sample_providers
    
    async def _get_symbol_trades(self, symbol: str, user_id: str = None) -> List[TradeMetrics]:
        """Get trades for specific symbol"""
        all_trades = await self._get_trades_data(user_id)
        return [t for t in all_trades if t.symbol == symbol]


# Global analytics engine instance
_analytics_engine = None


def get_analytics_engine() -> AnalyticsEngine:
    """Get global analytics engine instance"""
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = AnalyticsEngine()
    return _analytics_engine