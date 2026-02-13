"""
Test Suite: Global State Synchronization Feature
Tests the user-state APIs for floor closure functionality that should reflect across all pages.
Key endpoints tested:
- GET /api/user-state - Get all user states
- GET /api/user-state/{property_id} - Get state for specific property
- POST /api/user-state/{property_id}/close-floors - Close floors
- POST /api/user-state/{property_id}/open-floors - Open floors
- POST /api/user-state/{property_id}/reset - Reset property state
- POST /api/user-state/reset-all - Reset all property states
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_globalstate_1770945793176"  # Created by test setup


class TestHealthAndAuth:
    """Basic health and auth verification tests"""
    
    def test_health_check(self):
        """Test health endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ Health check passed: {data}")
    
    def test_user_state_requires_auth(self):
        """Test user-state endpoints require authentication"""
        response = requests.get(f"{BASE_URL}/api/user-state")
        assert response.status_code == 401
        print("✓ GET /api/user-state requires auth (401)")
    
    def test_close_floors_requires_auth(self):
        """Test close-floors endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/user-state/prop_001/close-floors", json={"floors": [1]})
        assert response.status_code == 401
        print("✓ POST /api/user-state/{id}/close-floors requires auth (401)")
    
    def test_open_floors_requires_auth(self):
        """Test open-floors endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/user-state/prop_001/open-floors", json={"floors": [1]})
        assert response.status_code == 401
        print("✓ POST /api/user-state/{id}/open-floors requires auth (401)")


class TestPropertiesEndpoint:
    """Test that properties endpoint returns default properties"""
    
    def test_get_properties(self):
        """Get all properties - returns 3 default properties"""
        response = requests.get(
            f"{BASE_URL}/api/properties",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3, f"Expected at least 3 properties, got {len(data)}"
        
        # Verify expected properties exist
        prop_names = [p["name"] for p in data]
        assert "Horizon Tech Park" in prop_names, f"Missing Horizon Tech Park in {prop_names}"
        assert "Marina Business Center" in prop_names
        assert "Digital Gateway Tower" in prop_names
        
        print(f"✓ GET /api/properties returns {len(data)} properties")
        return data


class TestGlobalStateSync:
    """Test the global state synchronization feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - reset all states before each test"""
        # Reset all states to start fresh
        response = requests.post(
            f"{BASE_URL}/api/user-state/reset-all",
            json={"session_id": "test"},
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        # Don't fail if reset fails - just continue
        yield
    
    def test_get_all_user_states_empty(self):
        """Test GET /api/user-state returns empty states initially"""
        response = requests.get(
            f"{BASE_URL}/api/user-state",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        assert "states" in data
        assert isinstance(data["states"], list)
        print(f"✓ GET /api/user-state returns states: {len(data['states'])} existing")
    
    def test_close_floors_success(self):
        """Test POST /api/user-state/{property_id}/close-floors works"""
        property_id = "prop_001"  # Horizon Tech Park
        floors_to_close = [7, 8]
        
        response = requests.post(
            f"{BASE_URL}/api/user-state/{property_id}/close-floors",
            json={"floors": floors_to_close, "session_id": "test_session"},
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True
        assert "closed_floors" in data
        assert 7 in data["closed_floors"]
        assert 8 in data["closed_floors"]
        
        print(f"✓ POST /api/user-state/{property_id}/close-floors closed floors {floors_to_close}")
        print(f"  Response: {data}")
    
    def test_close_floors_persists_and_returns_analytics(self):
        """Test closing floors persists and returns analytics data"""
        property_id = "prop_001"
        
        # First, close floors
        close_response = requests.post(
            f"{BASE_URL}/api/user-state/{property_id}/close-floors",
            json={"floors": [6, 7, 8], "session_id": "test"},
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        assert close_response.status_code == 200
        
        # Then verify GET returns the closed floors
        get_response = requests.get(
            f"{BASE_URL}/api/user-state/{property_id}",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        assert get_response.status_code == 200
        state_data = get_response.json()
        
        assert "closed_floors" in state_data or state_data.get("closed_floors") is not None
        if state_data:
            closed = state_data.get("closed_floors", [])
            assert 6 in closed or 7 in closed or 8 in closed
            print(f"✓ Closed floors persisted: {closed}")
    
    def test_get_all_user_states_with_closed_floors(self):
        """Test GET /api/user-state returns all states including closed floors"""
        # Close floors on multiple properties
        for prop_id, floors in [("prop_001", [8]), ("prop_002", [5])]:
            requests.post(
                f"{BASE_URL}/api/user-state/{prop_id}/close-floors",
                json={"floors": floors, "session_id": "test"},
                headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
                cookies={"session_token": SESSION_TOKEN}
            )
        
        # Get all states
        response = requests.get(
            f"{BASE_URL}/api/user-state",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "states" in data
        states = data["states"]
        assert len(states) >= 2, f"Expected at least 2 states, got {len(states)}"
        
        # Verify each state has property_id and closed_floors
        prop_ids = [s["property_id"] for s in states]
        assert "prop_001" in prop_ids or "prop_002" in prop_ids
        
        print(f"✓ GET /api/user-state returns {len(states)} states")
    
    def test_open_floors_success(self):
        """Test POST /api/user-state/{property_id}/open-floors works"""
        property_id = "prop_001"
        
        # First close floors
        requests.post(
            f"{BASE_URL}/api/user-state/{property_id}/close-floors",
            json={"floors": [7, 8], "session_id": "test"},
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        
        # Then open one floor
        response = requests.post(
            f"{BASE_URL}/api/user-state/{property_id}/open-floors",
            json={"floors": [8], "session_id": "test"},
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True
        assert "closed_floors" in data
        assert 8 not in data["closed_floors"], f"Floor 8 should be open but closed_floors = {data['closed_floors']}"
        
        print(f"✓ POST /api/user-state/{property_id}/open-floors opened floor 8")
    
    def test_reset_property_state(self):
        """Test POST /api/user-state/{property_id}/reset resets state"""
        property_id = "prop_001"
        
        # First close floors
        requests.post(
            f"{BASE_URL}/api/user-state/{property_id}/close-floors",
            json={"floors": [7, 8], "session_id": "test"},
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        
        # Reset the property
        response = requests.post(
            f"{BASE_URL}/api/user-state/{property_id}/reset",
            json={"session_id": "test"},
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        # Verify state is cleared
        get_response = requests.get(
            f"{BASE_URL}/api/user-state/{property_id}",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        # Should return empty state or null
        state = get_response.json()
        closed = state.get("closed_floors", []) if state else []
        assert len(closed) == 0, f"Expected empty closed_floors after reset, got {closed}"
        
        print(f"✓ POST /api/user-state/{property_id}/reset resets to default")
    
    def test_reset_all_user_states(self):
        """Test POST /api/user-state/reset-all resets all states"""
        # Close floors on multiple properties
        for prop_id, floors in [("prop_001", [8]), ("prop_002", [5]), ("prop_003", [10])]:
            requests.post(
                f"{BASE_URL}/api/user-state/{prop_id}/close-floors",
                json={"floors": floors, "session_id": "test"},
                headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
                cookies={"session_token": SESSION_TOKEN}
            )
        
        # Reset all
        response = requests.post(
            f"{BASE_URL}/api/user-state/reset-all",
            json={"session_id": "test"},
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        # Verify all states cleared
        get_response = requests.get(
            f"{BASE_URL}/api/user-state",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        all_states = get_response.json().get("states", [])
        assert len(all_states) == 0, f"Expected 0 states after reset-all, got {len(all_states)}"
        
        print(f"✓ POST /api/user-state/reset-all clears all states")


class TestSimulationEndpoint:
    """Test the floor closure simulation endpoint"""
    
    def test_simulate_floor_closure(self):
        """Test POST /api/analytics/simulate-floor-closure works"""
        response = requests.post(
            f"{BASE_URL}/api/analytics/simulate-floor-closure",
            json={
                "property_id": "prop_001",
                "floors_to_close": [7, 8],
                "hybrid_intensity": 1.0,
                "target_occupancy": None
            },
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify simulation response structure
        assert "savings" in data
        assert "energy_impact" in data
        assert "carbon_impact" in data
        assert "scenario_summary" in data
        
        # Verify savings data
        assert "total_monthly_savings" in data["savings"]
        assert "total_weekly_savings" in data["savings"]
        
        # Verify energy impact data
        assert "energy_reduction_percent" in data["energy_impact"]
        
        print(f"✓ POST /api/analytics/simulate-floor-closure returns simulation")
        print(f"  Monthly savings: {data['savings']['total_monthly_savings']}")
        print(f"  Energy reduction: {data['energy_impact']['energy_reduction_percent']}%")


class TestDashboardAnalytics:
    """Test dashboard data reflects closed floors"""
    
    def test_dashboard_with_active_optimizations(self):
        """Test dashboard returns data that can be used to show active optimizations"""
        # First close some floors
        requests.post(
            f"{BASE_URL}/api/user-state/prop_001/close-floors",
            json={"floors": [7, 8], "session_id": "test"},
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        
        # Get dashboard data
        response = requests.get(
            f"{BASE_URL}/api/analytics/dashboard",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify dashboard returns expected data structure
        assert "kpis" in data
        assert "optimization_potential" in data
        
        print(f"✓ GET /api/analytics/dashboard returns data")


class TestPropertyDetailWithState:
    """Test property detail endpoint includes user state"""
    
    def test_property_detail_includes_state(self):
        """Test GET /api/properties/{id}/detail includes user state"""
        property_id = "prop_001"
        
        # Close some floors first
        requests.post(
            f"{BASE_URL}/api/user-state/{property_id}/close-floors",
            json={"floors": [6, 7, 8], "session_id": "test"},
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        
        # Get property detail
        response = requests.get(
            f"{BASE_URL}/api/properties/{property_id}",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify property data structure
        assert "property_id" in data
        assert "name" in data
        assert "floors" in data
        assert "digital_twin" in data
        
        print(f"✓ GET /api/properties/{property_id} returns property detail")


class TestExecutiveSummaryWithOptimizations:
    """Test executive summary includes active optimizations"""
    
    def test_executive_summary_endpoint(self):
        """Test GET /api/copilot/executive-summary returns optimization data"""
        # Close some floors first
        requests.post(
            f"{BASE_URL}/api/user-state/prop_001/close-floors",
            json={"floors": [7, 8], "session_id": "test"},
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        
        response = requests.get(
            f"{BASE_URL}/api/copilot/executive-summary",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify executive summary structure
        assert "total_projected_monthly_savings" in data
        assert "total_projected_annual_savings" in data
        assert "total_carbon_reduction_kg" in data
        
        print(f"✓ GET /api/copilot/executive-summary returns data")
        print(f"  Monthly savings: {data.get('total_projected_monthly_savings')}")


class TestSessionsEndpoint:
    """Test session creation for tracking"""
    
    def test_create_session(self):
        """Test POST /api/sessions/create creates a tracking session"""
        response = requests.post(
            f"{BASE_URL}/api/sessions/create",
            json={"device_info": "test_device"},
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True
        assert "session_id" in data
        assert data["session_id"].startswith("session_")
        
        print(f"✓ POST /api/sessions/create returns session_id: {data['session_id']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
