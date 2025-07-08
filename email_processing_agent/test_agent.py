#!/usr/bin/env python3
"""Test script for email processing agent functionality."""
import os
import sys
import email
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.models import NormalizedEmail

# Import our main module
import main

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_email():
    """Create a test email message."""
    msg = email.message.EmailMessage()
    msg['From'] = 'test@example.com'
    msg['Subject'] = 'Test Email Subject'
    msg['Date'] = 'Mon, 01 Jan 2024 12:00:00 +0000'
    msg.set_content('This is the plain text body of the test email.')
    return msg


def test_normalize_email():
    """Test the normalize_email function."""
    print("\n=== Testing normalize_email ===")
    test_msg = create_test_email()
    
    normalized = main.normalize_email(test_msg)
    
    if normalized:
        print(f"✓ Successfully normalized email")
        print(f"  Sender: {normalized.sender}")
        print(f"  Subject: {normalized.subject}")
        print(f"  Body: {normalized.body}")
        print(f"  Received Time: {normalized.received_time}")
        return True
    else:
        print("✗ Failed to normalize email")
        return False


def test_decode_mime_header():
    """Test MIME header decoding."""
    print("\n=== Testing decode_mime_header ===")
    
    # Test regular string
    result = main.decode_mime_header("Simple Subject")
    print(f"✓ Simple header: '{result}'")
    
    # Test encoded string
    encoded = "=?UTF-8?B?VGVzdCDwn5iA?="  # "Test 😀"
    result = main.decode_mime_header(encoded)
    print(f"✓ Encoded header: '{result}'")
    
    return True


def test_get_email_body():
    """Test email body extraction."""
    print("\n=== Testing get_email_body ===")
    
    # Test plain text email
    msg = email.message.EmailMessage()
    msg.set_content("Plain text content")
    body = main.get_email_body(msg)
    print(f"✓ Plain text body: '{body}'")
    
    # Test HTML email
    html_msg = email.message.EmailMessage()
    html_msg.set_content("<html><body><p>HTML content</p></body></html>", subtype='html')
    body = main.get_email_body(html_msg)
    print(f"✓ HTML body converted: '{body}'")
    
    return True


def test_dispatch_to_classifier():
    """Test the dispatch_to_classifier function with mock."""
    print("\n=== Testing dispatch_to_classifier ===")
    
    # Create a test normalized email
    test_email = NormalizedEmail(
        sender="test@example.com",
        subject="Test Subject",
        body="Test body content",
        received_time=datetime.utcnow().isoformat()
    )
    
    # Mock the requests.post call
    with patch('main.requests.post') as mock_post:
        # Simulate successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Set the classification URL for testing
        main.CLASSIFICATION_AGENT_URL = "http://localhost:8001/classify"
        
        result = main.dispatch_to_classifier(test_email)
        
        if result:
            print("✓ Successfully dispatched email (mocked)")
            print(f"  Called URL: {mock_post.call_args[0][0]}")
            print(f"  Payload: {mock_post.call_args[1]['json']}")
        else:
            print("✗ Failed to dispatch email")
        
        # Test failure case
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        result = main.dispatch_to_classifier(test_email)
        print(f"✓ Handled error response correctly: {not result}")
    
    return True


def test_imap_connection():
    """Test IMAP connection handling."""
    print("\n=== Testing IMAP Connection (with mock) ===")
    
    with patch('main.imaplib.IMAP4_SSL') as mock_imap:
        # Mock successful connection
        mock_mail = MagicMock()
        mock_imap.return_value = mock_mail
        
        # Set test credentials
        main.IMAP_SERVER = "imap.test.com"
        main.IMAP_USERNAME = "test@test.com"
        main.IMAP_PASSWORD = "testpass"
        
        result = main.connect_to_imap()
        
        if result:
            print("✓ Successfully connected to IMAP (mocked)")
            mock_mail.login.assert_called_with("test@test.com", "testpass")
        else:
            print("✗ Failed to connect to IMAP")
            
        # Test connection failure
        mock_imap.side_effect = Exception("Connection failed")
        result = main.connect_to_imap()
        print(f"✓ Handled connection error correctly: {result is None}")
    
    return True


def run_all_tests():
    """Run all test functions."""
    print("=== Email Processing Agent Test Suite ===")
    
    tests = [
        test_decode_mime_header,
        test_get_email_body,
        test_normalize_email,
        test_dispatch_to_classifier,
        test_imap_connection
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
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
    success = run_all_tests()
    sys.exit(0 if success else 1)