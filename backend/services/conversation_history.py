"""
Conversation History Module for PropTech WhatsApp Integration
Persists chat history to MongoDB for context and analytics
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class ConversationHistory:
    """
    Manages conversation history persistence in MongoDB.
    Enables context-aware responses and conversation analytics.
    """
    
    COLLECTION_NAME = "whatsapp_conversations"
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db[self.COLLECTION_NAME]
    
    async def ensure_indexes(self):
        """Create necessary indexes for efficient querying."""
        try:
            await self.collection.create_index("phone_number")
            await self.collection.create_index("created_at")
            await self.collection.create_index([("phone_number", 1), ("created_at", -1)])
            logger.info("Conversation history indexes created")
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    async def add_message(
        self,
        phone_number: str,
        direction: str,  # "inbound" or "outbound"
        message_body: str,
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a message to conversation history.
        
        Args:
            phone_number: User's phone number (E.164 format)
            direction: "inbound" (from user) or "outbound" (to user)
            message_body: The message content
            message_type: Type of message (text, alert, template)
            metadata: Additional metadata (property_id, command, etc.)
        """
        try:
            message_doc = {
                "phone_number": phone_number,
                "direction": direction,
                "message_body": message_body,
                "message_type": message_type,
                "metadata": metadata or {},
                "created_at": datetime.now(timezone.utc),
                "timestamp_iso": datetime.now(timezone.utc).isoformat()
            }
            
            result = await self.collection.insert_one(message_doc)
            
            logger.info(f"Message saved: {direction} - {phone_number[:8]}...")
            
            return {
                "success": True,
                "message_id": str(result.inserted_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_conversation(
        self,
        phone_number: str,
        limit: int = 20,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history for a phone number.
        
        Args:
            phone_number: User's phone number
            limit: Maximum messages to return
            since: Only return messages after this timestamp
        """
        try:
            query = {"phone_number": phone_number}
            
            if since:
                query["created_at"] = {"$gte": since}
            
            cursor = self.collection.find(
                query,
                {"_id": 0}
            ).sort("created_at", -1).limit(limit)
            
            messages = await cursor.to_list(length=limit)
            
            # Reverse to get chronological order
            return list(reversed(messages))
            
        except Exception as e:
            logger.error(f"Failed to get conversation: {e}")
            return []
    
    async def get_last_message(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get the most recent message for a phone number."""
        try:
            message = await self.collection.find_one(
                {"phone_number": phone_number},
                {"_id": 0},
                sort=[("created_at", -1)]
            )
            return message
        except Exception as e:
            logger.error(f"Failed to get last message: {e}")
            return None
    
    async def get_context(self, phone_number: str, messages_count: int = 5) -> str:
        """
        Get conversation context as a formatted string.
        Useful for providing context to AI responses.
        """
        messages = await self.get_conversation(phone_number, limit=messages_count)
        
        if not messages:
            return "No previous conversation history."
        
        context_lines = []
        for msg in messages:
            direction = "User" if msg["direction"] == "inbound" else "Bot"
            context_lines.append(f"{direction}: {msg['message_body'][:100]}...")
        
        return "\n".join(context_lines)
    
    async def get_user_stats(self, phone_number: str) -> Dict[str, Any]:
        """Get statistics for a user's conversations."""
        try:
            pipeline = [
                {"$match": {"phone_number": phone_number}},
                {"$group": {
                    "_id": "$phone_number",
                    "total_messages": {"$sum": 1},
                    "inbound_count": {
                        "$sum": {"$cond": [{"$eq": ["$direction", "inbound"]}, 1, 0]}
                    },
                    "outbound_count": {
                        "$sum": {"$cond": [{"$eq": ["$direction", "outbound"]}, 1, 0]}
                    },
                    "first_message": {"$min": "$created_at"},
                    "last_message": {"$max": "$created_at"}
                }}
            ]
            
            result = await self.collection.aggregate(pipeline).to_list(length=1)
            
            if result:
                stats = result[0]
                return {
                    "phone_number": phone_number,
                    "total_messages": stats["total_messages"],
                    "messages_sent": stats["inbound_count"],
                    "messages_received": stats["outbound_count"],
                    "first_interaction": stats["first_message"].isoformat() if stats["first_message"] else None,
                    "last_interaction": stats["last_message"].isoformat() if stats["last_message"] else None
                }
            
            return {"phone_number": phone_number, "total_messages": 0}
            
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return {"phone_number": phone_number, "error": str(e)}
    
    async def search_conversations(
        self,
        query_text: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search conversations by message content."""
        try:
            cursor = self.collection.find(
                {"message_body": {"$regex": query_text, "$options": "i"}},
                {"_id": 0}
            ).sort("created_at", -1).limit(limit)
            
            return await cursor.to_list(length=limit)
            
        except Exception as e:
            logger.error(f"Failed to search conversations: {e}")
            return []
    
    async def clear_old_messages(self, days_to_keep: int = 90) -> int:
        """Remove messages older than specified days."""
        try:
            from datetime import timedelta
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            result = await self.collection.delete_many(
                {"created_at": {"$lt": cutoff_date}}
            )
            
            logger.info(f"Cleared {result.deleted_count} old messages")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Failed to clear old messages: {e}")
            return 0
