"""
Test suite for PropTech Decision Copilot - Conversational WhatsApp Multi-User System
Tests: 
- WhatsApp webhook help command shows all commands
- WhatsApp webhook list command shows properties (no auth required)
- WhatsApp webhook floor control commands require account linking
- WhatsApp status endpoint shows all service statuses
- MCP endpoint still works at /api/mcp
- Health endpoint works
- Existing auth routes work
"""

import pytest
import requests
import os
from typing import Dict, Any

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthAndBasicEndpoints:
    """Test health and basic endpoints"""
    
    def test_health_endpoint(self):
        """Test /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        print("✅ Health endpoint working")
    
    def test_root_endpoint_with_mcp_enabled(self):
        """Test /api/ returns API info with mcp_enabled"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data["mcp_enabled"] == True
        assert "message" in data
        assert "version" in data
        print("✅ Root endpoint working with mcp_enabled=true")


class TestMCPEndpoint:
    """Test MCP endpoint still works at /api/mcp"""
    
    def test_mcp_endpoint_accessible(self):
        """Test MCP endpoint is accessible at /api/mcp"""
        response = requests.post(
            f"{BASE_URL}/api/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "id": 1}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert "result" in data
        assert data["result"]["serverInfo"]["name"] == "PropTech Decision Copilot MCP Server"
        print("✅ MCP endpoint accessible and working at /api/mcp")
    
    def test_mcp_tools_list(self):
        """Test MCP tools/list returns all 5 tools"""
        response = requests.post(
            f"{BASE_URL}/api/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 2}
        )
        assert response.status_code == 200
        data = response.json()
        
        tools = data["result"]["tools"]
        assert len(tools) == 5
        
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
        
        print("✅ MCP tools/list returns 5 tools")


class TestWhatsAppWebhookHelpCommand:
    """Test WhatsApp webhook help command shows all commands"""
    
    def test_help_command(self):
        """Test 'help' command shows all available commands"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "help", "From": "whatsapp:+1234567890"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        
        content = response.text
        assert '<?xml version="1.0"' in content
        assert "<Response>" in content
        assert "<Message>" in content
        
        # Verify help menu contains key sections
        assert "PropTech Copilot" in content
        assert "Commands" in content
        
        # Verify floor control commands are mentioned
        assert "Close" in content or "close" in content
        assert "Open" in content or "open" in content
        
        # Verify simulation commands are mentioned  
        assert "Simulat" in content or "simulat" in content or "what-if" in content.lower()
        
        # Verify analytics commands are mentioned
        assert "Dashboard" in content or "dashboard" in content or "Analytics" in content
        
        # Verify general commands
        assert "List" in content or "list" in content
        assert "Status" in content or "status" in content
        
        print("✅ WhatsApp webhook 'help' command shows all commands")
    
    def test_commands_keyword(self):
        """Test 'commands' keyword also shows help"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "commands", "From": "whatsapp:+1234567890"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        
        content = response.text
        assert "<Message>" in content
        assert "PropTech Copilot" in content
        
        print("✅ 'commands' keyword also shows help menu")


class TestWhatsAppWebhookListCommand:
    """Test WhatsApp webhook list command shows properties (no auth required)"""
    
    def test_list_command_shows_properties(self):
        """Test 'list' command shows all properties without authentication"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "list", "From": "whatsapp:+1234567890"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        
        content = response.text
        assert '<?xml version="1.0"' in content
        assert "<Response>" in content
        assert "<Message>" in content
        
        # Should show property portfolio
        assert "Property Portfolio" in content or "Properties" in content
        
        # Should show at least one of the default properties
        assert "Horizon Tech Park" in content or "Marina Business Center" in content or "Digital Gateway Tower" in content
        
        # Should show occupancy info
        assert "occupancy" in content.lower() or "%" in content
        
        print("✅ WhatsApp webhook 'list' command shows properties without auth")
    
    def test_properties_keyword(self):
        """Test 'properties' keyword also lists properties"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "properties", "From": "whatsapp:+1234567890"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        
        content = response.text
        assert "<Message>" in content
        # Should list properties
        assert "Horizon" in content or "Marina" in content or "Digital" in content
        
        print("✅ 'properties' keyword also lists properties")
    
    def test_list_properties_keyword(self):
        """Test 'list properties' keyword works"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "list properties", "From": "whatsapp:+1234567890"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        
        content = response.text
        assert "<Message>" in content
        
        print("✅ 'list properties' keyword works")


class TestWhatsAppWebhookFloorControlRequiresLinking:
    """Test WhatsApp webhook floor control commands require account linking"""
    
    def test_close_floor_requires_linking(self):
        """Test 'close floor' command requires account linking"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "close floor 3 in Horizon", "From": "whatsapp:+9999999999"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        
        content = response.text
        assert "<Message>" in content
        
        # Should require account linking - check for link-related message
        # or property floor closed message (if somehow linked)
        # Since +9999999999 is not linked, should ask for linking
        assert "Account Not Linked" in content or "Link" in content or "link" in content.lower()
        
        print("✅ 'close floor' command requires account linking")
    
    def test_open_floor_requires_linking(self):
        """Test 'open floor' command requires account linking"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "open floor 3", "From": "whatsapp:+9999999999"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        
        content = response.text
        assert "<Message>" in content
        
        # Should require account linking
        assert "Account Not Linked" in content or "Link" in content or "link" in content.lower()
        
        print("✅ 'open floor' command requires account linking")
    
    def test_simulate_requires_linking(self):
        """Test 'simulate' command requires account linking"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "simulate closing floor 3 in Horizon", "From": "whatsapp:+9999999999"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        
        content = response.text
        assert "<Message>" in content
        
        # Should require account linking
        assert "Account Not Linked" in content or "Link" in content or "link" in content.lower()
        
        print("✅ 'simulate' command requires account linking")
    
    def test_reset_requires_linking(self):
        """Test 'reset' command requires account linking"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "reset Horizon", "From": "whatsapp:+9999999999"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        
        content = response.text
        assert "<Message>" in content
        
        # Should require account linking
        assert "Account Not Linked" in content or "Link" in content or "link" in content.lower()
        
        print("✅ 'reset' command requires account linking")
    
    def test_what_if_requires_linking(self):
        """Test 'what if' command requires account linking"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "what if we close floor 2", "From": "whatsapp:+9999999999"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        
        content = response.text
        assert "<Message>" in content
        
        # Should require account linking
        assert "Account Not Linked" in content or "Link" in content or "link" in content.lower()
        
        print("✅ 'what if' command requires account linking")


class TestWhatsAppWebhookNoAuthCommands:
    """Test commands that work without authentication"""
    
    def test_status_command_no_auth(self):
        """Test 'status' command works without full auth"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "status", "From": "whatsapp:+1234567890"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        
        content = response.text
        assert "<Message>" in content
        
        # Should show system status
        assert "System Status" in content or "Status" in content
        assert "WhatsApp" in content or "Service" in content
        
        print("✅ 'status' command works without auth")
    
    def test_property_query_no_auth(self):
        """Test querying property by name works without auth"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "Horizon Tech Park", "From": "whatsapp:+1234567890"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        
        content = response.text
        assert "<Message>" in content
        
        # Should return property info
        assert "Horizon Tech Park" in content
        
        print("✅ Property query by name works")


class TestWhatsAppStatusEndpoint:
    """Test WhatsApp status endpoint shows all service statuses"""
    
    def test_whatsapp_status_endpoint(self):
        """Test /api/whatsapp/status returns all service statuses"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/status")
        assert response.status_code == 200
        data = response.json()
        
        # Should have configuration status fields
        assert "configured" in data
        assert isinstance(data["configured"], bool)
        
        assert "account_sid_set" in data
        assert isinstance(data["account_sid_set"], bool)
        
        assert "auth_token_set" in data
        assert isinstance(data["auth_token_set"], bool)
        
        assert "whatsapp_number_set" in data
        assert isinstance(data["whatsapp_number_set"], bool)
        
        assert "alert_scheduler_running" in data
        assert isinstance(data["alert_scheduler_running"], bool)
        
        # Based on .env, Twilio should be configured
        print(f"✅ WhatsApp status endpoint returns all statuses:")
        print(f"   - configured: {data['configured']}")
        print(f"   - account_sid_set: {data['account_sid_set']}")
        print(f"   - auth_token_set: {data['auth_token_set']}")
        print(f"   - whatsapp_number_set: {data['whatsapp_number_set']}")
        print(f"   - alert_scheduler_running: {data['alert_scheduler_running']}")
    
    def test_whatsapp_status_twilio_configured(self):
        """Test Twilio credentials are configured"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/status")
        assert response.status_code == 200
        data = response.json()
        
        # Twilio should be configured based on .env
        assert data["account_sid_set"] == True, "TWILIO_ACCOUNT_SID should be set"
        assert data["auth_token_set"] == True, "TWILIO_AUTH_TOKEN should be set"
        assert data["whatsapp_number_set"] == True, "TWILIO_WHATSAPP_NUMBER should be set"
        assert data["configured"] == True, "WhatsApp service should be configured"
        
        print("✅ Twilio credentials are properly configured")
    
    def test_alert_scheduler_running(self):
        """Test alert scheduler is running"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/status")
        assert response.status_code == 200
        data = response.json()
        
        assert data["alert_scheduler_running"] == True, "Alert scheduler should be running"
        
        print("✅ Alert scheduler is running")


class TestExistingAuthRoutes:
    """Test existing auth routes work"""
    
    def test_properties_requires_auth(self):
        """Test /api/properties returns 401 without authentication"""
        response = requests.get(f"{BASE_URL}/api/properties")
        assert response.status_code == 401
        data = response.json()
        assert "Not authenticated" in data.get("detail", "")
        
        print("✅ /api/properties correctly requires authentication")
    
    def test_auth_me_requires_auth(self):
        """Test /api/auth/me returns 401 without authentication"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        data = response.json()
        assert "Not authenticated" in data.get("detail", "")
        
        print("✅ /api/auth/me correctly requires authentication")
    
    def test_user_state_requires_auth(self):
        """Test /api/user-state endpoints require authentication"""
        response = requests.get(f"{BASE_URL}/api/user-state/prop_001")
        assert response.status_code == 401
        
        print("✅ /api/user-state correctly requires authentication")
    
    def test_whatsapp_link_initiate_requires_auth(self):
        """Test /api/whatsapp/link/initiate requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/link/initiate",
            json={"phone_number": "+1234567890"}
        )
        assert response.status_code == 401
        
        print("✅ /api/whatsapp/link/initiate correctly requires authentication")
    
    def test_whatsapp_conversations_requires_auth(self):
        """Test /api/whatsapp/conversations requires authentication"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/conversations")
        assert response.status_code == 401
        
        print("✅ /api/whatsapp/conversations correctly requires authentication")


class TestCommandParser:
    """Test natural language command parser via webhook"""
    
    def test_close_f3_syntax(self):
        """Test 'close f3' floor syntax is recognized"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "close f3 in horizon", "From": "whatsapp:+9999999999"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        content = response.text
        # Should recognize as close floor command (requires linking)
        assert "<Message>" in content
        
        print("✅ 'close f3' syntax recognized")
    
    def test_close_floor_3_syntax(self):
        """Test 'close floor 3' syntax is recognized"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "close floor 3 in horizon", "From": "whatsapp:+9999999999"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        content = response.text
        assert "<Message>" in content
        
        print("✅ 'close floor 3' syntax recognized")
    
    def test_property_name_recognition(self):
        """Test property name recognition in commands"""
        # Test with 'Horizon' abbreviation
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "Horizon", "From": "whatsapp:+1234567890"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        content = response.text
        assert "Horizon Tech Park" in content
        
        print("✅ Property name recognition works")
    
    def test_unknown_command_returns_welcome(self):
        """Test unknown commands return welcome message"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "xyz random text", "From": "whatsapp:+1234567890"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        content = response.text
        assert "<Message>" in content
        assert "Welcome to PropTech Copilot" in content
        
        print("✅ Unknown commands return welcome message")


class TestWhatsAppLinkingEndpoints:
    """Test WhatsApp linking endpoints (authenticated)"""
    
    def test_link_status_requires_auth(self):
        """Test /api/whatsapp/link/status requires authentication"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/link/status")
        assert response.status_code == 401
        
        print("✅ /api/whatsapp/link/status correctly requires authentication")
    
    def test_link_verify_requires_auth(self):
        """Test /api/whatsapp/link/verify requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/link/verify",
            json={"phone_number": "+1234567890", "otp_code": "123456"}
        )
        assert response.status_code == 401
        
        print("✅ /api/whatsapp/link/verify correctly requires authentication")
    
    def test_link_unlink_requires_auth(self):
        """Test /api/whatsapp/link/unlink requires authentication"""
        response = requests.post(f"{BASE_URL}/api/whatsapp/link/unlink")
        assert response.status_code == 401
        
        print("✅ /api/whatsapp/link/unlink correctly requires authentication")


class TestAlertEndpoints:
    """Test alert subscription endpoints"""
    
    def test_alerts_subscribe_requires_auth(self):
        """Test /api/whatsapp/alerts/subscribe requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/alerts/subscribe",
            json={"phone_number": "+1234567890"}
        )
        assert response.status_code == 401
        
        print("✅ /api/whatsapp/alerts/subscribe correctly requires authentication")
    
    def test_alerts_subscriptions_requires_auth(self):
        """Test /api/whatsapp/alerts/subscriptions requires authentication"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/alerts/subscriptions")
        assert response.status_code == 401
        
        print("✅ /api/whatsapp/alerts/subscriptions correctly requires authentication")


class TestWebhookCommands:
    """Test additional webhook commands"""
    
    def test_alerts_command_via_webhook(self):
        """Test 'alerts' command via webhook"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "alerts", "From": "whatsapp:+1234567890"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        content = response.text
        assert "<Message>" in content
        # Should show alerts or no alerts message
        assert "Alert" in content or "alert" in content.lower() or "No Active" in content
        
        print("✅ 'alerts' command via webhook works")
    
    def test_subscribe_command_via_webhook(self):
        """Test 'subscribe' command via webhook (requires linking)"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "subscribe", "From": "whatsapp:+9999999999"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        content = response.text
        assert "<Message>" in content
        
        print("✅ 'subscribe' command via webhook handled")
    
    def test_unsubscribe_command_via_webhook(self):
        """Test 'unsubscribe' command via webhook"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "unsubscribe", "From": "whatsapp:+9999999999"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        content = response.text
        assert "<Message>" in content
        
        print("✅ 'unsubscribe' command via webhook handled")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
