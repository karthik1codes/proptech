"""
WhatsApp User Linking Service
Manages WhatsApp phone number to Google account mapping with OTP verification
"""

import os
import random
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class WhatsAppLinkingService:
    """
    Manages WhatsApp phone number to user account linking.
    Uses OTP verification via Twilio for security.
    """
    
    MAPPING_COLLECTION = "whatsapp_user_mapping"
    OTP_COLLECTION = "whatsapp_otp_codes"
    OTP_EXPIRY_MINUTES = 10
    
    def __init__(self, db: AsyncIOMotorDatabase, whatsapp_service):
        self.db = db
        self.mappings = db[self.MAPPING_COLLECTION]
        self.otp_codes = db[self.OTP_COLLECTION]
        self.whatsapp_service = whatsapp_service
    
    async def ensure_indexes(self):
        """Create necessary indexes."""
        try:
            await self.mappings.create_index("phone_number", unique=True)
            await self.mappings.create_index("user_id")
            await self.otp_codes.create_index("phone_number")
            await self.otp_codes.create_index("expires_at", expireAfterSeconds=0)
            logger.info("WhatsApp linking indexes created")
        except Exception as e:
            logger.error(f"Failed to create linking indexes: {e}")
    
    def generate_otp(self) -> str:
        """Generate a 6-digit OTP code."""
        return str(random.randint(100000, 999999))
    
    async def initiate_linking(
        self,
        user_id: str,
        phone_number: str,
        user_name: str = "User"
    ) -> Dict[str, Any]:
        """
        Initiate WhatsApp linking by sending OTP.
        
        Args:
            user_id: The authenticated user's ID
            phone_number: Phone number to link (E.164 format)
            user_name: User's name for personalization
        """
        if not phone_number.startswith("+"):
            return {"success": False, "error": "Phone number must be in E.164 format (+XXX...)"}
        
        # Check if already linked to another user
        existing = await self.mappings.find_one({"phone_number": phone_number})
        if existing and existing.get("user_id") != user_id:
            return {
                "success": False,
                "error": "This phone number is already linked to another account"
            }
        
        # Generate OTP
        otp_code = self.generate_otp()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.OTP_EXPIRY_MINUTES)
        
        try:
            # Store OTP
            await self.otp_codes.update_one(
                {"phone_number": phone_number},
                {
                    "$set": {
                        "phone_number": phone_number,
                        "user_id": user_id,
                        "otp_code": otp_code,
                        "expires_at": expires_at,
                        "created_at": datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
            
            # Send OTP via WhatsApp
            message = f"""🔐 *PropTech Copilot - Verification Code*

Hi {user_name}!

Your verification code is: *{otp_code}*

This code expires in {self.OTP_EXPIRY_MINUTES} minutes.

If you didn't request this, please ignore this message."""

            result = self.whatsapp_service.send_whatsapp_message(phone_number, message)
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to send OTP: {result.get('error', 'Unknown error')}"
                }
            
            logger.info(f"OTP sent to {phone_number[:8]}... for user {user_id}")
            
            return {
                "success": True,
                "message": "Verification code sent to your WhatsApp",
                "expires_in_minutes": self.OTP_EXPIRY_MINUTES
            }
            
        except Exception as e:
            logger.error(f"Failed to initiate linking: {e}")
            return {"success": False, "error": str(e)}
    
    async def verify_otp(
        self,
        user_id: str,
        phone_number: str,
        otp_code: str
    ) -> Dict[str, Any]:
        """
        Verify OTP and complete the linking process.
        """
        try:
            # Find the OTP record
            otp_record = await self.otp_codes.find_one({
                "phone_number": phone_number,
                "user_id": user_id
            })
            
            if not otp_record:
                return {"success": False, "error": "No pending verification for this number"}
            
            # Check expiry
            expires_at = otp_record.get("expires_at")
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if datetime.now(timezone.utc) > expires_at:
                await self.otp_codes.delete_one({"phone_number": phone_number})
                return {"success": False, "error": "Verification code expired. Please request a new one."}
            
            # Verify OTP
            if otp_record.get("otp_code") != otp_code:
                return {"success": False, "error": "Invalid verification code"}
            
            # Create/update mapping
            await self.mappings.update_one(
                {"phone_number": phone_number},
                {
                    "$set": {
                        "phone_number": phone_number,
                        "user_id": user_id,
                        "linked_at": datetime.now(timezone.utc),
                        "verified": True
                    }
                },
                upsert=True
            )
            
            # Delete OTP record
            await self.otp_codes.delete_one({"phone_number": phone_number})
            
            # Send confirmation
            self.whatsapp_service.send_whatsapp_message(
                phone_number,
                """✅ *WhatsApp Linked Successfully!*

Your WhatsApp is now connected to your PropTech Copilot account.

You can now:
• Control floor closures
• Run simulations
• View analytics
• Download reports
• Receive alerts

Type *help* to see all commands."""
            )
            
            logger.info(f"WhatsApp linked: {phone_number[:8]}... -> user {user_id}")
            
            return {
                "success": True,
                "message": "WhatsApp successfully linked to your account"
            }
            
        except Exception as e:
            logger.error(f"Failed to verify OTP: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_user_by_phone(self, phone_number: str) -> Optional[str]:
        """
        Get user_id for a phone number.
        Returns None if not linked.
        """
        try:
            # Normalize phone number
            if not phone_number.startswith("+"):
                phone_number = f"+{phone_number}"
            phone_number = phone_number.replace("whatsapp:", "")
            
            mapping = await self.mappings.find_one(
                {"phone_number": phone_number, "verified": True}
            )
            
            if mapping:
                return mapping.get("user_id")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user by phone: {e}")
            return None
    
    async def get_phone_by_user(self, user_id: str) -> Optional[str]:
        """Get linked phone number for a user."""
        try:
            mapping = await self.mappings.find_one(
                {"user_id": user_id, "verified": True}
            )
            
            if mapping:
                return mapping.get("phone_number")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get phone by user: {e}")
            return None
    
    async def unlink_phone(self, user_id: str) -> Dict[str, Any]:
        """Unlink a phone number from a user account."""
        try:
            result = await self.mappings.delete_one({"user_id": user_id})
            
            if result.deleted_count > 0:
                logger.info(f"WhatsApp unlinked for user {user_id}")
                return {"success": True, "message": "WhatsApp number unlinked"}
            else:
                return {"success": False, "error": "No linked phone number found"}
            
        except Exception as e:
            logger.error(f"Failed to unlink phone: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_linking_status(self, user_id: str) -> Dict[str, Any]:
        """Get WhatsApp linking status for a user."""
        try:
            mapping = await self.mappings.find_one(
                {"user_id": user_id},
                {"_id": 0}
            )
            
            if mapping and mapping.get("verified"):
                return {
                    "linked": True,
                    "phone_number": mapping.get("phone_number"),
                    "linked_at": mapping.get("linked_at")
                }
            else:
                return {"linked": False}
            
        except Exception as e:
            logger.error(f"Failed to get linking status: {e}")
            return {"linked": False, "error": str(e)}


# Global instance
whatsapp_linking_service: Optional[WhatsAppLinkingService] = None


def init_whatsapp_linking_service(
    db: AsyncIOMotorDatabase,
    whatsapp_service
) -> WhatsAppLinkingService:
    """Initialize the global WhatsApp linking service."""
    global whatsapp_linking_service
    whatsapp_linking_service = WhatsAppLinkingService(db, whatsapp_service)
    return whatsapp_linking_service
