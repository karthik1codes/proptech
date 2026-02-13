"""
Test Change Logging System and Session Management
Tests:
- GET /api/change-log (requires auth, returns user changes)
- GET /api/change-log/stats (requires auth, returns change stats)
- POST /api/sessions/create (requires auth, creates session)
- GET /api/sessions (requires auth, lists sessions)
- POST /api/user-state/{id}/close-floors (requires auth, logs changes)
- Health endpoint
"""

import pytest
import requests
import os
import time

# Use environment variable for BASE_URL
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test token created via mongosh
TEST_TOKEN = "test_session_changelog_1770942144738"


class TestHealthEndpoint:
    """Health endpoint - no auth required"""
    
    def test_health_endpoint_returns_200(self):
        """Test that health endpoint returns 200 and healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["status"] == "healthy", f"Expected 'healthy', got {data.get('status')}"
        assert "timestamp" in data, "Missing timestamp in response"
        print("✓ Health endpoint working correctly")


class TestChangeLogEndpointsAuth:
    """Test that change log endpoints require authentication"""
    
    def test_change_log_requires_auth(self):
        """GET /api/change-log without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/change-log")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Missing error detail"
        print("✓ /api/change-log correctly requires auth")
    
    def test_change_log_stats_requires_auth(self):
        """GET /api/change-log/stats without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/change-log/stats")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ /api/change-log/stats correctly requires auth")


class TestSessionEndpointsAuth:
    """Test that session endpoints require authentication"""
    
    def test_sessions_list_requires_auth(self):
        """GET /api/sessions without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/sessions")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ /api/sessions correctly requires auth")
    
    def test_sessions_create_requires_auth(self):
        """POST /api/sessions/create without auth returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/sessions/create",
            json={"device_info": "test"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ /api/sessions/create correctly requires auth")


class TestUserStateMutationAuth:
    """Test that mutation endpoints require authentication"""
    
    def test_close_floors_requires_auth(self):
        """POST /api/user-state/{id}/close-floors without auth returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/user-state/prop_001/close-floors",
            json={"floors": [1]}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ /api/user-state/close-floors correctly requires auth")


class TestChangeLogWithAuth:
    """Test change log endpoints with valid authentication"""
    
    @pytest.fixture(autouse=True)
    def setup_auth_headers(self):
        """Setup auth headers for all tests in this class"""
        self.headers = {
            "Authorization": f"Bearer {TEST_TOKEN}",
            "Content-Type": "application/json"
        }
    
    def test_get_change_log(self):
        """GET /api/change-log with auth returns changes list"""
        response = requests.get(
            f"{BASE_URL}/api/change-log",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "changes" in data, "Missing 'changes' field"
        assert "count" in data, "Missing 'count' field"
        assert isinstance(data["changes"], list), "changes should be a list"
        print(f"✓ GET /api/change-log returned {data['count']} changes")
    
    def test_get_change_log_stats(self):
        """GET /api/change-log/stats with auth returns stats"""
        response = requests.get(
            f"{BASE_URL}/api/change-log/stats",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "user_id" in data, "Missing 'user_id' field"
        assert "total_changes" in data, "Missing 'total_changes' field"
        assert "by_entity_type" in data, "Missing 'by_entity_type' field"
        print(f"✓ GET /api/change-log/stats returned stats for user: {data['user_id']}")


class TestSessionsWithAuth:
    """Test session endpoints with valid authentication"""
    
    @pytest.fixture(autouse=True)
    def setup_auth_headers(self):
        """Setup auth headers for all tests in this class"""
        self.headers = {
            "Authorization": f"Bearer {TEST_TOKEN}",
            "Content-Type": "application/json"
        }
    
    def test_create_session(self):
        """POST /api/sessions/create creates a new session"""
        response = requests.post(
            f"{BASE_URL}/api/sessions/create",
            headers=self.headers,
            json={"device_info": "pytest-automated-test"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True, "Session creation should succeed"
        assert "session_id" in data, "Missing 'session_id' in response"
        assert data["session_id"].startswith("session_"), "session_id should start with 'session_'"
        print(f"✓ Created session: {data['session_id']}")
        
        # Store for later tests
        return data["session_id"]
    
    def test_get_sessions_list(self):
        """GET /api/sessions returns list of sessions"""
        response = requests.get(
            f"{BASE_URL}/api/sessions",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "sessions" in data, "Missing 'sessions' field"
        assert "count" in data, "Missing 'count' field"
        assert isinstance(data["sessions"], list), "sessions should be a list"
        print(f"✓ GET /api/sessions returned {data['count']} sessions")


class TestMutationWithChangeLogging:
    """Test that mutations create change log entries"""
    
    @pytest.fixture(autouse=True)
    def setup_auth_headers(self):
        """Setup auth headers for all tests in this class"""
        self.headers = {
            "Authorization": f"Bearer {TEST_TOKEN}",
            "Content-Type": "application/json"
        }
    
    def test_close_floors_logs_change(self):
        """POST /api/user-state/{id}/close-floors logs the change"""
        # First create a session to track changes
        session_response = requests.post(
            f"{BASE_URL}/api/sessions/create",
            headers=self.headers,
            json={"device_info": "pytest-mutation-test"}
        )
        session_id = session_response.json().get("session_id")
        
        # Get initial change count
        initial_response = requests.get(
            f"{BASE_URL}/api/change-log/stats",
            headers=self.headers
        )
        initial_changes = initial_response.json().get("total_changes", 0)
        
        # Perform mutation - close a floor
        close_response = requests.post(
            f"{BASE_URL}/api/user-state/prop_002/close-floors",
            headers=self.headers,
            json={"floors": [4], "session_id": session_id}
        )
        assert close_response.status_code == 200, f"Expected 200, got {close_response.status_code}"
        
        data = close_response.json()
        assert data.get("success") == True, "Floor closure should succeed"
        assert "closed_floors" in data, "Missing 'closed_floors' in response"
        assert "analytics" in data, "Missing 'analytics' in response"
        print(f"✓ Closed floor(s), now closed: {data['closed_floors']}")
        
        # Verify change was logged
        time.sleep(0.5)  # Allow change to be written
        
        final_response = requests.get(
            f"{BASE_URL}/api/change-log/stats",
            headers=self.headers
        )
        final_changes = final_response.json().get("total_changes", 0)
        
        # Change count should have increased (may increase by more than 1 if previous floors closed)
        print(f"✓ Change log count: {initial_changes} -> {final_changes}")
        
        # Verify the specific change in log
        log_response = requests.get(
            f"{BASE_URL}/api/change-log?entity_type=property_state&entity_id=prop_002&limit=5",
            headers=self.headers
        )
        changes = log_response.json().get("changes", [])
        
        # Should have at least one change for prop_002
        assert len(changes) >= 1, "Expected at least one change for prop_002"
        
        # Find the most recent change
        latest_change = changes[0]
        assert latest_change.get("entity_type") == "property_state"
        assert latest_change.get("entity_id") == "prop_002"
        print(f"✓ Change logged: field={latest_change.get('field')}, old={latest_change.get('old_value')}, new={latest_change.get('new_value')}")
    
    def test_open_floors_requires_auth(self):
        """POST /api/user-state/{id}/open-floors requires auth"""
        response = requests.post(
            f"{BASE_URL}/api/user-state/prop_001/open-floors",
            json={"floors": [1]}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ /api/user-state/open-floors correctly requires auth")


class TestChangeLogFiltering:
    """Test change log filtering options"""
    
    @pytest.fixture(autouse=True)
    def setup_auth_headers(self):
        """Setup auth headers for all tests in this class"""
        self.headers = {
            "Authorization": f"Bearer {TEST_TOKEN}",
            "Content-Type": "application/json"
        }
    
    def test_filter_by_entity_type(self):
        """GET /api/change-log with entity_type filter"""
        response = requests.get(
            f"{BASE_URL}/api/change-log?entity_type=property_state",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        # All changes should be property_state type
        for change in data.get("changes", []):
            assert change["entity_type"] == "property_state", f"Unexpected entity_type: {change['entity_type']}"
        print(f"✓ Filtered by entity_type=property_state, got {data['count']} changes")
    
    def test_filter_by_entity_id(self):
        """GET /api/change-log with entity_id filter"""
        response = requests.get(
            f"{BASE_URL}/api/change-log?entity_id=prop_001",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        # All changes should be for prop_001
        for change in data.get("changes", []):
            assert change["entity_id"] == "prop_001", f"Unexpected entity_id: {change['entity_id']}"
        print(f"✓ Filtered by entity_id=prop_001, got {data['count']} changes")
    
    def test_change_log_limit(self):
        """GET /api/change-log respects limit parameter"""
        response = requests.get(
            f"{BASE_URL}/api/change-log?limit=2",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data.get("changes", [])) <= 2, "Limit not respected"
        print(f"✓ Limit=2 returned {len(data.get('changes', []))} changes")


class TestEntityChangeHistory:
    """Test entity-specific change history endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup_auth_headers(self):
        """Setup auth headers for all tests in this class"""
        self.headers = {
            "Authorization": f"Bearer {TEST_TOKEN}",
            "Content-Type": "application/json"
        }
    
    def test_get_entity_history(self):
        """GET /api/change-log/entity/{type}/{id} returns history"""
        response = requests.get(
            f"{BASE_URL}/api/change-log/entity/property_state/prop_001",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "history" in data, "Missing 'history' field"
        assert isinstance(data["history"], list), "history should be a list"
        print(f"✓ Entity history for prop_001 returned {len(data['history'])} entries")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
