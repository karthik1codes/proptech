"""
Scheduled Alert Checker for PropTech WhatsApp Integration
Runs background tasks to monitor property metrics and send alerts
"""

import asyncio
import logging
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class AlertScheduler:
    """
    Background task scheduler for property alerts.
    Periodically checks property metrics and sends WhatsApp alerts.
    """
    
    COLLECTION_NAME = "alert_subscriptions"
    ALERT_LOG_COLLECTION = "alert_logs"
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        whatsapp_service,
        property_store,
        intelligence_engine,
        check_interval: int = 1800  # 30 minutes default
    ):
        self.db = db
        self.subscriptions = db[self.COLLECTION_NAME]
        self.alert_logs = db[self.ALERT_LOG_COLLECTION]
        self.whatsapp_service = whatsapp_service
        self.property_store = property_store
        self.intelligence_engine = intelligence_engine
        self.check_interval = check_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def ensure_indexes(self):
        """Create necessary indexes."""
        try:
            await self.subscriptions.create_index("phone_number", unique=True)
            await self.alert_logs.create_index("phone_number")
            await self.alert_logs.create_index("created_at")
            await self.alert_logs.create_index("alert_type")
            logger.info("Alert scheduler indexes created")
        except Exception as e:
            logger.error(f"Failed to create alert indexes: {e}")
    
    # ==================== SUBSCRIPTION MANAGEMENT ====================
    
    async def subscribe(
        self,
        phone_number: str,
        property_ids: Optional[List[str]] = None,
        alert_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Subscribe a phone number to receive property alerts.
        
        Args:
            phone_number: Phone number in E.164 format
            property_ids: List of property IDs to monitor (None = all)
            alert_types: Types of alerts to receive (None = all)
        """
        if not phone_number.startswith("+"):
            return {"success": False, "error": "Invalid phone number format"}
        
        try:
            subscription = {
                "phone_number": phone_number,
                "property_ids": property_ids,
                "alert_types": alert_types or ["high_occupancy", "low_utilization", "energy_spike"],
                "active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            await self.subscriptions.update_one(
                {"phone_number": phone_number},
                {"$set": subscription},
                upsert=True
            )
            
            logger.info(f"Alert subscription saved: {phone_number}")
            return {"success": True, "message": "Subscribed to alerts"}
            
        except Exception as e:
            logger.error(f"Failed to save subscription: {e}")
            return {"success": False, "error": str(e)}
    
    async def unsubscribe(self, phone_number: str) -> Dict[str, Any]:
        """Unsubscribe a phone number from alerts."""
        try:
            result = await self.subscriptions.update_one(
                {"phone_number": phone_number},
                {"$set": {"active": False, "updated_at": datetime.now(timezone.utc)}}
            )
            
            if result.modified_count > 0:
                logger.info(f"Alert subscription deactivated: {phone_number}")
                return {"success": True, "message": "Unsubscribed from alerts"}
            return {"success": False, "error": "Subscription not found"}
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_subscription(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get subscription details for a phone number."""
        try:
            return await self.subscriptions.find_one(
                {"phone_number": phone_number, "active": True},
                {"_id": 0}
            )
        except Exception as e:
            logger.error(f"Failed to get subscription: {e}")
            return None
    
    async def get_all_active_subscriptions(self) -> List[Dict[str, Any]]:
        """Get all active alert subscriptions."""
        try:
            cursor = self.subscriptions.find({"active": True}, {"_id": 0})
            return await cursor.to_list(length=1000)
        except Exception as e:
            logger.error(f"Failed to get subscriptions: {e}")
            return []
    
    # ==================== ALERT CHECKING ====================
    
    async def check_property_alerts(self, property_id: str) -> List[Dict[str, Any]]:
        """
        Check a property for alert conditions.
        
        Returns list of triggered alerts.
        """
        prop = self.property_store.get_by_id(property_id)
        if not prop:
            return []
        
        digital_twin = prop.get("digital_twin", {})
        daily_data = digital_twin.get("daily_history", [])
        
        if len(daily_data) < 2:
            return []
        
        # Calculate current metrics
        recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
        
        # Calculate energy change
        recent_energy = sum(d.get("energy_kwh", 0) for d in daily_data[-7:])
        prev_energy = sum(d.get("energy_kwh", 0) for d in daily_data[-14:-7]) if len(daily_data) >= 14 else recent_energy
        energy_change = ((recent_energy - prev_energy) / prev_energy * 100) if prev_energy > 0 else 0
        
        financials = self.intelligence_engine.calculate_financials(prop, recent_occupancy)
        
        # Check for alerts
        return self.whatsapp_service.check_and_generate_alerts(
            property_name=prop["name"],
            occupancy_rate=recent_occupancy,
            utilization_rate=recent_occupancy,
            energy_change_percent=energy_change,
            financials=financials
        )
    
    async def check_all_properties(self) -> Dict[str, List[Dict[str, Any]]]:
        """Check all properties for alerts."""
        all_alerts = {}
        
        for prop in self.property_store.get_all():
            alerts = await self.check_property_alerts(prop["property_id"])
            if alerts:
                all_alerts[prop["property_id"]] = alerts
        
        return all_alerts
    
    # ==================== ALERT SENDING ====================
    
    async def send_alerts_to_subscriber(
        self,
        phone_number: str,
        alerts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Send alerts to a subscriber."""
        results = []
        
        for alert in alerts:
            message = self.whatsapp_service.format_property_alert(
                property_name=alert["property_name"],
                alert_type=alert["type"],
                metric_value=alert["metric_value"],
                financial_impact=alert["financial_impact"],
                suggested_action=alert["suggested_action"]
            )
            
            result = self.whatsapp_service.send_whatsapp_message(phone_number, message)
            
            # Log the alert
            await self.log_alert(
                phone_number=phone_number,
                alert_type=alert["type"],
                property_name=alert["property_name"],
                sent=result.get("success", False),
                message_sid=result.get("message_sid")
            )
            
            results.append({
                "alert_type": alert["type"],
                "property_name": alert["property_name"],
                "sent": result.get("success", False),
                "message_sid": result.get("message_sid")
            })
        
        return results
    
    async def log_alert(
        self,
        phone_number: str,
        alert_type: str,
        property_name: str,
        sent: bool,
        message_sid: Optional[str] = None
    ):
        """Log an alert to the database."""
        try:
            await self.alert_logs.insert_one({
                "phone_number": phone_number,
                "alert_type": alert_type,
                "property_name": property_name,
                "sent": sent,
                "message_sid": message_sid,
                "created_at": datetime.now(timezone.utc)
            })
        except Exception as e:
            logger.error(f"Failed to log alert: {e}")
    
    async def get_alert_history(
        self,
        phone_number: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get alert history, optionally filtered by phone number."""
        try:
            query = {"phone_number": phone_number} if phone_number else {}
            cursor = self.alert_logs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Failed to get alert history: {e}")
            return []
    
    # ==================== SCHEDULED TASK ====================
    
    async def _run_scheduled_check(self):
        """Background task that periodically checks for alerts."""
        logger.info(f"Alert scheduler started (interval: {self.check_interval}s)")
        
        while self._running:
            try:
                # Get all property alerts
                all_alerts = await self.check_all_properties()
                
                if all_alerts:
                    # Get active subscribers
                    subscribers = await self.get_all_active_subscriptions()
                    
                    for sub in subscribers:
                        phone = sub["phone_number"]
                        sub_property_ids = sub.get("property_ids")
                        sub_alert_types = sub.get("alert_types", [])
                        
                        # Filter alerts for this subscriber
                        subscriber_alerts = []
                        for prop_id, alerts in all_alerts.items():
                            # Check if subscriber is interested in this property
                            if sub_property_ids is None or prop_id in sub_property_ids:
                                for alert in alerts:
                                    # Check if subscriber wants this alert type
                                    if alert["type"] in sub_alert_types:
                                        subscriber_alerts.append(alert)
                        
                        # Send alerts
                        if subscriber_alerts:
                            await self.send_alerts_to_subscriber(phone, subscriber_alerts)
                            logger.info(f"Sent {len(subscriber_alerts)} alerts to {phone[:8]}...")
                
                logger.info(f"Alert check completed. Properties with alerts: {len(all_alerts)}")
                
            except Exception as e:
                logger.error(f"Error in scheduled alert check: {e}")
            
            # Wait for next check interval
            await asyncio.sleep(self.check_interval)
    
    def start(self):
        """Start the scheduled alert checker."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run_scheduled_check())
            logger.info("Alert scheduler started")
    
    def stop(self):
        """Stop the scheduled alert checker."""
        self._running = False
        if self._task:
            self._task.cancel()
            logger.info("Alert scheduler stopped")
    
    @property
    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self._running


# Global instance (initialized in server.py)
alert_scheduler: Optional[AlertScheduler] = None


def init_alert_scheduler(
    db: AsyncIOMotorDatabase,
    whatsapp_service,
    property_store,
    intelligence_engine,
    check_interval: int = 1800
) -> AlertScheduler:
    """Initialize the global alert scheduler."""
    global alert_scheduler
    alert_scheduler = AlertScheduler(
        db=db,
        whatsapp_service=whatsapp_service,
        property_store=property_store,
        intelligence_engine=intelligence_engine,
        check_interval=check_interval
    )
    return alert_scheduler
