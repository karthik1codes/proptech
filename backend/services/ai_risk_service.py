"""
AI Risk Analysis Service
Uses OpenAI GPT via Emergent Integrations for property-specific risk analysis,
recommendations, and mitigation strategies based on location.
"""

import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
import asyncio

logger = logging.getLogger(__name__)

# Location-specific data for Indian cities
LOCATION_DATA = {
    "bangalore": {
        "city": "Bangalore",
        "state": "Karnataka",
        "region": "South",
        "grid_emission_factor": 0.82,  # kg CO2/kWh - Southern grid
        "risks": {
            "water_scarcity": {"level": "high", "score": 0.8},
            "traffic_congestion": {"level": "high", "score": 0.85},
            "it_sector_dependency": {"level": "medium", "score": 0.6},
            "seismic": {"level": "low", "score": 0.2},
            "flooding": {"level": "medium", "score": 0.45},
            "air_quality": {"level": "medium", "score": 0.5},
            "real_estate_volatility": {"level": "medium", "score": 0.55}
        },
        "climate": "tropical_savanna",
        "avg_temp": 24,
        "rainfall_mm": 970
    },
    "mumbai": {
        "city": "Mumbai",
        "state": "Maharashtra", 
        "region": "West",
        "grid_emission_factor": 0.79,  # kg CO2/kWh - Western grid
        "risks": {
            "flooding": {"level": "critical", "score": 0.95},
            "coastal_erosion": {"level": "high", "score": 0.75},
            "real_estate_costs": {"level": "critical", "score": 0.9},
            "traffic_congestion": {"level": "critical", "score": 0.92},
            "seismic": {"level": "medium", "score": 0.5},
            "cyclone": {"level": "medium", "score": 0.55},
            "air_quality": {"level": "high", "score": 0.7}
        },
        "climate": "tropical_monsoon",
        "avg_temp": 27,
        "rainfall_mm": 2400
    },
    "hyderabad": {
        "city": "Hyderabad",
        "state": "Telangana",
        "region": "South",
        "grid_emission_factor": 0.82,  # kg CO2/kWh - Southern grid
        "risks": {
            "drought": {"level": "high", "score": 0.75},
            "rapid_urbanization": {"level": "high", "score": 0.8},
            "water_scarcity": {"level": "high", "score": 0.7},
            "heat_waves": {"level": "high", "score": 0.72},
            "flooding": {"level": "medium", "score": 0.5},
            "seismic": {"level": "low", "score": 0.25},
            "air_quality": {"level": "medium", "score": 0.45}
        },
        "climate": "semi_arid",
        "avg_temp": 26,
        "rainfall_mm": 800
    }
}

def get_location_key(location: str) -> str:
    """Extract city key from location string."""
    location_lower = location.lower()
    if "bangalore" in location_lower or "bengaluru" in location_lower:
        return "bangalore"
    elif "mumbai" in location_lower:
        return "mumbai"
    elif "hyderabad" in location_lower:
        return "hyderabad"
    return "bangalore"  # Default

def get_carbon_factor(location: str) -> float:
    """Get regional grid emission factor for carbon calculations."""
    loc_key = get_location_key(location)
    return LOCATION_DATA.get(loc_key, LOCATION_DATA["bangalore"])["grid_emission_factor"]

def get_location_risks(location: str) -> Dict:
    """Get location-specific risk data."""
    loc_key = get_location_key(location)
    return LOCATION_DATA.get(loc_key, LOCATION_DATA["bangalore"])


class AIRiskAnalysisService:
    """Service for AI-powered risk analysis using OpenAI GPT."""
    
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        self._chat = None
    
    def _get_chat(self, session_id: str, system_message: str):
        """Initialize LLM chat with OpenAI."""
        from emergentintegrations.llm.chat import LlmChat
        
        chat = LlmChat(
            api_key=self.api_key,
            session_id=session_id,
            system_message=system_message
        ).with_model("openai", "gpt-4o")  # Using gpt-4o for cost efficiency
        
        return chat
    
    async def generate_property_recommendations(
        self, 
        property_data: Dict,
        user_state: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Generate 5-6 AI-powered recommendations for a property based on:
        - Property location and type
        - Current occupancy and efficiency
        - Location-specific risks
        - User's optimization state (closed floors)
        """
        
        location = property_data.get("location", "")
        loc_data = get_location_risks(location)
        closed_floors = user_state.get("closed_floors", []) if user_state else []
        
        # Build context for GPT
        property_context = f"""
Property: {property_data.get('name')}
Location: {property_data.get('location')}
Type: {property_data.get('type')}
Floors: {property_data.get('floors')}
Current Occupancy: {property_data.get('current_occupancy', 0.6) * 100:.1f}%
Efficiency Score: {property_data.get('efficiency_score', 70)}%
Energy Cost/Unit: ₹{property_data.get('energy_cost_per_unit', 8)}
Revenue/Seat: ₹{property_data.get('revenue_per_seat', 2500)}
Closed Floors: {closed_floors if closed_floors else 'None'}

Location Risk Profile ({loc_data['city']}):
- Climate: {loc_data['climate']}
- Annual Rainfall: {loc_data['rainfall_mm']}mm
- Grid Emission Factor: {loc_data['grid_emission_factor']} kg CO2/kWh
"""
        
        # Add risk data
        risk_context = "\nKey Location Risks:\n"
        for risk_name, risk_info in loc_data['risks'].items():
            risk_context += f"- {risk_name.replace('_', ' ').title()}: {risk_info['level'].upper()} (Score: {risk_info['score']})\n"
        
        system_prompt = """You are an expert PropTech advisor specializing in commercial real estate optimization in India. 
Generate exactly 6 actionable recommendations for property optimization.

Each recommendation must include:
1. type: One of [Floor Consolidation, Energy Optimization, Risk Mitigation, Sustainability, Hybrid Optimization, Capacity Expansion, Cost Reduction, Revenue Enhancement]
2. priority: High, Medium, or Low
3. title: Brief actionable title (max 15 words)
4. description: Detailed explanation (2-3 sentences)
5. financial_impact: Monthly savings/revenue in INR (realistic number)
6. energy_reduction_percent: Expected energy reduction (0-30%)
7. carbon_reduction_kg: Monthly CO2 reduction in kg
8. efficiency_improvement: Percentage points improvement (0-15%)
9. confidence_score: Your confidence (0.7-0.95)
10. risk_factor: The location risk this addresses (if applicable)
11. mitigation_strategy: How to implement this recommendation

Focus on location-specific risks and opportunities. Be specific to Indian market conditions.
Return valid JSON array only, no markdown."""

        user_prompt = f"""{property_context}
{risk_context}

Generate 6 recommendations addressing:
1. Energy and cost optimization
2. Location-specific risk mitigation
3. Sustainability improvements
4. Operational efficiency
5. Revenue optimization
6. Future-proofing

Return as JSON array."""

        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            chat = self._get_chat(
                session_id=f"rec_{property_data.get('property_id', 'unknown')}_{datetime.now().timestamp()}",
                system_message=system_prompt
            )
            
            response = await chat.send_message(UserMessage(text=user_prompt))
            
            # Parse JSON response
            recommendations = json.loads(response.strip())
            
            # Ensure each recommendation has required fields
            for i, rec in enumerate(recommendations):
                rec["id"] = f"rec_{property_data.get('property_id', 'prop')}_{i+1}"
                rec["property_id"] = property_data.get("property_id")
                rec["generated_at"] = datetime.now(timezone.utc).isoformat()
                rec["ai_generated"] = True
            
            return recommendations[:6]
            
        except Exception as e:
            logger.error(f"AI recommendation generation failed: {e}")
            # Return fallback recommendations based on location data
            return self._generate_fallback_recommendations(property_data, loc_data, closed_floors)
    
    async def generate_risk_analysis(
        self,
        property_data: Dict,
        user_state: Optional[Dict] = None
    ) -> Dict:
        """
        Generate comprehensive AI risk analysis for a property.
        """
        
        location = property_data.get("location", "")
        loc_data = get_location_risks(location)
        closed_floors = user_state.get("closed_floors", []) if user_state else []
        
        property_context = f"""
Property: {property_data.get('name')}
Location: {property_data.get('location')} ({loc_data['city']}, {loc_data['state']})
Type: {property_data.get('type')}
Total Floors: {property_data.get('floors')}
Active Floors: {property_data.get('floors', 0) - len(closed_floors)}
Closed Floors: {closed_floors if closed_floors else 'None'}
Current Occupancy: {property_data.get('current_occupancy', 0.6) * 100:.1f}%
"""
        
        system_prompt = """You are an expert real estate risk analyst specializing in Indian commercial properties.
Analyze the property and provide a comprehensive risk assessment.

Return a JSON object with:
1. overall_risk_score: 0-100
2. risk_level: "LOW", "MEDIUM", "HIGH", or "CRITICAL"
3. key_risks: Array of top 5 risks with {name, severity, probability, impact, description}
4. mitigation_strategies: Array of specific actions to reduce risks
5. opportunities: Array of potential opportunities based on location
6. climate_resilience_score: 0-100
7. financial_risk_assessment: Brief analysis of financial risks
8. recommendation_summary: 2-3 sentence summary

Be specific to Indian market conditions and regulations. Return valid JSON only."""

        risk_context = f"""
Location Climate: {loc_data['climate']}
Annual Rainfall: {loc_data['rainfall_mm']}mm
Average Temperature: {loc_data['avg_temp']}°C
Grid Emission Factor: {loc_data['grid_emission_factor']} kg CO2/kWh

Known Location Risks:
"""
        for risk_name, risk_info in loc_data['risks'].items():
            risk_context += f"- {risk_name.replace('_', ' ').title()}: {risk_info['level']} (Score: {risk_info['score']})\n"

        user_prompt = f"""{property_context}
{risk_context}

Provide comprehensive risk analysis in JSON format."""

        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            chat = self._get_chat(
                session_id=f"risk_{property_data.get('property_id', 'unknown')}_{datetime.now().timestamp()}",
                system_message=system_prompt
            )
            
            response = await chat.send_message(UserMessage(text=user_prompt))
            
            # Parse JSON response
            risk_analysis = json.loads(response.strip())
            risk_analysis["property_id"] = property_data.get("property_id")
            risk_analysis["property_name"] = property_data.get("name")
            risk_analysis["location"] = property_data.get("location")
            risk_analysis["generated_at"] = datetime.now(timezone.utc).isoformat()
            risk_analysis["ai_generated"] = True
            
            return risk_analysis
            
        except Exception as e:
            logger.error(f"AI risk analysis failed: {e}")
            return self._generate_fallback_risk_analysis(property_data, loc_data)
    
    def _generate_fallback_recommendations(
        self, 
        property_data: Dict, 
        loc_data: Dict,
        closed_floors: List[int]
    ) -> List[Dict]:
        """Generate fallback recommendations without AI."""
        
        recommendations = []
        prop_id = property_data.get("property_id", "prop")
        
        # Get highest risks
        sorted_risks = sorted(
            loc_data['risks'].items(),
            key=lambda x: x[1]['score'],
            reverse=True
        )
        
        base_recs = [
            {
                "type": "Energy Optimization",
                "priority": "High",
                "title": f"Implement Smart HVAC for {loc_data['city']} Climate",
                "description": f"Given {loc_data['city']}'s {loc_data['climate'].replace('_', ' ')} climate with avg temp {loc_data['avg_temp']}°C, optimize HVAC scheduling based on occupancy patterns and weather forecasts.",
                "financial_impact": 45000,
                "energy_reduction_percent": 18,
                "carbon_reduction_kg": 2500,
                "efficiency_improvement": 8,
                "confidence_score": 0.88,
                "risk_factor": "energy_costs",
                "mitigation_strategy": "Install smart thermostats and integrate with BMS for automated climate control"
            },
            {
                "type": "Risk Mitigation",
                "priority": "High" if sorted_risks[0][1]['score'] > 0.7 else "Medium",
                "title": f"Address {sorted_risks[0][0].replace('_', ' ').title()} Risk",
                "description": f"The {sorted_risks[0][0].replace('_', ' ')} risk in {loc_data['city']} is {sorted_risks[0][1]['level']}. Implement preventive measures to protect property assets and ensure business continuity.",
                "financial_impact": 35000,
                "energy_reduction_percent": 5,
                "carbon_reduction_kg": 800,
                "efficiency_improvement": 5,
                "confidence_score": 0.85,
                "risk_factor": sorted_risks[0][0],
                "mitigation_strategy": f"Develop contingency plans and invest in infrastructure upgrades for {sorted_risks[0][0].replace('_', ' ')} mitigation"
            },
            {
                "type": "Sustainability",
                "priority": "Medium",
                "title": "Install Solar Panels for Grid Independence",
                "description": f"With grid emission factor of {loc_data['grid_emission_factor']} kg CO2/kWh in {loc_data['state']}, rooftop solar can significantly reduce carbon footprint and energy costs.",
                "financial_impact": 55000,
                "energy_reduction_percent": 25,
                "carbon_reduction_kg": 4200,
                "efficiency_improvement": 10,
                "confidence_score": 0.9,
                "risk_factor": "carbon_emissions",
                "mitigation_strategy": "Partner with solar providers for rooftop installation with net metering"
            },
            {
                "type": "Floor Consolidation",
                "priority": "High" if property_data.get('current_occupancy', 0.6) < 0.5 else "Medium",
                "title": "Optimize Floor Utilization Based on Occupancy",
                "description": f"Current occupancy at {property_data.get('current_occupancy', 0.6)*100:.0f}%. Consider consolidating operations to reduce energy waste and maintenance costs on underutilized floors.",
                "financial_impact": 65000,
                "energy_reduction_percent": 20,
                "carbon_reduction_kg": 3500,
                "efficiency_improvement": 12,
                "confidence_score": 0.87,
                "risk_factor": "operational_efficiency",
                "mitigation_strategy": "Implement hot-desking and flexible workspace allocation"
            },
            {
                "type": "Risk Mitigation", 
                "priority": "Medium",
                "title": f"Implement {sorted_risks[1][0].replace('_', ' ').title()} Protection",
                "description": f"Secondary risk factor: {sorted_risks[1][0].replace('_', ' ')} ({sorted_risks[1][1]['level']}). Proactive measures can prevent operational disruptions.",
                "financial_impact": 28000,
                "energy_reduction_percent": 3,
                "carbon_reduction_kg": 500,
                "efficiency_improvement": 4,
                "confidence_score": 0.82,
                "risk_factor": sorted_risks[1][0],
                "mitigation_strategy": f"Conduct risk assessment and implement targeted solutions for {sorted_risks[1][0].replace('_', ' ')}"
            },
            {
                "type": "Hybrid Optimization",
                "priority": "Medium",
                "title": "Implement Flexible Workspace Model",
                "description": "Adopt hybrid work policies with desk booking system to optimize space utilization and reduce per-seat costs while maintaining productivity.",
                "financial_impact": 40000,
                "energy_reduction_percent": 12,
                "carbon_reduction_kg": 1800,
                "efficiency_improvement": 7,
                "confidence_score": 0.84,
                "risk_factor": "space_utilization",
                "mitigation_strategy": "Deploy workspace management software and establish clear hybrid work policies"
            }
        ]
        
        for i, rec in enumerate(base_recs):
            rec["id"] = f"rec_{prop_id}_{i+1}"
            rec["property_id"] = prop_id
            rec["generated_at"] = datetime.now(timezone.utc).isoformat()
            rec["ai_generated"] = False
            recommendations.append(rec)
        
        return recommendations
    
    def _generate_fallback_risk_analysis(self, property_data: Dict, loc_data: Dict) -> Dict:
        """Generate fallback risk analysis without AI."""
        
        # Calculate overall risk from location data
        risk_scores = [r['score'] for r in loc_data['risks'].values()]
        avg_risk = sum(risk_scores) / len(risk_scores)
        
        risk_level = "LOW"
        if avg_risk > 0.7:
            risk_level = "CRITICAL"
        elif avg_risk > 0.55:
            risk_level = "HIGH"
        elif avg_risk > 0.4:
            risk_level = "MEDIUM"
        
        sorted_risks = sorted(
            loc_data['risks'].items(),
            key=lambda x: x[1]['score'],
            reverse=True
        )[:5]
        
        key_risks = [
            {
                "name": risk[0].replace('_', ' ').title(),
                "severity": risk[1]['level'].upper(),
                "probability": risk[1]['score'],
                "impact": "HIGH" if risk[1]['score'] > 0.7 else "MEDIUM" if risk[1]['score'] > 0.4 else "LOW",
                "description": f"{risk[0].replace('_', ' ').title()} is a {risk[1]['level']} concern in {loc_data['city']}"
            }
            for risk in sorted_risks
        ]
        
        return {
            "property_id": property_data.get("property_id"),
            "property_name": property_data.get("name"),
            "location": property_data.get("location"),
            "overall_risk_score": int(avg_risk * 100),
            "risk_level": risk_level,
            "key_risks": key_risks,
            "mitigation_strategies": [
                f"Implement {sorted_risks[0][0].replace('_', ' ')} mitigation measures",
                "Develop comprehensive business continuity plan",
                "Invest in infrastructure resilience upgrades",
                "Establish emergency response protocols",
                "Regular risk assessments and monitoring"
            ],
            "opportunities": [
                f"Leverage {loc_data['city']}'s growing tech ecosystem",
                "Access to skilled workforce in the region",
                f"Government incentives for green buildings in {loc_data['state']}"
            ],
            "climate_resilience_score": 100 - int(avg_risk * 100),
            "financial_risk_assessment": f"Property in {loc_data['city']} faces {risk_level.lower()} financial risk due to {sorted_risks[0][0].replace('_', ' ')} and related factors.",
            "recommendation_summary": f"Focus on mitigating {sorted_risks[0][0].replace('_', ' ')} risk which is the primary concern. Implement sustainability measures to reduce carbon footprint and operational costs.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "ai_generated": False
        }


# Global service instance
ai_risk_service = AIRiskAnalysisService()


def calculate_adjusted_carbon(
    property_data: Dict,
    energy_usage: float,
    closed_floors: List[int] = None
) -> Dict:
    """
    Calculate carbon emissions adjusted for location and floor closures.
    """
    location = property_data.get("location", "")
    carbon_factor = get_carbon_factor(location)
    loc_data = get_location_risks(location)
    
    total_floors = property_data.get("floors", 1)
    active_floors = total_floors - len(closed_floors or [])
    
    # Adjust energy for active floors
    adjusted_energy = energy_usage * (active_floors / total_floors) if total_floors > 0 else energy_usage
    
    # Calculate carbon
    monthly_carbon_kg = adjusted_energy * carbon_factor * 30
    annual_carbon_tons = monthly_carbon_kg * 12 / 1000
    
    return {
        "location": location,
        "city": loc_data["city"],
        "region": loc_data["region"],
        "grid_emission_factor": carbon_factor,
        "monthly_energy_kwh": adjusted_energy * 30,
        "monthly_carbon_kg": round(monthly_carbon_kg, 2),
        "annual_carbon_tons": round(annual_carbon_tons, 2),
        "active_floors": active_floors,
        "total_floors": total_floors,
        "carbon_reduction_potential": round(monthly_carbon_kg * 0.25, 2)  # 25% reduction potential
    }
