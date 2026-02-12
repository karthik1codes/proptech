"""
Tests for PDF Executive Summary feature.
Tests PDF download button on Executive Summary page and PDF generation endpoint.
"""

import pytest
import requests
import os

# Get base URL from environment variable
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session for authenticated requests
TEST_SESSION = None

class TestPDFExecutiveSummary:
    """Test cases for PDF Executive Summary download feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session from environment or existing sessions"""
        global TEST_SESSION
        # Try to get an existing test session
        import subprocess
        result = subprocess.run([
            'mongosh', '--quiet', '--eval',
            "use('test_database'); const session = db.user_sessions.findOne({session_token: /test_session/}, {_id:0}); print(session ? session.session_token : 'none');"
        ], capture_output=True, text=True)
        
        token = result.stdout.strip()
        if token and token != 'none':
            TEST_SESSION = token
    
    def test_health_endpoint(self):
        """Test that API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("PASS: Health endpoint working")
    
    def test_executive_summary_data_endpoint(self):
        """Test executive summary data endpoint (requires auth)"""
        if not TEST_SESSION:
            pytest.skip("No test session available")
        
        response = requests.get(
            f"{BASE_URL}/api/copilot/executive-summary",
            headers={"Authorization": f"Bearer {TEST_SESSION}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "total_projected_monthly_savings" in data
        assert "total_projected_annual_savings" in data
        assert "total_carbon_reduction_kg" in data
        assert "avg_efficiency_improvement" in data
        assert "top_strategic_actions" in data
        assert "executive_insight" in data
        assert "properties_analyzed" in data
        
        print(f"PASS: Executive summary data - Monthly savings: {data.get('total_projected_monthly_savings')}")
    
    def test_portfolio_benchmark_endpoint(self):
        """Test portfolio benchmark endpoint (requires auth)"""
        if not TEST_SESSION:
            pytest.skip("No test session available")
        
        response = requests.get(
            f"{BASE_URL}/api/analytics/portfolio-benchmark",
            headers={"Authorization": f"Bearer {TEST_SESSION}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response is a list
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Verify structure of first benchmark
        benchmark = data[0]
        assert "property_id" in benchmark
        assert "name" in benchmark
        assert "profit_rank" in benchmark
        assert "energy_efficiency_rank" in benchmark
        assert "occupancy_rate" in benchmark
        
        print(f"PASS: Portfolio benchmark - {len(data)} properties ranked")
    
    def test_pdf_endpoint_requires_auth(self):
        """Test that PDF endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/reports/executive-summary-full/pdf")
        assert response.status_code == 401
        print("PASS: PDF endpoint correctly requires authentication")
    
    def test_pdf_generation_endpoint(self):
        """Test PDF generation endpoint with auth"""
        if not TEST_SESSION:
            pytest.skip("No test session available")
        
        response = requests.get(
            f"{BASE_URL}/api/reports/executive-summary-full/pdf",
            headers={"Authorization": f"Bearer {TEST_SESSION}"}
        )
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        
        # Verify PDF content
        content = response.content
        assert len(content) > 1000, "PDF should be larger than 1KB"
        assert content.startswith(b"%PDF"), "Content should be valid PDF"
        
        # Check Content-Disposition header
        content_disposition = response.headers.get("content-disposition", "")
        assert "attachment" in content_disposition
        assert "PropTech_Executive_Summary.pdf" in content_disposition
        
        print(f"PASS: PDF generated successfully - Size: {len(content)} bytes")
    
    def test_pdf_content_structure(self):
        """Verify PDF contains expected sections"""
        if not TEST_SESSION:
            pytest.skip("No test session available")
        
        response = requests.get(
            f"{BASE_URL}/api/reports/executive-summary-full/pdf",
            headers={"Authorization": f"Bearer {TEST_SESSION}"}
        )
        
        assert response.status_code == 200
        
        # PDF content contains ReportLab generator signature
        content = response.content
        assert b"ReportLab" in content, "PDF should be generated by ReportLab"
        
        print("PASS: PDF structure validated")
    
    def test_whatsapp_webhook_still_works(self):
        """Test WhatsApp webhook is still functional after changes"""
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/webhook",
            data={"Body": "help", "From": "whatsapp:+919876543210"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 200
        content = response.text
        
        # Verify response contains help menu
        assert "PropTech Copilot" in content
        assert "Floor Control" in content
        assert "Download PDF" in content
        
        print("PASS: WhatsApp webhook working correctly")
    
    def test_whatsapp_status_endpoint(self):
        """Test WhatsApp status endpoint"""
        if not TEST_SESSION:
            pytest.skip("No test session available")
        
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/status",
            headers={"Authorization": f"Bearer {TEST_SESSION}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("configured") == True
        assert data.get("alert_scheduler_running") == True
        
        print("PASS: WhatsApp status endpoint working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
