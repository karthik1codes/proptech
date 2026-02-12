"""
WhatsApp Service Module for PropTech Decision Copilot
Uses Twilio API for WhatsApp messaging

Features:
- Send WhatsApp messages with templates
- Receive and process incoming messages via webhook
- Automated alerts for property metrics (occupancy, utilization, energy)
- Conversation history persistence to MongoDB
- Scheduled alert checks
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

logger = logging.getLogger(__name__)


# ==================== MESSAGE TEMPLATES ====================

class MessageTemplates:
    """
    Pre-defined WhatsApp message templates for better delivery.
    Templates follow WhatsApp Business API format guidelines.
    """
    
    @staticmethod
    def welcome() -> str:
        return """👋 *Welcome to PropTech Copilot!*

I'm your AI-powered property analytics assistant.

📋 *Quick Commands:*
• *list* - View all properties
• *[property name]* - Get detailed analytics
• *alerts* - Check active alerts
• *help* - Show all commands

Reply with a command to get started!"""

    @staticmethod
    def help_menu() -> str:
        return """🤖 *PropTech Copilot - Help Menu*

📋 *Available Commands:*

*Property Analytics:*
• *list* or *properties* - Show all properties
• *[property name]* - Get property details
• *overview* - Portfolio summary

*Alerts & Monitoring:*
• *alerts* - View active alerts
• *status* - System status

*Navigation:*
• *help* - Show this menu
• *back* - Previous menu

💡 *Tip:* Just type a property name like "Horizon" to get instant analytics!"""

    @staticmethod
    def property_list(properties: List[Dict], format_fn) -> str:
        msg = "📋 *Property Portfolio Overview*\n\n"
        
        for prop in properties:
            occupancy = prop.get("occupancy", 0)
            status_emoji = "🟢" if occupancy >= 70 else "🟡" if occupancy >= 50 else "🔴"
            
            msg += f"{status_emoji} *{prop['name']}*\n"
            msg += f"   📍 {prop['location']}\n"
            msg += f"   📊 Occupancy: {occupancy:.1f}%\n\n"
        
        msg += "_Reply with property name for detailed analytics._"
        return msg

    @staticmethod
    def property_details(
        name: str,
        location: str,
        prop_type: str,
        occupancy: float,
        utilization: str,
        efficiency: float,
        revenue: str,
        profit: str,
        energy_cost: str,
        recommendation: Optional[Dict] = None
    ) -> str:
        msg = f"""📊 *{name}*

📍 *Location:* {location}
🏢 *Type:* {prop_type}

━━━━━━━━━━━━━━━━━━
📈 *Performance Metrics*
━━━━━━━━━━━━━━━━━━
• Occupancy: {occupancy:.1f}%
• Utilization: {utilization}
• Efficiency: {efficiency:.1f}%

━━━━━━━━━━━━━━━━━━
💰 *Financial Summary*
━━━━━━━━━━━━━━━━━━
• Revenue: {revenue}
• Profit: {profit}
• Energy Cost: {energy_cost}
"""
        if recommendation:
            msg += f"""
━━━━━━━━━━━━━━━━━━
💡 *Top Recommendation*
━━━━━━━━━━━━━━━━━━
{recommendation['title']}
Impact: {recommendation['impact']}/month
"""
        return msg

    @staticmethod
    def alert_notification(
        alert_type: str,
        property_name: str,
        metric_value: float,
        financial_impact: str,
        suggested_action: str
    ) -> str:
        alert_config = {
            "high_occupancy": {"emoji": "🔴", "title": "High Occupancy Alert"},
            "low_utilization": {"emoji": "🟡", "title": "Low Utilization Alert"},
            "energy_spike": {"emoji": "⚡", "title": "Energy Spike Alert"}
        }
        
        config = alert_config.get(alert_type, {"emoji": "📊", "title": "Property Alert"})
        
        return f"""{config['emoji']} *{config['title']}*

━━━━━━━━━━━━━━━━━━
🏢 *Property:* {property_name}
📊 *Current Value:* {metric_value:.1f}%
💰 *Financial Impact:* {financial_impact}

━━━━━━━━━━━━━━━━━━
*Recommended Action:*
{suggested_action}

_Reply with property name for detailed analytics._"""

    @staticmethod
    def no_alerts() -> str:
        return """✅ *No Active Alerts*

All properties are operating within normal parameters.

📊 *Monitoring Thresholds:*
• Occupancy > 90% → High Occupancy Alert
• Utilization < 40% → Low Utilization Alert  
• Energy Change > 15% → Energy Spike Alert

_Reply 'list' to view all properties._"""

    @staticmethod
    def active_alerts(alerts: List[Dict], format_fn) -> str:
        if not alerts:
            return MessageTemplates.no_alerts()
        
        msg = f"⚠️ *{len(alerts)} Active Alert(s)*\n\n"
        
        for i, alert in enumerate(alerts, 1):
            emoji = {"high_occupancy": "🔴", "low_utilization": "🟡", "energy_spike": "⚡"}.get(alert['type'], "📊")
            msg += f"{emoji} *{alert['property_name']}*\n"
            msg += f"   {alert['type'].replace('_', ' ').title()}: {alert['metric_value']:.1f}%\n"
            msg += f"   Impact: {format_fn(alert['financial_impact'])}\n\n"
        
        msg += "_Reply with property name for details._"
        return msg

    @staticmethod
    def error_message() -> str:
        return """❌ *Something went wrong*

I couldn't process your request. Please try again.

*Quick Commands:*
• *list* - View properties
• *help* - Show help menu

_If the issue persists, please contact support._"""


# ==================== WHATSAPP SERVICE ====================

class WhatsAppService:
    """
    WhatsApp messaging service using Twilio API.
    Handles sending/receiving messages, automated alerts, and conversation history.
    """
    
    def __init__(self):
        self.account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        self.auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        self.whatsapp_number = os.environ.get("TWILIO_WHATSAPP_NUMBER")
        self._client: Optional[Client] = None
        self.templates = MessageTemplates()
        
        # Alert check interval in seconds (default: 30 minutes)
        self.alert_check_interval = int(os.environ.get("ALERT_CHECK_INTERVAL", 1800))
        
        # Registered alert subscribers (phone numbers)
        self._alert_subscribers: Dict[str, Dict] = {}
        
        # Background task reference
        self._alert_task: Optional[asyncio.Task] = None
        
    @property
    def is_configured(self) -> bool:
        """Check if Twilio credentials are configured"""
        return all([self.account_sid, self.auth_token, self.whatsapp_number])
    
    @property
    def client(self) -> Optional[Client]:
        """Lazy-load Twilio client"""
        if not self.is_configured:
            return None
        if self._client is None:
            try:
                self._client = Client(self.account_sid, self.auth_token)
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
                return None
        return self._client
    
    def send_whatsapp_message(self, to_number: str, message: str) -> Dict[str, Any]:
        """
        Send a WhatsApp message to a phone number.
        
        Args:
            to_number: Phone number in E.164 format (e.g., +919876543210)
            message: Message text to send
            
        Returns:
            Dict with status and message_sid or error
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "WhatsApp service not configured. Missing Twilio credentials."
            }
        
        if not self.client:
            return {
                "success": False,
                "error": "Failed to initialize Twilio client"
            }
        
        # Validate phone number format
        if not to_number.startswith("+"):
            return {
                "success": False,
                "error": "Phone number must be in E.164 format starting with +"
            }
        
        try:
            # Format WhatsApp numbers - use sandbox number for Twilio sandbox
            from_whatsapp = f"whatsapp:{self.whatsapp_number}"
            to_whatsapp = f"whatsapp:{to_number}"
            
            msg = self.client.messages.create(
                from_=from_whatsapp,
                to=to_whatsapp,
                body=message
            )
            
            logger.info(f"WhatsApp message sent: {msg.sid}")
            
            return {
                "success": True,
                "message_sid": msg.sid,
                "to": to_number,
                "status": msg.status
            }
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def send_template_message(
        self,
        to_number: str,
        template_type: str,
        template_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send a templated WhatsApp message.
        
        Args:
            to_number: Phone number in E.164 format
            template_type: Type of template (welcome, help, property_list, etc.)
            template_data: Data to populate the template
            
        Returns:
            Dict with status and message_sid or error
        """
        try:
            # Generate message from template
            if template_type == "welcome":
                message = self.templates.welcome()
            elif template_type == "help":
                message = self.templates.help_menu()
            elif template_type == "property_list":
                message = self.templates.property_list(
                    template_data.get("properties", []),
                    self.format_currency_inr
                )
            elif template_type == "property_details":
                message = self.templates.property_details(**template_data)
            elif template_type == "alert":
                message = self.templates.alert_notification(**template_data)
            elif template_type == "active_alerts":
                message = self.templates.active_alerts(
                    template_data.get("alerts", []),
                    self.format_currency_inr
                )
            elif template_type == "no_alerts":
                message = self.templates.no_alerts()
            elif template_type == "error":
                message = self.templates.error_message()
            else:
                return {"success": False, "error": f"Unknown template type: {template_type}"}
            
            return self.send_whatsapp_message(to_number, message)
            
        except Exception as e:
            logger.error(f"Failed to send template message: {e}")
            return {"success": False, "error": str(e)}
    
    def format_currency_inr(self, value: float) -> str:
        """Format value in Indian Rupees with Lakhs/Crores notation"""
        if abs(value) >= 10000000:
            return f"₹{value / 10000000:.2f} Cr"
        elif abs(value) >= 100000:
            return f"₹{value / 100000:.2f} L"
        else:
            return f"₹{value:,.0f}"
    
    def format_property_alert(
        self,
        property_name: str,
        alert_type: str,
        metric_value: float,
        financial_impact: float,
        suggested_action: str
    ) -> str:
        """Format a property alert message using template."""
        return self.templates.alert_notification(
            alert_type=alert_type,
            property_name=property_name,
            metric_value=metric_value,
            financial_impact=self.format_currency_inr(financial_impact),
            suggested_action=suggested_action
        )

    def check_and_generate_alerts(
        self,
        property_name: str,
        occupancy_rate: float,
        utilization_rate: float,
        energy_change_percent: float,
        financials: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Check property metrics and generate alerts if thresholds exceeded.
        
        Thresholds:
        - High Occupancy: > 90%
        - Low Utilization: < 40%
        - Energy Spike: > 15% increase
        """
        alerts = []
        occupancy_pct = occupancy_rate * 100
        utilization_pct = utilization_rate * 100
        
        # High Occupancy Alert (> 90%)
        if occupancy_pct > 90:
            alerts.append({
                "type": "high_occupancy",
                "property_name": property_name,
                "metric_value": occupancy_pct,
                "financial_impact": financials.get("revenue", 0) * 0.05,
                "suggested_action": "Consider temporary overflow arrangements or redirect bookings to nearby properties to maintain service quality."
            })
        
        # Low Utilization Alert (< 40%)
        if utilization_pct < 40:
            monthly_loss = financials.get("maintenance_cost", 0) * 0.3
            alerts.append({
                "type": "low_utilization",
                "property_name": property_name,
                "metric_value": utilization_pct,
                "financial_impact": monthly_loss,
                "suggested_action": "Consider floor consolidation or hybrid scheduling to reduce operational costs."
            })
        
        # Energy Spike Alert (> 15%)
        if energy_change_percent > 15:
            energy_cost_impact = financials.get("energy_cost", 0) * (energy_change_percent / 100)
            alerts.append({
                "type": "energy_spike",
                "property_name": property_name,
                "metric_value": energy_change_percent,
                "financial_impact": energy_cost_impact,
                "suggested_action": "Investigate HVAC systems and lighting schedules. Consider smart energy management."
            })
        
        return alerts
    
    def create_webhook_response(self, message: str) -> str:
        """Create a TwiML response for webhook."""
        response = MessagingResponse()
        response.message(message)
        return str(response)
    
    # ==================== ALERT SUBSCRIBERS ====================
    
    def subscribe_to_alerts(self, phone_number: str, property_ids: List[str] = None) -> Dict[str, Any]:
        """
        Subscribe a phone number to receive property alerts.
        
        Args:
            phone_number: Phone number in E.164 format
            property_ids: List of property IDs to monitor (None = all)
        """
        if not phone_number.startswith("+"):
            return {"success": False, "error": "Invalid phone number format"}
        
        self._alert_subscribers[phone_number] = {
            "property_ids": property_ids,  # None means all properties
            "subscribed_at": datetime.now(timezone.utc).isoformat(),
            "active": True
        }
        
        logger.info(f"Alert subscription added: {phone_number}")
        return {"success": True, "message": "Subscribed to alerts"}
    
    def unsubscribe_from_alerts(self, phone_number: str) -> Dict[str, Any]:
        """Unsubscribe a phone number from alerts."""
        if phone_number in self._alert_subscribers:
            del self._alert_subscribers[phone_number]
            logger.info(f"Alert subscription removed: {phone_number}")
            return {"success": True, "message": "Unsubscribed from alerts"}
        return {"success": False, "error": "Subscription not found"}
    
    def get_subscribers(self) -> Dict[str, Dict]:
        """Get all alert subscribers."""
        return self._alert_subscribers.copy()


# Singleton instance
whatsapp_service = WhatsAppService()
