"""
User Change Log Service
Tracks all user changes with full audit trail
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
import uuid

logger = logging.getLogger(__name__)


class ChangeLogService:
    """
    Manages change logging for audit trail and history.
    Tracks all mutations with user_id, timestamps, and field-level changes.
    """
    
    COLLECTION_NAME = "user_change_log"
    SESSION_COLLECTION = "user_sessions"
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db[self.COLLECTION_NAME]
        self.sessions = db[self.SESSION_COLLECTION]
    
    async def ensure_indexes(self):
        """Create necessary indexes for efficient querying."""
        try:
            # Change log indexes
            await self.collection.create_index("user_id")
            await self.collection.create_index("entity_type")
            await self.collection.create_index("entity_id")
            await self.collection.create_index("timestamp")
            await self.collection.create_index("session_id")
            await self.collection.create_index([("user_id", 1), ("timestamp", -1)])
            await self.collection.create_index([("user_id", 1), ("entity_type", 1), ("entity_id", 1)])
            
            # Session indexes
            await self.sessions.create_index("user_id")
            await self.sessions.create_index("session_id", unique=True)
            await self.sessions.create_index([("user_id", 1), ("started_at", -1)])
            
            logger.info("Change log indexes created")
        except Exception as e:
            logger.error(f"Failed to create change log indexes: {e}")
    
    async def log_change(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        field: str,
        old_value: Any,
        new_value: Any,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log a single field change.
        
        Args:
            user_id: The user making the change
            entity_type: Type of entity (e.g., 'property_state', 'simulation', 'alert')
            entity_id: ID of the entity being changed
            field: The field being changed
            old_value: Previous value
            new_value: New value
            session_id: Optional session identifier
            metadata: Additional context (device, IP, etc.)
        
        Returns:
            Dict with change_id and status
        """
        try:
            change_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            change_doc = {
                "change_id": change_id,
                "user_id": user_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "field": field,
                "old_value": self._serialize_value(old_value),
                "new_value": self._serialize_value(new_value),
                "timestamp": now,
                "timestamp_iso": now.isoformat(),
                "session_id": session_id,
                "metadata": metadata or {}
            }
            
            await self.collection.insert_one(change_doc)
            
            logger.info(f"Change logged: {entity_type}/{entity_id}.{field} by {user_id}")
            
            return {
                "success": True,
                "change_id": change_id,
                "timestamp": now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to log change: {e}")
            return {"success": False, "error": str(e)}
    
    async def log_changes_batch(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        changes: Dict[str, tuple],  # field: (old_value, new_value)
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log multiple field changes in a single batch.
        
        Args:
            changes: Dict mapping field names to (old_value, new_value) tuples
        """
        try:
            batch_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            change_docs = []
            for field, (old_value, new_value) in changes.items():
                change_docs.append({
                    "change_id": str(uuid.uuid4()),
                    "batch_id": batch_id,
                    "user_id": user_id,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "field": field,
                    "old_value": self._serialize_value(old_value),
                    "new_value": self._serialize_value(new_value),
                    "timestamp": now,
                    "timestamp_iso": now.isoformat(),
                    "session_id": session_id,
                    "metadata": metadata or {}
                })
            
            if change_docs:
                await self.collection.insert_many(change_docs)
                logger.info(f"Batch logged: {len(change_docs)} changes for {entity_type}/{entity_id}")
            
            return {
                "success": True,
                "batch_id": batch_id,
                "changes_logged": len(change_docs),
                "timestamp": now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to log batch changes: {e}")
            return {"success": False, "error": str(e)}
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize value for MongoDB storage."""
        if isinstance(value, (list, dict, str, int, float, bool, type(None))):
            return value
        elif isinstance(value, datetime):
            return value.isoformat()
        else:
            return str(value)
    
    async def get_user_changes(
        self,
        user_id: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get changes made by a user with optional filters.
        """
        try:
            query = {"user_id": user_id}
            
            if entity_type:
                query["entity_type"] = entity_type
            if entity_id:
                query["entity_id"] = entity_id
            if session_id:
                query["session_id"] = session_id
            
            cursor = self.collection.find(
                query,
                {"_id": 0}
            ).sort("timestamp", -1).skip(skip).limit(limit)
            
            return await cursor.to_list(length=limit)
            
        except Exception as e:
            logger.error(f"Failed to get user changes: {e}")
            return []
    
    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get complete change history for an entity."""
        try:
            cursor = self.collection.find(
                {"entity_type": entity_type, "entity_id": entity_id},
                {"_id": 0}
            ).sort("timestamp", -1).limit(limit)
            
            return await cursor.to_list(length=limit)
            
        except Exception as e:
            logger.error(f"Failed to get entity history: {e}")
            return []
    
    async def get_changes_by_session(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """Get all changes from a specific session."""
        try:
            cursor = self.collection.find(
                {"session_id": session_id},
                {"_id": 0}
            ).sort("timestamp", 1)
            
            return await cursor.to_list(length=1000)
            
        except Exception as e:
            logger.error(f"Failed to get session changes: {e}")
            return []
    
    async def get_user_sessions(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get list of user's previous sessions."""
        try:
            cursor = self.sessions.find(
                {"user_id": user_id},
                {"_id": 0}
            ).sort("started_at", -1).limit(limit)
            
            return await cursor.to_list(length=limit)
            
        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
            return []
    
    # ==================== SESSION MANAGEMENT ====================
    
    async def create_session(
        self,
        user_id: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new user session for change tracking."""
        try:
            session_id = f"session_{uuid.uuid4().hex[:16]}"
            now = datetime.now(timezone.utc)
            
            session_doc = {
                "session_id": session_id,
                "user_id": user_id,
                "started_at": now,
                "started_at_iso": now.isoformat(),
                "last_activity": now,
                "device_info": device_info,
                "ip_address": ip_address,
                "changes_count": 0,
                "active": True
            }
            
            await self.sessions.insert_one(session_doc)
            
            logger.info(f"Session created: {session_id} for user {user_id}")
            
            return {
                "success": True,
                "session_id": session_id,
                "started_at": now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_session_activity(
        self,
        session_id: str,
        increment_changes: bool = True
    ):
        """Update session last activity timestamp."""
        try:
            update = {
                "$set": {"last_activity": datetime.now(timezone.utc)}
            }
            
            if increment_changes:
                update["$inc"] = {"changes_count": 1}
            
            await self.sessions.update_one(
                {"session_id": session_id},
                update
            )
            
        except Exception as e:
            logger.error(f"Failed to update session: {e}")
    
    async def end_session(self, session_id: str):
        """Mark a session as ended."""
        try:
            await self.sessions.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "active": False,
                        "ended_at": datetime.now(timezone.utc)
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to end session: {e}")
    
    async def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of a session including all changes."""
        try:
            session = await self.sessions.find_one(
                {"session_id": session_id},
                {"_id": 0}
            )
            
            if not session:
                return {"error": "Session not found"}
            
            changes = await self.get_changes_by_session(session_id)
            
            # Group changes by entity
            entities_modified = {}
            for change in changes:
                key = f"{change['entity_type']}/{change['entity_id']}"
                if key not in entities_modified:
                    entities_modified[key] = []
                entities_modified[key].append(change['field'])
            
            return {
                **session,
                "changes": changes,
                "entities_modified": entities_modified,
                "total_changes": len(changes)
            }
            
        except Exception as e:
            logger.error(f"Failed to get session summary: {e}")
            return {"error": str(e)}
    
    async def get_change_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about user's changes."""
        try:
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": "$entity_type",
                    "count": {"$sum": 1},
                    "last_change": {"$max": "$timestamp"}
                }}
            ]
            
            results = await self.collection.aggregate(pipeline).to_list(length=100)
            
            total_changes = sum(r["count"] for r in results)
            
            return {
                "user_id": user_id,
                "total_changes": total_changes,
                "by_entity_type": {r["_id"]: r["count"] for r in results},
                "last_activity": max((r["last_change"] for r in results), default=None)
            }
            
        except Exception as e:
            logger.error(f"Failed to get change stats: {e}")
            return {"error": str(e)}


# Global instance
change_log_service: Optional[ChangeLogService] = None


def init_change_log_service(db: AsyncIOMotorDatabase) -> ChangeLogService:
    """Initialize the global change log service."""
    global change_log_service
    change_log_service = ChangeLogService(db)
    return change_log_service
