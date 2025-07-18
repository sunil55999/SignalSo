"""
Trading API endpoints
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from core.trade import TradeExecutor, TradeOrder, OrderStatus
from services.parser_ai import ParsedSignal, SignalType
from utils.logging_config import get_logger

logger = get_logger("api.trading")
trading_router = APIRouter()

# Global trade executor instance (in production, use dependency injection)
trade_executor = TradeExecutor()


class ExecuteSignalRequest(BaseModel):
    """Execute signal request model"""
    signal_data: Dict[str, Any]
    auto_execute: bool = True
    risk_override: Optional[float] = None


class ExecuteSignalResponse(BaseModel):
    """Execute signal response model"""
    success: bool
    order_id: Optional[str] = None
    order_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class CloseOrderRequest(BaseModel):
    """Close order request model"""
    order_id: str
    reason: Optional[str] = None


class TradingStatsResponse(BaseModel):
    """Trading statistics response model"""
    total_orders: int
    successful_orders: int
    failed_orders: int
    success_rate: float
    total_volume: float
    active_orders_count: int


@trading_router.post("/initialize")
async def initialize_trading():
    """Initialize trading engine"""
    try:
        success = await trade_executor.initialize()
        
        if success:
            logger.info("Trading engine initialized successfully")
            return {"message": "Trading engine initialized", "status": "ready"}
        else:
            raise HTTPException(status_code=503, detail="Failed to initialize trading engine")
            
    except Exception as e:
        logger.error(f"Trading initialization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trading_router.post("/execute", response_model=ExecuteSignalResponse)
async def execute_signal(request: ExecuteSignalRequest, bg_request: Request):
    """Execute trading signal"""
    try:
        user_id = getattr(bg_request.state, 'user_id', 'unknown')
        
        # Convert signal data to ParsedSignal object
        signal_data = request.signal_data
        
        # Create ParsedSignal from data
        signal = ParsedSignal(
            symbol=signal_data.get("symbol", ""),
            signal_type=SignalType(signal_data.get("signal_type", "BUY")),
            entry_price=signal_data.get("entry_price"),
            stop_loss=signal_data.get("stop_loss"),
            take_profit=signal_data.get("take_profit", []),
            lot_size=signal_data.get("lot_size"),
            raw_text=signal_data.get("raw_text", ""),
            parsing_method=signal_data.get("parsing_method", "api")
        )
        
        # Execute the signal
        order = await trade_executor.execute_signal(signal)
        
        if order.status == OrderStatus.EXECUTED:
            logger.info(f"Signal executed successfully for user {user_id}: {order.id}")
            
            return ExecuteSignalResponse(
                success=True,
                order_id=order.id,
                order_data=order.to_dict()
            )
        else:
            logger.warning(f"Signal execution failed for user {user_id}: {order.error_message}")
            
            return ExecuteSignalResponse(
                success=False,
                error=order.error_message
            )
            
    except Exception as e:
        logger.error(f"Signal execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trading_router.post("/close")
async def close_order(request: CloseOrderRequest, bg_request: Request):
    """Close an active trading order"""
    try:
        user_id = getattr(bg_request.state, 'user_id', 'unknown')
        
        success = await trade_executor.close_order(request.order_id)
        
        if success:
            logger.info(f"Order {request.order_id} closed by user {user_id}")
            return {"message": f"Order {request.order_id} closed successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Order {request.order_id} not found or cannot be closed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Close order error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trading_router.get("/orders")
async def get_active_orders(bg_request: Request):
    """Get list of active trading orders"""
    try:
        user_id = getattr(bg_request.state, 'user_id', 'unknown')
        
        orders = trade_executor.get_active_orders()
        
        # In production, filter by user_id
        return {
            "orders": orders,
            "count": len(orders)
        }
        
    except Exception as e:
        logger.error(f"Get orders error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trading_router.get("/orders/{order_id}")
async def get_order_details(order_id: str, bg_request: Request):
    """Get details of a specific order"""
    try:
        user_id = getattr(bg_request.state, 'user_id', 'unknown')
        
        # Find order in active orders
        orders = trade_executor.get_active_orders()
        order = next((o for o in orders if o["id"] == order_id), None)
        
        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        
        return order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get order details error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trading_router.get("/stats", response_model=TradingStatsResponse)
async def get_trading_stats():
    """Get trading statistics"""
    try:
        stats = trade_executor.get_execution_stats()
        
        return TradingStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Trading stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trading_router.get("/account")
async def get_account_info():
    """Get MT5 account information"""
    try:
        # Get account info from MT5 bridge
        if not trade_executor.mt5_bridge.is_connected:
            raise HTTPException(status_code=503, detail="MT5 bridge not connected")
        
        account_info = await trade_executor.mt5_bridge.get_account_info()
        
        return account_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trading_router.get("/symbols/{symbol}")
async def get_symbol_info(symbol: str):
    """Get symbol information from MT5"""
    try:
        if not trade_executor.mt5_bridge.is_connected:
            raise HTTPException(status_code=503, detail="MT5 bridge not connected")
        
        symbol_info = await trade_executor.mt5_bridge.get_symbol_info(symbol)
        
        return symbol_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Symbol info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trading_router.post("/test-connection")
async def test_mt5_connection():
    """Test MT5 bridge connection"""
    try:
        if trade_executor.mt5_bridge.is_connected:
            # Test with account info request
            account_info = await trade_executor.mt5_bridge.get_account_info()
            
            return {
                "connected": True,
                "mt5_account": account_info.get("login", "unknown"),
                "balance": account_info.get("balance", 0)
            }
        else:
            # Try to reconnect
            success = await trade_executor.mt5_bridge.connect()
            
            return {
                "connected": success,
                "message": "Connection successful" if success else "Connection failed"
            }
            
    except Exception as e:
        logger.error(f"MT5 connection test error: {e}")
        return {
            "connected": False,
            "error": str(e)
        }


@trading_router.post("/shutdown")
async def shutdown_trading():
    """Shutdown trading engine"""
    try:
        await trade_executor.shutdown()
        
        logger.info("Trading engine shutdown complete")
        return {"message": "Trading engine shutdown", "status": "stopped"}
        
    except Exception as e:
        logger.error(f"Trading shutdown error: {e}")
        raise HTTPException(status_code=500, detail=str(e))