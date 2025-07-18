"""
Future Phase: Webhook system for Discord/Slack/Telegram notifications
"""

import asyncio
import json
import httpx
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from enum import Enum

from utils.logging_config import get_logger

logger = get_logger("webhooks")


class WebhookType(str, Enum):
    """Webhook types"""
    DISCORD = "discord"
    SLACK = "slack"
    TELEGRAM = "telegram"
    GENERIC = "generic"


class EventType(str, Enum):
    """Event types for webhooks"""
    TRADE_OPENED = "trade_opened"
    TRADE_CLOSED = "trade_closed"
    TRADE_MODIFIED = "trade_modified"
    SIGNAL_RECEIVED = "signal_received"
    SIGNAL_PARSED = "signal_parsed"
    ACCOUNT_BALANCE_CHANGED = "account_balance_changed"
    SYSTEM_ERROR = "system_error"
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"


class WebhookConfig(BaseModel):
    """Webhook configuration model"""
    id: str
    name: str
    type: WebhookType
    url: HttpUrl
    events: List[EventType]
    active: bool = True
    retry_count: int = 3
    timeout: int = 30
    headers: Dict[str, str] = {}
    template: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WebhookEvent(BaseModel):
    """Webhook event model"""
    id: str
    type: EventType
    data: Dict[str, Any]
    timestamp: datetime
    source: str = "SignalOS"
    
    class Config:
        from_attributes = True


class WebhookDelivery(BaseModel):
    """Webhook delivery model"""
    id: str
    webhook_id: str
    event_id: str
    status: str
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    attempts: int = 0
    delivered_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class WebhookService:
    """Webhook service for event notifications"""
    
    def __init__(self):
        self.webhooks: Dict[str, WebhookConfig] = {}
        self.deliveries: Dict[str, WebhookDelivery] = {}
        self.templates = {
            "discord": self._get_discord_template(),
            "slack": self._get_slack_template(),
            "telegram": self._get_telegram_template()
        }
    
    async def create_webhook(self, webhook_data: Dict[str, Any]) -> WebhookConfig:
        """Create new webhook"""
        try:
            webhook = WebhookConfig(
                id=f"webhook_{len(self.webhooks) + 1}",
                name=webhook_data["name"],
                type=WebhookType(webhook_data["type"]),
                url=webhook_data["url"],
                events=[EventType(event) for event in webhook_data["events"]],
                active=webhook_data.get("active", True),
                retry_count=webhook_data.get("retry_count", 3),
                timeout=webhook_data.get("timeout", 30),
                headers=webhook_data.get("headers", {}),
                template=webhook_data.get("template"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.webhooks[webhook.id] = webhook
            logger.info(f"Created webhook: {webhook.id}")
            
            return webhook
            
        except Exception as e:
            logger.error(f"Error creating webhook: {e}")
            raise
    
    async def update_webhook(self, webhook_id: str, 
                           update_data: Dict[str, Any]) -> Optional[WebhookConfig]:
        """Update existing webhook"""
        try:
            webhook = self.webhooks.get(webhook_id)
            if not webhook:
                return None
            
            # Update fields
            for field, value in update_data.items():
                if hasattr(webhook, field):
                    setattr(webhook, field, value)
            
            webhook.updated_at = datetime.utcnow()
            
            logger.info(f"Updated webhook: {webhook_id}")
            return webhook
            
        except Exception as e:
            logger.error(f"Error updating webhook {webhook_id}: {e}")
            raise
    
    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete webhook"""
        try:
            if webhook_id in self.webhooks:
                del self.webhooks[webhook_id]
                logger.info(f"Deleted webhook: {webhook_id}")
                return True
            else:
                logger.warning(f"Webhook not found for deletion: {webhook_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting webhook {webhook_id}: {e}")
            return False
    
    async def get_webhooks(self, active_only: bool = True) -> List[WebhookConfig]:
        """Get all webhooks"""
        try:
            webhooks = list(self.webhooks.values())
            
            if active_only:
                webhooks = [w for w in webhooks if w.active]
            
            logger.info(f"Retrieved {len(webhooks)} webhooks")
            return webhooks
            
        except Exception as e:
            logger.error(f"Error getting webhooks: {e}")
            return []
    
    async def send_event(self, event_type: EventType, data: Dict[str, Any], 
                        source: str = "SignalOS") -> str:
        """Send event to all matching webhooks"""
        try:
            # Create event
            event = WebhookEvent(
                id=f"event_{int(datetime.utcnow().timestamp() * 1000)}",
                type=event_type,
                data=data,
                timestamp=datetime.utcnow(),
                source=source
            )
            
            # Get matching webhooks
            matching_webhooks = [
                w for w in self.webhooks.values()
                if w.active and event_type in w.events
            ]
            
            # Send to all matching webhooks
            tasks = []
            for webhook in matching_webhooks:
                task = asyncio.create_task(
                    self._deliver_webhook(webhook, event)
                )
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            logger.info(f"Sent event {event.id} to {len(matching_webhooks)} webhooks")
            return event.id
            
        except Exception as e:
            logger.error(f"Error sending event: {e}")
            raise
    
    async def _deliver_webhook(self, webhook: WebhookConfig, event: WebhookEvent):
        """Deliver webhook to specific endpoint"""
        delivery_id = f"delivery_{int(datetime.utcnow().timestamp() * 1000)}"
        
        delivery = WebhookDelivery(
            id=delivery_id,
            webhook_id=webhook.id,
            event_id=event.id,
            status="pending",
            created_at=datetime.utcnow()
        )
        
        self.deliveries[delivery_id] = delivery
        
        try:
            # Prepare payload
            payload = self._prepare_payload(webhook, event)
            
            # Send webhook
            async with httpx.AsyncClient(timeout=webhook.timeout) as client:
                response = await client.post(
                    str(webhook.url),
                    json=payload,
                    headers=webhook.headers
                )
                
                delivery.status = "success"
                delivery.response_code = response.status_code
                delivery.response_body = response.text[:1000]  # Limit response body
                delivery.delivered_at = datetime.utcnow()
                
                logger.info(f"Webhook delivered successfully: {delivery_id}")
                
        except Exception as e:
            delivery.status = "failed"
            delivery.error_message = str(e)
            delivery.attempts += 1
            
            logger.error(f"Webhook delivery failed: {delivery_id} - {e}")
            
            # Retry if configured
            if delivery.attempts < webhook.retry_count:
                await asyncio.sleep(2 ** delivery.attempts)  # Exponential backoff
                await self._deliver_webhook(webhook, event)
    
    def _prepare_payload(self, webhook: WebhookConfig, event: WebhookEvent) -> Dict[str, Any]:
        """Prepare webhook payload based on type"""
        try:
            if webhook.type == WebhookType.DISCORD:
                return self._prepare_discord_payload(webhook, event)
            elif webhook.type == WebhookType.SLACK:
                return self._prepare_slack_payload(webhook, event)
            elif webhook.type == WebhookType.TELEGRAM:
                return self._prepare_telegram_payload(webhook, event)
            else:
                return self._prepare_generic_payload(webhook, event)
                
        except Exception as e:
            logger.error(f"Error preparing payload: {e}")
            return self._prepare_generic_payload(webhook, event)
    
    def _prepare_discord_payload(self, webhook: WebhookConfig, event: WebhookEvent) -> Dict[str, Any]:
        """Prepare Discord webhook payload"""
        # Get event-specific message
        message = self._get_event_message(event)
        
        # Get event color
        color = self._get_event_color(event.type)
        
        payload = {
            "embeds": [
                {
                    "title": f"SignalOS - {event.type.value.replace('_', ' ').title()}",
                    "description": message,
                    "color": color,
                    "timestamp": event.timestamp.isoformat(),
                    "footer": {
                        "text": f"SignalOS | {event.source}"
                    },
                    "fields": self._get_event_fields(event)
                }
            ]
        }
        
        return payload
    
    def _prepare_slack_payload(self, webhook: WebhookConfig, event: WebhookEvent) -> Dict[str, Any]:
        """Prepare Slack webhook payload"""
        message = self._get_event_message(event)
        
        payload = {
            "text": f"SignalOS - {event.type.value.replace('_', ' ').title()}",
            "attachments": [
                {
                    "color": self._get_slack_color(event.type),
                    "fields": [
                        {
                            "title": "Event",
                            "value": message,
                            "short": False
                        }
                    ] + self._get_slack_fields(event),
                    "footer": f"SignalOS | {event.source}",
                    "ts": int(event.timestamp.timestamp())
                }
            ]
        }
        
        return payload
    
    def _prepare_telegram_payload(self, webhook: WebhookConfig, event: WebhookEvent) -> Dict[str, Any]:
        """Prepare Telegram webhook payload"""
        message = self._get_event_message(event)
        
        # Format message with Telegram markdown
        formatted_message = f"*SignalOS - {event.type.value.replace('_', ' ').title()}*\n\n{message}"
        
        # Add event details
        for field in self._get_event_fields(event):
            formatted_message += f"\n*{field['name']}:* {field['value']}"
        
        payload = {
            "text": formatted_message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        return payload
    
    def _prepare_generic_payload(self, webhook: WebhookConfig, event: WebhookEvent) -> Dict[str, Any]:
        """Prepare generic webhook payload"""
        return {
            "event": event.type.value,
            "timestamp": event.timestamp.isoformat(),
            "source": event.source,
            "data": event.data
        }
    
    def _get_event_message(self, event: WebhookEvent) -> str:
        """Get formatted message for event"""
        event_type = event.type
        data = event.data
        
        if event_type == EventType.TRADE_OPENED:
            return f"🟢 Trade opened: {data.get('symbol', 'N/A')} {data.get('type', 'N/A')} {data.get('volume', 'N/A')}"
        elif event_type == EventType.TRADE_CLOSED:
            profit = data.get('profit', 0)
            profit_emoji = "🟢" if profit > 0 else "🔴"
            return f"{profit_emoji} Trade closed: {data.get('symbol', 'N/A')} | P&L: ${profit:.2f}"
        elif event_type == EventType.SIGNAL_RECEIVED:
            return f"📶 Signal received: {data.get('symbol', 'N/A')} {data.get('type', 'N/A')}"
        elif event_type == EventType.SIGNAL_PARSED:
            return f"✅ Signal parsed: {data.get('symbol', 'N/A')} | Method: {data.get('method', 'N/A')}"
        elif event_type == EventType.ACCOUNT_BALANCE_CHANGED:
            return f"💰 Account balance: ${data.get('balance', 0):.2f} | Change: ${data.get('change', 0):.2f}"
        elif event_type == EventType.SYSTEM_ERROR:
            return f"❌ System error: {data.get('error', 'Unknown error')}"
        elif event_type == EventType.SYSTEM_STARTED:
            return f"🚀 SignalOS started successfully"
        elif event_type == EventType.SYSTEM_STOPPED:
            return f"⏹️ SignalOS stopped"
        else:
            return f"Event: {event_type.value}"
    
    def _get_event_color(self, event_type: EventType) -> int:
        """Get Discord color for event type"""
        colors = {
            EventType.TRADE_OPENED: 0x00ff00,      # Green
            EventType.TRADE_CLOSED: 0x0099ff,      # Blue
            EventType.TRADE_MODIFIED: 0xffaa00,    # Orange
            EventType.SIGNAL_RECEIVED: 0x9900ff,   # Purple
            EventType.SIGNAL_PARSED: 0x00ffaa,     # Cyan
            EventType.ACCOUNT_BALANCE_CHANGED: 0xffff00,  # Yellow
            EventType.SYSTEM_ERROR: 0xff0000,      # Red
            EventType.SYSTEM_STARTED: 0x00ff00,    # Green
            EventType.SYSTEM_STOPPED: 0xff9900     # Orange
        }
        return colors.get(event_type, 0x808080)  # Gray default
    
    def _get_slack_color(self, event_type: EventType) -> str:
        """Get Slack color for event type"""
        colors = {
            EventType.TRADE_OPENED: "good",
            EventType.TRADE_CLOSED: "good",
            EventType.TRADE_MODIFIED: "warning",
            EventType.SIGNAL_RECEIVED: "#9900ff",
            EventType.SIGNAL_PARSED: "good",
            EventType.ACCOUNT_BALANCE_CHANGED: "warning",
            EventType.SYSTEM_ERROR: "danger",
            EventType.SYSTEM_STARTED: "good",
            EventType.SYSTEM_STOPPED: "warning"
        }
        return colors.get(event_type, "#808080")
    
    def _get_event_fields(self, event: WebhookEvent) -> List[Dict[str, Any]]:
        """Get event fields for webhook"""
        fields = []
        data = event.data
        
        # Common fields
        if "symbol" in data:
            fields.append({"name": "Symbol", "value": data["symbol"], "inline": True})
        
        if "type" in data:
            fields.append({"name": "Type", "value": data["type"], "inline": True})
        
        if "volume" in data:
            fields.append({"name": "Volume", "value": str(data["volume"]), "inline": True})
        
        if "profit" in data:
            fields.append({"name": "Profit", "value": f"${data['profit']:.2f}", "inline": True})
        
        if "price" in data:
            fields.append({"name": "Price", "value": str(data["price"]), "inline": True})
        
        return fields
    
    def _get_slack_fields(self, event: WebhookEvent) -> List[Dict[str, Any]]:
        """Get Slack-formatted event fields"""
        fields = []
        data = event.data
        
        for field in self._get_event_fields(event):
            fields.append({
                "title": field["name"],
                "value": field["value"],
                "short": field.get("inline", False)
            })
        
        return fields
    
    def _get_discord_template(self) -> str:
        """Get Discord webhook template"""
        return """
        {
            "embeds": [
                {
                    "title": "SignalOS - {{event_type}}",
                    "description": "{{message}}",
                    "color": {{color}},
                    "timestamp": "{{timestamp}}",
                    "footer": {
                        "text": "SignalOS | {{source}}"
                    },
                    "fields": {{fields}}
                }
            ]
        }
        """
    
    def _get_slack_template(self) -> str:
        """Get Slack webhook template"""
        return """
        {
            "text": "SignalOS - {{event_type}}",
            "attachments": [
                {
                    "color": "{{color}}",
                    "fields": [
                        {
                            "title": "Event",
                            "value": "{{message}}",
                            "short": false
                        }
                    ],
                    "footer": "SignalOS | {{source}}",
                    "ts": {{timestamp}}
                }
            ]
        }
        """
    
    def _get_telegram_template(self) -> str:
        """Get Telegram webhook template"""
        return """
        {
            "text": "*SignalOS - {{event_type}}*\\n\\n{{message}}",
            "parse_mode": "Markdown",
            "disable_web_page_preview": true
        }
        """
    
    async def get_deliveries(self, webhook_id: str = None, 
                           status: str = None) -> List[WebhookDelivery]:
        """Get webhook deliveries"""
        try:
            deliveries = list(self.deliveries.values())
            
            if webhook_id:
                deliveries = [d for d in deliveries if d.webhook_id == webhook_id]
            
            if status:
                deliveries = [d for d in deliveries if d.status == status]
            
            # Sort by creation time (most recent first)
            deliveries.sort(key=lambda d: d.created_at, reverse=True)
            
            logger.info(f"Retrieved {len(deliveries)} deliveries")
            return deliveries
            
        except Exception as e:
            logger.error(f"Error getting deliveries: {e}")
            return []
    
    async def test_webhook(self, webhook_id: str) -> bool:
        """Test webhook delivery"""
        try:
            webhook = self.webhooks.get(webhook_id)
            if not webhook:
                return False
            
            # Create test event
            test_event = WebhookEvent(
                id="test_event",
                type=EventType.SYSTEM_STARTED,
                data={"message": "This is a test webhook from SignalOS"},
                timestamp=datetime.utcnow(),
                source="SignalOS Test"
            )
            
            # Deliver webhook
            await self._deliver_webhook(webhook, test_event)
            
            logger.info(f"Test webhook sent: {webhook_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error testing webhook {webhook_id}: {e}")
            return False


# Global webhook service instance
_webhook_service = None


def get_webhook_service() -> WebhookService:
    """Get global webhook service instance"""
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookService()
    return _webhook_service


# Convenience functions for common events
async def send_trade_opened_event(symbol: str, trade_type: str, volume: float, 
                                price: float, ticket: int):
    """Send trade opened event"""
    webhook_service = get_webhook_service()
    await webhook_service.send_event(
        EventType.TRADE_OPENED,
        {
            "symbol": symbol,
            "type": trade_type,
            "volume": volume,
            "price": price,
            "ticket": ticket
        }
    )


async def send_trade_closed_event(symbol: str, profit: float, duration: int, 
                                ticket: int):
    """Send trade closed event"""
    webhook_service = get_webhook_service()
    await webhook_service.send_event(
        EventType.TRADE_CLOSED,
        {
            "symbol": symbol,
            "profit": profit,
            "duration": duration,
            "ticket": ticket
        }
    )


async def send_signal_received_event(symbol: str, signal_type: str, 
                                   provider: str, raw_text: str):
    """Send signal received event"""
    webhook_service = get_webhook_service()
    await webhook_service.send_event(
        EventType.SIGNAL_RECEIVED,
        {
            "symbol": symbol,
            "type": signal_type,
            "provider": provider,
            "raw_text": raw_text[:200]  # Limit text length
        }
    )


async def send_system_error_event(error_message: str, component: str):
    """Send system error event"""
    webhook_service = get_webhook_service()
    await webhook_service.send_event(
        EventType.SYSTEM_ERROR,
        {
            "error": error_message,
            "component": component
        }
    )