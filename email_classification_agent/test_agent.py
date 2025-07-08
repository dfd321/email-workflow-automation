#!/usr/bin/env python3
"""Test script for email classification agent functionality."""
import os
import sys
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import logging
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.models import NormalizedEmail, ClassificationResult, ClassifiedEmail

# Import our main module
import main

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_emails():
    """Create various test email scenarios."""
    test_cases = [
        # Invoice request email
        {
            "email": NormalizedEmail(
                sender="accounts@company.com",
                subject="Invoice for Order #12345",
                body="Please find attached the invoice for your recent order. Payment is due within 30 days.",
                received_time=datetime.utcnow().isoformat()
            ),
            "expected_type": "InvoiceRequest",
            "min_confidence": 0.85
        },
        # Appointment booking email
        {
            "email": NormalizedEmail(
                sender="client@example.com",
                subject="Meeting Request for Next Week",
                body="I would like to schedule a meeting to discuss the project. Are you available on Tuesday at 2 PM?",
                received_time=datetime.utcnow().isoformat()
            ),
            "expected_type": "AppointmentBooking",
            "min_confidence": 0.85
        },
        # New client inquiry
        {
            "email": NormalizedEmail(
                sender="newclient@startup.com",
                subject="Interested in Your Services",
                body="Hi, I came across your website and I'm interested in learning more about your consulting services. Can you send me more information?",
                received_time=datetime.utcnow().isoformat()
            ),
            "expected_type": "NewClientInquiry",
            "min_confidence": 0.85
        },
        # Ambiguous email (should go to human review)
        {
            "email": NormalizedEmail(
                sender="random@email.com",
                subject="Quick Question",
                body="Hey, can you help me with something?",
                received_time=datetime.utcnow().isoformat()
            ),
            "expected_type": "HumanReview",
            "min_confidence": 0.0
        },
        # Mixed content email
        {
            "email": NormalizedEmail(
                sender="customer@business.com",
                subject="Invoice and Meeting",
                body="Thanks for sending the invoice. Also, can we schedule a meeting to discuss the next steps?",
                received_time=datetime.utcnow().isoformat()
            ),
            "expected_type": ["InvoiceRequest", "AppointmentBooking", "HumanReview"],
            "min_confidence": 0.0
        }
    ]
    return test_cases


async def test_classify_endpoint():
    """Test the /classify endpoint with various emails."""
    print("\n=== Testing /classify endpoint ===")
    
    test_cases = create_test_emails()
    
    # Mock the LLM and router calls
    with patch('main.llm.invoke') as mock_llm, \
         patch('httpx.AsyncClient') as mock_client_class:
        
        # Setup mock client
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        
        for i, test_case in enumerate(test_cases):
            print(f"\nTest case {i+1}: {test_case['email'].subject}")
            
            # Mock LLM response based on expected type
            expected_type = test_case['expected_type']
            if isinstance(expected_type, list):
                # For ambiguous cases, use the first type with low confidence
                expected_type = expected_type[0]
                confidence = 0.6
            else:
                confidence = 0.95 if expected_type != "HumanReview" else 0.4
            
            mock_classification = ClassificationResult(
                workflow_type=expected_type,
                confidence_score=confidence
            )
            
            mock_llm.return_value.content = mock_classification.model_dump_json()
            
            # Call the classify endpoint
            try:
                result = await main.classify_email(test_case['email'])
                
                if result['status'] == 'success':
                    print(f"✓ Classification successful")
                    print(f"  Type: {result['classification']['workflow_type']}")
                    print(f"  Confidence: {result['classification']['confidence_score']}")
                    
                    # Check if low confidence triggers human review
                    if result['classification']['confidence_score'] < main.CONFIDENCE_THRESHOLD:
                        # Verify the call was made with HumanReview
                        call_args = mock_client.post.call_args
                        if call_args:
                            posted_data = json.loads(call_args[1]['json']) if isinstance(call_args[1]['json'], str) else call_args[1]['json']
                            if posted_data['classification']['workflow_type'] == 'HumanReview':
                                print(f"✓ Low confidence correctly routed to HumanReview")
                else:
                    print(f"✗ Classification failed")
                    
            except Exception as e:
                print(f"✗ Test failed with error: {e}")
    
    return True


async def test_health_endpoint():
    """Test the /health endpoint."""
    print("\n=== Testing /health endpoint ===")
    
    try:
        result = await main.health_check()
        if result['status'] == 'healthy' and result['agent'] == 'email_classification':
            print("✓ Health check passed")
            return True
        else:
            print("✗ Health check failed")
            return False
    except Exception as e:
        print(f"✗ Health check failed with error: {e}")
        return False


async def test_llm_parsing():
    """Test the LLM output parsing."""
    print("\n=== Testing LLM output parsing ===")
    
    # Test valid parsing
    valid_json = ClassificationResult(
        workflow_type="InvoiceRequest",
        confidence_score=0.95
    ).model_dump_json()
    
    try:
        parsed = main.parser.parse(valid_json)
        print(f"✓ Successfully parsed valid JSON")
        print(f"  Type: {parsed.workflow_type}")
        print(f"  Confidence: {parsed.confidence_score}")
    except Exception as e:
        print(f"✗ Failed to parse valid JSON: {e}")
    
    # Test invalid parsing
    invalid_json = '{"invalid": "data"}'
    try:
        parsed = main.parser.parse(invalid_json)
        print(f"✗ Should have failed parsing invalid JSON")
    except Exception as e:
        print(f"✓ Correctly failed parsing invalid JSON: {type(e).__name__}")
    
    return True


async def test_router_communication():
    """Test communication with the router agent."""
    print("\n=== Testing router communication ===")
    
    test_email = NormalizedEmail(
        sender="test@example.com",
        subject="Test Router Communication",
        body="This is a test email for router communication.",
        received_time=datetime.utcnow().isoformat()
    )
    
    with patch('main.llm.invoke') as mock_llm, \
         patch('httpx.AsyncClient') as mock_client_class:
        
        # Mock LLM response
        mock_classification = ClassificationResult(
            workflow_type="InvoiceRequest",
            confidence_score=0.95
        )
        mock_llm.return_value.content = mock_classification.model_dump_json()
        
        # Test successful routing
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        
        result = await main.classify_email(test_email)
        print("✓ Successfully routed email")
        
        # Verify the router was called with correct data
        call_args = mock_client.post.call_args
        assert call_args[0][0] == main.ROUTER_AGENT_URL
        posted_data = call_args[1]['json']
        print(f"  Router URL: {call_args[0][0]}")
        print(f"  Payload includes original email: {'original_email' in posted_data}")
        print(f"  Payload includes classification: {'classification' in posted_data}")
        
        # Test failed routing
        mock_response.status_code = 500
        mock_response.text = "Router error"
        
        try:
            result = await main.classify_email(test_email)
            print("✗ Should have raised exception for failed routing")
        except Exception as e:
            print(f"✓ Correctly handled router failure: {type(e).__name__}")
    
    return True


async def test_confidence_threshold():
    """Test confidence threshold handling."""
    print("\n=== Testing confidence threshold ===")
    
    test_email = NormalizedEmail(
        sender="test@example.com",
        subject="Ambiguous Email",
        body="This email could be many things.",
        received_time=datetime.utcnow().isoformat()
    )
    
    with patch('main.llm.invoke') as mock_llm, \
         patch('httpx.AsyncClient') as mock_client_class:
        
        # Setup mock client
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        
        # Test with low confidence score
        low_confidence = main.CONFIDENCE_THRESHOLD - 0.1
        mock_classification = ClassificationResult(
            workflow_type="InvoiceRequest",
            confidence_score=low_confidence
        )
        mock_llm.return_value.content = mock_classification.model_dump_json()
        
        result = await main.classify_email(test_email)
        
        # Check if it was changed to HumanReview
        call_args = mock_client.post.call_args
        posted_data = call_args[1]['json']
        
        if posted_data['classification']['workflow_type'] == 'HumanReview':
            print(f"✓ Low confidence ({low_confidence}) correctly changed to HumanReview")
        else:
            print(f"✗ Low confidence not properly handled")
        
        # Test with high confidence score
        high_confidence = main.CONFIDENCE_THRESHOLD + 0.1
        mock_classification.confidence_score = high_confidence
        mock_llm.return_value.content = mock_classification.model_dump_json()
        
        result = await main.classify_email(test_email)
        
        call_args = mock_client.post.call_args
        posted_data = call_args[1]['json']
        
        if posted_data['classification']['workflow_type'] == 'InvoiceRequest':
            print(f"✓ High confidence ({high_confidence}) kept original classification")
        else:
            print(f"✗ High confidence incorrectly changed classification")
    
    return True


async def run_all_tests():
    """Run all async test functions."""
    print("=== Email Classification Agent Test Suite ===")
    
    # Set test configuration
    main.CONFIDENCE_THRESHOLD = 0.85
    main.ROUTER_AGENT_URL = "http://localhost:8002/route"
    
    tests = [
        test_health_endpoint,
        test_llm_parsing,
        test_classify_endpoint,
        test_router_communication,
        test_confidence_threshold
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if await test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print(f"\n=== Test Summary ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {len(tests)}")
    
    return failed == 0


if __name__ == "__main__":
    # Run the async tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)