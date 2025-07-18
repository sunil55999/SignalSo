"""
Analytics API endpoints - PnL, WinRate, DD, Latency, Reports
"""

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
import io

from core.analytics import AnalyticsEngine, AnalyticsTimeframe, get_analytics_engine
from services.report_pdf import get_pdf_builder
from utils.logging_config import get_logger

logger = get_logger("api.analytics")
analytics_router = APIRouter()

# Global analytics engine
analytics_engine = get_analytics_engine()
pdf_builder = get_pdf_builder()


class AnalyticsRequest(BaseModel):
    """Analytics request model"""
    user_id: Optional[str] = None
    timeframe: str = "all_time"
    symbol: Optional[str] = None
    provider_id: Optional[str] = None


class SummaryResponse(BaseModel):
    """Summary analytics response model"""
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


class ProviderResponse(BaseModel):
    """Provider analytics response model"""
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


class ChartDataResponse(BaseModel):
    """Chart data response model"""
    labels: List[str]
    datasets: List[Dict[str, Any]]


@analytics_router.get("/summary", response_model=SummaryResponse)
async def get_summary_analytics(request: Request, 
                               timeframe: str = "all_time",
                               user_id: Optional[str] = None):
    """Get summary analytics - PnL, WinRate, DD, Latency"""
    try:
        # Get user ID from auth middleware if not provided
        if user_id is None:
            user_id = getattr(request.state, 'user_id', None)
        
        # Parse timeframe
        try:
            timeframe_enum = AnalyticsTimeframe(timeframe)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")
        
        # Get analytics summary
        summary = await analytics_engine.get_summary_analytics(user_id, timeframe_enum)
        
        logger.info(f"Summary analytics retrieved for user {user_id or 'all'}")
        
        return SummaryResponse(
            total_trades=summary.total_trades,
            winning_trades=summary.winning_trades,
            losing_trades=summary.losing_trades,
            win_rate=summary.win_rate,
            total_pnl=summary.total_pnl,
            total_pnl_percentage=summary.total_pnl_percentage,
            average_win=summary.average_win,
            average_loss=summary.average_loss,
            profit_factor=summary.profit_factor,
            max_drawdown=summary.max_drawdown,
            max_drawdown_percentage=summary.max_drawdown_percentage,
            sharpe_ratio=summary.sharpe_ratio,
            average_trade_duration=summary.average_trade_duration,
            best_trade=summary.best_trade,
            worst_trade=summary.worst_trade,
            consecutive_wins=summary.consecutive_wins,
            consecutive_losses=summary.consecutive_losses,
            total_volume=summary.total_volume,
            average_latency_ms=summary.average_latency_ms
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting summary analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@analytics_router.get("/provider/{provider_id}", response_model=ProviderResponse)
async def get_provider_analytics(provider_id: str, request: Request):
    """Get analytics for specific signal provider"""
    try:
        # Get provider analytics
        providers = await analytics_engine.get_provider_analytics(provider_id)
        
        if not providers:
            raise HTTPException(status_code=404, detail=f"Provider {provider_id} not found")
        
        provider = providers[0]
        
        logger.info(f"Provider analytics retrieved for provider {provider_id}")
        
        return ProviderResponse(
            provider_id=provider.provider_id,
            provider_name=provider.provider_name,
            total_signals=provider.total_signals,
            executed_signals=provider.executed_signals,
            execution_rate=provider.execution_rate,
            win_rate=provider.win_rate,
            average_pnl=provider.average_pnl,
            best_performing_symbol=provider.best_performing_symbol,
            worst_performing_symbol=provider.worst_performing_symbol,
            average_signal_latency_ms=provider.average_signal_latency_ms,
            last_signal_time=provider.last_signal_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting provider analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@analytics_router.get("/providers", response_model=List[ProviderResponse])
async def get_all_providers_analytics(request: Request):
    """Get analytics for all signal providers"""
    try:
        # Get all provider analytics
        providers = await analytics_engine.get_provider_analytics()
        
        result = []
        for provider in providers:
            result.append(ProviderResponse(
                provider_id=provider.provider_id,
                provider_name=provider.provider_name,
                total_signals=provider.total_signals,
                executed_signals=provider.executed_signals,
                execution_rate=provider.execution_rate,
                win_rate=provider.win_rate,
                average_pnl=provider.average_pnl,
                best_performing_symbol=provider.best_performing_symbol,
                worst_performing_symbol=provider.worst_performing_symbol,
                average_signal_latency_ms=provider.average_signal_latency_ms,
                last_signal_time=provider.last_signal_time
            ))
        
        logger.info(f"All provider analytics retrieved ({len(result)} providers)")
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting all provider analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@analytics_router.get("/symbol/{symbol}")
async def get_symbol_analytics(symbol: str, request: Request, user_id: Optional[str] = None):
    """Get analytics for specific symbol"""
    try:
        # Get user ID from auth middleware if not provided
        if user_id is None:
            user_id = getattr(request.state, 'user_id', None)
        
        # Get symbol analytics
        analytics = await analytics_engine.get_symbol_analytics(symbol, user_id)
        
        logger.info(f"Symbol analytics retrieved for {symbol}")
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting symbol analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@analytics_router.get("/chart", response_model=ChartDataResponse)
async def get_chart_data(request: Request, 
                        timeframe: str = "monthly",
                        user_id: Optional[str] = None):
    """Get performance chart data"""
    try:
        # Get user ID from auth middleware if not provided
        if user_id is None:
            user_id = getattr(request.state, 'user_id', None)
        
        # Parse timeframe
        try:
            timeframe_enum = AnalyticsTimeframe(timeframe)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")
        
        # Get chart data
        chart_data = await analytics_engine.get_performance_chart_data(user_id, timeframe_enum)
        
        logger.info(f"Chart data retrieved for user {user_id or 'all'}")
        
        return ChartDataResponse(
            labels=chart_data.get("labels", []),
            datasets=chart_data.get("datasets", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@analytics_router.post("/report/pdf")
async def generate_pdf_report(request: Request, 
                             analytics_request: AnalyticsRequest):
    """Generate and download PDF analytics report"""
    try:
        # Get user ID from auth middleware if not provided
        user_id = analytics_request.user_id or getattr(request.state, 'user_id', None)
        
        # Parse timeframe
        try:
            timeframe_enum = AnalyticsTimeframe(analytics_request.timeframe)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe: {analytics_request.timeframe}")
        
        # Get analytics data
        summary = await analytics_engine.get_summary_analytics(user_id, timeframe_enum)
        providers = await analytics_engine.get_provider_analytics(analytics_request.provider_id)
        chart_data = await analytics_engine.get_performance_chart_data(user_id, timeframe_enum)
        
        # Generate PDF report
        user_name = f"User {user_id}" if user_id else "All Users"
        pdf_bytes = pdf_builder.generate_analytics_report(
            summary=summary,
            providers=providers,
            chart_data=chart_data,
            user_name=user_name
        )
        
        # Create response
        filename = f"analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        def generate():
            yield pdf_bytes
        
        logger.info(f"PDF report generated for user {user_id or 'all'}")
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@analytics_router.get("/performance-metrics")
async def get_performance_metrics(request: Request, 
                                 timeframe: str = "all_time",
                                 user_id: Optional[str] = None):
    """Get detailed performance metrics"""
    try:
        # Get user ID from auth middleware if not provided
        if user_id is None:
            user_id = getattr(request.state, 'user_id', None)
        
        # Parse timeframe
        try:
            timeframe_enum = AnalyticsTimeframe(timeframe)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")
        
        # Get summary analytics
        summary = await analytics_engine.get_summary_analytics(user_id, timeframe_enum)
        
        # Extended performance metrics
        performance_metrics = {
            "profitability": {
                "total_pnl": summary.total_pnl,
                "total_pnl_percentage": summary.total_pnl_percentage,
                "profit_factor": summary.profit_factor,
                "average_win": summary.average_win,
                "average_loss": summary.average_loss,
                "best_trade": summary.best_trade,
                "worst_trade": summary.worst_trade
            },
            "risk_management": {
                "max_drawdown": summary.max_drawdown,
                "max_drawdown_percentage": summary.max_drawdown_percentage,
                "sharpe_ratio": summary.sharpe_ratio,
                "win_rate": summary.win_rate,
                "consecutive_wins": summary.consecutive_wins,
                "consecutive_losses": summary.consecutive_losses
            },
            "trading_activity": {
                "total_trades": summary.total_trades,
                "winning_trades": summary.winning_trades,
                "losing_trades": summary.losing_trades,
                "total_volume": summary.total_volume,
                "average_trade_duration": summary.average_trade_duration
            },
            "execution_quality": {
                "average_latency_ms": summary.average_latency_ms,
                "execution_rate": 95.5,  # Simulated
                "slippage_average": 0.3   # Simulated
            }
        }
        
        logger.info(f"Performance metrics retrieved for user {user_id or 'all'}")
        
        return performance_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@analytics_router.get("/risk-metrics")
async def get_risk_metrics(request: Request, 
                          timeframe: str = "all_time",
                          user_id: Optional[str] = None):
    """Get risk management metrics"""
    try:
        # Get user ID from auth middleware if not provided
        if user_id is None:
            user_id = getattr(request.state, 'user_id', None)
        
        # Parse timeframe
        try:
            timeframe_enum = AnalyticsTimeframe(timeframe)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")
        
        # Get summary analytics
        summary = await analytics_engine.get_summary_analytics(user_id, timeframe_enum)
        
        # Risk metrics
        risk_metrics = {
            "drawdown_analysis": {
                "max_drawdown": summary.max_drawdown,
                "max_drawdown_percentage": summary.max_drawdown_percentage,
                "current_drawdown": 0.0,  # Would be calculated from current position
                "recovery_factor": summary.total_pnl / summary.max_drawdown if summary.max_drawdown > 0 else 0
            },
            "volatility_metrics": {
                "sharpe_ratio": summary.sharpe_ratio,
                "sortino_ratio": summary.sharpe_ratio * 1.2,  # Approximation
                "volatility": 0.15,  # Simulated
                "beta": 1.0  # Simulated
            },
            "risk_adjusted_returns": {
                "risk_reward_ratio": summary.profit_factor,
                "calmar_ratio": summary.total_pnl / summary.max_drawdown if summary.max_drawdown > 0 else 0,
                "information_ratio": summary.sharpe_ratio * 0.8  # Approximation
            }
        }
        
        logger.info(f"Risk metrics retrieved for user {user_id or 'all'}")
        
        return risk_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting risk metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@analytics_router.get("/trading-statistics")
async def get_trading_statistics(request: Request, 
                               timeframe: str = "all_time",
                               user_id: Optional[str] = None):
    """Get comprehensive trading statistics"""
    try:
        # Get user ID from auth middleware if not provided
        if user_id is None:
            user_id = getattr(request.state, 'user_id', None)
        
        # Parse timeframe
        try:
            timeframe_enum = AnalyticsTimeframe(timeframe)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")
        
        # Get summary analytics
        summary = await analytics_engine.get_summary_analytics(user_id, timeframe_enum)
        
        # Comprehensive trading statistics
        trading_stats = {
            "overview": {
                "total_trades": summary.total_trades,
                "winning_trades": summary.winning_trades,
                "losing_trades": summary.losing_trades,
                "win_rate": summary.win_rate,
                "total_pnl": summary.total_pnl,
                "total_volume": summary.total_volume
            },
            "performance": {
                "profit_factor": summary.profit_factor,
                "average_win": summary.average_win,
                "average_loss": summary.average_loss,
                "best_trade": summary.best_trade,
                "worst_trade": summary.worst_trade,
                "sharpe_ratio": summary.sharpe_ratio
            },
            "risk": {
                "max_drawdown": summary.max_drawdown,
                "max_drawdown_percentage": summary.max_drawdown_percentage,
                "consecutive_wins": summary.consecutive_wins,
                "consecutive_losses": summary.consecutive_losses
            },
            "execution": {
                "average_latency_ms": summary.average_latency_ms,
                "average_trade_duration": summary.average_trade_duration,
                "execution_success_rate": 95.5  # Simulated
            },
            "generated_at": datetime.utcnow().isoformat(),
            "timeframe": timeframe
        }
        
        logger.info(f"Trading statistics retrieved for user {user_id or 'all'}")
        
        return trading_stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trading statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))