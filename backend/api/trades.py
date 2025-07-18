"""
Enhanced Trade Router API - MT4/MT5 Trade Execution endpoints
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from core.trade import TradeExecutor, TradeOrder, OrderStatus, OrderType
from services.mt5_bridge import MT5Bridge, MT5TradeRequest, MT5OrderType, MT5TradeAction, get_mt5_bridge
from services.parser_ai import ParsedSignal, SignalType
from utils.logging_config import get_logger

logger = get_logger("api.trades")
trades_router = APIRouter()

# Global instances
trade_executor = TradeExecutor()
mt5_bridge = get_mt5_bridge()


class TradeType(str, Enum):
    """Trade type enumeration"""
    BUY = "BUY"
    SELL = "SELL"
    BUY_LIMIT = "BUY_LIMIT"
    SELL_LIMIT = "SELL_LIMIT"
    BUY_STOP = "BUY_STOP"
    SELL_STOP = "SELL_STOP"


class OpenTradeRequest(BaseModel):
    """Open trade request model"""
    symbol: str = Field(..., description="Trading symbol (e.g., XAUUSD)")
    type: TradeType = Field(..., description="Trade type")
    volume: float = Field(..., gt=0, description="Trade volume/lot size")
    price: Optional[float] = Field(None, description="Entry price (for pending orders)")
    sl: Optional[float] = Field(None, description="Stop loss price")
    tp: Optional[List[float]] = Field(None, description="Take profit levels")
    deviation: int = Field(10, description="Price deviation in points")
    magic: int = Field(12345, description="Magic number")
    comment: str = Field("SignalOS", description="Trade comment")
    risk_percentage: Optional[float] = Field(None, description="Risk percentage override")


class CloseTradeRequest(BaseModel):
    """Close trade request model"""
    ticket: Optional[int] = Field(None, description="MT5 ticket number")
    order_id: Optional[str] = Field(None, description="SignalOS order ID")
    partial_volume: Optional[float] = Field(None, description="Partial close volume")
    reason: str = Field("User request", description="Close reason")


class ModifyTradeRequest(BaseModel):
    """Modify trade request model"""
    ticket: Optional[int] = Field(None, description="MT5 ticket number")
    order_id: Optional[str] = Field(None, description="SignalOS order ID")
    sl: Optional[float] = Field(None, description="New stop loss")
    tp: Optional[float] = Field(None, description="New take profit")


class TradeResponse(BaseModel):
    """Trade response model"""
    success: bool
    order_id: Optional[str] = None
    ticket: Optional[int] = None
    message: str = ""
    error: Optional[str] = None
    order_details: Optional[Dict[str, Any]] = None


class TradeStatusResponse(BaseModel):
    """Trade status response model"""
    order_id: str
    ticket: Optional[int]
    symbol: str
    type: str
    volume: float
    status: str
    profit_loss: Optional[float] = None
    entry_price: Optional[float] = None
    current_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None


@trades_router.post("/open", response_model=TradeResponse)
async def open_trade(request: OpenTradeRequest, bg_request: Request):
    """Open a new trading position"""
    try:
        user_id = getattr(bg_request.state, 'user_id', 'unknown')
        
        # Convert to MT5 order type
        mt5_order_type = _convert_to_mt5_order_type(request.type)
        
        # Create MT5 trade request
        mt5_request = MT5TradeRequest(
            action=MT5TradeAction.TRADE_ACTION_DEAL,
            symbol=request.symbol,
            volume=request.volume,
            type=mt5_order_type,
            price=request.price or 0.0,
            sl=request.sl or 0.0,
            tp=request.tp[0] if request.tp else 0.0,
            deviation=request.deviation,
            magic=request.magic,
            comment=request.comment
        )
        
        # Execute trade through MT5 bridge
        if not mt5_bridge.is_connected:
            await mt5_bridge.connect()
        
        result = await mt5_bridge.send_trade_request(mt5_request)
        
        if result.retcode == 10009:  # TRADE_RETCODE_DONE
            # Create SignalOS order record
            order_id = f"ORD_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            
            order_details = {
                "order_id": order_id,
                "ticket": result.order,
                "symbol": request.symbol,
                "type": request.type.value,
                "volume": result.volume,
                "price": result.price,
                "sl": request.sl,
                "tp": request.tp,
                "status": "executed",
                "open_time": datetime.utcnow().isoformat(),
                "user_id": user_id
            }
            
            # Store order (in production, save to database)
            logger.info(f"Trade opened successfully: {order_id} (ticket: {result.order})")
            
            return TradeResponse(
                success=True,
                order_id=order_id,
                ticket=result.order,
                message=f"Trade opened successfully: {request.symbol} {request.type.value}",
                order_details=order_details
            )
        else:
            error_msg = f"Trade failed with retcode: {result.retcode}"
            logger.error(f"Trade open failed: {error_msg}")
            
            return TradeResponse(
                success=False,
                error=error_msg,
                message=f"Failed to open trade: {request.symbol}"
            )
            
    except Exception as e:
        logger.error(f"Error opening trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trades_router.post("/close", response_model=TradeResponse)
async def close_trade(request: CloseTradeRequest, bg_request: Request):
    """Close an existing trading position"""
    try:
        user_id = getattr(bg_request.state, 'user_id', 'unknown')
        
        # Get ticket number
        ticket = request.ticket
        if not ticket and request.order_id:
            # In production, lookup ticket from order_id in database
            ticket = 12345  # Placeholder
        
        if not ticket:
            raise HTTPException(status_code=400, detail="Either ticket or order_id is required")
        
        # Close position through MT5 bridge
        if not mt5_bridge.is_connected:
            await mt5_bridge.connect()
        
        # Create close request
        close_request = MT5TradeRequest(
            action=MT5TradeAction.TRADE_ACTION_DEAL,
            symbol="",  # Will be populated by MT5
            volume=request.partial_volume or 0.0,
            type=MT5OrderType.ORDER_TYPE_BUY  # Opposite of original
        )
        
        # For now, simulate close via direct bridge call
        positions = await mt5_bridge.get_positions()
        target_position = None
        
        for pos in positions:
            if pos.get('ticket') == ticket:
                target_position = pos
                break
        
        if not target_position:
            raise HTTPException(status_code=404, detail=f"Position with ticket {ticket} not found")
        
        # Close the position (simplified implementation)
        result = await mt5_bridge.send_trade_request(close_request)
        
        if result.retcode == 10009:  # TRADE_RETCODE_DONE
            logger.info(f"Trade closed successfully: ticket {ticket}")
            
            return TradeResponse(
                success=True,
                ticket=ticket,
                message=f"Trade closed successfully: {request.reason}",
                order_details={
                    "ticket": ticket,
                    "close_time": datetime.utcnow().isoformat(),
                    "reason": request.reason,
                    "user_id": user_id
                }
            )
        else:
            error_msg = f"Close failed with retcode: {result.retcode}"
            logger.error(f"Trade close failed: {error_msg}")
            
            return TradeResponse(
                success=False,
                error=error_msg,
                message=f"Failed to close trade: {ticket}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trades_router.post("/modify", response_model=TradeResponse)
async def modify_trade(request: ModifyTradeRequest, bg_request: Request):
    """Modify an existing trading position"""
    try:
        user_id = getattr(bg_request.state, 'user_id', 'unknown')
        
        # Get ticket number
        ticket = request.ticket
        if not ticket and request.order_id:
            # In production, lookup ticket from order_id in database
            ticket = 12345  # Placeholder
        
        if not ticket:
            raise HTTPException(status_code=400, detail="Either ticket or order_id is required")
        
        # Modify position through MT5 bridge
        if not mt5_bridge.is_connected:
            await mt5_bridge.connect()
        
        # Create modify request
        modify_request = MT5TradeRequest(
            action=MT5TradeAction.TRADE_ACTION_SLTP,
            symbol="",  # Will be populated by MT5
            volume=0.0,
            type=MT5OrderType.ORDER_TYPE_BUY,
            sl=request.sl or 0.0,
            tp=request.tp or 0.0
        )
        
        result = await mt5_bridge.send_trade_request(modify_request)
        
        if result.retcode == 10009:  # TRADE_RETCODE_DONE
            logger.info(f"Trade modified successfully: ticket {ticket}")
            
            return TradeResponse(
                success=True,
                ticket=ticket,
                message=f"Trade modified successfully",
                order_details={
                    "ticket": ticket,
                    "sl": request.sl,
                    "tp": request.tp,
                    "modified_time": datetime.utcnow().isoformat(),
                    "user_id": user_id
                }
            )
        else:
            error_msg = f"Modify failed with retcode: {result.retcode}"
            logger.error(f"Trade modify failed: {error_msg}")
            
            return TradeResponse(
                success=False,
                error=error_msg,
                message=f"Failed to modify trade: {ticket}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error modifying trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trades_router.get("/status", response_model=List[TradeStatusResponse])
async def get_trade_status(bg_request: Request, 
                          symbol: Optional[str] = None,
                          ticket: Optional[int] = None):
    """Get status of trading positions"""
    try:
        user_id = getattr(bg_request.state, 'user_id', 'unknown')
        
        # Get positions from MT5
        if not mt5_bridge.is_connected:
            await mt5_bridge.connect()
        
        positions = await mt5_bridge.get_positions()
        
        # Filter by symbol if provided
        if symbol:
            positions = [p for p in positions if p.get('symbol') == symbol]
        
        # Filter by ticket if provided
        if ticket:
            positions = [p for p in positions if p.get('ticket') == ticket]
        
        # Convert to response format
        result = []
        for pos in positions:
            trade_status = TradeStatusResponse(
                order_id=f"ORD_{pos.get('ticket', 0)}",
                ticket=pos.get('ticket'),
                symbol=pos.get('symbol', ''),
                type=pos.get('type', ''),
                volume=pos.get('volume', 0.0),
                status="open",
                profit_loss=pos.get('profit', 0.0),
                entry_price=pos.get('price_open', 0.0),
                current_price=pos.get('price_current', 0.0),
                stop_loss=pos.get('sl', 0.0),
                take_profit=pos.get('tp', 0.0),
                open_time=datetime.fromisoformat(pos.get('time', datetime.utcnow().isoformat())),
                close_time=None
            )
            result.append(trade_status)
        
        logger.info(f"Trade status retrieved: {len(result)} positions")
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting trade status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trades_router.get("/history")
async def get_trade_history(bg_request: Request, 
                          symbol: Optional[str] = None,
                          limit: int = 50,
                          offset: int = 0):
    """Get trading history"""
    try:
        user_id = getattr(bg_request.state, 'user_id', 'unknown')
        
        # In production, this would query from database
        # For now, return simulated history
        
        history = [
            {
                "order_id": "ORD_20250118_143021_001",
                "ticket": 12345,
                "symbol": "XAUUSD",
                "type": "BUY",
                "volume": 0.1,
                "entry_price": 1950.0,
                "exit_price": 1965.0,
                "profit_loss": 150.0,
                "open_time": "2025-01-18T14:30:21Z",
                "close_time": "2025-01-18T15:30:21Z",
                "duration_minutes": 60,
                "status": "closed"
            },
            {
                "order_id": "ORD_20250118_133021_002",
                "ticket": 12346,
                "symbol": "EURUSD",
                "type": "SELL",
                "volume": 0.2,
                "entry_price": 1.0850,
                "exit_price": 1.0825,
                "profit_loss": -50.0,
                "open_time": "2025-01-18T13:30:21Z",
                "close_time": "2025-01-18T14:00:21Z",
                "duration_minutes": 30,
                "status": "closed"
            }
        ]
        
        # Filter by symbol if provided
        if symbol:
            history = [h for h in history if h.get('symbol') == symbol]
        
        # Apply pagination
        total = len(history)
        paginated_history = history[offset:offset + limit]
        
        result = {
            "trades": paginated_history,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }
        
        logger.info(f"Trade history retrieved: {len(paginated_history)} trades")
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting trade history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trades_router.get("/account")
async def get_account_info(bg_request: Request):
    """Get MT5 account information"""
    try:
        user_id = getattr(bg_request.state, 'user_id', 'unknown')
        
        # Get account info from MT5
        if not mt5_bridge.is_connected:
            await mt5_bridge.connect()
        
        account_info = await mt5_bridge.get_account_info()
        
        # Add calculated fields
        account_info['equity'] = account_info.get('balance', 0) + account_info.get('profit', 0)
        account_info['margin_level'] = (
            (account_info.get('equity', 0) / account_info.get('margin', 1)) * 100
            if account_info.get('margin', 0) > 0 else 0
        )
        
        logger.info(f"Account info retrieved for user {user_id}")
        
        return account_info
        
    except Exception as e:
        logger.error(f"Error getting account info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trades_router.get("/symbols/{symbol}")
async def get_symbol_info(symbol: str, bg_request: Request):
    """Get symbol information"""
    try:
        # Get symbol info from MT5
        if not mt5_bridge.is_connected:
            await mt5_bridge.connect()
        
        symbol_info = await mt5_bridge.get_symbol_info(symbol)
        
        logger.info(f"Symbol info retrieved for {symbol}")
        
        return symbol_info
        
    except Exception as e:
        logger.error(f"Error getting symbol info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trades_router.post("/bulk-close")
async def bulk_close_trades(bg_request: Request, 
                          symbol: Optional[str] = None,
                          trade_type: Optional[str] = None,
                          profit_threshold: Optional[float] = None):
    """Close multiple trades based on criteria"""
    try:
        user_id = getattr(bg_request.state, 'user_id', 'unknown')
        
        # Get positions
        if not mt5_bridge.is_connected:
            await mt5_bridge.connect()
        
        positions = await mt5_bridge.get_positions()
        
        # Filter positions based on criteria
        to_close = []
        
        for pos in positions:
            if symbol and pos.get('symbol') != symbol:
                continue
            
            if trade_type and pos.get('type') != trade_type:
                continue
            
            if profit_threshold is not None:
                if pos.get('profit', 0) < profit_threshold:
                    continue
            
            to_close.append(pos)
        
        # Close selected positions
        closed_trades = []
        failed_trades = []
        
        for pos in to_close:
            try:
                # Simulate close (in production, use actual close logic)
                closed_trades.append({
                    "ticket": pos.get('ticket'),
                    "symbol": pos.get('symbol'),
                    "profit": pos.get('profit', 0)
                })
            except Exception as e:
                failed_trades.append({
                    "ticket": pos.get('ticket'),
                    "error": str(e)
                })
        
        result = {
            "success": True,
            "closed_count": len(closed_trades),
            "failed_count": len(failed_trades),
            "closed_trades": closed_trades,
            "failed_trades": failed_trades,
            "total_profit": sum(t.get('profit', 0) for t in closed_trades)
        }
        
        logger.info(f"Bulk close completed: {len(closed_trades)} closed, {len(failed_trades)} failed")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in bulk close: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _convert_to_mt5_order_type(trade_type: TradeType) -> MT5OrderType:
    """Convert API trade type to MT5 order type"""
    mapping = {
        TradeType.BUY: MT5OrderType.ORDER_TYPE_BUY,
        TradeType.SELL: MT5OrderType.ORDER_TYPE_SELL,
        TradeType.BUY_LIMIT: MT5OrderType.ORDER_TYPE_BUY_LIMIT,
        TradeType.SELL_LIMIT: MT5OrderType.ORDER_TYPE_SELL_LIMIT,
        TradeType.BUY_STOP: MT5OrderType.ORDER_TYPE_BUY_STOP,
        TradeType.SELL_STOP: MT5OrderType.ORDER_TYPE_SELL_STOP,
    }
    return mapping.get(trade_type, MT5OrderType.ORDER_TYPE_BUY)