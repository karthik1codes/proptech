"""
Test suite for PropTech Decision Copilot - MCP and WhatsApp endpoints
Tests MCP (Model Context Protocol) endpoints and Twilio WhatsApp webhook integration
"""

import pytest
import requests
import os
from typing import Dict, Any

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthEndpoints:
    """Health and basic endpoint tests"""
    
    def test_health_endpoint(self):
        """Test /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        print("✅ Health endpoint working")
    
    def test_root_endpoint(self):
        """Test /api/ returns API info with mcp_enabled"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data["mcp_enabled"] == True
        assert "message" in data
        assert "version" in data
        print("✅ Root endpoint working with mcp_enabled=true")


class TestMCPEndpoint:
    """MCP (Model Context Protocol) endpoint tests"""
    
    def test_mcp_initialize(self):
        """Test MCP initialize method returns protocol version and capabilities"""
        response = requests.post(
            f"{BASE_URL}/api/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "id": 1}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify JSON-RPC structure
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert "result" in data
        
        # Verify result content
        result = data["result"]
        assert "protocolVersion" in result
        assert result["serverInfo"]["name"] == "PropTech Decision Copilot MCP Server"
        assert result["capabilities"]["tools"] == True
        print("✅ MCP initialize method working")
    
    def test_mcp_tools_list(self):
        """Test MCP tools/list method returns all 5 tools"""
        response = requests.post(
            f"{BASE_URL}/api/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 2}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify result structure
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 2
        tools = data["result"]["tools"]
        
        # Should have 5 tools
        assert len(tools) == 5
        
        # Verify tool names
        tool_names = [t["name"] for t in tools]
        expected_tools = [
            "list_properties",
            "get_property_overview", 
            "simulate_floor_closure",
            "energy_savings_report",
            "get_recommendations"
        ]
        for expected in expected_tools:
            assert expected in tool_names, f"Missing tool: {expected}"
        
        # Verify tool structure
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
        
        print(f"✅ MCP tools/list returns {len(tools)} tools")
    
    def test_mcp_tools_call_list_properties(self):
        """Test MCP tools/call with list_properties returns property data"""
        response = requests.post(
            f"{BASE_URL}/api/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "list_properties", "arguments": {}},
                "id": 3
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure with annotations and isError
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 3
        result = data["result"]
        
        assert "content" in result
        assert len(result["content"]) > 0
        content = result["content"][0]
        
        assert content["type"] == "text"
        assert "annotations" in content
        assert isinstance(content["annotations"], list)
        assert result["isError"] == False
        
        # Verify markdown content has property data
        text = content["text"]
        assert "Property Portfolio Overview" in text
        assert "prop_001" in text or "prop_002" in text or "prop_003" in text
        
        print("✅ MCP tools/call list_properties working")
    
    def test_mcp_tools_call_get_property_overview(self):
        """Test MCP tools/call with get_property_overview returns detailed property data"""
        response = requests.post(
            f"{BASE_URL}/api/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_property_overview",
                    "arguments": {"property_id": "prop_001"}
                },
                "id": 4
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        result = data["result"]
        assert result["isError"] == False
        assert "content" in result
        
        content = result["content"][0]
        assert content["type"] == "text"
        assert "annotations" in content
        assert content["annotations"] == []
        
        # Verify property overview content
        text = content["text"]
        assert "Horizon Tech Park" in text
        assert "Revenue" in text
        assert "Profit" in text
        assert "Sustainability Score" in text
        assert "Efficiency Score" in text
        
        print("✅ MCP tools/call get_property_overview working")
    
    def test_mcp_error_response_format(self):
        """Test MCP error response has isError: true and annotations: []"""
        # Test with invalid property_id
        response = requests.post(
            f"{BASE_URL}/api/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_property_overview",
                    "arguments": {"property_id": "invalid_property"}
                },
                "id": 5
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify error response structure
        result = data["result"]
        assert result["isError"] == True
        assert "content" in result
        
        content = result["content"][0]
        assert content["type"] == "text"
        assert "annotations" in content
        assert content["annotations"] == []
        assert "Property not found" in content["text"]
        
        print("✅ MCP error response format correct (isError: true, annotations: [])")
    
    def test_mcp_unknown_tool_error(self):
        """Test MCP returns error for unknown tool"""
        response = requests.post(
            f"{BASE_URL}/api/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "unknown_tool", "arguments": {}},
                "id": 6
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        result = data["result"]
        assert result["isError"] == True
        assert "Unknown tool" in result["content"][0]["text"]
        
        print("✅ MCP unknown tool error handled correctly")


class TestWhatsAppEndpoints:
    """WhatsApp webhook and status endpoint tests"""
    
    def test_whatsapp_status_endpoint(self):
        """Test /api/whatsapp/status returns configuration status"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/status")
        assert response.status_code == 200
        data = response.json()
        
        # Should have configuration status fields
        assert "configured" in data
        assert "account_sid_set" in data
        assert "auth_token_set" in data
        assert "whatsapp_number_set" in data
        assert "alert_scheduler_running" in data
        
        # Twilio credentials are now configured
        print(f"✅ WhatsApp status endpoint working (configured: {data['configured']}, scheduler: {data['alert_scheduler_running']})")
    
    def test_whatsapp_webhook_list_command(self):
        """Test WhatsApp webhook with 'list' command returns property list"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "list", "From": "whatsapp:+1234567890"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        
        # Should return TwiML XML response
        content = response.text
        assert '<?xml version="1.0"' in content
        assert "<Response>" in content
        assert "<Message>" in content
        assert "Property Portfolio" in content
        
        # Should list properties
        assert "Horizon Tech Park" in content or "Marina Business Center" in content
        
        print("✅ WhatsApp webhook 'list' command working")
    
    def test_whatsapp_webhook_property_query(self):
        """Test WhatsApp webhook with property name query"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "Horizon Tech Park", "From": "whatsapp:+1234567890"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        
        content = response.text
        assert '<?xml version="1.0"' in content
        assert "<Response>" in content
        
        # Should return property analytics
        assert "Horizon Tech Park" in content
        assert "Analytics" in content or "Occupancy" in content
        assert "Financials" in content or "Revenue" in content
        
        print("✅ WhatsApp webhook property name query working")
    
    def test_whatsapp_webhook_help_command(self):
        """Test WhatsApp webhook with 'help' command"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "help", "From": "whatsapp:+1234567890"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        
        content = response.text
        assert "<Message>" in content
        assert "PropTech Copilot" in content
        assert "Available" in content or "Commands" in content
        
        print("✅ WhatsApp webhook 'help' command working")
    
    def test_whatsapp_webhook_default_response(self):
        """Test WhatsApp webhook default response for unknown commands"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "random unknown message", "From": "whatsapp:+1234567890"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        
        content = response.text
        assert "<Message>" in content
        assert "Welcome to PropTech Copilot" in content
        
        print("✅ WhatsApp webhook default response working")


class TestAuthAndProtectedRoutes:
    """Test authentication and protected routes"""
    
    def test_properties_requires_auth(self):
        """Test /api/properties returns 401 without authentication"""
        response = requests.get(f"{BASE_URL}/api/properties")
        assert response.status_code == 401
        data = response.json()
        assert "Not authenticated" in data.get("detail", "")
        
        print("✅ Properties endpoint correctly requires authentication")
    
    def test_openai_mcp_removed(self):
        """Test /api/mcp/openai returns 404 (endpoint removed)"""
        response = requests.post(
            f"{BASE_URL}/api/mcp/openai",
            json={}
        )
        assert response.status_code == 404
        
        print("✅ OpenAI MCP endpoint correctly removed (404)")


class TestMCPAdditionalTools:
    """Test additional MCP tools"""
    
    def test_simulate_floor_closure(self):
        """Test MCP simulate_floor_closure tool"""
        response = requests.post(
            f"{BASE_URL}/api/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "simulate_floor_closure",
                    "arguments": {
                        "property_id": "prop_001",
                        "floors_to_close": [8, 7]
                    }
                },
                "id": 7
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        result = data["result"]
        assert result["isError"] == False
        
        text = result["content"][0]["text"]
        assert "Floor Closure Simulation" in text
        assert "Savings" in text
        assert "Energy Reduction" in text
        
        print("✅ MCP simulate_floor_closure tool working")
    
    def test_energy_savings_report(self):
        """Test MCP energy_savings_report tool"""
        response = requests.post(
            f"{BASE_URL}/api/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "energy_savings_report",
                    "arguments": {"property_id": "prop_002"}
                },
                "id": 8
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        result = data["result"]
        assert result["isError"] == False
        
        text = result["content"][0]["text"]
        assert "Energy Savings Report" in text
        assert "Marina Business Center" in text
        
        print("✅ MCP energy_savings_report tool working")
    
    def test_get_recommendations(self):
        """Test MCP get_recommendations tool"""
        response = requests.post(
            f"{BASE_URL}/api/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_recommendations",
                    "arguments": {"property_id": "prop_003"}
                },
                "id": 9
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        result = data["result"]
        assert result["isError"] == False
        
        text = result["content"][0]["text"]
        assert "AI Recommendations" in text
        assert "Digital Gateway Tower" in text
        assert "Impact Analysis" in text
        
        print("✅ MCP get_recommendations tool working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
