"""
User Property State Service
Manages per-user optimization state with MongoDB persistence
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class UserPropertyStateService:
    """
    Manages per-user property optimization states.
    Ensures multi-user isolation - each user sees only their own overrides.
    """
    
    COLLECTION_NAME = "user_property_states"
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db[self.COLLECTION_NAME]
    
    async def ensure_indexes(self):
        """Create necessary indexes for efficient querying."""
        try:
            await self.collection.create_index([("user_id", 1), ("property_id", 1)], unique=True)
            await self.collection.create_index("user_id")
            await self.collection.create_index("property_id")
            await self.collection.create_index("updated_at")
            logger.info("User property state indexes created")
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    async def get_user_state(
        self,
        user_id: str,
        property_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user's optimization state for a property.
        Returns None if no override exists.
        """
        try:
            state = await self.collection.find_one(
                {"user_id": user_id, "property_id": property_id},
                {"_id": 0}
            )
            return state
        except Exception as e:
            logger.error(f"Failed to get user state: {e}")
            return None
    
    async def get_all_user_states(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all property states for a user."""
        try:
            cursor = self.collection.find({"user_id": user_id}, {"_id": 0})
            return await cursor.to_list(length=100)
        except Exception as e:
            logger.error(f"Failed to get user states: {e}")
            return []
    
    async def set_closed_floors(
        self,
        user_id: str,
        property_id: str,
        closed_floors: List[int]
    ) -> Dict[str, Any]:
        """
        Set closed floors for a user's property state.
        Creates new state if doesn't exist, updates if exists.
        """
        try:
            now = datetime.now(timezone.utc)
            
            result = await self.collection.update_one(
                {"user_id": user_id, "property_id": property_id},
                {
                    "$set": {
                        "closed_floors": closed_floors,
                        "updated_at": now
                    },
                    "$setOnInsert": {
                        "user_id": user_id,
                        "property_id": property_id,
                        "hybrid_intensity": 1.0,
                        "target_occupancy": None,
                        "last_simulation_result": None,
                        "created_at": now
                    }
                },
                upsert=True
            )
            
            logger.info(f"User {user_id} set closed floors {closed_floors} for {property_id}")
            
            return {
                "success": True,
                "user_id": user_id,
                "property_id": property_id,
                "closed_floors": closed_floors
            }
            
        except Exception as e:
            logger.error(f"Failed to set closed floors: {e}")
            return {"success": False, "error": str(e)}
    
    async def open_floors(
        self,
        user_id: str,
        property_id: str,
        floors_to_open: List[int]
    ) -> Dict[str, Any]:
        """Remove specific floors from closed floors list."""
        try:
            state = await self.get_user_state(user_id, property_id)
            
            if not state:
                return {
                    "success": True,
                    "message": "No closed floors to open",
                    "closed_floors": []
                }
            
            current_closed = state.get("closed_floors", [])
            new_closed = [f for f in current_closed if f not in floors_to_open]
            
            return await self.set_closed_floors(user_id, property_id, new_closed)
            
        except Exception as e:
            logger.error(f"Failed to open floors: {e}")
            return {"success": False, "error": str(e)}
    
    async def close_floors(
        self,
        user_id: str,
        property_id: str,
        floors_to_close: List[int]
    ) -> Dict[str, Any]:
        """Add specific floors to closed floors list."""
        try:
            state = await self.get_user_state(user_id, property_id)
            
            current_closed = state.get("closed_floors", []) if state else []
            new_closed = list(set(current_closed + floors_to_close))
            new_closed.sort()
            
            return await self.set_closed_floors(user_id, property_id, new_closed)
            
        except Exception as e:
            logger.error(f"Failed to close floors: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_simulation_params(
        self,
        user_id: str,
        property_id: str,
        hybrid_intensity: Optional[float] = None,
        target_occupancy: Optional[float] = None
    ) -> Dict[str, Any]:
        """Update simulation parameters for a user's property state."""
        try:
            update_fields = {"updated_at": datetime.now(timezone.utc)}
            
            if hybrid_intensity is not None:
                update_fields["hybrid_intensity"] = hybrid_intensity
            if target_occupancy is not None:
                update_fields["target_occupancy"] = target_occupancy
            
            await self.collection.update_one(
                {"user_id": user_id, "property_id": property_id},
                {"$set": update_fields},
                upsert=True
            )
            
            return {"success": True, "updated": update_fields}
            
        except Exception as e:
            logger.error(f"Failed to update simulation params: {e}")
            return {"success": False, "error": str(e)}
    
    async def save_simulation_result(
        self,
        user_id: str,
        property_id: str,
        simulation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save last simulation result for a user's property."""
        try:
            await self.collection.update_one(
                {"user_id": user_id, "property_id": property_id},
                {
                    "$set": {
                        "last_simulation_result": simulation_result,
                        "updated_at": datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Failed to save simulation result: {e}")
            return {"success": False, "error": str(e)}
    
    async def reset_property_state(
        self,
        user_id: str,
        property_id: str
    ) -> Dict[str, Any]:
        """Reset user's property state to defaults (removes override)."""
        try:
            result = await self.collection.delete_one(
                {"user_id": user_id, "property_id": property_id}
            )
            
            if result.deleted_count > 0:
                logger.info(f"User {user_id} reset state for {property_id}")
                return {"success": True, "message": "Property state reset to default"}
            else:
                return {"success": True, "message": "No override state existed"}
            
        except Exception as e:
            logger.error(f"Failed to reset property state: {e}")
            return {"success": False, "error": str(e)}
    
    async def reset_all_user_states(self, user_id: str) -> Dict[str, Any]:
        """Reset all property states for a user."""
        try:
            result = await self.collection.delete_many({"user_id": user_id})
            
            logger.info(f"User {user_id} reset all states ({result.deleted_count} properties)")
            
            return {
                "success": True,
                "properties_reset": result.deleted_count
            }
            
        except Exception as e:
            logger.error(f"Failed to reset all user states: {e}")
            return {"success": False, "error": str(e)}
    
    def apply_override_to_property(
        self,
        property_data: Dict[str, Any],
        user_state: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Apply user's override state to property data.
        Returns modified property data with overrides applied.
        Does NOT modify original data.
        """
        if not user_state:
            return property_data
        
        # Create a copy to avoid modifying original
        modified = property_data.copy()
        
        closed_floors = user_state.get("closed_floors", [])
        
        if closed_floors:
            total_floors = modified.get("floors", 0)
            active_floors = total_floors - len(closed_floors)
            
            # Store override info
            modified["_override"] = {
                "closed_floors": closed_floors,
                "active_floors": active_floors,
                "original_floors": total_floors,
                "hybrid_intensity": user_state.get("hybrid_intensity", 1.0),
                "target_occupancy": user_state.get("target_occupancy")
            }
        
        return modified


# Global instance (initialized in server.py)
user_state_service: Optional[UserPropertyStateService] = None


def init_user_state_service(db: AsyncIOMotorDatabase) -> UserPropertyStateService:
    """Initialize the global user state service."""
    global user_state_service
    user_state_service = UserPropertyStateService(db)
    return user_state_service
