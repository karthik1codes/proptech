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

# Import WhatsApp service
from services.whatsapp_service import whatsapp_service, WhatsAppService

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="PropTech Decision Copilot API")

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
            result_lines.append(f"### Impact Analysis")
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


# ==================== MCP ENDPOINT ====================

@api_router.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """
    MCP (Model Context Protocol) endpoint for AI assistant integration.
    Supports JSON-RPC style requests for property analytics tools.
    """
    response = MCPHandler.handle_request(request.model_dump())
    return response


# ==================== OPENAI MCP SERVER (EXCLUSIVE) ====================

class OpenAIMCPRequest(BaseModel):
    """Request model for OpenAI MCP endpoint"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: str
    params: Optional[Dict[str, Any]] = None

class OpenAIChatRequest(BaseModel):
    """Request model for chat completions"""
    messages: List[Dict[str, str]]
    session_id: Optional[str] = None
    system_message: Optional[str] = "You are a helpful AI assistant powered by OpenAI GPT-5.2."
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096

class OpenAIMCPServer:
    """
    OpenAI-Exclusive MCP Server
    Routes ALL model inference requests to OpenAI ChatGPT API ONLY.
    Single-provider architecture - No multi-model routing.
    """
    
    MCP_VERSION = "1.0.0"
    SERVER_NAME = "openai-mcp-server"
    PROVIDER = "openai"
    MODEL = "gpt-5.2"
    
    # Available tools exposed by this MCP server
    TOOLS = {
        "chat_completion": {
            "description": "Send a message to OpenAI GPT-5.2 and get a response. Single-turn or multi-turn conversations supported.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "description": "Array of message objects with 'role' and 'content' keys",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "enum": ["user", "assistant", "system"]},
                                "content": {"type": "string"}
                            },
                            "required": ["role", "content"]
                        }
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session ID for conversation tracking"
                    },
                    "system_message": {
                        "type": "string",
                        "description": "Optional system message to set assistant behavior"
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Sampling temperature (0-2). Higher = more creative",
                        "default": 0.7
                    }
                },
                "required": ["messages"]
            }
        },
        "get_model_info": {
            "description": "Get information about the configured OpenAI model",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        "health_check": {
            "description": "Check if the OpenAI MCP server is operational",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
    
    # Store active chat sessions
    _chat_sessions: Dict[str, LlmChat] = {}
    
    @classmethod
    def get_api_key(cls) -> str:
        """Get OpenAI API key from environment"""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        return api_key
    
    @classmethod
    def get_or_create_chat(cls, session_id: str, system_message: str) -> LlmChat:
        """Get existing chat session or create a new one"""
        if session_id not in cls._chat_sessions:
            chat = LlmChat(
                api_key=cls.get_api_key(),
                session_id=session_id,
                system_message=system_message
            ).with_model(cls.PROVIDER, cls.MODEL)
            cls._chat_sessions[session_id] = chat
        return cls._chat_sessions[session_id]
    
    @classmethod
    async def handle_request(cls, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process MCP request and return response"""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                return cls._handle_initialize(request_id)
            elif method == "tools/list":
                return cls._handle_tools_list(request_id)
            elif method == "tools/call":
                return await cls._handle_tools_call(request_id, params)
            elif method == "chat/completions":
                return await cls._handle_chat_completions(request_id, params)
            else:
                return cls._error_response(request_id, -32601, f"Method not found: {method}")
        except Exception as e:
            logger.error(f"OpenAI MCP error: {e}")
            return cls._error_response(request_id, -32603, str(e))
    
    @classmethod
    def _handle_initialize(cls, request_id: Optional[str]) -> Dict[str, Any]:
        """Handle MCP initialization - returns server capabilities"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": cls.MCP_VERSION,
                "serverInfo": {
                    "name": cls.SERVER_NAME,
                    "version": cls.MCP_VERSION,
                    "description": "OpenAI-Exclusive MCP Server - Routes ALL requests to OpenAI GPT-5.2 ONLY"
                },
                "capabilities": {
                    "tools": {"listChanged": False},
                    "provider": cls.PROVIDER,
                    "model": cls.MODEL,
                    "features": ["chat_completion", "multi_turn_conversation", "system_messages"]
                }
            }
        }
    
    @classmethod
    def _handle_tools_list(cls, request_id: Optional[str]) -> Dict[str, Any]:
        """Return list of available tools"""
        tools = []
        for name, info in cls.TOOLS.items():
            tools.append({
                "name": name,
                "description": info["description"],
                "inputSchema": info["inputSchema"]
            })
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools}
        }
    
    @classmethod
    async def _handle_tools_call(cls, request_id: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool invocation"""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        try:
            if tool_name == "chat_completion":
                result = await cls._tool_chat_completion(arguments)
            elif tool_name == "get_model_info":
                result = cls._tool_get_model_info()
            elif tool_name == "health_check":
                result = cls._tool_health_check()
            else:
                return cls._error_response(request_id, -32602, f"Unknown tool: {tool_name}")
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": result}],
                    "isError": False
                }
            }
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                    "isError": True
                }
            }
    
    @classmethod
    async def _handle_chat_completions(cls, request_id: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """Direct chat completions endpoint"""
        try:
            result = await cls._tool_chat_completion(params)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "model": cls.MODEL,
                    "provider": cls.PROVIDER,
                    "response": result,
                    "usage": {
                        "prompt_tokens": "N/A",
                        "completion_tokens": "N/A",
                        "total_tokens": "N/A"
                    }
                }
            }
        except Exception as e:
            return cls._error_response(request_id, -32603, str(e))
    
    @classmethod
    async def _tool_chat_completion(cls, arguments: Dict[str, Any]) -> str:
        """Execute chat completion using OpenAI GPT-5.2"""
        messages = arguments.get("messages", [])
        session_id = arguments.get("session_id", f"session_{uuid.uuid4().hex[:8]}")
        system_message = arguments.get("system_message", "You are a helpful AI assistant powered by OpenAI GPT-5.2.")
        
        if not messages:
            return "Error: No messages provided"
        
        # Get or create chat session
        chat = cls.get_or_create_chat(session_id, system_message)
        
        # Get the last user message
        last_user_msg = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break
        
        if not last_user_msg:
            return "Error: No user message found in messages array"
        
        # Send message to OpenAI
        user_message = UserMessage(text=last_user_msg)
        response = await chat.send_message(user_message)
        
        return response
    
    @classmethod
    def _tool_get_model_info(cls) -> str:
        """Return information about the configured model"""
        return f"""## OpenAI MCP Server - Model Information

**Provider:** {cls.PROVIDER}
**Model:** {cls.MODEL}
**Protocol Version:** {cls.MCP_VERSION}

### Capabilities
- Chat completions with GPT-5.2
- Multi-turn conversations
- System message customization
- Session-based conversation tracking

### Architecture
- **Single-Provider Design:** Routes ALL requests exclusively to OpenAI
- **No Multi-Model Routing:** GPT-5.2 only, no fallbacks
- **Secure Authentication:** API key stored securely in environment

### Rate Limits
Subject to OpenAI API rate limits for your account tier."""
    
    @classmethod
    def _tool_health_check(cls) -> str:
        """Check server health status"""
        try:
            api_key = cls.get_api_key()
            key_preview = f"{api_key[:10]}...{api_key[-4:]}" if len(api_key) > 14 else "***"
            return f"""## OpenAI MCP Server - Health Check

**Status:** ✅ Operational
**Provider:** {cls.PROVIDER}
**Model:** {cls.MODEL}
**API Key:** Configured ({key_preview})
**Active Sessions:** {len(cls._chat_sessions)}
**Timestamp:** {datetime.now(timezone.utc).isoformat()}"""
        except Exception as e:
            return f"""## OpenAI MCP Server - Health Check

**Status:** ❌ Error
**Error:** {str(e)}
**Timestamp:** {datetime.now(timezone.utc).isoformat()}"""
    
    @classmethod
    def _error_response(cls, request_id: Optional[str], code: int, message: str) -> Dict[str, Any]:
        """Generate JSON-RPC error response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }


# OpenAI MCP Endpoint
@api_router.post("/mcp/openai")
async def openai_mcp_endpoint(request: OpenAIMCPRequest):
    """
    OpenAI-Exclusive MCP Server Endpoint.
    Routes ALL model inference requests to OpenAI GPT-5.2 ONLY.
    Single-provider architecture - No multi-model routing.
    
    Supported methods:
    - initialize: Get server info and capabilities
    - tools/list: List available tools
    - tools/call: Execute a tool (chat_completion, get_model_info, health_check)
    - chat/completions: Direct chat completions
    """
    response = await OpenAIMCPServer.handle_request(request.model_dump())
    return response


# Direct Chat Completions Endpoint (OpenAI-style)
@api_router.post("/mcp/openai/chat/completions")
async def openai_chat_completions(request: OpenAIChatRequest):
    """
    Direct OpenAI Chat Completions endpoint.
    Simplified interface for chat requests without MCP wrapper.
    
    Example:
    {
        "messages": [{"role": "user", "content": "Hello!"}],
        "session_id": "my-session",
        "system_message": "You are helpful.",
        "temperature": 0.7
    }
    """
    try:
        session_id = request.session_id or f"session_{uuid.uuid4().hex[:8]}"
        chat = OpenAIMCPServer.get_or_create_chat(session_id, request.system_message)
        
        # Get the last user message
        last_user_msg = None
        for msg in reversed(request.messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break
        
        if not last_user_msg:
            raise HTTPException(status_code=400, detail="No user message found")
        
        user_message = UserMessage(text=last_user_msg)
        response = await chat.send_message(user_message)
        
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "model": OpenAIMCPServer.MODEL,
            "provider": OpenAIMCPServer.PROVIDER,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response
                },
                "finish_reason": "stop"
            }],
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Chat completions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
