from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Form
from fastapi.responses import JSONResponse, PlainTextResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import random
import math

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import WhatsApp service and related modules
from services.whatsapp_service import whatsapp_service, WhatsAppService, MessageTemplates
from services.conversation_history import ConversationHistory
from services.alert_scheduler import AlertScheduler, init_alert_scheduler
from services.user_state_service import UserPropertyStateService, init_user_state_service, set_change_log_service
from services.whatsapp_linking_service import WhatsAppLinkingService, init_whatsapp_linking_service
from services.command_parser import CommandParser, CommandIntent, ParsedCommand, init_command_parser
from services.pdf_generator import PDFReportGenerator, init_pdf_generator
from services.change_log_service import ChangeLogService, init_change_log_service
from services.ai_risk_service import (
    ai_risk_service, 
    get_carbon_factor, 
    get_location_risks,
    calculate_adjusted_carbon,
    LOCATION_DATA
)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize conversation history
conversation_history = ConversationHistory(db)

# Initialize user state service
user_state_service = init_user_state_service(db)

# Create the main app
app = FastAPI(title="Infranomic Decision Copilot API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== IN-MEMORY PROPERTY STORE ====================

class PropertyStore:
    def __init__(self):
        self.properties: Dict[str, Dict] = {}
        self._initialize_default_properties()
    
    def _initialize_default_properties(self):
        """Initialize 3 default realistic properties with digital twin data"""
        default_properties = [
            {
                "property_id": "prop_001",
                "name": "Horizon Tech Park",
                "type": "Commercial Office",
                "location": "Bangalore, Karnataka",
                "floors": 8,
                "rooms_per_floor": 12,
                "revenue_per_seat": 2500,
                "energy_cost_per_unit": 8.5,
                "maintenance_per_floor": 45000,
                "baseline_energy_intensity": 150,
                "total_capacity": 960,
            },
            {
                "property_id": "prop_002",
                "name": "Marina Business Center",
                "type": "Co-Working Space",
                "location": "Mumbai, Maharashtra",
                "floors": 5,
                "rooms_per_floor": 20,
                "revenue_per_seat": 3200,
                "energy_cost_per_unit": 9.2,
                "maintenance_per_floor": 62000,
                "baseline_energy_intensity": 180,
                "total_capacity": 800,
            },
            {
                "property_id": "prop_003",
                "name": "Digital Gateway Tower",
                "type": "IT Park",
                "location": "Hyderabad, Telangana",
                "floors": 12,
                "rooms_per_floor": 15,
                "revenue_per_seat": 2800,
                "energy_cost_per_unit": 7.8,
                "maintenance_per_floor": 52000,
                "baseline_energy_intensity": 165,
                "total_capacity": 1800,
            }
        ]
        
        for prop in default_properties:
            prop["digital_twin"] = self._generate_digital_twin(prop)
            prop["created_at"] = datetime.now(timezone.utc).isoformat()
            self.properties[prop["property_id"]] = prop
    
    def _generate_digital_twin(self, prop: Dict) -> Dict:
        """Generate 90-day digital twin data for a property"""
        floors = prop["floors"]
        rooms_per_floor = prop["rooms_per_floor"]
        baseline_energy = prop["baseline_energy_intensity"]
        
        daily_data = []
        floor_data = []
        
        # Generate floor-level data
        for floor_num in range(1, floors + 1):
            rooms = []
            for room_num in range(1, rooms_per_floor + 1):
                capacity = random.choice([8, 10, 12, 15, 20])
                room_type = random.choice(["Conference", "Open Desk", "Private Office", "Hot Desk", "Meeting Room"])
                rooms.append({
                    "room_id": f"F{floor_num}R{room_num}",
                    "room_type": room_type,
                    "capacity": capacity,
                    "current_occupancy": 0,
                })
            
            floor_data.append({
                "floor_number": floor_num,
                "rooms": rooms,
                "total_capacity": sum(r["capacity"] for r in rooms),
                "is_active": True,
            })
        
        # Generate 90-day historical data
        base_date = datetime.now(timezone.utc) - timedelta(days=90)
        
        for day_offset in range(90):
            current_date = base_date + timedelta(days=day_offset)
            day_of_week = current_date.weekday()
            
            if day_of_week < 5:
                base_occupancy = random.uniform(0.65, 0.85)
                if day_of_week == 4:
                    base_occupancy *= 0.85
            else:
                base_occupancy = random.uniform(0.15, 0.35)
            
            is_event_day = random.random() < 0.1
            if is_event_day:
                base_occupancy = min(base_occupancy * 1.25, 0.98)
            
            occupancy_rate = base_occupancy + random.uniform(-0.05, 0.05)
            occupancy_rate = max(0.1, min(0.98, occupancy_rate))
            
            energy_usage = baseline_energy * occupancy_rate * (1 + random.uniform(-0.1, 0.1))
            booking_count = int(rooms_per_floor * floors * occupancy_rate * random.uniform(0.8, 1.2))
            
            daily_data.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "occupancy_rate": round(occupancy_rate, 3),
                "energy_usage": round(energy_usage, 2),
                "booking_count": booking_count,
                "is_event_day": is_event_day,
                "day_of_week": day_of_week,
            })
        
        recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7
        for floor in floor_data:
            for room in floor["rooms"]:
                room["current_occupancy"] = int(room["capacity"] * recent_occupancy * random.uniform(0.8, 1.2))
                room["current_occupancy"] = min(room["current_occupancy"], room["capacity"])
        
        return {
            "floor_data": floor_data,
            "daily_history": daily_data,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    
    def get_all(self) -> List[Dict]:
        return list(self.properties.values())
    
    def get_by_id(self, property_id: str) -> Optional[Dict]:
        return self.properties.get(property_id)
    
    def add_property(self, prop_data: Dict) -> Dict:
        property_id = f"prop_{uuid.uuid4().hex[:8]}"
        prop_data["property_id"] = property_id
        prop_data["total_capacity"] = prop_data["floors"] * prop_data["rooms_per_floor"] * 10
        prop_data["digital_twin"] = self._generate_digital_twin(prop_data)
        prop_data["created_at"] = datetime.now(timezone.utc).isoformat()
        self.properties[property_id] = prop_data
        return prop_data

# Initialize property store
property_store = PropertyStore()


# ==================== INTELLIGENCE ENGINE ====================

class IntelligenceEngine:
    @staticmethod
    def calculate_7day_forecast(daily_data: List[Dict]) -> List[Dict]:
        if len(daily_data) < 14:
            return []
        
        weekday_averages = {}
        for d in daily_data[-30:]:
            dow = d["day_of_week"]
            if dow not in weekday_averages:
                weekday_averages[dow] = []
            weekday_averages[dow].append(d["occupancy_rate"])
        
        for dow in weekday_averages:
            weekday_averages[dow] = sum(weekday_averages[dow]) / len(weekday_averages[dow])
        
        forecast = []
        last_date = datetime.strptime(daily_data[-1]["date"], "%Y-%m-%d")
        
        for i in range(1, 8):
            forecast_date = last_date + timedelta(days=i)
            dow = forecast_date.weekday()
            base_forecast = weekday_averages.get(dow, 0.5)
            
            forecasted_occupancy = base_forecast * random.uniform(0.95, 1.05)
            forecasted_occupancy = max(0.1, min(0.95, forecasted_occupancy))
            
            forecast.append({
                "date": forecast_date.strftime("%Y-%m-%d"),
                "forecasted_occupancy": round(forecasted_occupancy, 3),
                "confidence": round(0.85 - (i * 0.02), 2),
            })
        
        return forecast
    
    @staticmethod
    def classify_utilization(occupancy_rate: float) -> str:
        if occupancy_rate < 0.4:
            return "Underutilized"
        elif occupancy_rate <= 0.85:
            return "Optimal"
        else:
            return "Overloaded"
    
    @staticmethod
    def calculate_financials(prop: Dict, occupancy_rate: float) -> Dict:
        total_capacity = prop.get("total_capacity", prop["floors"] * prop["rooms_per_floor"] * 10)
        occupied_seats = int(total_capacity * occupancy_rate)
        
        revenue = occupied_seats * prop["revenue_per_seat"]
        energy_cost = prop["baseline_energy_intensity"] * occupancy_rate * prop["energy_cost_per_unit"] * prop["floors"]
        maintenance_cost = prop["floors"] * prop["maintenance_per_floor"]
        profit = revenue - energy_cost - maintenance_cost
        
        return {
            "revenue": round(revenue, 2),
            "energy_cost": round(energy_cost, 2),
            "maintenance_cost": round(maintenance_cost, 2),
            "profit": round(profit, 2),
            "occupied_seats": occupied_seats,
            "total_capacity": total_capacity,
        }
    
    @staticmethod
    def calculate_sustainability_score(prop: Dict, occupancy_rate: float) -> float:
        energy_efficiency = 100 - (prop["baseline_energy_intensity"] / 2)
        sustainability_score = energy_efficiency * 0.4 + (1 - occupancy_rate * 0.3) * 100 * 0.3 + 50 * 0.3
        return round(sustainability_score, 1)
    
    @staticmethod
    def calculate_efficiency_score(prop: Dict) -> float:
        digital_twin = prop.get("digital_twin", {})
        floor_data = digital_twin.get("floor_data", [])
        total_floors = prop["floors"]
        
        optimal_floors = 0
        for f in floor_data:
            floor_capacity = sum(r["capacity"] for r in f["rooms"])
            floor_occupancy = sum(r["current_occupancy"] for r in f["rooms"])
            floor_rate = floor_occupancy / floor_capacity if floor_capacity > 0 else 0
            if 0.4 <= floor_rate <= 0.85:
                optimal_floors += 1
        
        return round((optimal_floors / total_floors) * 100, 1) if total_floors > 0 else 0
    
    @staticmethod
    def calculate_carbon_estimate(prop: Dict, occupancy_rate: float) -> float:
        carbon_per_kwh = 0.82
        return round(prop["baseline_energy_intensity"] * occupancy_rate * prop["floors"] * carbon_per_kwh * 30, 2)
    
    @staticmethod
    def calculate_energy_savings(prop: Dict, current_occupancy: float, floors_to_close: List[int], 
                                  new_occupancy: float = None) -> Dict:
        floors = prop["floors"]
        baseline_energy = prop["baseline_energy_intensity"]
        energy_cost = prop["energy_cost_per_unit"]
        
        current_energy = baseline_energy * current_occupancy * floors
        current_cost_daily = current_energy * energy_cost
        
        active_floors = floors - len(floors_to_close)
        target_occupancy = new_occupancy if new_occupancy else current_occupancy
        
        if active_floors > 0:
            redistributed_occupancy = min(target_occupancy * floors / active_floors, 0.95)
        else:
            redistributed_occupancy = 0
        
        new_energy = baseline_energy * redistributed_occupancy * active_floors
        new_cost_daily = new_energy * energy_cost
        
        savings_daily = current_cost_daily - new_cost_daily
        
        return {
            "before_energy_usage": round(current_energy, 2),
            "after_energy_usage": round(new_energy, 2),
            "before_cost_daily": round(current_cost_daily, 2),
            "after_cost_daily": round(new_cost_daily, 2),
            "daily_savings": round(savings_daily, 2),
            "weekly_savings": round(savings_daily * 7, 2),
            "monthly_savings": round(savings_daily * 30, 2),
            "energy_reduction_percent": round((1 - new_energy / current_energy) * 100 if current_energy > 0 else 0, 1),
            "redistributed_occupancy": round(redistributed_occupancy, 3),
        }
    
    @staticmethod
    def calculate_redistribution_efficiency(prop: Dict, floors_to_close: List[int]) -> Dict:
        """
        Calculate efficiency metrics when redistributing occupants from closed floors.
        Used by change logging and WhatsApp commands.
        """
        total_floors = prop.get("floors", 8)
        active_floors = total_floors - len(floors_to_close)
        
        if active_floors <= 0:
            return {
                "efficiency": 0,
                "new_avg_occupancy": 0,
                "risk_level": "critical",
                "redistribution_possible": False
            }
        
        # Calculate redistribution
        digital_twin = prop.get("digital_twin", {})
        daily_data = digital_twin.get("daily_history", [])
        recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
        
        # When closing floors, occupants must redistribute to remaining floors
        # New avg occupancy = current occupancy * total floors / active floors
        new_avg_occupancy = recent_occupancy * total_floors / active_floors
        
        # Calculate efficiency (0-1 scale)
        if new_avg_occupancy <= 0.85:
            efficiency = 0.95  # Excellent - room to grow
        elif new_avg_occupancy <= 0.92:
            efficiency = 0.80  # Good - approaching capacity
        elif new_avg_occupancy <= 0.98:
            efficiency = 0.65  # Moderate - near max
        else:
            efficiency = 0.40  # Poor - overcrowded
        
        # Determine risk level
        if new_avg_occupancy > 0.95:
            risk_level = "high"
        elif new_avg_occupancy > 0.85:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "efficiency": efficiency,
            "new_avg_occupancy": round(new_avg_occupancy, 3),
            "risk_level": risk_level,
            "redistribution_possible": new_avg_occupancy < 1.0,
            "floors_closed": len(floors_to_close),
            "active_floors": active_floors
        }
    
    @staticmethod
    def simulate_floor_closure(prop: Dict, floors_to_close: List[int], 
                                hybrid_intensity: float = 1.0, 
                                target_occupancy: float = None) -> Dict:
        digital_twin = prop.get("digital_twin", {})
        daily_data = digital_twin.get("daily_history", [])
        floor_data = digital_twin.get("floor_data", [])
        
        recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
        current_financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
        
        total_floors = prop["floors"]
        optimal_floors = sum(1 for f in floor_data if 0.4 <= (sum(r["current_occupancy"] for r in f["rooms"]) / 
                            sum(r["capacity"] for r in f["rooms"])) <= 0.85) if floor_data else int(total_floors * 0.6)
        current_efficiency_score = round((optimal_floors / total_floors) * 100, 1)
        
        effective_occupancy = target_occupancy if target_occupancy else recent_occupancy * hybrid_intensity
        
        energy_savings = IntelligenceEngine.calculate_energy_savings(
            prop, recent_occupancy, floors_to_close, effective_occupancy
        )
        
        active_floors = total_floors - len(floors_to_close)
        new_financials = IntelligenceEngine.calculate_financials(
            {**prop, "floors": active_floors}, 
            energy_savings["redistributed_occupancy"]
        )
        
        maintenance_savings = len(floors_to_close) * prop["maintenance_per_floor"]
        
        overload_risk = "High" if energy_savings["redistributed_occupancy"] > 0.9 else \
                       "Medium" if energy_savings["redistributed_occupancy"] > 0.8 else "Low"
        
        carbon_per_kwh = 0.82
        carbon_reduction = (energy_savings["before_energy_usage"] - energy_savings["after_energy_usage"]) * carbon_per_kwh * 30
        
        new_optimal_floors = int(active_floors * 0.8)
        new_efficiency_score = round((new_optimal_floors / active_floors) * 100 if active_floors > 0 else 0, 1)
        
        return {
            "scenario_summary": {
                "floors_closed": floors_to_close,
                "active_floors": active_floors,
                "hybrid_intensity": hybrid_intensity,
                "target_occupancy": effective_occupancy,
            },
            "current_state": {
                "occupancy_rate": round(recent_occupancy, 3),
                "efficiency_score": current_efficiency_score,
                **current_financials,
            },
            "projected_state": {
                "occupancy_rate": round(energy_savings["redistributed_occupancy"], 3),
                "efficiency_score": new_efficiency_score,
                **new_financials,
            },
            "savings": {
                "weekly_energy_savings": energy_savings["weekly_savings"],
                "monthly_energy_savings": energy_savings["monthly_savings"],
                "weekly_maintenance_savings": round(maintenance_savings * 7 / 30, 2),
                "monthly_maintenance_savings": maintenance_savings,
                "total_weekly_savings": round(energy_savings["weekly_savings"] + maintenance_savings * 7 / 30, 2),
                "total_monthly_savings": round(energy_savings["monthly_savings"] + maintenance_savings, 2),
            },
            "energy_impact": energy_savings,
            "carbon_impact": {
                "monthly_carbon_reduction_kg": round(carbon_reduction, 2),
                "annual_carbon_reduction_tons": round(carbon_reduction * 12 / 1000, 2),
            },
            "risk_assessment": {
                "overload_risk": overload_risk,
                "redistribution_efficiency": "Good" if energy_savings["redistributed_occupancy"] < 0.85 else "Constrained",
            },
            "efficiency_score_change": {
                "before": current_efficiency_score,
                "after": new_efficiency_score,
                "improvement": round(new_efficiency_score - current_efficiency_score, 1),
            },
        }
    
    @staticmethod
    def generate_recommendations(prop: Dict) -> List[Dict]:
        digital_twin = prop.get("digital_twin", {})
        daily_data = digital_twin.get("daily_history", [])
        
        recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
        utilization = IntelligenceEngine.classify_utilization(recent_occupancy)
        
        recommendations = []
        
        if utilization == "Underutilized":
            floors_to_close = [prop["floors"], prop["floors"] - 1]
            simulation = IntelligenceEngine.simulate_floor_closure(prop, floors_to_close)
            
            recommendations.append({
                "id": f"rec_{uuid.uuid4().hex[:8]}",
                "type": "Floor Consolidation",
                "priority": "High",
                "title": f"Consolidate operations by closing floors {floors_to_close[0]} and {floors_to_close[1]}",
                "description": "Low utilization detected. Consolidating to fewer floors will reduce energy and maintenance costs significantly.",
                "financial_impact": simulation["savings"]["total_monthly_savings"],
                "weekly_energy_savings": simulation["savings"]["weekly_energy_savings"],
                "monthly_energy_savings": simulation["savings"]["monthly_energy_savings"],
                "energy_reduction_percent": simulation["energy_impact"]["energy_reduction_percent"],
                "carbon_reduction_kg": simulation["carbon_impact"]["monthly_carbon_reduction_kg"],
                "efficiency_improvement": simulation["efficiency_score_change"]["improvement"],
                "confidence_score": 0.87,
            })
        
        if utilization == "Overloaded":
            recommendations.append({
                "id": f"rec_{uuid.uuid4().hex[:8]}",
                "type": "Capacity Expansion",
                "priority": "High",
                "title": "Consider expanding capacity or redistributing load",
                "description": "High utilization may impact employee comfort and productivity. Consider flexible scheduling or space expansion.",
                "financial_impact": prop["revenue_per_seat"] * 50,
                "weekly_energy_savings": 0,
                "monthly_energy_savings": 0,
                "energy_reduction_percent": 0,
                "carbon_reduction_kg": 0,
                "efficiency_improvement": 8.5,
                "confidence_score": 0.82,
            })
        
        energy_savings = IntelligenceEngine.calculate_energy_savings(prop, recent_occupancy, [], recent_occupancy * 0.9)
        recommendations.append({
            "id": f"rec_{uuid.uuid4().hex[:8]}",
            "type": "Energy Optimization",
            "priority": "Medium",
            "title": "Implement smart HVAC scheduling",
            "description": "Optimize HVAC systems based on occupancy patterns to reduce energy consumption during low-traffic periods.",
            "financial_impact": energy_savings["monthly_savings"] * 0.3,
            "weekly_energy_savings": energy_savings["weekly_savings"] * 0.3,
            "monthly_energy_savings": energy_savings["monthly_savings"] * 0.3,
            "energy_reduction_percent": energy_savings["energy_reduction_percent"] * 0.3,
            "carbon_reduction_kg": energy_savings["monthly_savings"] * 0.3 * 0.82,
            "efficiency_improvement": 3.2,
            "confidence_score": 0.91,
        })
        
        recommendations.append({
            "id": f"rec_{uuid.uuid4().hex[:8]}",
            "type": "Hybrid Optimization",
            "priority": "Medium",
            "title": "Implement desk hoteling for hybrid workers",
            "description": "Reduce fixed desk assignments and implement booking system to improve space utilization efficiency.",
            "financial_impact": prop["maintenance_per_floor"] * 0.15 * prop["floors"],
            "weekly_energy_savings": prop["baseline_energy_intensity"] * 0.1 * prop["energy_cost_per_unit"] * 7,
            "monthly_energy_savings": prop["baseline_energy_intensity"] * 0.1 * prop["energy_cost_per_unit"] * 30,
            "energy_reduction_percent": 10,
            "carbon_reduction_kg": prop["baseline_energy_intensity"] * 0.1 * 0.82 * 30,
            "efficiency_improvement": 5.5,
            "confidence_score": 0.78,
        })
        
        return recommendations
    
    @staticmethod
    def generate_copilot_insight(prop: Dict, query: str = None) -> Dict:
        digital_twin = prop.get("digital_twin", {})
        daily_data = digital_twin.get("daily_history", [])
        
        recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
        utilization = IntelligenceEngine.classify_utilization(recent_occupancy)
        financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
        
        if utilization == "Underutilized":
            root_cause = "Hybrid work patterns and seasonal variations have reduced daily occupancy below optimal levels."
            action = f"Consolidate operations to {max(1, prop['floors'] - 2)} floors during off-peak periods."
            simulation = IntelligenceEngine.simulate_floor_closure(prop, [prop["floors"], prop["floors"] - 1])
        elif utilization == "Overloaded":
            root_cause = "High demand and limited space are causing capacity constraints during peak hours."
            action = "Implement staggered schedules and expand to adjacent spaces if available."
            simulation = IntelligenceEngine.simulate_floor_closure(prop, [])
        else:
            root_cause = "Current utilization is within optimal range with minor optimization opportunities."
            action = "Maintain current operations while monitoring for seasonal variations."
            simulation = IntelligenceEngine.simulate_floor_closure(prop, [prop["floors"]])
        
        return {
            "property_id": prop["property_id"],
            "property_name": prop["name"],
            "insight_summary": f"{prop['name']} is currently {utilization.lower()} with {round(recent_occupancy * 100, 1)}% average occupancy over the past week.",
            "root_cause": root_cause,
            "recommended_action": action,
            "financial_impact": simulation["savings"]["total_monthly_savings"],
            "weekly_savings": simulation["savings"]["total_weekly_savings"],
            "monthly_savings": simulation["savings"]["total_monthly_savings"],
            "energy_reduction_percent": simulation["energy_impact"]["energy_reduction_percent"],
            "efficiency_score_change": simulation["efficiency_score_change"],
            "carbon_impact_kg": simulation["carbon_impact"]["monthly_carbon_reduction_kg"],
            "confidence_score": 0.85,
            "current_metrics": {
                "occupancy_rate": round(recent_occupancy, 3),
                "utilization_status": utilization,
                **financials,
            },
        }


# ==================== MCP (Model Context Protocol) HANDLER ====================

class MCPHandler:
    """
    MCP Handler for PropTech Decision Copilot
    Implements JSON-RPC style protocol for AI assistant integration
    """
    
    MCP_VERSION = "1.0.0"
    
    TOOLS = {
        "list_properties": {
            "description": "Returns all properties with name, location, occupancy, profit (₹), and efficiency score",
            "parameters": {}
        },
        "get_property_overview": {
            "description": "Get detailed overview of a property including revenue, profit, sustainability score, efficiency score, and carbon estimate",
            "parameters": {
                "property_id": {"type": "string", "description": "The unique property identifier", "required": True}
            }
        },
        "simulate_floor_closure": {
            "description": "Simulate closing floors and get projected savings including weekly/monthly savings (₹), energy reduction %, efficiency change, and carbon reduction",
            "parameters": {
                "property_id": {"type": "string", "description": "The unique property identifier", "required": True},
                "floors_to_close": {"type": "array", "items": {"type": "integer"}, "description": "List of floor numbers to close", "required": True}
            }
        },
        "energy_savings_report": {
            "description": "Get energy savings analysis for a property with weekly/monthly savings and percentage reduction",
            "parameters": {
                "property_id": {"type": "string", "description": "The unique property identifier", "required": True}
            }
        },
        "get_recommendations": {
            "description": "Get AI recommendations for a property including financial impact (₹), energy savings, carbon impact, and confidence score",
            "parameters": {
                "property_id": {"type": "string", "description": "The unique property identifier", "required": True}
            }
        }
    }
    
    @staticmethod
    def format_currency_inr(value: float) -> str:
        """Format value in Indian Rupees with Lakhs/Crores notation"""
        if abs(value) >= 10000000:
            return f"₹{value / 10000000:.2f} Cr"
        elif abs(value) >= 100000:
            return f"₹{value / 100000:.2f} L"
        else:
            return f"₹{value:,.0f}"
    
    @staticmethod
    def handle_request(request_data: Dict) -> Dict:
        """Process MCP request and return response"""
        method = request_data.get("method", "")
        params = request_data.get("params", {})
        request_id = request_data.get("id", 1)
        
        # Handle initialization
        if method == "initialize":
            return MCPHandler._handle_initialize(request_id)
        
        # Handle tools/list
        if method == "tools/list":
            return MCPHandler._handle_tools_list(request_id)
        
        # Handle tools/call
        if method == "tools/call":
            return MCPHandler._handle_tools_call(request_id, params)
        
        # Unknown method
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }
    
    @staticmethod
    def _handle_initialize(request_id: int) -> Dict:
        """Handle MCP initialization"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": MCPHandler.MCP_VERSION,
                "serverInfo": {
                    "name": "PropTech Decision Copilot MCP Server",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": True,
                    "prompts": False,
                    "resources": False
                }
            }
        }
    
    @staticmethod
    def _handle_tools_list(request_id: int) -> Dict:
        """Return list of available tools"""
        tools = []
        for name, info in MCPHandler.TOOLS.items():
            tool_schema = {
                "name": name,
                "description": info["description"],
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
            for param_name, param_info in info["parameters"].items():
                tool_schema["inputSchema"]["properties"][param_name] = {
                    "type": param_info["type"],
                    "description": param_info.get("description", "")
                }
                if param_info.get("required", False):
                    tool_schema["inputSchema"]["required"].append(param_name)
            tools.append(tool_schema)
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools}
        }
    
    @staticmethod
    def _handle_tools_call(request_id: int, params: Dict) -> Dict:
        """Execute a tool and return result"""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        try:
            if tool_name == "list_properties":
                result = MCPHandler._tool_list_properties()
            elif tool_name == "get_property_overview":
                result = MCPHandler._tool_get_property_overview(arguments.get("property_id"))
            elif tool_name == "simulate_floor_closure":
                result = MCPHandler._tool_simulate_floor_closure(
                    arguments.get("property_id"),
                    arguments.get("floors_to_close", [])
                )
            elif tool_name == "energy_savings_report":
                result = MCPHandler._tool_energy_savings_report(arguments.get("property_id"))
            elif tool_name == "get_recommendations":
                result = MCPHandler._tool_get_recommendations(arguments.get("property_id"))
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": f"Unknown tool: {tool_name}",
                            "annotations": []
                        }],
                        "isError": True
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": result,
                        "annotations": []
                    }],
                    "isError": False
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": str(e),
                        "annotations": []
                    }],
                    "isError": True
                }
            }
    
    @staticmethod
    def _tool_list_properties() -> str:
        """List all properties with key metrics"""
        properties = property_store.get_all()
        result_lines = ["# Property Portfolio Overview\n"]
        
        for prop in properties:
            digital_twin = prop.get("digital_twin", {})
            daily_data = digital_twin.get("daily_history", [])
            
            recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
            financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
            efficiency_score = IntelligenceEngine.calculate_efficiency_score(prop)
            
            result_lines.append(f"## {prop['name']}")
            result_lines.append(f"- **Location**: {prop['location']}")
            result_lines.append(f"- **Occupancy**: {round(recent_occupancy * 100, 1)}%")
            result_lines.append(f"- **Profit**: {MCPHandler.format_currency_inr(financials['profit'])}")
            result_lines.append(f"- **Efficiency Score**: {efficiency_score}%")
            result_lines.append(f"- **Property ID**: `{prop['property_id']}`\n")
        
        return "\n".join(result_lines)
    
    @staticmethod
    def _tool_get_property_overview(property_id: str) -> str:
        """Get detailed property overview"""
        if not property_id:
            raise ValueError("property_id is required")
        
        prop = property_store.get_by_id(property_id)
        if not prop:
            raise ValueError(f"Property not found: {property_id}")
        
        digital_twin = prop.get("digital_twin", {})
        daily_data = digital_twin.get("daily_history", [])
        
        recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
        financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
        efficiency_score = IntelligenceEngine.calculate_efficiency_score(prop)
        sustainability_score = IntelligenceEngine.calculate_sustainability_score(prop, recent_occupancy)
        carbon_estimate = IntelligenceEngine.calculate_carbon_estimate(prop, recent_occupancy)
        
        return f"""# {prop['name']} Overview

## Key Metrics
- **Revenue**: {MCPHandler.format_currency_inr(financials['revenue'])}
- **Profit**: {MCPHandler.format_currency_inr(financials['profit'])}
- **Sustainability Score**: {sustainability_score}/100
- **Efficiency Score**: {efficiency_score}%
- **Carbon Estimate**: {carbon_estimate} kg CO₂/month

## Property Details
- **Type**: {prop['type']}
- **Location**: {prop['location']}
- **Floors**: {prop['floors']}
- **Total Capacity**: {financials['total_capacity']} seats
- **Current Occupancy**: {round(recent_occupancy * 100, 1)}% ({financials['occupied_seats']} seats)

## Financial Breakdown
- **Energy Cost**: {MCPHandler.format_currency_inr(financials['energy_cost'])}
- **Maintenance Cost**: {MCPHandler.format_currency_inr(financials['maintenance_cost'])}
"""
    
    @staticmethod
    def _tool_simulate_floor_closure(property_id: str, floors_to_close: List[int]) -> str:
        """Simulate floor closure scenario"""
        if not property_id:
            raise ValueError("property_id is required")
        if not floors_to_close:
            raise ValueError("floors_to_close array is required")
        
        prop = property_store.get_by_id(property_id)
        if not prop:
            raise ValueError(f"Property not found: {property_id}")
        
        simulation = IntelligenceEngine.simulate_floor_closure(prop, floors_to_close)
        
        return f"""# Floor Closure Simulation: {prop['name']}

## Scenario
- **Floors to Close**: {', '.join(map(str, floors_to_close))}
- **Active Floors**: {simulation['scenario_summary']['active_floors']} (from {prop['floors']})

## Projected Savings
- **Weekly Savings**: {MCPHandler.format_currency_inr(simulation['savings']['total_weekly_savings'])}
- **Monthly Savings**: {MCPHandler.format_currency_inr(simulation['savings']['total_monthly_savings'])}
- **Energy Reduction**: {simulation['energy_impact']['energy_reduction_percent']}%

## Efficiency Impact
- **Before**: {simulation['efficiency_score_change']['before']}%
- **After**: {simulation['efficiency_score_change']['after']}%
- **Change**: {'+' if simulation['efficiency_score_change']['improvement'] > 0 else ''}{simulation['efficiency_score_change']['improvement']}%

## Carbon Impact
- **Monthly Carbon Reduction**: {simulation['carbon_impact']['monthly_carbon_reduction_kg']} kg CO₂
- **Annual Carbon Reduction**: {simulation['carbon_impact']['annual_carbon_reduction_tons']} tons CO₂

## Risk Assessment
- **Overload Risk**: {simulation['risk_assessment']['overload_risk']}
- **Redistribution Efficiency**: {simulation['risk_assessment']['redistribution_efficiency']}
"""
    
    @staticmethod
    def _tool_energy_savings_report(property_id: str) -> str:
        """Get energy savings analysis"""
        if not property_id:
            raise ValueError("property_id is required")
        
        prop = property_store.get_by_id(property_id)
        if not prop:
            raise ValueError(f"Property not found: {property_id}")
        
        digital_twin = prop.get("digital_twin", {})
        daily_data = digital_twin.get("daily_history", [])
        recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
        
        # Calculate scenarios
        scenarios = [
            {"floors": [prop["floors"]], "label": "Close 1 Floor"},
            {"floors": [prop["floors"], prop["floors"]-1], "label": "Close 2 Floors"},
        ]
        
        result_lines = [f"# Energy Savings Report: {prop['name']}\n"]
        result_lines.append(f"**Current Occupancy**: {round(recent_occupancy * 100, 1)}%\n")
        
        for scenario in scenarios:
            savings = IntelligenceEngine.calculate_energy_savings(prop, recent_occupancy, scenario["floors"])
            result_lines.append(f"## {scenario['label']}")
            result_lines.append(f"- **Weekly Savings**: {MCPHandler.format_currency_inr(savings['weekly_savings'])}")
            result_lines.append(f"- **Monthly Savings**: {MCPHandler.format_currency_inr(savings['monthly_savings'])}")
            result_lines.append(f"- **Energy Reduction**: {savings['energy_reduction_percent']}%\n")
        
        return "\n".join(result_lines)
    
    @staticmethod
    def _tool_get_recommendations(property_id: str) -> str:
        """Get AI recommendations"""
        if not property_id:
            raise ValueError("property_id is required")
        
        prop = property_store.get_by_id(property_id)
        if not prop:
            raise ValueError(f"Property not found: {property_id}")
        
        recommendations = IntelligenceEngine.generate_recommendations(prop)
        
        result_lines = [f"# AI Recommendations: {prop['name']}\n"]
        
        for i, rec in enumerate(recommendations, 1):
            result_lines.append(f"## {i}. {rec['title']}")
            result_lines.append(f"**Type**: {rec['type']} | **Priority**: {rec['priority']}")
            result_lines.append(f"\n{rec['description']}\n")
            result_lines.append("### Impact Analysis")
            result_lines.append(f"- **Financial Impact**: {MCPHandler.format_currency_inr(rec['financial_impact'])}/month")
            result_lines.append(f"- **Energy Savings**: {MCPHandler.format_currency_inr(rec['weekly_energy_savings'])}/week")
            result_lines.append(f"- **Carbon Reduction**: {rec['carbon_reduction_kg']:.1f} kg CO₂/month")
            result_lines.append(f"- **Confidence Score**: {rec['confidence_score'] * 100:.0f}%\n")
        
        return "\n".join(result_lines)


# ==================== PYDANTIC MODELS ====================

class UserSession(BaseModel):
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime

class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime

class PropertyCreate(BaseModel):
    name: str
    type: str
    location: str
    floors: int = Field(ge=1, le=50)
    rooms_per_floor: int = Field(ge=1, le=50)
    revenue_per_seat: float = Field(ge=100)
    energy_cost_per_unit: float = Field(ge=1)
    maintenance_per_floor: float = Field(ge=1000)
    baseline_energy_intensity: float = Field(ge=50)

class FloorClosureRequest(BaseModel):
    property_id: str
    floors_to_close: List[int]
    hybrid_intensity: float = Field(default=1.0, ge=0.1, le=1.5)
    target_occupancy: Optional[float] = Field(default=None, ge=0.1, le=1.0)

class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = {}
    id: Optional[int] = 1


# ==================== AUTH MIDDLEWARE ====================

async def get_current_user(request: Request) -> User:
    """Extract and validate user from session token"""
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    user_doc = await db.users.find_one(
        {"user_id": session_doc["user_id"]},
        {"_id": 0}
    )
    
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    
    return User(**user_doc)


# ==================== MCP ENDPOINT (ROOT-LEVEL, NO AUTH) ====================
# Note: Due to Kubernetes ingress routing, MCP is accessible at:
# - Internal: /mcp (direct app route)
# - External: /api/mcp (via ingress routing)

@app.post("/mcp")
async def mcp_endpoint_root(request: MCPRequest):
    """
    MCP (Model Context Protocol) endpoint - Root level.
    No authentication required.
    """
    response = MCPHandler.handle_request(request.model_dump())
    return response


@api_router.post("/mcp")
async def mcp_endpoint_api(request: MCPRequest):
    """
    MCP (Model Context Protocol) endpoint - API prefixed for external access.
    No authentication required.
    
    Response format follows MCP standard:
    {
        "jsonrpc": "2.0",
        "id": "...",
        "result": {
            "content": [{
                "type": "text",
                "text": "...",
                "annotations": []
            }],
            "isError": false
        }
    }
    """
    response = MCPHandler.handle_request(request.model_dump())
    return response


# ==================== WHATSAPP WEBHOOK ====================

class WhatsAppMessageRequest(BaseModel):
    """Request model for sending WhatsApp messages"""
    to_number: str
    message: str


async def _handle_whatsapp_webhook(body: str, from_number: str):
    """
    Conversational WhatsApp webhook handler.
    Supports natural language commands with user authentication via phone linking.
    Every website action can be executed via WhatsApp.
    """
    global _whatsapp_linking_service, _command_parser, _pdf_generator
    
    try:
        original_body = body.strip()
        sender_phone = from_number.replace("whatsapp:", "")
        if not sender_phone.startswith("+"):
            sender_phone = f"+{sender_phone}"
        
        logger.info(f"WhatsApp message from {sender_phone}: {original_body}")
        
        # Save incoming message to conversation history
        await conversation_history.add_message(
            phone_number=sender_phone,
            direction="inbound",
            message_body=original_body,
            message_type="text",
            metadata={"raw": original_body}
        )
        
        # Check if user is linked
        user_id = await _whatsapp_linking_service.get_user_by_phone(sender_phone) if _whatsapp_linking_service else None
        
        # Update command parser with latest properties
        properties = property_store.get_all()
        if _command_parser:
            _command_parser.update_properties(properties)
        
        # Parse the command
        parsed = _command_parser.parse(original_body) if _command_parser else ParsedCommand(
            intent=CommandIntent.UNKNOWN, raw_message=original_body
        )
        
        # Commands that don't require linking (read-only operations)
        no_auth_commands = {
            CommandIntent.HELP, CommandIntent.LIST_PROPERTIES, 
            CommandIntent.STATUS, CommandIntent.UNKNOWN,
            CommandIntent.PROPERTY_DETAILS, CommandIntent.CHECK_ALERTS,
            CommandIntent.GET_RECOMMENDATIONS, CommandIntent.SUBSCRIBE_ALERTS,
            CommandIntent.UNSUBSCRIBE_ALERTS, CommandIntent.SHOW_DASHBOARD,
            CommandIntent.EXECUTIVE_SUMMARY, CommandIntent.PORTFOLIO_OVERVIEW,
            CommandIntent.ENERGY_REPORT
        }
        
        # Check if command requires authentication (write operations)
        if parsed.intent not in no_auth_commands and not user_id:
            response_text = """🔒 *Account Not Linked*

To use floor controls, simulations, and reports, please link your WhatsApp in the dashboard.

━━━━━━━━━━━━━━━━━━
*Available without linking:*
• *list* - View all properties
• *help* - Show commands
• *status* - System status
━━━━━━━━━━━━━━━━━━

_Log in to your dashboard and go to Settings → Link WhatsApp_"""
            return await _send_response(sender_phone, response_text, {"requires_auth": True})
        
        # Handle commands
        response_text = await _process_command(parsed, user_id, sender_phone, properties)
        
        return await _send_response(sender_phone, response_text, {"intent": parsed.intent.value})
        
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}")
        return MessageTemplates.error_message()


async def _send_response(phone: str, text: str, metadata: Dict = None) -> str:
    """Save outbound message and return response text."""
    await conversation_history.add_message(
        phone_number=phone,
        direction="outbound",
        message_body=text[:500],
        message_type="response",
        metadata=metadata or {}
    )
    return text


async def _process_command(
    parsed: ParsedCommand,
    user_id: Optional[str],
    phone: str,
    properties: List[Dict]
) -> str:
    """Process parsed command and return response."""
    global _alert_scheduler, _pdf_generator
    
    templates = MessageTemplates()
    intent = parsed.intent
    
    # ==================== FLOOR CONTROL ====================
    if intent == CommandIntent.CLOSE_FLOOR:
        if not parsed.property_id:
            return _property_required_message(properties)
        
        if not parsed.floors:
            return "❌ Please specify which floors to close.\n\nExample: *Close F3 in Horizon*"
        
        prop = property_store.get_by_id(parsed.property_id)
        result = await user_state_service.close_floors(user_id, parsed.property_id, parsed.floors)
        
        if result["success"]:
            state = await user_state_service.get_user_state(user_id, parsed.property_id)
            analytics = await _get_property_analytics_with_override(prop, state)
            
            return _format_floor_action_response(
                action="closed",
                floors=parsed.floors,
                property_name=parsed.property_name,
                analytics=analytics
            )
        return f"❌ Failed to close floors: {result.get('error', 'Unknown error')}"
    
    elif intent == CommandIntent.OPEN_FLOOR:
        if not parsed.property_id:
            return _property_required_message(properties)
        
        if not parsed.floors:
            return "❌ Please specify which floors to open.\n\nExample: *Open F3*"
        
        prop = property_store.get_by_id(parsed.property_id)
        result = await user_state_service.open_floors(user_id, parsed.property_id, parsed.floors)
        
        if result["success"]:
            state = await user_state_service.get_user_state(user_id, parsed.property_id)
            analytics = await _get_property_analytics_with_override(prop, state)
            
            return _format_floor_action_response(
                action="opened",
                floors=parsed.floors,
                property_name=parsed.property_name,
                analytics=analytics
            )
        return f"❌ Failed to open floors: {result.get('error', 'Unknown error')}"
    
    # ==================== SIMULATION ====================
    elif intent in {CommandIntent.SIMULATE, CommandIntent.WHAT_IF}:
        if not parsed.property_id:
            return _property_required_message(properties)
        
        prop = property_store.get_by_id(parsed.property_id)
        floors_to_simulate = parsed.floors or [1]  # Default to floor 1 if not specified
        
        digital_twin = prop.get("digital_twin", {})
        daily_data = digital_twin.get("daily_history", [])
        recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
        
        savings = IntelligenceEngine.calculate_energy_savings(prop, recent_occupancy, floors_to_simulate)
        redistribution = IntelligenceEngine.calculate_redistribution_efficiency(prop, floors_to_simulate)
        
        # Save simulation result
        await user_state_service.save_simulation_result(user_id, parsed.property_id, {
            "floors": floors_to_simulate,
            "savings": savings,
            "redistribution": redistribution,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return _format_simulation_response(
            property_name=parsed.property_name,
            floors=floors_to_simulate,
            savings=savings,
            redistribution=redistribution
        )
    
    elif intent == CommandIntent.RUN_OPTIMIZATION:
        if not parsed.property_id:
            return _property_required_message(properties)
        
        prop = property_store.get_by_id(parsed.property_id)
        insight = IntelligenceEngine.generate_copilot_insight(prop)
        
        return _format_optimization_response(parsed.property_name, insight)
    
    # ==================== DASHBOARD & ANALYTICS ====================
    elif intent == CommandIntent.SHOW_DASHBOARD:
        return await _format_dashboard_response(user_id, properties)
    
    elif intent == CommandIntent.EXECUTIVE_SUMMARY:
        return await _format_executive_summary(user_id, properties)
    
    elif intent == CommandIntent.PORTFOLIO_OVERVIEW:
        return await _format_portfolio_overview(user_id, properties)
    
    elif intent == CommandIntent.PROPERTY_DETAILS:
        if not parsed.property_id:
            return _property_required_message(properties)
        
        return await _format_property_details(user_id, parsed.property_id, parsed.property_name)
    
    # ==================== REPORTS ====================
    elif intent == CommandIntent.DOWNLOAD_PDF:
        return """📄 *PDF Reports Available*

To download reports, please use the web dashboard:

• Property Report: Dashboard → Property → Download PDF
• Executive Summary: Dashboard → Reports → Executive Summary
• Energy Report: Dashboard → Property → Energy Analysis

_PDF download via WhatsApp coming soon!_"""
    
    elif intent == CommandIntent.ENERGY_REPORT:
        if not parsed.property_id:
            return _property_required_message(properties)
        
        return await _format_energy_report(user_id, parsed.property_id, parsed.property_name)
    
    # ==================== RECOMMENDATIONS ====================
    elif intent == CommandIntent.GET_RECOMMENDATIONS:
        if not parsed.property_id:
            return await _format_portfolio_recommendations(properties)
        
        prop = property_store.get_by_id(parsed.property_id)
        recommendations = IntelligenceEngine.generate_recommendations(prop)
        
        return _format_recommendations(parsed.property_name, recommendations)
    
    # ==================== RESET ====================
    elif intent == CommandIntent.RESET_PROPERTY:
        if not parsed.property_id:
            return _property_required_message(properties)
        
        result = await user_state_service.reset_property_state(user_id, parsed.property_id)
        
        if result["success"]:
            return f"""✅ *{parsed.property_name} Reset*

All floor closures and optimizations have been reverted to default state.

_Reply with property name to view current analytics._"""
        return f"❌ Reset failed: {result.get('error', 'Unknown error')}"
    
    elif intent == CommandIntent.RESET_ALL:
        result = await user_state_service.reset_all_user_states(user_id)
        
        return f"""✅ *All Properties Reset*

{result.get('properties_reset', 0)} property state(s) reverted to default.

_Reply 'list' to view properties._"""
    
    elif intent == CommandIntent.UNDO:
        # Get last simulation and undo it
        states = await user_state_service.get_all_user_states(user_id)
        if states:
            latest = max(states, key=lambda x: x.get("updated_at", ""))
            prop_id = latest.get("property_id")
            await user_state_service.reset_property_state(user_id, prop_id)
            return f"✅ Last change undone for property {prop_id}"
        return "ℹ️ No changes to undo."
    
    # ==================== ALERTS ====================
    elif intent == CommandIntent.CHECK_ALERTS:
        return await _format_active_alerts(user_id, properties)
    
    elif intent == CommandIntent.SUBSCRIBE_ALERTS:
        if _alert_scheduler:
            result = await _alert_scheduler.subscribe(phone)
            if result["success"]:
                return """✅ *Subscribed to Alerts*

You will receive automated alerts for:
• 🔴 High Occupancy (>90%)
• 🟡 Low Utilization (<40%)
• ⚡ Energy Spikes (>15%)

_Reply 'unsubscribe' to stop._"""
        return "❌ Alert subscription failed."
    
    elif intent == CommandIntent.UNSUBSCRIBE_ALERTS:
        if _alert_scheduler:
            result = await _alert_scheduler.unsubscribe(phone)
            if result["success"]:
                return "✅ *Unsubscribed* - You will no longer receive automated alerts."
        return "❌ You are not subscribed to alerts."
    
    # ==================== SYSTEM ====================
    elif intent == CommandIntent.HELP:
        return _command_parser.get_help_text() if _command_parser else templates.help_menu()
    
    elif intent == CommandIntent.STATUS:
        return await _format_system_status(user_id, phone, properties)
    
    elif intent == CommandIntent.LIST_PROPERTIES:
        return _format_property_list(properties)
    
    # ==================== UNKNOWN ====================
    else:
        # Try to match property name for details
        for prop in properties:
            if prop["name"].lower() in parsed.raw_message.lower():
                return await _format_property_details(user_id, prop["property_id"], prop["name"])
        
        return templates.welcome()


# ==================== RESPONSE FORMATTERS ====================

def _property_required_message(properties: List[Dict]) -> str:
    """Message when property is not specified."""
    prop_list = "\n".join([f"• {p['name']}" for p in properties])
    return f"""❓ *Which property?*

Please specify a property name:
{prop_list}

Example: *Close F3 in Horizon*"""


def _format_floor_action_response(
    action: str,
    floors: List[int],
    property_name: str,
    analytics: Dict
) -> str:
    """Format response for floor open/close actions."""
    floor_str = ", ".join([f"F{f}" for f in floors])
    
    return f"""✅ *Floor(s) {action.title()}*

━━━━━━━━━━━━━━━━━━
🏢 *Property:* {property_name}
🚪 *Floors {action}:* {floor_str}

━━━━━━━━━━━━━━━━━━
📊 *Updated Analytics*
━━━━━━━━━━━━━━━━━━
• Active Floors: {analytics.get('active_floors', 0)}/{analytics.get('total_floors', 0)}
• Closed Floors: {', '.join(map(str, analytics.get('closed_floors', [])))}
• Monthly Savings: {whatsapp_service.format_currency_inr(analytics.get('monthly_savings', 0))}
• Energy Reduction: {analytics.get('energy_reduction_pct', 0):.1f}%
• Carbon Reduction: {analytics.get('carbon_reduction_kg', 0):.1f} kg CO₂
• Efficiency: {analytics.get('efficiency_score_before', 0)}% → {analytics.get('efficiency_score_after', 0)}%
• Risk Level: {analytics.get('risk_level', 'low').title()}
• Confidence: {analytics.get('confidence_score', 0.85)*100:.0f}%

_Reply 'reset {property_name}' to undo._"""


def _format_simulation_response(
    property_name: str,
    floors: List[int],
    savings: Dict,
    redistribution: Dict
) -> str:
    """Format what-if simulation response."""
    floor_str = ", ".join([f"F{f}" for f in floors])
    
    return f"""🔮 *What-If Simulation*

━━━━━━━━━━━━━━━━━━
🏢 *Property:* {property_name}
🚪 *Simulating:* Close {floor_str}

━━━━━━━━━━━━━━━━━━
💰 *Projected Savings*
━━━━━━━━━━━━━━━━━━
• Monthly: {whatsapp_service.format_currency_inr(savings.get('monthly_cost_savings', 0))}
• Annual: {whatsapp_service.format_currency_inr(savings.get('monthly_cost_savings', 0) * 12)}
• Energy Saved: {savings.get('energy_saved_kwh', 0):,.0f} kWh
• Carbon: -{savings.get('carbon_reduction_kg', 0):,.0f} kg CO₂

━━━━━━━━━━━━━━━━━━
📊 *Redistribution Analysis*
━━━━━━━━━━━━━━━━━━
• New Avg Occupancy: {redistribution.get('new_avg_occupancy', 0)*100:.1f}%
• Efficiency: {redistribution.get('efficiency', 0)*100:.1f}%
• Risk Level: {redistribution.get('risk_level', 'low').title()}

━━━━━━━━━━━━━━━━━━
*To apply:* Close {floor_str} in {property_name}"""


def _format_optimization_response(property_name: str, insight: Dict) -> str:
    """Format optimization run response."""
    return f"""⚡ *Optimization Analysis*

━━━━━━━━━━━━━━━━━━
🏢 *Property:* {property_name}

━━━━━━━━━━━━━━━━━━
📊 *Current State*
━━━━━━━━━━━━━━━━━━
• Utilization: {insight.get('utilization_class', 'N/A')}
• Efficiency Before: {insight.get('efficiency_score_change', {}).get('before', 0)}%
• Efficiency After: {insight.get('efficiency_score_change', {}).get('after', 0)}%
• Improvement: +{insight.get('efficiency_score_change', {}).get('improvement', 0)}%

━━━━━━━━━━━━━━━━━━
💡 *Recommendation*
━━━━━━━━━━━━━━━━━━
{insight.get('recommended_action', 'No action needed')}

━━━━━━━━━━━━━━━━━━
💰 *Potential Impact*
━━━━━━━━━━━━━━━━━━
• Monthly Savings: {whatsapp_service.format_currency_inr(insight.get('monthly_savings', 0))}
• Carbon Reduction: {insight.get('carbon_impact_kg', 0):,.0f} kg CO₂
• Confidence: {insight.get('confidence_score', 0)*100:.0f}%"""


async def _format_dashboard_response(user_id: str, properties: List[Dict]) -> str:
    """Format dashboard overview response."""
    total_revenue = 0
    total_profit = 0
    total_occupancy = 0
    overrides_count = 0
    
    for prop in properties:
        digital_twin = prop.get("digital_twin", {})
        daily_data = digital_twin.get("daily_history", [])
        recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
        
        financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
        total_revenue += financials["revenue"]
        total_profit += financials["profit"]
        total_occupancy += recent_occupancy
        
        if user_id:
            state = await user_state_service.get_user_state(user_id, prop["property_id"])
            if state and state.get("closed_floors"):
                overrides_count += 1
    
    avg_occupancy = (total_occupancy / len(properties) * 100) if properties else 0
    
    return f"""📊 *Dashboard Overview*

━━━━━━━━━━━━━━━━━━
💰 *Portfolio Financials*
━━━━━━━━━━━━━━━━━━
• Total Revenue: {whatsapp_service.format_currency_inr(total_revenue)}
• Total Profit: {whatsapp_service.format_currency_inr(total_profit)}
• Avg Occupancy: {avg_occupancy:.1f}%

━━━━━━━━━━━━━━━━━━
🏢 *Properties*
━━━━━━━━━━━━━━━━━━
• Total: {len(properties)}
• With Optimizations: {overrides_count}

━━━━━━━━━━━━━━━━━━
_Reply with property name for details._"""


async def _format_executive_summary(user_id: str, properties: List[Dict]) -> str:
    """Format executive summary response."""
    total_savings = 0
    total_carbon = 0
    top_actions = []
    
    for prop in properties:
        insight = IntelligenceEngine.generate_copilot_insight(prop)
        recommendations = IntelligenceEngine.generate_recommendations(prop)
        
        total_savings += insight["monthly_savings"]
        total_carbon += insight["carbon_impact_kg"]
        
        if recommendations:
            top_rec = max(recommendations, key=lambda x: x["financial_impact"])
            top_actions.append({
                "property": prop["name"],
                "action": top_rec["title"],
                "impact": top_rec["financial_impact"]
            })
    
    top_actions = sorted(top_actions, key=lambda x: x["impact"], reverse=True)[:3]
    
    actions_text = "\n".join([
        f"• {a['property']}: {a['action']} ({whatsapp_service.format_currency_inr(a['impact'])})"
        for a in top_actions
    ])
    
    return f"""📈 *Executive Summary*

━━━━━━━━━━━━━━━━━━
💰 *Savings Potential*
━━━━━━━━━━━━━━━━━━
• Monthly: {whatsapp_service.format_currency_inr(total_savings)}
• Annual: {whatsapp_service.format_currency_inr(total_savings * 12)}
• Carbon Reduction: {total_carbon:,.0f} kg CO₂

━━━━━━━━━━━━━━━━━━
🎯 *Top Actions*
━━━━━━━━━━━━━━━━━━
{actions_text}

_Reply 'recommendations' for full list._"""


async def _format_portfolio_overview(user_id: str, properties: List[Dict]) -> str:
    """Format portfolio overview."""
    lines = ["📋 *Portfolio Overview*\n"]
    
    for prop in properties:
        digital_twin = prop.get("digital_twin", {})
        daily_data = digital_twin.get("daily_history", [])
        recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
        
        status_emoji = "🟢" if recent_occupancy >= 0.7 else "🟡" if recent_occupancy >= 0.5 else "🔴"
        
        state = await user_state_service.get_user_state(user_id, prop["property_id"]) if user_id else None
        override_marker = " ⚙️" if state and state.get("closed_floors") else ""
        
        lines.append(f"{status_emoji} *{prop['name']}*{override_marker}")
        lines.append(f"   📊 {recent_occupancy*100:.0f}% occupancy | {prop['location']}\n")
    
    lines.append("\n_⚙️ = Custom optimization active_")
    return "\n".join(lines)


async def _format_property_details(user_id: str, property_id: str, property_name: str) -> str:
    """Format detailed property response with user overrides."""
    prop = property_store.get_by_id(property_id)
    if not prop:
        return f"❌ Property not found: {property_name}"
    
    # Get user state
    user_state = await user_state_service.get_user_state(user_id, property_id) if user_id else None
    
    digital_twin = prop.get("digital_twin", {})
    daily_data = digital_twin.get("daily_history", [])
    recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
    
    financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
    efficiency = IntelligenceEngine.calculate_efficiency_score(prop)
    utilization = IntelligenceEngine.classify_utilization(recent_occupancy)
    recommendations = IntelligenceEngine.generate_recommendations(prop)
    
    closed_floors = user_state.get("closed_floors", []) if user_state else []
    total_floors = prop.get("floors", 0)
    active_floors = total_floors - len(closed_floors)
    
    # Calculate savings if floors are closed
    if closed_floors:
        analytics = await _get_property_analytics_with_override(prop, user_state)
        savings_text = f"""
━━━━━━━━━━━━━━━━━━
⚙️ *Your Optimization*
━━━━━━━━━━━━━━━━━━
• Closed Floors: {', '.join(map(str, closed_floors))}
• Active: {active_floors}/{total_floors}
• Monthly Savings: {whatsapp_service.format_currency_inr(analytics.get('monthly_savings', 0))}
• Energy Reduction: {analytics.get('energy_reduction_pct', 0):.1f}%"""
    else:
        savings_text = ""
    
    # Top recommendation
    rec_text = ""
    if recommendations:
        top_rec = recommendations[0]
        rec_text = f"""
━━━━━━━━━━━━━━━━━━
💡 *Top Recommendation*
━━━━━━━━━━━━━━━━━━
{top_rec['title']}
Impact: {whatsapp_service.format_currency_inr(top_rec['financial_impact'])}/month"""
    
    return f"""📊 *{property_name}*

📍 {prop['location']} | {prop['type']}

━━━━━━━━━━━━━━━━━━
📈 *Performance*
━━━━━━━━━━━━━━━━━━
• Occupancy: {recent_occupancy*100:.1f}%
• Utilization: {utilization}
• Efficiency: {efficiency}%
• Floors: {total_floors}

━━━━━━━━━━━━━━━━━━
💰 *Financials*
━━━━━━━━━━━━━━━━━━
• Revenue: {whatsapp_service.format_currency_inr(financials['revenue'])}
• Profit: {whatsapp_service.format_currency_inr(financials['profit'])}
• Energy Cost: {whatsapp_service.format_currency_inr(financials['energy_cost'])}{savings_text}{rec_text}"""


async def _format_energy_report(user_id: str, property_id: str, property_name: str) -> str:
    """Format energy savings report."""
    prop = property_store.get_by_id(property_id)
    if not prop:
        return f"❌ Property not found: {property_name}"
    
    user_state = await user_state_service.get_user_state(user_id, property_id) if user_id else None
    closed_floors = user_state.get("closed_floors", []) if user_state else []
    
    digital_twin = prop.get("digital_twin", {})
    daily_data = digital_twin.get("daily_history", [])
    recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
    
    savings = IntelligenceEngine.calculate_energy_savings(prop, recent_occupancy, closed_floors)
    
    total_floors = prop.get("floors", 0)
    baseline = prop.get("baseline_energy_intensity", 150) * total_floors * 30
    
    return f"""⚡ *Energy Report: {property_name}*

━━━━━━━━━━━━━━━━━━
📊 *Energy Analysis*
━━━━━━━━━━━━━━━━━━
• Baseline: {baseline:,.0f} kWh/month
• Current: {baseline - savings.get('energy_saved_kwh', 0):,.0f} kWh/month
• Reduction: {savings.get('energy_reduction_percentage', 0):.1f}%

━━━━━━━━━━━━━━━━━━
💰 *Savings*
━━━━━━━━━━━━━━━━━━
• Weekly: {whatsapp_service.format_currency_inr(savings.get('monthly_cost_savings', 0)/4)}
• Monthly: {whatsapp_service.format_currency_inr(savings.get('monthly_cost_savings', 0))}
• Annual: {whatsapp_service.format_currency_inr(savings.get('monthly_cost_savings', 0)*12)}

━━━━━━━━━━━━━━━━━━
🌱 *Environmental*
━━━━━━━━━━━━━━━━━━
• Carbon Reduction: {savings.get('carbon_reduction_kg', 0):,.0f} kg CO₂"""


def _format_recommendations(property_name: str, recommendations: List[Dict]) -> str:
    """Format recommendations response."""
    if not recommendations:
        return f"✅ No recommendations for {property_name} - all metrics within optimal range."
    
    rec_lines = []
    for i, rec in enumerate(recommendations[:5], 1):
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec.get("priority", "medium"), "⚪")
        rec_lines.append(f"{priority_emoji} *{i}. {rec['title']}*")
        rec_lines.append(f"   Impact: {whatsapp_service.format_currency_inr(rec['financial_impact'])}/month\n")
    
    return f"""💡 *Recommendations: {property_name}*

━━━━━━━━━━━━━━━━━━
{chr(10).join(rec_lines)}
_🔴 High | 🟡 Medium | 🟢 Low priority_"""


async def _format_portfolio_recommendations(properties: List[Dict]) -> str:
    """Format recommendations across all properties."""
    all_recs = []
    
    for prop in properties:
        recommendations = IntelligenceEngine.generate_recommendations(prop)
        for rec in recommendations[:2]:
            all_recs.append({
                "property": prop["name"],
                **rec
            })
    
    # Sort by impact
    all_recs = sorted(all_recs, key=lambda x: x["financial_impact"], reverse=True)[:5]
    
    lines = ["💡 *Top Portfolio Recommendations*\n"]
    for i, rec in enumerate(all_recs, 1):
        lines.append(f"*{i}. {rec['property']}*")
        lines.append(f"   {rec['title']}")
        lines.append(f"   Impact: {whatsapp_service.format_currency_inr(rec['financial_impact'])}/month\n")
    
    return "\n".join(lines)


async def _format_active_alerts(user_id: str, properties: List[Dict]) -> str:
    """Format active alerts across all properties."""
    all_alerts = []
    
    for prop in properties:
        digital_twin = prop.get("digital_twin", {})
        daily_data = digital_twin.get("daily_history", [])
        
        if len(daily_data) >= 2:
            recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
            
            recent_energy = sum(d.get("energy_kwh", 0) for d in daily_data[-7:])
            prev_energy = sum(d.get("energy_kwh", 0) for d in daily_data[-14:-7]) if len(daily_data) >= 14 else recent_energy
            energy_change = ((recent_energy - prev_energy) / prev_energy * 100) if prev_energy > 0 else 0
            
            financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
            
            alerts = whatsapp_service.check_and_generate_alerts(
                property_name=prop["name"],
                occupancy_rate=recent_occupancy,
                utilization_rate=recent_occupancy,
                energy_change_percent=energy_change,
                financials=financials
            )
            all_alerts.extend(alerts)
    
    if not all_alerts:
        return """✅ *No Active Alerts*

All properties operating within normal parameters.

*Monitoring thresholds:*
• Occupancy >90% → Alert
• Utilization <40% → Alert
• Energy spike >15% → Alert"""
    
    lines = [f"⚠️ *{len(all_alerts)} Active Alert(s)*\n"]
    
    for alert in all_alerts:
        emoji = {"high_occupancy": "🔴", "low_utilization": "🟡", "energy_spike": "⚡"}.get(alert["type"], "📊")
        lines.append(f"{emoji} *{alert['property_name']}*")
        lines.append(f"   {alert['type'].replace('_', ' ').title()}: {alert['metric_value']:.1f}%")
        lines.append(f"   Impact: {whatsapp_service.format_currency_inr(alert['financial_impact'])}\n")
    
    return "\n".join(lines)


async def _format_system_status(user_id: str, phone: str, properties: List[Dict]) -> str:
    """Format system status response."""
    global _alert_scheduler, _whatsapp_linking_service
    
    scheduler_status = "Running" if _alert_scheduler and _alert_scheduler.is_running else "Stopped"
    subs_count = len(await _alert_scheduler.get_all_active_subscriptions()) if _alert_scheduler else 0
    
    linked = await _whatsapp_linking_service.get_linking_status(user_id) if _whatsapp_linking_service and user_id else {"linked": False}
    
    user_states = await user_state_service.get_all_user_states(user_id) if user_id else []
    active_optimizations = sum(1 for s in user_states if s.get("closed_floors"))
    
    return f"""🔧 *System Status*

━━━━━━━━━━━━━━━━━━
📱 *WhatsApp Service*
━━━━━━━━━━━━━━━━━━
• Status: {"✅ Active" if whatsapp_service.is_configured else "❌ Not Configured"}
• Account Linked: {"✅ Yes" if linked.get("linked") else "❌ No"}
• Alert Scheduler: {scheduler_status}
• Subscribers: {subs_count}

━━━━━━━━━━━━━━━━━━
🏢 *Your Data*
━━━━━━━━━━━━━━━━━━
• Properties: {len(properties)}
• Active Optimizations: {active_optimizations}

━━━━━━━━━━━━━━━━━━
📊 *MCP Endpoint*
━━━━━━━━━━━━━━━━━━
• Status: ✅ Active
• Tools: 5 available"""


def _format_property_list(properties: List[Dict]) -> str:
    """Format property list response."""
    lines = ["📋 *Property Portfolio*\n"]
    
    for prop in properties:
        digital_twin = prop.get("digital_twin", {})
        daily_data = digital_twin.get("daily_history", [])
        recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
        
        status = "🟢" if recent_occupancy >= 0.7 else "🟡" if recent_occupancy >= 0.5 else "🔴"
        
        lines.append(f"{status} *{prop['name']}*")
        lines.append(f"   📍 {prop['location']}")
        lines.append(f"   📊 {recent_occupancy*100:.0f}% occupancy\n")
    
    lines.append("_Reply with property name for details._")
    return "\n".join(lines)


@app.post("/whatsapp/webhook")
async def whatsapp_webhook_root(
    request: Request,
    Body: str = Form(default=""),
    From: str = Form(default="")
):
    """
    Twilio WhatsApp webhook endpoint (root level).
    No authentication required.
    """
    response_text = await _handle_whatsapp_webhook(Body, From)
    twiml_response = whatsapp_service.create_webhook_response(response_text)
    return PlainTextResponse(content=twiml_response, media_type="application/xml")


@api_router.post("/whatsapp/webhook")
async def whatsapp_webhook_api(
    request: Request,
    Body: str = Form(default=""),
    From: str = Form(default="")
):
    """
    Twilio WhatsApp webhook endpoint (api-prefixed for external access).
    No authentication required for webhook.
    
    Workflow:
    1. Parse incoming message
    2. Detect property name
    3. Call analytics engine
    4. Respond with formatted result
    """
    response_text = await _handle_whatsapp_webhook(Body, From)
    twiml_response = whatsapp_service.create_webhook_response(response_text)
    return PlainTextResponse(content=twiml_response, media_type="application/xml")


@api_router.post("/whatsapp/send")
async def send_whatsapp_message(request: WhatsAppMessageRequest, user: User = Depends(get_current_user)):
    """
    Send a WhatsApp message (authenticated endpoint).
    Requires Twilio credentials to be configured.
    """
    result = whatsapp_service.send_whatsapp_message(request.to_number, request.message)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to send message"))
    
    return result


@api_router.post("/whatsapp/alert")
async def send_property_alert(
    property_id: str,
    to_number: str,
    user: User = Depends(get_current_user)
):
    """
    Send property alerts via WhatsApp.
    Checks for alert conditions and sends if thresholds exceeded:
    - Occupancy > 90%
    - Utilization < 40%
    - Energy spike > 15%
    """
    prop = property_store.get_by_id(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Get current metrics
    digital_twin = prop.get("digital_twin", {})
    daily_data = digital_twin.get("daily_history", [])
    
    if len(daily_data) < 2:
        raise HTTPException(status_code=400, detail="Insufficient data for alert analysis")
    
    recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
    utilization = recent_occupancy  # Simplified utilization calculation
    
    # Calculate energy change
    recent_energy = sum(d.get("energy_kwh", 0) for d in daily_data[-7:])
    prev_energy = sum(d.get("energy_kwh", 0) for d in daily_data[-14:-7]) if len(daily_data) >= 14 else recent_energy
    energy_change = ((recent_energy - prev_energy) / prev_energy * 100) if prev_energy > 0 else 0
    
    financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
    
    # Check for alerts
    alerts = whatsapp_service.check_and_generate_alerts(
        property_name=prop["name"],
        occupancy_rate=recent_occupancy,
        utilization_rate=utilization,
        energy_change_percent=energy_change,
        financials=financials
    )
    
    if not alerts:
        return {"message": "No alerts triggered", "alerts_sent": 0}
    
    # Send alerts
    sent_alerts = []
    for alert in alerts:
        message = whatsapp_service.format_property_alert(
            property_name=alert["property_name"],
            alert_type=alert["type"],
            metric_value=alert["metric_value"],
            financial_impact=alert["financial_impact"],
            suggested_action=alert["suggested_action"]
        )
        
        result = whatsapp_service.send_whatsapp_message(to_number, message)
        sent_alerts.append({
            "alert_type": alert["type"],
            "sent": result["success"],
            "message_sid": result.get("message_sid")
        })
    
    return {
        "message": f"Sent {len([a for a in sent_alerts if a['sent']])} alerts",
        "alerts": sent_alerts
    }


@api_router.get("/whatsapp/status")
async def whatsapp_status():
    """Check WhatsApp service configuration status"""
    global _alert_scheduler
    return {
        "configured": whatsapp_service.is_configured,
        "account_sid_set": bool(os.environ.get("TWILIO_ACCOUNT_SID")),
        "auth_token_set": bool(os.environ.get("TWILIO_AUTH_TOKEN")),
        "whatsapp_number_set": bool(os.environ.get("TWILIO_WHATSAPP_NUMBER")),
        "alert_scheduler_running": _alert_scheduler.is_running if _alert_scheduler else False
    }


# ==================== CONVERSATION HISTORY ENDPOINTS ====================

@api_router.get("/whatsapp/conversations/{phone_number}")
async def get_conversation_history(
    phone_number: str,
    limit: int = 20,
    user: User = Depends(get_current_user)
):
    """Get conversation history for a phone number."""
    # Ensure phone number has + prefix
    if not phone_number.startswith("+"):
        phone_number = f"+{phone_number}"
    
    messages = await conversation_history.get_conversation(phone_number, limit=limit)
    stats = await conversation_history.get_user_stats(phone_number)
    
    return {
        "phone_number": phone_number,
        "messages": messages,
        "stats": stats
    }


@api_router.get("/whatsapp/conversations")
async def search_conversations(
    query: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user)
):
    """Search conversation history."""
    if query:
        messages = await conversation_history.search_conversations(query, limit=limit)
    else:
        # Return recent messages from all conversations
        messages = await conversation_history.collection.find(
            {},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(length=limit)
    
    return {"messages": messages, "count": len(messages)}


# ==================== ALERT SUBSCRIPTION ENDPOINTS ====================

class AlertSubscriptionRequest(BaseModel):
    phone_number: str
    property_ids: Optional[List[str]] = None
    alert_types: Optional[List[str]] = None


@api_router.post("/whatsapp/alerts/subscribe")
async def subscribe_to_alerts(
    request: AlertSubscriptionRequest,
    user: User = Depends(get_current_user)
):
    """Subscribe a phone number to property alerts."""
    global _alert_scheduler
    if not _alert_scheduler:
        raise HTTPException(status_code=503, detail="Alert scheduler not available")
    
    result = await _alert_scheduler.subscribe(
        phone_number=request.phone_number,
        property_ids=request.property_ids,
        alert_types=request.alert_types
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to subscribe"))
    
    return result


@api_router.post("/whatsapp/alerts/unsubscribe")
async def unsubscribe_from_alerts(
    phone_number: str,
    user: User = Depends(get_current_user)
):
    """Unsubscribe a phone number from alerts."""
    global _alert_scheduler
    if not _alert_scheduler:
        raise HTTPException(status_code=503, detail="Alert scheduler not available")
    
    result = await _alert_scheduler.unsubscribe(phone_number)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to unsubscribe"))
    
    return result


@api_router.get("/whatsapp/alerts/subscriptions")
async def get_alert_subscriptions(user: User = Depends(get_current_user)):
    """Get all active alert subscriptions."""
    global _alert_scheduler
    if not _alert_scheduler:
        raise HTTPException(status_code=503, detail="Alert scheduler not available")
    
    subscriptions = await _alert_scheduler.get_all_active_subscriptions()
    return {"subscriptions": subscriptions, "count": len(subscriptions)}


@api_router.get("/whatsapp/alerts/history")
async def get_alert_history(
    phone_number: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user)
):
    """Get alert sending history."""
    global _alert_scheduler
    if not _alert_scheduler:
        raise HTTPException(status_code=503, detail="Alert scheduler not available")
    
    history = await _alert_scheduler.get_alert_history(phone_number=phone_number, limit=limit)
    return {"alerts": history, "count": len(history)}


@api_router.post("/whatsapp/alerts/check-now")
async def trigger_alert_check(user: User = Depends(get_current_user)):
    """Manually trigger an alert check across all properties."""
    global _alert_scheduler
    if not _alert_scheduler:
        raise HTTPException(status_code=503, detail="Alert scheduler not available")
    
    all_alerts = await _alert_scheduler.check_all_properties()
    
    total_alerts = sum(len(alerts) for alerts in all_alerts.values())
    
    return {
        "properties_checked": len(property_store.get_all()),
        "properties_with_alerts": len(all_alerts),
        "total_alerts": total_alerts,
        "alerts_by_property": {
            prop_id: [{"type": a["type"], "property": a["property_name"], "value": a["metric_value"]} 
                      for a in alerts]
            for prop_id, alerts in all_alerts.items()
        }
    }


# ==================== WHATSAPP LINKING ROUTES ====================

class LinkPhoneRequest(BaseModel):
    phone_number: str

class VerifyOTPRequest(BaseModel):
    phone_number: str
    otp_code: str


@api_router.post("/whatsapp/link/initiate")
async def initiate_phone_linking(
    request: LinkPhoneRequest,
    user: User = Depends(get_current_user)
):
    """Initiate WhatsApp phone linking by sending OTP."""
    global _whatsapp_linking_service
    if not _whatsapp_linking_service:
        raise HTTPException(status_code=503, detail="Linking service not available")
    
    result = await _whatsapp_linking_service.initiate_linking(
        user_id=user.user_id,
        phone_number=request.phone_number,
        user_name=user.name or "User"
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to initiate linking"))
    
    return result


@api_router.post("/whatsapp/link/verify")
async def verify_phone_linking(
    request: VerifyOTPRequest,
    user: User = Depends(get_current_user)
):
    """Verify OTP and complete phone linking."""
    global _whatsapp_linking_service
    if not _whatsapp_linking_service:
        raise HTTPException(status_code=503, detail="Linking service not available")
    
    result = await _whatsapp_linking_service.verify_otp(
        user_id=user.user_id,
        phone_number=request.phone_number,
        otp_code=request.otp_code
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Verification failed"))
    
    return result


@api_router.get("/whatsapp/link/status")
async def get_linking_status(user: User = Depends(get_current_user)):
    """Get WhatsApp linking status for current user."""
    global _whatsapp_linking_service
    if not _whatsapp_linking_service:
        raise HTTPException(status_code=503, detail="Linking service not available")
    
    return await _whatsapp_linking_service.get_linking_status(user.user_id)


@api_router.post("/whatsapp/link/unlink")
async def unlink_phone(user: User = Depends(get_current_user)):
    """Unlink WhatsApp phone number from account."""
    global _whatsapp_linking_service
    if not _whatsapp_linking_service:
        raise HTTPException(status_code=503, detail="Linking service not available")
    
    result = await _whatsapp_linking_service.unlink_phone(user.user_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to unlink"))
    
    return result


# ==================== CHANGE LOG & SESSION ROUTES ====================

class CreateSessionRequest(BaseModel):
    device_info: Optional[str] = None


@api_router.post("/sessions/create")
async def create_user_session(
    request: CreateSessionRequest,
    user: User = Depends(get_current_user)
):
    """Create a new session for tracking changes."""
    global _change_log_service
    if not _change_log_service:
        raise HTTPException(status_code=503, detail="Change log service not available")
    
    result = await _change_log_service.create_session(
        user_id=user.user_id,
        device_info=request.device_info
    )
    
    return result


@api_router.get("/sessions")
async def get_user_sessions(
    limit: int = 20,
    user: User = Depends(get_current_user)
):
    """Get list of user's previous sessions."""
    global _change_log_service
    if not _change_log_service:
        raise HTTPException(status_code=503, detail="Change log service not available")
    
    sessions = await _change_log_service.get_user_sessions(user.user_id, limit=limit)
    return {"sessions": sessions, "count": len(sessions)}


@api_router.get("/sessions/{session_id}")
async def get_session_summary(
    session_id: str,
    user: User = Depends(get_current_user)
):
    """Get detailed summary of a session including all changes."""
    global _change_log_service
    if not _change_log_service:
        raise HTTPException(status_code=503, detail="Change log service not available")
    
    summary = await _change_log_service.get_session_summary(session_id)
    
    if "error" in summary:
        raise HTTPException(status_code=404, detail=summary["error"])
    
    return summary


@api_router.post("/sessions/{session_id}/end")
async def end_user_session(
    session_id: str,
    user: User = Depends(get_current_user)
):
    """Mark a session as ended."""
    global _change_log_service
    if not _change_log_service:
        raise HTTPException(status_code=503, detail="Change log service not available")
    
    await _change_log_service.end_session(session_id)
    return {"success": True, "message": "Session ended"}


@api_router.get("/change-log")
async def get_user_change_log(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    user: User = Depends(get_current_user)
):
    """Get user's change history with optional filters."""
    global _change_log_service
    if not _change_log_service:
        raise HTTPException(status_code=503, detail="Change log service not available")
    
    changes = await _change_log_service.get_user_changes(
        user_id=user.user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        session_id=session_id,
        limit=limit,
        skip=skip
    )
    
    return {"changes": changes, "count": len(changes)}


@api_router.get("/change-log/entity/{entity_type}/{entity_id}")
async def get_entity_change_history(
    entity_type: str,
    entity_id: str,
    limit: int = 50,
    user: User = Depends(get_current_user)
):
    """Get complete change history for a specific entity."""
    global _change_log_service
    if not _change_log_service:
        raise HTTPException(status_code=503, detail="Change log service not available")
    
    history = await _change_log_service.get_entity_history(entity_type, entity_id, limit=limit)
    return {"entity_type": entity_type, "entity_id": entity_id, "history": history}


@api_router.get("/change-log/stats")
async def get_change_stats(user: User = Depends(get_current_user)):
    """Get statistics about user's changes."""
    global _change_log_service
    if not _change_log_service:
        raise HTTPException(status_code=503, detail="Change log service not available")
    
    stats = await _change_log_service.get_change_stats(user.user_id)
    return stats


# ==================== USER STATE ROUTES ====================

class CloseFloorsRequest(BaseModel):
    floors: List[int]
    session_id: Optional[str] = None

class SimulationParamsRequest(BaseModel):
    hybrid_intensity: Optional[float] = None
    target_occupancy: Optional[float] = None
    session_id: Optional[str] = None


@api_router.get("/user-state/{property_id}")
async def get_user_property_state(
    property_id: str,
    user: User = Depends(get_current_user)
):
    """Get user's optimization state for a property."""
    state = await user_state_service.get_user_state(user.user_id, property_id)
    
    if not state:
        return {
            "property_id": property_id,
            "has_override": False,
            "closed_floors": [],
            "message": "Using default property state"
        }
    
    return {
        "property_id": property_id,
        "has_override": True,
        **state
    }


@api_router.get("/user-state")
async def get_all_user_states(user: User = Depends(get_current_user)):
    """Get all property states for current user."""
    states = await user_state_service.get_all_user_states(user.user_id)
    return {"user_id": user.user_id, "states": states, "count": len(states)}


@api_router.post("/user-state/{property_id}/close-floors")
async def close_floors(
    property_id: str,
    request: CloseFloorsRequest,
    user: User = Depends(get_current_user)
):
    """Close specific floors for a property (user-scoped). Logged to change history."""
    # Validate property exists
    prop = property_store.get_by_id(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Validate floor numbers
    max_floors = prop.get("floors", 0)
    invalid_floors = [f for f in request.floors if f < 1 or f > max_floors]
    if invalid_floors:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid floor numbers: {invalid_floors}. Property has floors 1-{max_floors}"
        )
    
    result = await user_state_service.close_floors(
        user.user_id, 
        property_id, 
        request.floors,
        session_id=request.session_id,
        metadata={"source": "api", "property_name": prop.get("name")}
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to close floors"))
    
    # Get updated analytics
    state = await user_state_service.get_user_state(user.user_id, property_id)
    analytics = await _get_property_analytics_with_override(prop, state)
    
    return {
        **result,
        "analytics": analytics
    }


@api_router.post("/user-state/{property_id}/open-floors")
async def open_floors(
    property_id: str,
    request: CloseFloorsRequest,
    user: User = Depends(get_current_user)
):
    """Open (re-enable) specific floors for a property (user-scoped). Logged to change history."""
    prop = property_store.get_by_id(property_id)
    
    result = await user_state_service.open_floors(
        user.user_id, 
        property_id, 
        request.floors,
        session_id=request.session_id,
        metadata={"source": "api", "property_name": prop.get("name") if prop else None}
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to open floors"))
    
    # Get updated analytics
    state = await user_state_service.get_user_state(user.user_id, property_id)
    analytics = await _get_property_analytics_with_override(prop, state) if prop else {}
    
    return {
        **result,
        "analytics": analytics
    }


class ResetRequest(BaseModel):
    session_id: Optional[str] = None


@api_router.post("/user-state/{property_id}/reset")
async def reset_property_state(
    property_id: str,
    request: Optional[ResetRequest] = None,
    user: User = Depends(get_current_user)
):
    """Reset user's property state to default (remove all overrides). Logged to change history."""
    session_id = request.session_id if request else None
    result = await user_state_service.reset_property_state(user.user_id, property_id, session_id=session_id)
    return result


@api_router.post("/user-state/reset-all")
async def reset_all_user_states(
    request: Optional[ResetRequest] = None,
    user: User = Depends(get_current_user)
):
    """Reset all property states for current user. Logged to change history."""
    session_id = request.session_id if request else None
    result = await user_state_service.reset_all_user_states(user.user_id, session_id=session_id)
    return result


async def _get_property_analytics_with_override(
    prop: Dict[str, Any],
    user_state: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Calculate property analytics with user override applied."""
    digital_twin = prop.get("digital_twin", {})
    daily_data = digital_twin.get("daily_history", [])
    recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
    
    closed_floors = user_state.get("closed_floors", []) if user_state else []
    total_floors = prop.get("floors", 0)
    active_floors = total_floors - len(closed_floors)
    
    # Calculate adjusted metrics
    if closed_floors:
        # Simulate redistribution
        redistribution = IntelligenceEngine.calculate_redistribution_efficiency(
            prop, closed_floors
        )
        financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
        
        # Calculate savings from closed floors
        savings_per_floor = (financials["energy_cost"] + financials["maintenance_cost"]) / total_floors
        monthly_savings = savings_per_floor * len(closed_floors) * 0.7  # 70% realized savings
        
        # Energy calculations
        baseline_energy = prop.get("baseline_energy_intensity", 150) * total_floors * 30
        reduced_energy = baseline_energy * (active_floors / total_floors)
        energy_reduction_pct = ((baseline_energy - reduced_energy) / baseline_energy) * 100
        
        return {
            "total_floors": total_floors,
            "active_floors": active_floors,
            "closed_floors": closed_floors,
            "redistribution_efficiency": redistribution["efficiency"],
            "new_occupancy_per_floor": redistribution["new_avg_occupancy"],
            "monthly_savings": round(monthly_savings, 2),
            "energy_reduction_pct": round(energy_reduction_pct, 1),
            "carbon_reduction_kg": round(energy_reduction_pct * 10, 1),
            "risk_level": redistribution.get("risk_level", "low"),
            "efficiency_score_before": IntelligenceEngine.calculate_efficiency_score(prop),
            "efficiency_score_after": min(100, IntelligenceEngine.calculate_efficiency_score(prop) + len(closed_floors) * 3),
            "confidence_score": 0.85 if len(closed_floors) <= 3 else 0.75
        }
    else:
        financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
        return {
            "total_floors": total_floors,
            "active_floors": total_floors,
            "closed_floors": [],
            "monthly_savings": 0,
            "energy_reduction_pct": 0,
            "carbon_reduction_kg": 0,
            "efficiency_score": IntelligenceEngine.calculate_efficiency_score(prop),
            "financials": financials
        }


# ==================== PDF REPORT ROUTES ====================

@api_router.get("/reports/property/{property_id}/pdf")
async def download_property_pdf(
    property_id: str,
    user: User = Depends(get_current_user)
):
    """Generate and download property PDF report."""
    global _pdf_generator
    if not _pdf_generator:
        raise HTTPException(status_code=503, detail="PDF generator not available")
    
    prop = property_store.get_by_id(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Get user state
    user_state = await user_state_service.get_user_state(user.user_id, property_id)
    
    # Calculate financials
    digital_twin = prop.get("digital_twin", {})
    daily_data = digital_twin.get("daily_history", [])
    recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
    financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
    recommendations = IntelligenceEngine.generate_recommendations(prop)
    
    # Generate PDF
    pdf_bytes = _pdf_generator.generate_property_report(
        property_data=prop,
        financials=financials,
        recommendations=recommendations,
        user_state=user_state
    )
    
    filename = f"{prop['name'].replace(' ', '_')}_report.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@api_router.get("/reports/executive-summary/pdf")
async def download_executive_pdf(user: User = Depends(get_current_user)):
    """Generate and download executive summary PDF."""
    global _pdf_generator
    if not _pdf_generator:
        raise HTTPException(status_code=503, detail="PDF generator not available")
    
    properties = property_store.get_all()
    
    # Get user states for all properties
    user_states = {}
    for prop in properties:
        state = await user_state_service.get_user_state(user.user_id, prop["property_id"])
        if state:
            user_states[prop["property_id"]] = state
    
    # Calculate portfolio metrics
    total_revenue = 0
    total_profit = 0
    total_occupancy = 0
    property_revenues = {}
    
    for prop in properties:
        digital_twin = prop.get("digital_twin", {})
        daily_data = digital_twin.get("daily_history", [])
        recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
        
        financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
        total_revenue += financials["revenue"]
        total_profit += financials["profit"]
        total_occupancy += recent_occupancy
        property_revenues[prop["property_id"]] = financials["revenue"]
    
    portfolio_metrics = {
        "total_revenue": total_revenue,
        "total_profit": total_profit,
        "avg_occupancy": (total_occupancy / len(properties) * 100) if properties else 0,
        "property_revenues": property_revenues
    }
    
    # Generate PDF
    pdf_bytes = _pdf_generator.generate_executive_summary(
        properties=properties,
        portfolio_metrics=portfolio_metrics,
        user_states=user_states
    )
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=executive_summary.pdf"}
    )


@api_router.get("/reports/executive-summary-full/pdf")
async def download_executive_full_pdf(user: User = Depends(get_current_user)):
    """
    Generate and download comprehensive executive summary PDF.
    
    Includes:
    - Savings potential (monthly/annual)
    - Carbon reduction
    - Efficiency gains
    - Top strategic actions
    - Portfolio benchmarking
    - High/Low performing properties
    """
    global _pdf_generator
    if not _pdf_generator:
        raise HTTPException(status_code=503, detail="PDF generator not available")
    
    try:
        # Fetch executive data
        properties = property_store.get_all()
        
        # Calculate executive data
        total_monthly_savings = 0
        total_annual_savings = 0
        total_carbon = 0
        total_efficiency = 0
        top_actions = []
        
        for prop in properties:
            insight = IntelligenceEngine.generate_copilot_insight(prop)
            recommendations = IntelligenceEngine.generate_recommendations(prop)
            
            total_monthly_savings += insight.get("monthly_savings", 0)
            total_carbon += insight.get("carbon_impact_kg", 0)
            total_efficiency += insight.get("efficiency_score_change", {}).get("improvement", 0)
            
            # Get top action for this property
            if recommendations:
                top_rec = max(recommendations, key=lambda x: x.get("financial_impact", 0))
                top_actions.append({
                    "property_name": prop["name"],
                    "action": top_rec.get("title", ""),
                    "type": top_rec.get("type", "optimization"),
                    "impact": top_rec.get("financial_impact", 0)
                })
        
        total_annual_savings = total_monthly_savings * 12
        avg_efficiency = total_efficiency / len(properties) if properties else 0
        
        # Sort and limit top actions
        top_actions = sorted(top_actions, key=lambda x: x["impact"], reverse=True)[:5]
        
        # Create executive data structure
        executive_data = {
            "total_projected_monthly_savings": total_monthly_savings,
            "total_projected_annual_savings": total_annual_savings,
            "total_carbon_reduction_kg": total_carbon,
            "avg_efficiency_improvement": avg_efficiency,
            "properties_analyzed": len(properties),
            "top_strategic_actions": top_actions,
            "executive_insight": f"Your portfolio of {len(properties)} properties has significant optimization potential. "
                                f"By implementing the recommended actions, you can achieve monthly savings of "
                                f"₹{total_monthly_savings:,.0f} and reduce carbon emissions by {total_carbon:,.0f} kg annually."
        }
        
        # Get benchmark data
        benchmarks = []
        for prop in properties:
            digital_twin = prop.get("digital_twin", {})
            daily_data = digital_twin.get("daily_history", [])
            recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
            
            financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
            efficiency = IntelligenceEngine.calculate_efficiency_score(prop)
            
            benchmarks.append({
                "property_id": prop["property_id"],
                "name": prop["name"],
                "location": prop["location"],
                "occupancy_rate": recent_occupancy,
                "profit_rank": 1,  # Will be calculated below
                "energy_efficiency_rank": 1,
                "sustainability_score_rank": 1,
                "carbon_rank": 1,
                "profit": financials["profit"],
                "efficiency": efficiency
            })
        
        # Calculate rankings
        benchmarks_sorted_profit = sorted(benchmarks, key=lambda x: x["profit"], reverse=True)
        benchmarks_sorted_efficiency = sorted(benchmarks, key=lambda x: x["efficiency"], reverse=True)
        
        for i, b in enumerate(benchmarks_sorted_profit, 1):
            for bench in benchmarks:
                if bench["property_id"] == b["property_id"]:
                    bench["profit_rank"] = i
                    bench["carbon_rank"] = i  # Using same as profit for simplicity
                    break
        
        for i, b in enumerate(benchmarks_sorted_efficiency, 1):
            for bench in benchmarks:
                if bench["property_id"] == b["property_id"]:
                    bench["energy_efficiency_rank"] = i
                    bench["sustainability_score_rank"] = i
                    break
        
        # Generate comprehensive PDF
        pdf_bytes = _pdf_generator.generate_executive_summary_full(
            executive_data=executive_data,
            benchmarks=benchmarks,
            properties=properties
        )
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=PropTech_Executive_Summary.pdf"}
        )
        
    except Exception as e:
        logger.error(f"Error generating executive PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


@api_router.get("/reports/energy/{property_id}/pdf")
async def download_energy_pdf(
    property_id: str,
    user: User = Depends(get_current_user)
):
    """Generate and download energy savings PDF report."""
    global _pdf_generator
    if not _pdf_generator:
        raise HTTPException(status_code=503, detail="PDF generator not available")
    
    prop = property_store.get_by_id(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Get user state
    user_state = await user_state_service.get_user_state(user.user_id, property_id)
    closed_floors = user_state.get("closed_floors", []) if user_state else []
    
    # Calculate energy metrics
    digital_twin = prop.get("digital_twin", {})
    daily_data = digital_twin.get("daily_history", [])
    recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
    
    savings = IntelligenceEngine.calculate_energy_savings(prop, recent_occupancy, closed_floors)
    
    total_floors = prop.get("floors", 0)
    baseline_kwh = prop.get("baseline_energy_intensity", 150) * total_floors * 30
    
    energy_metrics = {
        "baseline_kwh": baseline_kwh,
        "current_kwh": baseline_kwh - savings.get("energy_saved_kwh", 0),
        "reduction_pct": savings.get("energy_reduction_percentage", 0),
        "weekly_savings": savings.get("monthly_cost_savings", 0) / 4,
        "monthly_savings": savings.get("monthly_cost_savings", 0),
        "annual_savings": savings.get("monthly_cost_savings", 0) * 12,
        "carbon_reduction": savings.get("carbon_reduction_kg", 0)
    }
    
    pdf_bytes = _pdf_generator.generate_energy_report(
        property_data=prop,
        energy_metrics=energy_metrics,
        user_state=user_state
    )
    
    filename = f"{prop['name'].replace(' ', '_')}_energy_report.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==================== AUTH ROUTES ====================

@api_router.post("/auth/session")
async def create_session(request: Request, response: Response):
    """Exchange session_id for session_token"""
    body = await request.json()
    session_id = body.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    try:
        async with httpx.AsyncClient() as client:
            auth_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id},
                timeout=10.0
            )
            
            if auth_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid session_id")
            
            auth_data = auth_response.json()
    except httpx.RequestError as e:
        logger.error(f"Auth service error: {e}")
        raise HTTPException(status_code=500, detail="Authentication service unavailable")
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    email = auth_data.get("email")
    name = auth_data.get("name")
    picture = auth_data.get("picture")
    session_token = auth_data.get("session_token")
    
    existing_user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if existing_user:
        user_id = existing_user["user_id"]
    else:
        user_doc = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(user_doc)
    
    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await db.user_sessions.delete_many({"user_id": user_id})
    await db.user_sessions.insert_one(session_doc)
    
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )
    
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    
    return {"user": user_doc, "session_token": session_token}


@api_router.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    """Get current authenticated user"""
    return user.model_dump()


@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user and clear session"""
    session_token = request.cookies.get("session_token")
    
    if session_token:
        await db.user_sessions.delete_many({"session_token": session_token})
    
    response.delete_cookie(
        key="session_token",
        path="/",
        secure=True,
        samesite="none",
    )
    
    return {"message": "Logged out successfully"}


# ==================== PROPERTY ROUTES ====================

@api_router.get("/properties")
async def get_properties(user: User = Depends(get_current_user)):
    """Get all properties"""
    properties = property_store.get_all()
    
    result = []
    for prop in properties:
        digital_twin = prop.get("digital_twin", {})
        daily_data = digital_twin.get("daily_history", [])
        
        recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
        financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
        utilization = IntelligenceEngine.classify_utilization(recent_occupancy)
        
        result.append({
            **{k: v for k, v in prop.items() if k != "digital_twin"},
            "current_occupancy": round(recent_occupancy, 3),
            "utilization_status": utilization,
            "current_profit": financials["profit"],
            "current_revenue": financials["revenue"],
            "current_energy_cost": financials["energy_cost"],
        })
    
    return result


@api_router.get("/properties/{property_id}")
async def get_property(property_id: str, user: User = Depends(get_current_user)):
    """Get property details with full digital twin data"""
    prop = property_store.get_by_id(property_id)
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    digital_twin = prop.get("digital_twin", {})
    daily_data = digital_twin.get("daily_history", [])
    
    recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
    financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
    utilization = IntelligenceEngine.classify_utilization(recent_occupancy)
    forecast = IntelligenceEngine.calculate_7day_forecast(daily_data)
    
    floor_data = digital_twin.get("floor_data", [])
    total_floors = prop["floors"]
    optimal_floors = 0
    for f in floor_data:
        floor_capacity = sum(r["capacity"] for r in f["rooms"])
        floor_occupancy = sum(r["current_occupancy"] for r in f["rooms"])
        floor_rate = floor_occupancy / floor_capacity if floor_capacity > 0 else 0
        if 0.4 <= floor_rate <= 0.85:
            optimal_floors += 1
    
    efficiency_score = round((optimal_floors / total_floors) * 100, 1) if total_floors > 0 else 0
    
    return {
        **prop,
        "current_occupancy": round(recent_occupancy, 3),
        "utilization_status": utilization,
        "financials": financials,
        "forecast": forecast,
        "efficiency_score": efficiency_score,
        "optimal_floors": optimal_floors,
    }


@api_router.post("/properties")
async def add_property(prop_data: PropertyCreate, user: User = Depends(get_current_user)):
    """Add a new property"""
    new_prop = property_store.add_property(prop_data.model_dump())
    return new_prop


# ==================== ANALYTICS ROUTES ====================

@api_router.get("/analytics/dashboard")
async def get_dashboard_analytics(user: User = Depends(get_current_user)):
    """Get dashboard KPIs and summary"""
    properties = property_store.get_all()
    
    total_revenue = 0
    total_energy_cost = 0
    total_maintenance = 0
    total_profit = 0
    total_capacity = 0
    total_occupied = 0
    total_carbon = 0
    
    property_metrics = []
    
    for prop in properties:
        digital_twin = prop.get("digital_twin", {})
        daily_data = digital_twin.get("daily_history", [])
        
        recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
        financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
        
        total_revenue += financials["revenue"]
        total_energy_cost += financials["energy_cost"]
        total_maintenance += financials["maintenance_cost"]
        total_profit += financials["profit"]
        total_capacity += financials["total_capacity"]
        total_occupied += financials["occupied_seats"]
        
        carbon = prop["baseline_energy_intensity"] * recent_occupancy * prop["floors"] * 0.82 * 30
        total_carbon += carbon
        
        property_metrics.append({
            "property_id": prop["property_id"],
            "name": prop["name"],
            "occupancy": round(recent_occupancy, 3),
            "profit": financials["profit"],
            "energy_cost": financials["energy_cost"],
            "utilization": IntelligenceEngine.classify_utilization(recent_occupancy),
        })
    
    overall_occupancy = total_occupied / total_capacity if total_capacity > 0 else 0
    
    potential_energy_savings = total_energy_cost * 0.15
    potential_carbon_reduction = total_carbon * 0.15
    
    return {
        "kpis": {
            "total_revenue": round(total_revenue, 2),
            "total_energy_cost": round(total_energy_cost, 2),
            "total_maintenance_cost": round(total_maintenance, 2),
            "total_profit": round(total_profit, 2),
            "overall_occupancy": round(overall_occupancy, 3),
            "total_capacity": total_capacity,
            "total_occupied": total_occupied,
            "property_count": len(properties),
            "total_carbon_kg": round(total_carbon, 2),
        },
        "optimization_potential": {
            "potential_monthly_savings": round(potential_energy_savings, 2),
            "potential_carbon_reduction_kg": round(potential_carbon_reduction, 2),
            "optimization_confidence": 0.85,
        },
        "property_metrics": property_metrics,
    }


@api_router.get("/analytics/portfolio-benchmark")
async def get_portfolio_benchmark(user: User = Depends(get_current_user)):
    """Get portfolio benchmarking with rankings"""
    properties = property_store.get_all()
    
    benchmarks = []
    
    for prop in properties:
        digital_twin = prop.get("digital_twin", {})
        daily_data = digital_twin.get("daily_history", [])
        
        recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
        financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
        
        energy_efficiency = 100 - (prop["baseline_energy_intensity"] / 2)
        sustainability_score = energy_efficiency * 0.4 + (1 - recent_occupancy * 0.3) * 100 * 0.3 + 50 * 0.3
        profit_score = (financials["profit"] / financials["revenue"]) * 100 if financials["revenue"] > 0 else 0
        carbon_intensity = prop["baseline_energy_intensity"] * recent_occupancy * 0.82
        
        benchmarks.append({
            "property_id": prop["property_id"],
            "name": prop["name"],
            "location": prop["location"],
            "profit": financials["profit"],
            "profit_margin": round(profit_score, 1),
            "energy_efficiency": round(energy_efficiency, 1),
            "sustainability_score": round(sustainability_score, 1),
            "carbon_intensity": round(carbon_intensity, 2),
            "occupancy_rate": round(recent_occupancy, 3),
        })
    
    for metric in ["profit", "energy_efficiency", "sustainability_score"]:
        sorted_benchmarks = sorted(benchmarks, key=lambda x: x[metric], reverse=True)
        for rank, b in enumerate(sorted_benchmarks, 1):
            for benchmark in benchmarks:
                if benchmark["property_id"] == b["property_id"]:
                    benchmark[f"{metric}_rank"] = rank
    
    sorted_carbon = sorted(benchmarks, key=lambda x: x["carbon_intensity"])
    for rank, b in enumerate(sorted_carbon, 1):
        for benchmark in benchmarks:
            if benchmark["property_id"] == b["property_id"]:
                benchmark["carbon_rank"] = rank
    
    return benchmarks


@api_router.post("/analytics/simulate-floor-closure")
async def simulate_floor_closure(request: FloorClosureRequest, user: User = Depends(get_current_user)):
    """Simulate what-if floor closure scenario"""
    prop = property_store.get_by_id(request.property_id)
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    max_floor = prop["floors"]
    for floor in request.floors_to_close:
        if floor < 1 or floor > max_floor:
            raise HTTPException(status_code=400, detail=f"Invalid floor number: {floor}")
    
    simulation = IntelligenceEngine.simulate_floor_closure(
        prop,
        request.floors_to_close,
        request.hybrid_intensity,
        request.target_occupancy
    )
    
    return simulation


@api_router.get("/analytics/energy-savings/{property_id}")
async def get_energy_savings(property_id: str, user: User = Depends(get_current_user)):
    """Get energy savings analysis for a property"""
    prop = property_store.get_by_id(property_id)
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    digital_twin = prop.get("digital_twin", {})
    daily_data = digital_twin.get("daily_history", [])
    
    recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
    
    scenarios = [
        {"floors_to_close": [], "label": "Current State"},
        {"floors_to_close": [prop["floors"]], "label": "Close 1 Floor"},
        {"floors_to_close": [prop["floors"], prop["floors"] - 1], "label": "Close 2 Floors"},
        {"floors_to_close": list(range(prop["floors"] - 2, prop["floors"] + 1)), "label": "Close 3 Floors"},
    ]
    
    results = []
    for scenario in scenarios:
        savings = IntelligenceEngine.calculate_energy_savings(
            prop, recent_occupancy, scenario["floors_to_close"]
        )
        results.append({
            "scenario": scenario["label"],
            "floors_closed": len(scenario["floors_to_close"]),
            **savings,
        })
    
    return {
        "property_id": property_id,
        "property_name": prop["name"],
        "current_occupancy": round(recent_occupancy, 3),
        "scenarios": results,
    }


# ==================== AI RISK ANALYSIS ROUTES ====================

@api_router.get("/ai/recommendations/{property_id}")
async def get_ai_recommendations(property_id: str, user: User = Depends(get_current_user)):
    """
    Get AI-powered recommendations for a property (5-6 recommendations).
    Uses OpenAI GPT for location-specific, contextual analysis.
    """
    prop = property_store.get_by_id(property_id)
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Get user's current state for this property
    user_state = await user_state_service.get_user_state(user.user_id, property_id)
    
    try:
        recommendations = await ai_risk_service.generate_property_recommendations(prop, user_state)
        return {
            "property_id": property_id,
            "property_name": prop["name"],
            "location": prop["location"],
            "recommendations": recommendations,
            "count": len(recommendations)
        }
    except Exception as e:
        logger.error(f"AI recommendation error: {e}")
        # Fallback to regular recommendations
        recs = IntelligenceEngine.generate_recommendations(prop)
        return {
            "property_id": property_id,
            "property_name": prop["name"],
            "location": prop["location"],
            "recommendations": recs,
            "count": len(recs),
            "fallback": True
        }


@api_router.get("/ai/risk-analysis/{property_id}")
async def get_ai_risk_analysis(property_id: str, user: User = Depends(get_current_user)):
    """
    Get comprehensive AI risk analysis for a property.
    Includes location-specific risks, mitigation strategies, and opportunities.
    """
    prop = property_store.get_by_id(property_id)
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Get user's current state
    user_state = await user_state_service.get_user_state(user.user_id, property_id)
    
    try:
        risk_analysis = await ai_risk_service.generate_risk_analysis(prop, user_state)
        return risk_analysis
    except Exception as e:
        logger.error(f"AI risk analysis error: {e}")
        # Generate fallback risk analysis
        loc_data = get_location_risks(prop.get("location", ""))
        return ai_risk_service._generate_fallback_risk_analysis(prop, loc_data)


@api_router.get("/ai/portfolio-risk")
async def get_portfolio_risk_analysis(user: User = Depends(get_current_user)):
    """
    Get AI risk analysis for entire portfolio.
    """
    properties = property_store.get_all()
    
    portfolio_risks = []
    total_risk_score = 0
    
    for prop in properties:
        user_state = await user_state_service.get_user_state(user.user_id, prop["property_id"])
        
        try:
            risk_analysis = await ai_risk_service.generate_risk_analysis(prop, user_state)
        except:
            loc_data = get_location_risks(prop.get("location", ""))
            risk_analysis = ai_risk_service._generate_fallback_risk_analysis(prop, loc_data)
        
        portfolio_risks.append({
            "property_id": prop["property_id"],
            "property_name": prop["name"],
            "location": prop["location"],
            "risk_score": risk_analysis.get("overall_risk_score", 50),
            "risk_level": risk_analysis.get("risk_level", "MEDIUM"),
            "top_risks": risk_analysis.get("key_risks", [])[:3]
        })
        total_risk_score += risk_analysis.get("overall_risk_score", 50)
    
    avg_risk = total_risk_score / len(properties) if properties else 0
    
    return {
        "portfolio_risk_score": round(avg_risk),
        "portfolio_risk_level": "CRITICAL" if avg_risk > 70 else "HIGH" if avg_risk > 55 else "MEDIUM" if avg_risk > 40 else "LOW",
        "properties": portfolio_risks,
        "total_properties": len(properties)
    }


@api_router.get("/ai/carbon-analysis/{property_id}")
async def get_carbon_analysis(property_id: str, user: User = Depends(get_current_user)):
    """
    Get location-adjusted carbon emissions analysis.
    Uses regional grid emission factors for accurate calculations.
    """
    prop = property_store.get_by_id(property_id)
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Get user's closed floors
    user_state = await user_state_service.get_user_state(user.user_id, property_id)
    closed_floors = user_state.get("closed_floors", []) if user_state else []
    
    # Calculate energy usage
    digital_twin = prop.get("digital_twin", {})
    daily_data = digital_twin.get("daily_history", [])
    recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
    
    daily_energy = prop["baseline_energy_intensity"] * recent_occupancy * prop["floors"]
    
    # Get carbon analysis
    carbon_data = calculate_adjusted_carbon(prop, daily_energy, closed_floors)
    
    return {
        "property_id": property_id,
        "property_name": prop["name"],
        **carbon_data
    }


@api_router.get("/analytics/dashboard-with-ai")
async def get_dashboard_with_ai_analytics(user: User = Depends(get_current_user)):
    """
    Enhanced dashboard with AI risk analysis for each property.
    Includes location-specific metrics and active optimization status.
    """
    properties = property_store.get_all()
    
    total_revenue = 0
    total_energy_cost = 0
    total_maintenance = 0
    total_profit = 0
    total_capacity = 0
    total_occupied = 0
    total_carbon = 0
    
    property_metrics = []
    active_optimizations = []
    
    for prop in properties:
        digital_twin = prop.get("digital_twin", {})
        daily_data = digital_twin.get("daily_history", [])
        
        # Get user's state for this property
        user_state = await user_state_service.get_user_state(user.user_id, prop["property_id"])
        closed_floors = user_state.get("closed_floors", []) if user_state else []
        
        # Adjust occupancy based on closed floors
        recent_occupancy = sum(d["occupancy_rate"] for d in daily_data[-7:]) / 7 if daily_data else 0.6
        
        active_floors = prop["floors"] - len(closed_floors)
        if len(closed_floors) > 0 and active_floors > 0:
            # Redistribute occupancy to remaining floors
            adjusted_occupancy = min(1.0, recent_occupancy * prop["floors"] / active_floors)
        else:
            adjusted_occupancy = recent_occupancy
        
        financials = IntelligenceEngine.calculate_financials(prop, recent_occupancy)
        
        # Adjust financials for closed floors
        if closed_floors:
            floor_ratio = active_floors / prop["floors"]
            financials["revenue"] *= floor_ratio
            financials["energy_cost"] *= floor_ratio
            financials["maintenance_cost"] *= floor_ratio
            financials["profit"] = financials["revenue"] - financials["energy_cost"] - financials["maintenance_cost"]
            financials["occupied_seats"] = int(financials["occupied_seats"] * floor_ratio)
            financials["total_capacity"] = int(financials["total_capacity"] * floor_ratio)
        
        total_revenue += financials["revenue"]
        total_energy_cost += financials["energy_cost"]
        total_maintenance += financials["maintenance_cost"]
        total_profit += financials["profit"]
        total_capacity += financials["total_capacity"]
        total_occupied += financials["occupied_seats"]
        
        # Calculate carbon with location-specific factor
        carbon_factor = get_carbon_factor(prop["location"])
        carbon = prop["baseline_energy_intensity"] * adjusted_occupancy * active_floors * carbon_factor * 30
        total_carbon += carbon
        
        # Get risk data
        loc_data = get_location_risks(prop["location"])
        risk_scores = [r['score'] for r in loc_data['risks'].values()]
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.5
        
        # Track active optimizations
        if closed_floors:
            savings_estimate = len(closed_floors) * 15000  # ~15k per floor/month
            active_optimizations.append({
                "property_id": prop["property_id"],
                "property_name": prop["name"],
                "closed_floors": closed_floors,
                "estimated_savings": savings_estimate,
                "efficiency_gain": len(closed_floors) * 5  # ~5% per floor
            })
        
        property_metrics.append({
            "property_id": prop["property_id"],
            "name": prop["name"],
            "location": prop["location"],
            "occupancy": round(adjusted_occupancy, 3),
            "efficiency": round(65 + adjusted_occupancy * 25 + len(closed_floors) * 5, 1),
            "profit": financials["profit"],
            "energy_cost": financials["energy_cost"],
            "carbon_kg": round(carbon, 2),
            "carbon_factor": carbon_factor,
            "utilization": IntelligenceEngine.classify_utilization(adjusted_occupancy),
            "risk_score": round(avg_risk * 100),
            "risk_level": "HIGH" if avg_risk > 0.65 else "MEDIUM" if avg_risk > 0.45 else "LOW",
            "top_risks": [{"name": k.replace('_', ' ').title(), "level": v['level']} 
                        for k, v in sorted(loc_data['risks'].items(), key=lambda x: x[1]['score'], reverse=True)[:3]],
            "closed_floors": closed_floors,
            "active_floors": active_floors,
            "total_floors": prop["floors"]
        })
    
    overall_occupancy = total_occupied / total_capacity if total_capacity > 0 else 0
    
    potential_energy_savings = total_energy_cost * 0.15
    potential_carbon_reduction = total_carbon * 0.15
    
    # Calculate total realized savings from active optimizations
    total_realized_savings = sum(opt["estimated_savings"] for opt in active_optimizations)
    
    return {
        "kpis": {
            "total_revenue": round(total_revenue, 2),
            "total_energy_cost": round(total_energy_cost, 2),
            "total_maintenance_cost": round(total_maintenance, 2),
            "total_profit": round(total_profit, 2),
            "overall_occupancy": round(overall_occupancy, 3),
            "total_capacity": total_capacity,
            "total_occupied": total_occupied,
            "property_count": len(properties),
            "total_carbon_kg": round(total_carbon, 2),
        },
        "optimization_potential": {
            "potential_monthly_savings": round(potential_energy_savings, 2),
            "potential_carbon_reduction_kg": round(potential_carbon_reduction, 2),
            "optimization_confidence": 0.85,
        },
        "active_optimizations": {
            "count": len(active_optimizations),
            "total_closed_floors": sum(len(opt["closed_floors"]) for opt in active_optimizations),
            "realized_monthly_savings": total_realized_savings,
            "details": active_optimizations
        },
        "property_metrics": property_metrics,
    }


# ==================== RECOMMENDATIONS ROUTES ====================

@api_router.get("/recommendations/{property_id}")
async def get_recommendations(property_id: str, user: User = Depends(get_current_user)):
    """Get AI recommendations for a property"""
    prop = property_store.get_by_id(property_id)
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    recommendations = IntelligenceEngine.generate_recommendations(prop)
    return recommendations


@api_router.get("/copilot/executive-summary")
async def get_executive_summary(user: User = Depends(get_current_user)):
    """Get executive summary across all properties"""
    properties = property_store.get_all()
    
    total_savings_potential = 0
    total_carbon_reduction = 0
    total_efficiency_improvement = 0
    top_actions = []
    
    for prop in properties:
        insight = IntelligenceEngine.generate_copilot_insight(prop)
        recommendations = IntelligenceEngine.generate_recommendations(prop)
        
        total_savings_potential += insight["monthly_savings"]
        total_carbon_reduction += insight["carbon_impact_kg"]
        total_efficiency_improvement += insight["efficiency_score_change"]["improvement"]
        
        if recommendations:
            top_rec = max(recommendations, key=lambda x: x["financial_impact"])
            top_actions.append({
                "property_name": prop["name"],
                "action": top_rec["title"],
                "impact": top_rec["financial_impact"],
                "type": top_rec["type"],
            })
    
    top_actions = sorted(top_actions, key=lambda x: x["impact"], reverse=True)[:5]
    
    avg_efficiency_improvement = total_efficiency_improvement / len(properties) if properties else 0
    
    return {
        "total_projected_monthly_savings": round(total_savings_potential, 2),
        "total_projected_annual_savings": round(total_savings_potential * 12, 2),
        "total_carbon_reduction_kg": round(total_carbon_reduction, 2),
        "avg_efficiency_improvement": round(avg_efficiency_improvement, 1),
        "properties_analyzed": len(properties),
        "top_strategic_actions": top_actions,
        "executive_insight": f"Across {len(properties)} properties, implementing recommended optimizations could save ₹{round(total_savings_potential / 100000, 2)} Lakhs monthly and reduce carbon emissions by {round(total_carbon_reduction / 1000, 2)} tons.",
    }


@api_router.get("/copilot/{property_id}")
async def get_copilot_insight(property_id: str, user: User = Depends(get_current_user)):
    """Get copilot-style insight for a property"""
    prop = property_store.get_by_id(property_id)
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    insight = IntelligenceEngine.generate_copilot_insight(prop)
    return insight


# ==================== ROOT ROUTES ====================

@api_router.get("/")
async def root():
    return {"message": "PropTech Decision Copilot API", "version": "1.1.0", "mcp_enabled": True}


@api_router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global alert scheduler instance
_alert_scheduler = None
_whatsapp_linking_service = None
_command_parser = None
_pdf_generator = None
_change_log_service = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global _alert_scheduler, _whatsapp_linking_service, _command_parser, _pdf_generator, _change_log_service
    
    # Initialize change log service FIRST (other services depend on it)
    _change_log_service = init_change_log_service(db)
    await _change_log_service.ensure_indexes()
    
    # Link change log service to user state service
    set_change_log_service(_change_log_service)
    
    # Create indexes for user state service
    await user_state_service.ensure_indexes()
    
    # Create indexes for conversation history
    await conversation_history.ensure_indexes()
    
    # Initialize WhatsApp linking service
    _whatsapp_linking_service = init_whatsapp_linking_service(db, whatsapp_service)
    await _whatsapp_linking_service.ensure_indexes()
    
    # Initialize command parser with properties
    properties = property_store.get_all()
    _command_parser = init_command_parser(properties)
    
    # Initialize PDF generator
    _pdf_generator = init_pdf_generator(whatsapp_service)
    
    # Initialize alert scheduler
    _alert_scheduler = init_alert_scheduler(
        db=db,
        whatsapp_service=whatsapp_service,
        property_store=property_store,
        intelligence_engine=IntelligenceEngine,
        check_interval=int(os.environ.get("ALERT_CHECK_INTERVAL", 1800))  # 30 min default
    )
    
    # Create indexes for alert scheduler
    await _alert_scheduler.ensure_indexes()
    
    # Start the scheduled alert checker (runs in background)
    _alert_scheduler.start()
    
    logger.info("PropTech Decision Copilot started - All services active (with change logging)")


@app.on_event("shutdown")
async def shutdown_db_client():
    """Cleanup on shutdown."""
    global _alert_scheduler
    
    # Stop alert scheduler
    if _alert_scheduler:
        _alert_scheduler.stop()
        logger.info("Alert scheduler stopped")
    
    # Close MongoDB connection
    client.close()
    logger.info("MongoDB connection closed")
