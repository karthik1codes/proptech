#!/usr/bin/env python3

import requests
import sys
from datetime import datetime
import json

class PropTechAPITester:
    def __init__(self, base_url="https://property-decision-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api"
        self.session_token = "test_session_1770903238467"  # From MongoDB test user creation
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_base}{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        # Add auth header if session token is available
        if self.session_token and not endpoint.startswith('/health') and not endpoint == '/':
            test_headers['Authorization'] = f'Bearer {self.session_token}'
            
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 500:
                        print(f"   Response: {json.dumps(response_data, indent=2)}")
                    elif isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                    return success, response_data
                except:
                    return success, {"raw_response": response.text}
            else:
                self.failed_tests.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:200] if response.text else "No response"
                })
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            self.failed_tests.append({
                "test": name,
                "error": str(e)
            })
            print(f"❌ FAILED - Error: {str(e)}")
            return False, {}

    def test_health_endpoints(self):
        """Test basic health endpoints"""
        print("\n" + "="*50)
        print("🏥 TESTING HEALTH ENDPOINTS")
        print("="*50)
        
        self.run_test("API Health Check", "GET", "/health", 200)
        self.run_test("API Root", "GET", "/", 200)

    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n" + "="*50)
        print("🔐 TESTING AUTHENTICATION ENDPOINTS")
        print("="*50)
        
        # Test /auth/me with our test session
        self.run_test("Get Current User", "GET", "/auth/me", 200)
        
        # Test invalid session
        old_token = self.session_token
        self.session_token = "invalid_token"
        self.run_test("Invalid Session Test", "GET", "/auth/me", 401)
        self.session_token = old_token

    def test_property_endpoints(self):
        """Test property management endpoints"""
        print("\n" + "="*50)
        print("🏢 TESTING PROPERTY ENDPOINTS")
        print("="*50)
        
        # Get all properties
        success, properties = self.run_test("Get All Properties", "GET", "/properties", 200)
        
        if success and isinstance(properties, list) and len(properties) > 0:
            # Test individual property
            property_id = properties[0].get('property_id')
            if property_id:
                self.run_test("Get Property Details", "GET", f"/properties/{property_id}", 200)
            
            print(f"   Found {len(properties)} properties in the system")
        
        # Test adding new property
        new_property = {
            "name": "Test Property",
            "type": "Commercial Office",
            "location": "Test City, State",
            "floors": 3,
            "rooms_per_floor": 8,
            "revenue_per_seat": 2000,
            "energy_cost_per_unit": 7.5,
            "maintenance_per_floor": 40000,
            "baseline_energy_intensity": 140
        }
        
        success, response = self.run_test("Add New Property", "POST", "/properties", 200, new_property)
        if success:
            test_property_id = response.get('property_id')
            print(f"   Created test property: {test_property_id}")

    def test_analytics_endpoints(self):
        """Test analytics endpoints"""
        print("\n" + "="*50)
        print("📊 TESTING ANALYTICS ENDPOINTS")
        print("="*50)
        
        self.run_test("Dashboard Analytics", "GET", "/analytics/dashboard", 200)
        self.run_test("Portfolio Benchmark", "GET", "/analytics/portfolio-benchmark", 200)
        
        # Test energy savings for first property (assuming property exists)
        success, properties = self.run_test("Get Properties for Energy Test", "GET", "/properties", 200)
        if success and isinstance(properties, list) and len(properties) > 0:
            property_id = properties[0].get('property_id')
            if property_id:
                self.run_test("Energy Savings Analysis", "GET", f"/analytics/energy-savings/{property_id}", 200)
        
        # Test floor closure simulation
        if success and isinstance(properties, list) and len(properties) > 0:
            property_id = properties[0].get('property_id')
            simulation_data = {
                "property_id": property_id,
                "floors_to_close": [3],  # Close top floor
                "hybrid_intensity": 0.8,
                "target_occupancy": 0.7
            }
            self.run_test("Floor Closure Simulation", "POST", "/analytics/simulate-floor-closure", 200, simulation_data)

    def test_recommendations_endpoints(self):
        """Test AI recommendations endpoints"""
        print("\n" + "="*50)
        print("🤖 TESTING AI RECOMMENDATIONS ENDPOINTS")
        print("="*50)
        
        # Get properties first
        success, properties = self.run_test("Get Properties for Recommendations", "GET", "/properties", 200)
        
        if success and isinstance(properties, list) and len(properties) > 0:
            property_id = properties[0].get('property_id')
            if property_id:
                self.run_test("Property Recommendations", "GET", f"/recommendations/{property_id}", 200)
                self.run_test("Copilot Insight", "GET", f"/copilot/{property_id}", 200)
        
        self.run_test("Executive Summary", "GET", "/copilot/executive-summary", 200)

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 STARTING PROPTECH API TESTS")
        print(f"Base URL: {self.base_url}")
        print(f"Using session token: {self.session_token[:20]}...")
        
        # Test suites in order
        self.test_health_endpoints()
        self.test_auth_endpoints() 
        self.test_property_endpoints()
        self.test_analytics_endpoints()
        self.test_recommendations_endpoints()
        
        # Print final results
        self.print_results()

    def print_results(self):
        """Print final test results"""
        print("\n" + "="*60)
        print("📊 FINAL TEST RESULTS")
        print("="*60)
        
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {len(self.failed_tests)}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for i, failed in enumerate(self.failed_tests, 1):
                print(f"{i}. {failed.get('test', 'Unknown')}")
                if 'expected' in failed:
                    print(f"   Expected: {failed['expected']}, Got: {failed['actual']}")
                if 'error' in failed:
                    print(f"   Error: {failed['error']}")
                if 'response' in failed:
                    print(f"   Response: {failed['response']}")
                print()
        
        return len(self.failed_tests) == 0

def main():
    tester = PropTechAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())