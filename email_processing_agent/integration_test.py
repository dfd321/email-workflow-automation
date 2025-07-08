#!/usr/bin/env python3
"""Integration test for email processing agent with mock IMAP server."""
import os
import sys
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import threading
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our main module
import main


class MockClassificationHandler(BaseHTTPRequestHandler):
    """Mock HTTP server to simulate the classification agent."""
    
    def do_POST(self):
        if self.path == '/classify':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                email_data = json.loads(post_data.decode('utf-8'))
                print(f"\n[Mock Classifier] Received email:")
                print(f"  From: {email_data.get('sender')}")
                print(f"  Subject: {email_data.get('subject')}")
                print(f"  Body preview: {email_data.get('body', '')[:50]}...")
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {'status': 'classified', 'workflow': 'support'}
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                print(f"[Mock Classifier] Error: {e}")
                self.send_error(400, "Bad Request")
        else:
            self.send_error(404, "Not Found")
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass


def start_mock_classifier(port=8001):
    """Start the mock classification server in a separate thread."""
    server = HTTPServer(('localhost', port), MockClassificationHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server


def create_test_emails():
    """Create multiple test email messages."""
    emails = []
    
    # Email 1: Simple text email
    msg1 = email.message.EmailMessage()
    msg1['From'] = 'customer@example.com'
    msg1['Subject'] = 'Help with login issue'
    msg1['Date'] = 'Mon, 01 Jan 2024 10:00:00 +0000'
    msg1['Message-ID'] = '<msg1@example.com>'
    msg1.set_content('I cannot log into my account. Please help!')
    emails.append(msg1)
    
    # Email 2: HTML email
    msg2 = email.message.EmailMessage()
    msg2['From'] = 'sales@company.com'
    msg2['Subject'] = 'Special Offer Just for You!'
    msg2['Date'] = 'Mon, 01 Jan 2024 11:00:00 +0000'
    msg2['Message-ID'] = '<msg2@example.com>'
    msg2.set_content('<html><body><h1>50% OFF Sale!</h1><p>Click here to save big!</p></body></html>', subtype='html')
    emails.append(msg2)
    
    # Email 3: Multipart email
    msg3 = MIMEMultipart('alternative')
    msg3['From'] = 'support@service.com'
    msg3['Subject'] = 'Your ticket has been updated'
    msg3['Date'] = 'Mon, 01 Jan 2024 12:00:00 +0000'
    msg3['Message-ID'] = '<msg3@example.com>'
    
    text_part = MIMEText('Your support ticket #1234 has been updated.', 'plain')
    html_part = MIMEText('<html><body><p>Your support ticket <b>#1234</b> has been updated.</p></body></html>', 'html')
    msg3.attach(text_part)
    msg3.attach(html_part)
    emails.append(msg3)
    
    return emails


def run_integration_test():
    """Run a full integration test of the email processing agent."""
    print("=== Email Processing Agent Integration Test ===\n")
    
    # Start mock classification server
    print("Starting mock classification server on port 8001...")
    classifier_server = start_mock_classifier(8001)
    time.sleep(1)  # Give server time to start
    
    # Override the classification URL
    main.CLASSIFICATION_AGENT_URL = "http://localhost:8001/classify"
    
    # Create test emails
    test_emails = create_test_emails()
    print(f"Created {len(test_emails)} test emails\n")
    
    # Mock IMAP connection
    with patch('main.imaplib.IMAP4_SSL') as mock_imap:
        mock_mail = MagicMock()
        mock_imap.return_value = mock_mail
        
        # Configure mock to return our test emails
        email_count = len(test_emails)
        mock_mail.search.return_value = ('OK', [b'1 2 3'])
        
        # Mock fetch to return our test emails
        fetch_responses = []
        for i, test_email in enumerate(test_emails):
            fetch_responses.append(('OK', [(None, test_email.as_bytes())]))
        
        mock_mail.fetch.side_effect = fetch_responses
        
        # Mock select and store
        mock_mail.select.return_value = ('OK', [b'3'])
        mock_mail.store.return_value = ('OK', [b''])
        
        # Set test credentials
        main.IMAP_SERVER = "imap.test.com"
        main.IMAP_USERNAME = "test@test.com"
        main.IMAP_PASSWORD = "testpass"
        main.EMAIL_PROVIDER = "IMAP"
        
        # Run one cycle of the main loop
        print("Running one email processing cycle...\n")
        
        try:
            # Connect
            mail = main.connect_to_imap()
            if mail:
                print("✓ Connected to mock IMAP server")
                
                # Process emails
                mail.select("INBOX")
                status, messages = mail.search(None, "UNSEEN")
                
                if status == "OK":
                    email_ids = messages[0].split()
                    print(f"✓ Found {len(email_ids)} unseen emails")
                    
                    processed_count = 0
                    for i, email_id in enumerate(email_ids):
                        if i < len(test_emails):
                            # Fetch email
                            status, msg_data = mail.fetch(email_id, "(RFC822)")
                            if status == "OK":
                                raw_email = msg_data[0][1]
                                msg = email.message_from_bytes(raw_email)
                                
                                # Normalize
                                normalized = main.normalize_email(msg)
                                if normalized:
                                    print(f"\n✓ Normalized email {i+1}:")
                                    print(f"  From: {normalized.sender}")
                                    print(f"  Subject: {normalized.subject}")
                                    
                                    # Dispatch
                                    if main.dispatch_to_classifier(normalized):
                                        print(f"✓ Dispatched email {i+1} to classifier")
                                        processed_count += 1
                                        
                                        # Mark as seen
                                        main.mark_email_as_seen(mail, email_id)
                    
                    print(f"\n✓ Successfully processed {processed_count}/{len(email_ids)} emails")
                
                # Logout
                mail.logout()
                print("✓ Disconnected from IMAP server")
                
        except Exception as e:
            print(f"✗ Error during processing: {e}")
            return False
    
    # Shutdown mock server
    classifier_server.shutdown()
    
    print("\n=== Integration Test Complete ===")
    return True


if __name__ == "__main__":
    success = run_integration_test()
    sys.exit(0 if success else 1)