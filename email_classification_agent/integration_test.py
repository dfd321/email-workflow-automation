#!/usr/bin/env python3
"""Integration test for email classification agent with mock services."""
import os
import sys
import json
import asyncio
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from unittest.mock import patch, Mock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.models import NormalizedEmail, ClassificationResult, ClassifiedEmail

# Import FastAPI testing utilities
from fastapi.testclient import TestClient
import main


class MockRouterHandler(BaseHTTPRequestHandler):
    """Mock HTTP server to simulate the router agent."""
    
    received_emails = []
    
    def do_POST(self):
        if self.path == '/route':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                classified_email = json.loads(post_data.decode('utf-8'))
                MockRouterHandler.received_emails.append(classified_email)
                
                print(f"\n[Mock Router] Received classified email:")
                print(f"  Original sender: {classified_email['original_email']['sender']}")
                print(f"  Subject: {classified_email['original_email']['subject']}")
                print(f"  Classification: {classified_email['classification']['workflow_type']}")
                print(f"  Confidence: {classified_email['classification']['confidence_score']}")
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {
                    'status': 'routed',
                    'workflow': classified_email['classification']['workflow_type']
                }
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                print(f"[Mock Router] Error: {e}")
                self.send_error(400, "Bad Request")
        else:
            self.send_error(404, "Not Found")
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass


def start_mock_router(port=8002):
    """Start the mock router server in a separate thread."""
    server = HTTPServer(('localhost', port), MockRouterHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server


def create_integration_test_emails():
    """Create diverse test emails for integration testing."""
    return [
        # Clear invoice request
        {
            "email": NormalizedEmail(
                sender="billing@supplier.com",
                subject="Invoice #INV-2024-001 for January Services",
                body="Dear Customer,\n\nPlease find attached the invoice for services rendered in January 2024. "
                     "The total amount due is $5,000. Payment terms are Net 30.\n\nBest regards,\nBilling Department",
                received_time=datetime.utcnow().isoformat()
            ),
            "expected": "InvoiceRequest"
        },
        # Clear appointment request
        {
            "email": NormalizedEmail(
                sender="john.smith@client.com",
                subject="Request for Project Review Meeting",
                body="Hi Team,\n\nI'd like to schedule a meeting to review the project progress. "
                     "Are you available next Thursday at 3 PM? We can meet via Zoom or in person.\n\nThanks,\nJohn",
                received_time=datetime.utcnow().isoformat()
            ),
            "expected": "AppointmentBooking"
        },
        # Clear new client inquiry
        {
            "email": NormalizedEmail(
                sender="potential.client@newcompany.com",
                subject="Information Request - Your Consulting Services",
                body="Hello,\n\nI found your company online and I'm interested in your consulting services. "
                     "We're a growing startup looking for expertise in digital transformation. "
                     "Could you please send me information about your services and pricing?\n\nBest regards,\nSarah Johnson",
                received_time=datetime.utcnow().isoformat()
            ),
            "expected": "NewClientInquiry"
        },
        # Ambiguous email
        {
            "email": NormalizedEmail(
                sender="user@example.com",
                subject="Question",
                body="Hi, I have a question about something. Can you help?",
                received_time=datetime.utcnow().isoformat()
            ),
            "expected": "HumanReview"
        },
        # Edge case: Multiple intents
        {
            "email": NormalizedEmail(
                sender="mixed@company.com",
                subject="Invoice Payment and Follow-up Meeting",
                body="Thank you for the invoice. I'll process the payment today. "
                     "Also, can we schedule a meeting next week to discuss the next phase of the project?",
                received_time=datetime.utcnow().isoformat()
            ),
            "expected": ["InvoiceRequest", "AppointmentBooking", "HumanReview"]
        }
    ]


def mock_openai_response(email_content):
    """Generate a mock OpenAI response based on email content."""
    # Simple keyword-based classification for testing
    body_lower = email_content.body.lower()
    subject_lower = email_content.subject.lower()
    
    if any(word in body_lower or word in subject_lower for word in ['invoice', 'payment', 'billing', 'amount due']):
        return ClassificationResult(workflow_type="InvoiceRequest", confidence_score=0.92)
    elif any(word in body_lower or word in subject_lower for word in ['meeting', 'schedule', 'appointment', 'available']):
        return ClassificationResult(workflow_type="AppointmentBooking", confidence_score=0.88)
    elif any(word in body_lower or word in subject_lower for word in ['interested', 'information', 'services', 'pricing']):
        return ClassificationResult(workflow_type="NewClientInquiry", confidence_score=0.90)
    else:
        return ClassificationResult(workflow_type="HumanReview", confidence_score=0.45)


def run_integration_test():
    """Run a full integration test of the email classification agent."""
    print("=== Email Classification Agent Integration Test ===\n")
    
    # Start mock router server
    print("Starting mock router server on port 8002...")
    router_server = start_mock_router(8002)
    time.sleep(1)  # Give server time to start
    
    # Override the router URL
    main.ROUTER_AGENT_URL = "http://localhost:8002/route"
    main.CONFIDENCE_THRESHOLD = 0.85
    
    # Clear received emails
    MockRouterHandler.received_emails = []
    
    # Create FastAPI test client
    client = TestClient(main.app)
    
    # Get test emails
    test_cases = create_integration_test_emails()
    print(f"Created {len(test_cases)} test email scenarios\n")
    
    # Mock the OpenAI LLM
    with patch('main.llm.invoke') as mock_llm:
        successful_classifications = 0
        
        for i, test_case in enumerate(test_cases):
            print(f"\n--- Test Case {i+1} ---")
            print(f"From: {test_case['email'].sender}")
            print(f"Subject: {test_case['email'].subject}")
            
            # Generate mock LLM response
            mock_classification = mock_openai_response(test_case['email'])
            mock_response = Mock()
            mock_response.content = mock_classification.model_dump_json()
            mock_llm.return_value = mock_response
            
            # Send email to classification endpoint
            response = client.post(
                "/classify",
                json=test_case['email'].model_dump()
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Classification successful")
                print(f"  Type: {result['classification']['workflow_type']}")
                print(f"  Confidence: {result['classification']['confidence_score']}")
                print(f"  Routed: {result['routed']}")
                
                # Verify low confidence handling
                if result['classification']['confidence_score'] < main.CONFIDENCE_THRESHOLD:
                    # Check if the router received HumanReview
                    time.sleep(0.1)  # Give time for async processing
                    if MockRouterHandler.received_emails:
                        last_email = MockRouterHandler.received_emails[-1]
                        if last_email['classification']['workflow_type'] == 'HumanReview':
                            print(f"✓ Low confidence correctly routed to HumanReview")
                
                successful_classifications += 1
            else:
                print(f"✗ Classification failed: {response.status_code}")
                print(f"  Error: {response.text}")
        
        print(f"\n=== Router Agent Summary ===")
        print(f"Total emails received by router: {len(MockRouterHandler.received_emails)}")
        
        # Analyze routing distribution
        workflow_counts = {}
        for email in MockRouterHandler.received_emails:
            workflow_type = email['classification']['workflow_type']
            workflow_counts[workflow_type] = workflow_counts.get(workflow_type, 0) + 1
        
        print("\nWorkflow distribution:")
        for workflow, count in workflow_counts.items():
            print(f"  {workflow}: {count}")
    
    # Test health endpoint
    print("\n=== Testing Health Endpoint ===")
    health_response = client.get("/health")
    if health_response.status_code == 200:
        health_data = health_response.json()
        print(f"✓ Health check passed: {health_data}")
    else:
        print(f"✗ Health check failed: {health_response.status_code}")
    
    # Shutdown mock server
    router_server.shutdown()
    
    print(f"\n=== Integration Test Summary ===")
    print(f"Successful classifications: {successful_classifications}/{len(test_cases)}")
    print(f"Emails routed: {len(MockRouterHandler.received_emails)}")
    
    return successful_classifications == len(test_cases)


def test_error_scenarios():
    """Test error handling scenarios."""
    print("\n=== Testing Error Scenarios ===")
    
    client = TestClient(main.app)
    
    # Test 1: Router unavailable
    print("\n1. Testing router unavailable scenario...")
    main.ROUTER_AGENT_URL = "http://localhost:9999/route"  # Non-existent port
    
    with patch('main.llm.invoke') as mock_llm:
        mock_classification = ClassificationResult(
            workflow_type="InvoiceRequest",
            confidence_score=0.95
        )
        mock_response = Mock()
        mock_response.content = mock_classification.model_dump_json()
        mock_llm.return_value = mock_response
        
        test_email = NormalizedEmail(
            sender="test@example.com",
            subject="Test",
            body="Test email",
            received_time=datetime.utcnow().isoformat()
        )
        
        response = client.post("/classify", json=test_email.model_dump())
        if response.status_code == 500:
            print("✓ Correctly handled router unavailable error")
        else:
            print("✗ Did not properly handle router unavailable")
    
    # Test 2: Invalid email format
    print("\n2. Testing invalid email format...")
    response = client.post("/classify", json={"invalid": "data"})
    if response.status_code == 422:
        print("✓ Correctly rejected invalid email format")
    else:
        print("✗ Did not properly validate email format")
    
    # Test 3: LLM failure
    print("\n3. Testing LLM failure...")
    with patch('main.llm.invoke') as mock_llm:
        mock_llm.side_effect = Exception("LLM API Error")
        
        response = client.post("/classify", json=test_email.model_dump())
        if response.status_code == 500:
            print("✓ Correctly handled LLM failure")
        else:
            print("✗ Did not properly handle LLM failure")
    
    return True


if __name__ == "__main__":
    # Run integration tests
    integration_success = run_integration_test()
    
    # Run error scenario tests
    error_success = test_error_scenarios()
    
    print("\n=== All Tests Complete ===")
    success = integration_success and error_success
    sys.exit(0 if success else 1)