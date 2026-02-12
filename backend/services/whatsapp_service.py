"""
WhatsApp Service Module for PropTech Decision Copilot
Uses Twilio API for WhatsApp messaging

Features:
- Send WhatsApp messages
- Receive and process incoming messages via webhook
- Automated alerts for property metrics (occupancy, utilization, energy)
"""

import os
import logging
from typing import Optional, Dict, Any, List
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    WhatsApp messaging service using Twilio API.
    Handles sending/receiving messages and automated alerts.
    """
    
    def __init__(self):
        self.account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        self.auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        self.whatsapp_number = os.environ.get("TWILIO_WHATSAPP_NUMBER")
        self._client: Optional[Client] = None
        
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
            # Format WhatsApp numbers
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
        """
        Format a property alert message for WhatsApp.
        
        Args:
            property_name: Name of the property
            alert_type: Type of alert (occupancy, utilization, energy)
            metric_value: Current metric value (percentage)
            financial_impact: Financial impact in INR
            suggested_action: Recommended action to take
        """
        alert_emoji = {
            "high_occupancy": "🔴",
            "low_utilization": "🟡",
            "energy_spike": "⚡"
        }.get(alert_type, "📊")
        
        return f"""{alert_emoji} *PropTech Alert*

*Property:* {property_name}
*Alert:* {alert_type.replace('_', ' ').title()}
*Current Value:* {metric_value:.1f}%
*Financial Impact:* {self.format_currency_inr(financial_impact)}

*Suggested Action:*
{suggested_action}

Reply with property name for detailed analytics."""

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
        
        Args:
            property_name: Name of the property
            occupancy_rate: Current occupancy (0-1)
            utilization_rate: Current utilization (0-1)
            energy_change_percent: Energy change percentage
            financials: Dict with financial metrics
            
        Returns:
            List of alert dictionaries
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
                "financial_impact": financials.get("revenue", 0) * 0.05,  # Risk of overflow
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
                "suggested_action": "Consider floor consolidation or hybrid scheduling to reduce operational costs. Potential monthly savings available."
            })
        
        # Energy Spike Alert (> 15%)
        if energy_change_percent > 15:
            energy_cost_impact = financials.get("energy_cost", 0) * (energy_change_percent / 100)
            alerts.append({
                "type": "energy_spike",
                "property_name": property_name,
                "metric_value": energy_change_percent,
                "financial_impact": energy_cost_impact,
                "suggested_action": "Investigate HVAC systems and lighting schedules. Consider smart energy management or off-peak scheduling."
            })
        
        return alerts
    
    def create_webhook_response(self, message: str) -> str:
        """
        Create a TwiML response for webhook.
        
        Args:
            message: Response message text
            
        Returns:
            TwiML XML string
        """
        response = MessagingResponse()
        response.message(message)
        return str(response)


# Singleton instance
whatsapp_service = WhatsAppService()
