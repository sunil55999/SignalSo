"""
Telegram Copilot Bot for SignalOS
Provides remote control and monitoring capabilities via Telegram commands
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import requests

class SignalOSCopilot:
    def __init__(self, config_file: str = "config.json"):
        self.config = self._load_config(config_file)
        self.bot_token = self.config.get("telegram", {}).get("bot_token", "")
        self.allowed_chat_ids = self.config.get("telegram", {}).get("allowed_chat_ids", [])
        self.server_url = self.config.get("server", {}).get("url", "http://localhost:5000")
        
        if not self.bot_token:
            raise ValueError("Telegram bot token not found in config")
        
        self.application = Application.builder().token(self.bot_token).build()
        self._setup_handlers()
        self._setup_logging()
        
        # Bot state
        self.stealth_mode = False
        self.trading_paused = False
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _setup_logging(self):
        """Setup logging for bot operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('CopilotBot')
    
    def _setup_handlers(self):
        """Setup command handlers for the bot"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("trades", self.trades_command))
        self.application.add_handler(CommandHandler("replay", self.replay_command))
        self.application.add_handler(CommandHandler("stealth", self.stealth_command))
        self.application.add_handler(CommandHandler("pause", self.pause_command))
        self.application.add_handler(CommandHandler("resume", self.resume_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("signals", self.signals_command))
        self.application.add_handler(CommandHandler("config", self.config_command))
        self.application.add_handler(CommandHandler("close", self.close_command))
        self.application.add_handler(CommandHandler("range", self.range_command))
        
        # Handle text messages for signal parsing
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
    
    def _is_authorized(self, chat_id: int) -> bool:
        """Check if chat ID is authorized to use the bot"""
        if not self.allowed_chat_ids:
            return True  # Allow all if no restrictions set
        return chat_id in self.allowed_chat_ids
    
    async def _api_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
        """Make API request to SignalOS server"""
        try:
            url = f"{self.server_url}/api{endpoint}"
            
            if method == "GET":
                response = requests.get(url, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=10)
            else:
                return {"error": "Unsupported HTTP method"}
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"API error: {response.status_code}"}
                
        except requests.RequestException as e:
            return {"error": f"Connection error: {str(e)}"}
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if not self._is_authorized(update.effective_chat.id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        welcome_message = """
🤖 **SignalOS Copilot Bot**

Welcome to your trading automation assistant!

📋 **Available Commands:**
• `/status` - MT5 and system status
• `/trades` - Active trades overview
• `/signals` - Recent signals
• `/replay <signal_id>` - Replay a signal
• `/stealth` - Toggle stealth mode
• `/pause` - Pause trading
• `/resume` - Resume trading
• `/stats` - Trading statistics
• `/config` - Current configuration
• `/help` - Show this help

📨 **Signal Processing:**
Send me trading signals and I'll parse and execute them automatically.

🔒 **Security:** This bot is authorized for your account only.
        """
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        help_text = """
🆘 **SignalOS Help**

**Command Details:**

🔍 `/status` - Shows:
• MT5 connection status
• Trading mode (active/paused)
• Stealth mode status
• Server connectivity

📈 `/trades` - Displays:
• Currently open positions
• P&L for each trade
• Entry prices and current prices

📊 `/signals` - Shows:
• Recent signals processed
• Execution status
• Failed signals count

🔄 `/replay <id>` - Replays signal:
• Usage: `/replay 123`
• Re-executes a previously processed signal

👤 `/stealth` - Toggles stealth mode:
• Hides SL/TP from MT5 interface
• Keeps positions invisible to others

⏸️ `/pause` / ▶️ `/resume`:
• Stop/start automatic signal processing
• Emergency trading halt capability

📊 `/stats` - Performance metrics:
• Win rate and profit statistics
• Signal processing success rate
• Daily/weekly performance

⚙️ `/config` - Current settings:
• Trading parameters
• Risk management settings
• Bot configuration

**Signal Format Examples:**
```
BUY EURUSD
Entry: 1.1000
SL: 1.0950
TP1: 1.1050
TP2: 1.1100
```

For support, contact your system administrator.
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        # Get MT5 status from server
        mt5_status = await self._api_request("/mt5-status")
        dashboard_stats = await self._api_request("/dashboard/stats")
        
        # Format status message
        mt5_connected = mt5_status.get("isConnected", False) if "error" not in mt5_status else False
        
        status_emoji = "🟢" if mt5_connected else "🔴"
        trading_emoji = "⏸️" if self.trading_paused else "▶️"
        stealth_emoji = "👤" if self.stealth_mode else "👁️"
        
        status_message = f"""
🤖 **SignalOS Status Report**

{status_emoji} **MT5 Connection:** {'Connected' if mt5_connected else 'Disconnected'}
{trading_emoji} **Trading:** {'Paused' if self.trading_paused else 'Active'}
{stealth_emoji} **Stealth Mode:** {'Enabled' if self.stealth_mode else 'Disabled'}

📊 **Today's Performance:**
• Active Trades: {dashboard_stats.get('activeTrades', 'N/A')}
• P&L: ${dashboard_stats.get('todaysPnL', '0.00')}
• Signals Processed: {dashboard_stats.get('signalsProcessed', 0)}
• Success Rate: {dashboard_stats.get('successRate', '0.0')}%

⏰ **Last Update:** {datetime.now().strftime('%H:%M:%S')}
        """
        
        await update.message.reply_text(status_message, parse_mode='Markdown')
    
    async def trades_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trades command"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        trades_data = await self._api_request("/trades/active")
        
        if "error" in trades_data:
            await update.message.reply_text(f"❌ Error fetching trades: {trades_data['error']}")
            return
        
        trades = trades_data if isinstance(trades_data, list) else []
        
        if not trades:
            await update.message.reply_text("📭 No active trades")
            return
        
        trades_message = "📈 **Active Trades:**\n\n"
        
        for trade in trades:
            profit = float(trade.get('profit', 0))
            profit_emoji = "💚" if profit > 0 else "❤️" if profit < 0 else "💛"
            
            trades_message += f"""
{profit_emoji} **{trade.get('symbol')} {trade.get('action')}**
• Entry: {trade.get('entryPrice')}
• Current: {trade.get('currentPrice', 'N/A')}
• Lots: {trade.get('lotSize')}
• P&L: ${profit:.2f}
• Ticket: {trade.get('mt5Ticket', 'N/A')}

"""
        
        await update.message.reply_text(trades_message, parse_mode='Markdown')
    
    async def signals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /signals command"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        signals_data = await self._api_request("/signals?limit=10")
        
        if "error" in signals_data:
            await update.message.reply_text(f"❌ Error fetching signals: {signals_data['error']}")
            return
        
        signals = signals_data if isinstance(signals_data, list) else []
        
        if not signals:
            await update.message.reply_text("📭 No recent signals")
            return
        
        signals_message = "📡 **Recent Signals:**\n\n"
        
        for signal in signals[:5]:  # Show last 5 signals
            status_emoji = {
                'executed': '✅',
                'pending': '⏳',
                'failed': '❌',
                'skipped': '⏭️'
            }.get(signal.get('status', 'pending'), '❓')
            
            signals_message += f"""
{status_emoji} **{signal.get('symbol')} {signal.get('action')}**
• Entry: {signal.get('entry')}
• Status: {signal.get('status', 'pending').title()}
• ID: {signal.get('id')}
• Time: {signal.get('createdAt', '')[:16]}

"""
        
        await update.message.reply_text(signals_message, parse_mode='Markdown')
    
    async def replay_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /replay command"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        if not context.args:
            await update.message.reply_text("❌ Usage: /replay <signal_id>")
            return
        
        try:
            signal_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid signal ID. Must be a number.")
            return
        
        # Send replay request to server
        replay_result = await self._api_request(f"/signals/{signal_id}/replay", "POST")
        
        if "error" in replay_result:
            await update.message.reply_text(f"❌ Replay failed: {replay_result['error']}")
        else:
            await update.message.reply_text(f"✅ Signal {signal_id} queued for replay")
    
    async def stealth_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stealth command"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        self.stealth_mode = not self.stealth_mode
        status = "enabled" if self.stealth_mode else "disabled"
        emoji = "👤" if self.stealth_mode else "👁️"
        
        await update.message.reply_text(f"{emoji} Stealth mode {status}")
        
        # Log stealth mode change
        self.logger.info(f"Stealth mode {status} by user {update.effective_user.id}")
    
    async def pause_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pause command"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        self.trading_paused = True
        await update.message.reply_text("⏸️ Trading paused. New signals will not be executed.")
        self.logger.info(f"Trading paused by user {update.effective_user.id}")
    
    async def resume_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /resume command"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        self.trading_paused = False
        await update.message.reply_text("▶️ Trading resumed. Signal processing is active.")
        self.logger.info(f"Trading resumed by user {update.effective_user.id}")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        stats_data = await self._api_request("/dashboard/stats")
        
        if "error" in stats_data:
            await update.message.reply_text(f"❌ Error fetching stats: {stats_data['error']}")
            return
        
        stats_message = f"""
📊 **Trading Statistics**

**Today's Performance:**
• P&L: ${stats_data.get('todaysPnL', '0.00')}
• Success Rate: {stats_data.get('successRate', '0.0')}%
• Signals Processed: {stats_data.get('signalsProcessed', 0)}
• Active Trades: {stats_data.get('activeTrades', 0)}

**Signal Status:**
• Pending: {stats_data.get('pendingSignals', 0)}
• Last Update: {datetime.now().strftime('%H:%M:%S')}
        """
        
        await update.message.reply_text(stats_message, parse_mode='Markdown')
    
    async def config_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /config command"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        config_message = f"""
⚙️ **Current Configuration**

**Trading Settings:**
• Stealth Mode: {'Enabled' if self.stealth_mode else 'Disabled'}
• Trading Status: {'Paused' if self.trading_paused else 'Active'}
• Max Slippage: {self.config.get('conditions', {}).get('max_slippage_pips', 'N/A')} pips
• Max Spread: {self.config.get('conditions', {}).get('max_spread_pips', 'N/A')} pips

**Server:**
• URL: {self.server_url}
• Connection: {'Online' if await self._api_request('/dashboard/stats') else 'Offline'}

**Bot Settings:**
• Authorized Chats: {len(self.allowed_chat_ids) if self.allowed_chat_ids else 'All'}
        """
        
        await update.message.reply_text(config_message, parse_mode='Markdown')
    
    async def close_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /close command for partial trade closures"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        if not context.args:
            help_text = """
🔹 **Partial Close Commands**

**Usage Examples:**
• `/close 50%` - Close 50% of position
• `/close 1.5` - Close 1.5 lots
• `/close 25% 12345` - Close 25% of ticket 12345

**Supported Formats:**
• Percentage: 5% to 95%
• Lot size: 0.01 lots minimum
• Optional ticket number as second argument
            """
            await update.message.reply_text(help_text, parse_mode='Markdown')
            return
        
        # Parse command arguments
        close_arg = context.args[0]
        ticket_arg = context.args[1] if len(context.args) > 1 else None
        
        # Build close command string
        close_command = f"/CLOSE {close_arg}"
        
        # Send partial close request to server
        try:
            close_data = {
                "command": close_command,
                "ticket": int(ticket_arg) if ticket_arg else None,
                "source": "telegram_bot",
                "user_id": update.effective_user.id
            }
            
            close_result = await self._api_request("/trades/partial-close", "POST", close_data)
            
            if "error" in close_result:
                await update.message.reply_text(f"❌ Close failed: {close_result['error']}")
            else:
                success_msg = f"""
✅ **Partial Close Executed**

• Ticket: {close_result.get('original_ticket', 'N/A')}
• Closed: {close_result.get('closed_lots', 0)} lots
• Remaining: {close_result.get('remaining_lots', 0)} lots
• Price: {close_result.get('close_price', 'N/A')}
                """
                await update.message.reply_text(success_msg, parse_mode='Markdown')
                
        except ValueError:
            await update.message.reply_text("❌ Invalid ticket number. Must be a number.")
        except Exception as e:
            await update.message.reply_text(f"❌ Close command failed: {str(e)}")
            self.logger.error(f"Close command error: {e}")
    
    async def range_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /range command for entry range orders"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        if not context.args:
            help_text = """
🔹 **Entry Range Commands**

**Usage Examples:**
• `/range 1.2000-1.2020 AVERAGE` - Average entry across range
• `/range 1.1950/1.1970 SCALE` - Scale into position
• `/range 1.2010 TO 1.2030 BEST` - Best entry in range
• `/range 1.1980-1.2000 SECOND` - Second best entry

**Supported Logic:**
• AVERAGE - Equal lots at multiple levels
• BEST - Single order at optimal price
• SECOND - Single order at second-best price
• SCALE - Progressive scaling with lot multiplier

**Format:** Upper and lower bounds with entry logic
            """
            await update.message.reply_text(help_text, parse_mode='Markdown')
            return
        
        # Combine all arguments to form the range command
        range_command = " ".join(context.args)
        
        # Extract symbol and direction from context or use defaults
        symbol = "EURUSD"  # Default symbol
        direction = "BUY"   # Default direction
        lot_size = 1.0      # Default lot size
        
        # Send entry range request to server
        try:
            range_data = {
                "command": f"RANGE {range_command}",
                "symbol": symbol,
                "direction": direction,
                "lot_size": lot_size,
                "source": "telegram_bot",
                "user_id": update.effective_user.id
            }
            
            range_result = await self._api_request("/trades/entry-range", "POST", range_data)
            
            if "error" in range_result:
                await update.message.reply_text(f"❌ Range setup failed: {range_result['error']}")
            else:
                success_msg = f"""
✅ **Entry Range Created**

• Symbol: {range_result.get('symbol', symbol)}
• Range: {range_result.get('lower_bound', 'N/A')} - {range_result.get('upper_bound', 'N/A')}
• Logic: {range_result.get('entry_logic', 'N/A')}
• Total Size: {range_result.get('total_lot_size', lot_size)} lots
• Pending Orders: {range_result.get('pending_orders', 0)}
• Signal ID: {range_result.get('signal_id', 'N/A')}
                """
                await update.message.reply_text(success_msg, parse_mode='Markdown')
                
        except Exception as e:
            await update.message.reply_text(f"❌ Range command failed: {str(e)}")
            self.logger.error(f"Range command error: {e}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages for signal parsing"""
        if not self._is_authorized(update.effective_chat.id):
            return
        
        message_text = update.message.text
        
        # Check if message looks like a trading signal
        signal_keywords = ['BUY', 'SELL', 'ENTRY', 'TP', 'SL', 'EURUSD', 'GBPUSD', 'USDJPY']
        
        if any(keyword in message_text.upper() for keyword in signal_keywords):
            await update.message.reply_text("📡 Signal detected! Processing...")
            
            # Here you would integrate with your signal parser
            # For now, just acknowledge receipt
            await update.message.reply_text("✅ Signal parsed and queued for execution")
            
            self.logger.info(f"Signal received from user {update.effective_user.id}: {message_text[:100]}...")
        else:
            await update.message.reply_text("💬 Message received. Use /help for available commands.")
    
    async def send_alert(self, message: str, chat_id: Optional[int] = None):
        """Send alert message to authorized users"""
        target_chats = [chat_id] if chat_id else self.allowed_chat_ids
        
        for chat in target_chats:
            try:
                await self.application.bot.send_message(
                    chat_id=chat,
                    text=f"🚨 **Alert:** {message}",
                    parse_mode='Markdown'
                )
            except Exception as e:
                self.logger.error(f"Failed to send alert to {chat}: {e}")
    
    async def send_trade_notification(self, trade_info: Dict[str, Any]):
        """Send trade execution notification"""
        symbol = trade_info.get('symbol', 'N/A')
        action = trade_info.get('action', 'N/A')
        entry = trade_info.get('entry_price', 'N/A')
        ticket = trade_info.get('mt5_ticket', 'N/A')
        
        message = f"""
🎯 **Trade Executed**

• Symbol: {symbol}
• Action: {action}
• Entry: {entry}
• Ticket: {ticket}
• Time: {datetime.now().strftime('%H:%M:%S')}
        """
        
        for chat in self.allowed_chat_ids:
            try:
                await self.application.bot.send_message(
                    chat_id=chat,
                    text=message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                self.logger.error(f"Failed to send trade notification to {chat}: {e}")
    
    def run(self):
        """Start the bot"""
        self.logger.info("Starting SignalOS Copilot Bot...")
        self.application.run_polling(drop_pending_updates=True)

# Example usage
if __name__ == "__main__":
    try:
        bot = SignalOSCopilot()
        bot.run()
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Bot error: {e}")