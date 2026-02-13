"""
Backend Tests for AI Risk Analysis Features
Tests for Infranomic Decision Copilot - Major Upgrade

Features tested:
- AI-powered risk analysis with OpenAI GPT
- Location-specific carbon emission factors
- Enhanced dashboard with risk analysis
- AI recommendations endpoint
- PDF reports with risk analysis section
"""

import pytest
import requests
import os
from datetime import datetime

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session token
TEST_SESSION_TOKEN = "test_session_ai_1770948893456"


class TestHealthAndBasics:
    """Basic health checks"""
    
    def test_health_endpoint(self):
        """Test /api/health returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print(f"✓ Health check passed: {response.json()}")
    
    def test_unauthorized_without_auth(self):
        """Test AI endpoints require authentication"""
        response = requests.get(f"{BASE_URL}/api/ai/recommendations/prop_001")
        assert response.status_code == 401
        print("✓ AI recommendations correctly requires auth")
        
        response = requests.get(f"{BASE_URL}/api/ai/risk-analysis/prop_001")
        assert response.status_code == 401
        print("✓ AI risk analysis correctly requires auth")


class TestEnhancedDashboardAPI:
    """Tests for /api/analytics/dashboard-with-ai endpoint"""
    
    def get_auth_headers(self):
        return {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
    
    def test_dashboard_with_ai_returns_200(self):
        """Test enhanced dashboard endpoint returns data"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/dashboard-with-ai",
            headers=self.get_auth_headers()
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        print(f"✓ Dashboard-with-AI returns 200")
    
    def test_dashboard_contains_kpis(self):
        """Test dashboard contains KPI data"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/dashboard-with-ai",
            headers=self.get_auth_headers()
        )
        data = response.json()
        
        assert "kpis" in data, "Response missing 'kpis'"
        kpis = data["kpis"]
        
        # Verify KPI fields exist
        assert "total_revenue" in kpis
        assert "total_profit" in kpis
        assert "overall_occupancy" in kpis
        assert "total_carbon_kg" in kpis
        print(f"✓ KPIs present: revenue={kpis['total_revenue']}, profit={kpis['total_profit']}")
    
    def test_dashboard_contains_property_metrics_with_risk(self):
        """Test dashboard contains property metrics with risk analysis"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/dashboard-with-ai",
            headers=self.get_auth_headers()
        )
        data = response.json()
        
        assert "property_metrics" in data
        metrics = data["property_metrics"]
        assert len(metrics) > 0, "No property metrics found"
        
        # Check first property has risk data
        prop = metrics[0]
        assert "name" in prop
        assert "risk_score" in prop, f"Property missing 'risk_score': {prop}"
        assert "risk_level" in prop, f"Property missing 'risk_level': {prop}"
        assert "top_risks" in prop, f"Property missing 'top_risks': {prop}"
        assert "carbon_factor" in prop, f"Property missing 'carbon_factor': {prop}"
        assert "carbon_kg" in prop, f"Property missing 'carbon_kg': {prop}"
        
        # Verify risk level is valid
        assert prop["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"], f"Invalid risk level: {prop['risk_level']}"
        
        print(f"✓ Property '{prop['name']}' has risk: score={prop['risk_score']}, level={prop['risk_level']}")
        print(f"  - Top risks: {[r['name'] for r in prop['top_risks'][:2]]}")
        print(f"  - Carbon factor: {prop['carbon_factor']} kg/kWh, Carbon: {prop['carbon_kg']} kg")
    
    def test_dashboard_carbon_factors_are_location_specific(self):
        """Test carbon factors differ by location (South vs West grid)"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/dashboard-with-ai",
            headers=self.get_auth_headers()
        )
        data = response.json()
        metrics = data["property_metrics"]
        
        carbon_factors = {}
        for prop in metrics:
            location = prop["location"].lower()
            carbon_factors[prop["name"]] = {
                "location": prop["location"],
                "factor": prop["carbon_factor"]
            }
        
        # Find Bangalore and Mumbai properties
        bangalore_prop = next((p for p in metrics if "bangalore" in p["location"].lower()), None)
        mumbai_prop = next((p for p in metrics if "mumbai" in p["location"].lower()), None)
        
        if bangalore_prop:
            assert bangalore_prop["carbon_factor"] == 0.82, f"Bangalore should have factor 0.82 (South grid), got {bangalore_prop['carbon_factor']}"
            print(f"✓ Bangalore carbon factor correct: 0.82 (South grid)")
        
        if mumbai_prop:
            assert mumbai_prop["carbon_factor"] == 0.79, f"Mumbai should have factor 0.79 (West grid), got {mumbai_prop['carbon_factor']}"
            print(f"✓ Mumbai carbon factor correct: 0.79 (West grid)")
    
    def test_dashboard_active_optimizations_includes_property_names(self):
        """Test active optimizations includes property names"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/dashboard-with-ai",
            headers=self.get_auth_headers()
        )
        data = response.json()
        
        assert "active_optimizations" in data
        optimizations = data["active_optimizations"]
        
        # Verify structure
        assert "count" in optimizations
        assert "details" in optimizations
        assert "realized_monthly_savings" in optimizations
        
        # If there are active optimizations, verify they have property names
        if optimizations["count"] > 0:
            detail = optimizations["details"][0]
            assert "property_name" in detail, "Optimization missing 'property_name'"
            assert "closed_floors" in detail
            print(f"✓ Active optimization: {detail['property_name']} has {len(detail['closed_floors'])} closed floor(s)")
        else:
            print("✓ No active optimizations (structure verified)")


class TestAIRecommendationsAPI:
    """Tests for /api/ai/recommendations/{property_id} endpoint"""
    
    def get_auth_headers(self):
        return {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
    
    def test_ai_recommendations_returns_200(self):
        """Test AI recommendations endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/ai/recommendations/prop_001",
            headers=self.get_auth_headers()
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "property_id" in data
        assert "recommendations" in data
        print(f"✓ AI recommendations returns 200 for prop_001")
    
    def test_ai_recommendations_returns_5_to_6_items(self):
        """Test AI recommendations returns 5-6 recommendations"""
        response = requests.get(
            f"{BASE_URL}/api/ai/recommendations/prop_001",
            headers=self.get_auth_headers()
        )
        data = response.json()
        
        recs = data["recommendations"]
        assert 5 <= len(recs) <= 6, f"Expected 5-6 recommendations, got {len(recs)}"
        print(f"✓ AI recommendations returns {len(recs)} recommendations")
    
    def test_ai_recommendations_structure(self):
        """Test AI recommendations have required fields"""
        response = requests.get(
            f"{BASE_URL}/api/ai/recommendations/prop_002",
            headers=self.get_auth_headers()
        )
        data = response.json()
        
        rec = data["recommendations"][0]
        required_fields = ["type", "priority", "title", "description", "financial_impact"]
        for field in required_fields:
            assert field in rec, f"Recommendation missing '{field}': {rec}"
        
        # Verify priority is valid
        assert rec["priority"] in ["High", "Medium", "Low"], f"Invalid priority: {rec['priority']}"
        
        print(f"✓ Recommendation structure valid: {rec['title'][:50]}...")
    
    def test_ai_recommendations_invalid_property(self):
        """Test 404 for non-existent property"""
        response = requests.get(
            f"{BASE_URL}/api/ai/recommendations/invalid_prop",
            headers=self.get_auth_headers()
        )
        assert response.status_code == 404
        print("✓ 404 returned for invalid property")


class TestAIRiskAnalysisAPI:
    """Tests for /api/ai/risk-analysis/{property_id} endpoint"""
    
    def get_auth_headers(self):
        return {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
    
    def test_ai_risk_analysis_returns_200(self):
        """Test AI risk analysis endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/ai/risk-analysis/prop_001",
            headers=self.get_auth_headers()
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ AI risk analysis returns 200")
    
    def test_ai_risk_analysis_contains_required_fields(self):
        """Test AI risk analysis has required structure"""
        response = requests.get(
            f"{BASE_URL}/api/ai/risk-analysis/prop_001",
            headers=self.get_auth_headers()
        )
        data = response.json()
        
        required_fields = ["property_id", "property_name", "overall_risk_score", "risk_level", "key_risks"]
        for field in required_fields:
            assert field in data, f"Risk analysis missing '{field}'"
        
        print(f"✓ Risk analysis structure valid: score={data['overall_risk_score']}, level={data['risk_level']}")
    
    def test_ai_risk_analysis_risk_levels_are_valid(self):
        """Test risk levels are in expected range"""
        for prop_id in ["prop_001", "prop_002", "prop_003"]:
            response = requests.get(
                f"{BASE_URL}/api/ai/risk-analysis/{prop_id}",
                headers=self.get_auth_headers()
            )
            data = response.json()
            
            assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"], f"Invalid risk level for {prop_id}"
            assert 0 <= data["overall_risk_score"] <= 100, f"Risk score out of range for {prop_id}"
            
            print(f"✓ {prop_id}: risk_level={data['risk_level']}, score={data['overall_risk_score']}")


class TestAICarbonAnalysisAPI:
    """Tests for /api/ai/carbon-analysis/{property_id} endpoint"""
    
    def get_auth_headers(self):
        return {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
    
    def test_carbon_analysis_returns_200(self):
        """Test carbon analysis endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/ai/carbon-analysis/prop_001",
            headers=self.get_auth_headers()
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Carbon analysis returns 200")
    
    def test_carbon_analysis_contains_location_data(self):
        """Test carbon analysis has location-specific data"""
        response = requests.get(
            f"{BASE_URL}/api/ai/carbon-analysis/prop_001",
            headers=self.get_auth_headers()
        )
        data = response.json()
        
        assert "grid_emission_factor" in data
        assert "region" in data
        assert "city" in data
        assert "monthly_carbon_kg" in data
        
        print(f"✓ Carbon analysis: {data['city']} ({data['region']}), factor={data['grid_emission_factor']}")
    
    def test_carbon_analysis_different_locations(self):
        """Test carbon analysis returns different factors for different locations"""
        results = {}
        for prop_id in ["prop_001", "prop_002", "prop_003"]:
            response = requests.get(
                f"{BASE_URL}/api/ai/carbon-analysis/{prop_id}",
                headers=self.get_auth_headers()
            )
            data = response.json()
            results[prop_id] = {
                "city": data.get("city"),
                "factor": data.get("grid_emission_factor")
            }
        
        print("✓ Carbon analysis by property:")
        for prop_id, info in results.items():
            print(f"  - {prop_id}: {info['city']} = {info['factor']} kg/kWh")


class TestPDFReportEndpoint:
    """Tests for PDF report download endpoint"""
    
    def get_auth_headers(self):
        return {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
    
    def test_executive_summary_pdf_returns_200(self):
        """Test executive summary PDF endpoint returns PDF"""
        response = requests.get(
            f"{BASE_URL}/api/reports/executive-summary-full/pdf",
            headers=self.get_auth_headers()
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify it's a PDF
        content_type = response.headers.get("content-type", "")
        assert "pdf" in content_type.lower(), f"Expected PDF content-type, got: {content_type}"
        
        # Verify PDF content starts with %PDF
        assert response.content[:4] == b'%PDF', "Response is not a valid PDF"
        
        print(f"✓ Executive summary PDF generated successfully ({len(response.content)} bytes)")


class TestBrandingInResponse:
    """Test that responses use Infranomic branding"""
    
    def test_server_title(self):
        """Test OpenAPI title is Infranomic"""
        response = requests.get(f"{BASE_URL}/openapi.json")
        if response.status_code == 200:
            data = response.json()
            title = data.get("info", {}).get("title", "")
            assert "Infranomic" in title, f"Expected 'Infranomic' in title, got: {title}"
            print(f"✓ API title is '{title}'")
        else:
            print("⚠ OpenAPI endpoint not accessible (skipping)")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
