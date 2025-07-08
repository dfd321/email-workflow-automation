#!/usr/bin/env python3
"""Example script demonstrating how to use the email classification agent."""
import requests
import json
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.models import NormalizedEmail


def classify_email(email_data):
    """Send an email to the classification agent."""
    url = "http://localhost:8001/classify"
    
    try:
        response = requests.post(url, json=email_data)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to classification agent. Make sure it's running on port 8001.")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def main():
    """Run example email classifications."""
    print("=== Email Classification Agent Example Usage ===\n")
    
    # Example emails to classify
    example_emails = [
        {
            "name": "Invoice Email",
            "email": NormalizedEmail(
                sender="accounting@vendor.com",
                subject="Invoice #2024-001 - Payment Due",
                body="Dear Customer,\n\nAttached is the invoice for services rendered last month. "
                     "The total amount is $2,500.00. Payment is due by the end of this month.\n\n"
                     "Thank you for your business!",
                received_time=datetime.utcnow().isoformat()
            )
        },
        {
            "name": "Meeting Request",
            "email": NormalizedEmail(
                sender="client@business.com",
                subject="Let's Schedule a Call",
                body="Hi,\n\nI'd like to discuss the project status with you. "
                     "Are you free for a call tomorrow at 2 PM? Let me know what works for you.\n\n"
                     "Best regards,\nJohn",
                received_time=datetime.utcnow().isoformat()
            )
        },
        {
            "name": "New Client Inquiry",
            "email": NormalizedEmail(
                sender="prospect@newcompany.com",
                subject="Interested in Your Services",
                body="Hello,\n\nI came across your website and I'm impressed with your portfolio. "
                     "Our company is looking for a consulting partner for our digital transformation project. "
                     "Could you send us more information about your services and availability?\n\n"
                     "Looking forward to hearing from you.",
                received_time=datetime.utcnow().isoformat()
            )
        },
        {
            "name": "Ambiguous Email",
            "email": NormalizedEmail(
                sender="random@email.com",
                subject="Quick Question",
                body="Hey, I need some help with something. Can you assist?",
                received_time=datetime.utcnow().isoformat()
            )
        },
        {
            "name": "Mixed Intent Email",
            "email": NormalizedEmail(
                sender="customer@company.com",
                subject="RE: Our Discussion",
                body="Thanks for the meeting yesterday. I've reviewed the invoice you sent and will "
                     "process the payment tomorrow. Also, can we schedule another meeting next week "
                     "to discuss the new requirements?",
                received_time=datetime.utcnow().isoformat()
            )
        }
    ]
    
    # Check if the agent is running
    try:
        health_check = requests.get("http://localhost:8001/health")
        if health_check.status_code == 200:
            print("✓ Classification agent is running\n")
        else:
            print("✗ Classification agent health check failed\n")
            return
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to classification agent.")
        print("  Please make sure it's running: python main.py")
        print("  Also ensure the router agent is running on port 8002")
        return
    
    # Process each example email
    for example in example_emails:
        print(f"\n--- {example['name']} ---")
        print(f"From: {example['email'].sender}")
        print(f"Subject: {example['email'].subject}")
        print(f"Body preview: {example['email'].body[:100]}...")
        
        # Classify the email
        result = classify_email(example['email'].model_dump())
        
        if result:
            classification = result['classification']
            print(f"\nClassification Result:")
            print(f"  Workflow Type: {classification['workflow_type']}")
            print(f"  Confidence: {classification['confidence_score']:.2f}")
            print(f"  Routed: {result['routed']}")
            
            # Explain the result
            if classification['confidence_score'] < 0.85:
                print(f"  Note: Low confidence - email will be sent for human review")
            
            if classification['workflow_type'] == 'InvoiceRequest':
                print(f"  → Email will be processed by the invoice handler")
            elif classification['workflow_type'] == 'AppointmentBooking':
                print(f"  → Email will be processed by the scheduler agent")
            elif classification['workflow_type'] == 'NewClientInquiry':
                print(f"  → Email will be processed by the info retrieval agent")
            elif classification['workflow_type'] == 'HumanReview':
                print(f"  → Email requires human review")
        else:
            print("\n✗ Classification failed")
    
    print("\n=== Example Complete ===")
    print("\nTo use this in production:")
    print("1. Ensure all agents are running (classification, router, and workflow agents)")
    print("2. Send normalized email data to http://localhost:8001/classify")
    print("3. The classification agent will automatically route to the appropriate workflow")


if __name__ == "__main__":
    main()