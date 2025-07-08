#!/usr/bin/env python3
"""Test script for the workflow router agent."""

import asyncio
import httpx
import json
import sys
import os

# Add parent directory to path to import shared models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.models import ClassifiedEmail, NormalizedEmail, ClassificationResult

async def test_router():
    """Test the workflow router with sample payloads."""
    
    # Create test payloads for different workflow types
    test_cases = [
        {
            "name": "Invoice Request",
            "payload": ClassifiedEmail(
                original_email=NormalizedEmail(
                    sender="vendor@example.com",
                    subject="Invoice #12345",
                    body="Please find attached invoice #12345 for services rendered.",
                    received_time="2024-01-15T10:30:00Z"
                ),
                classification=ClassificationResult(
                    workflow_type="InvoiceRequest",
                    confidence_score=0.95
                )
            )
        },
        {
            "name": "Appointment Booking",
            "payload": ClassifiedEmail(
                original_email=NormalizedEmail(
                    sender="client@example.com",
                    subject="Schedule appointment",
                    body="I would like to schedule an appointment for next week.",
                    received_time="2024-01-15T14:20:00Z"
                ),
                classification=ClassificationResult(
                    workflow_type="AppointmentBooking",
                    confidence_score=0.88
                )
            )
        },
        {
            "name": "New Client Inquiry",
            "payload": ClassifiedEmail(
                original_email=NormalizedEmail(
                    sender="newclient@example.com",
                    subject="Information about your services",
                    body="I'm interested in learning more about your services.",
                    received_time="2024-01-15T16:45:00Z"
                ),
                classification=ClassificationResult(
                    workflow_type="NewClientInquiry",
                    confidence_score=0.92
                )
            )
        },
        {
            "name": "Human Review",
            "payload": ClassifiedEmail(
                original_email=NormalizedEmail(
                    sender="complex@example.com",
                    subject="Complex inquiry",
                    body="This is a complex inquiry that requires human review.",
                    received_time="2024-01-15T18:00:00Z"
                ),
                classification=ClassificationResult(
                    workflow_type="HumanReview",
                    confidence_score=0.65
                )
            )
        }
    ]
    
    router_url = "http://localhost:8002/route"
    
    async with httpx.AsyncClient() as client:
        print("Testing Workflow Router Agent...")
        print("=" * 50)
        
        for test_case in test_cases:
            print(f"\nTesting: {test_case['name']}")
            print(f"Workflow Type: {test_case['payload'].classification.workflow_type}")
            
            try:
                response = await client.post(
                    router_url,
                    json=test_case['payload'].model_dump(),
                    timeout=30.0
                )
                
                print(f"Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"Response: {json.dumps(result, indent=2)}")
                else:
                    print(f"Error: {response.text}")
                    
            except httpx.ConnectError:
                print("❌ Connection failed - Is the router agent running?")
            except Exception as e:
                print(f"❌ Error: {e}")
            
            print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_router())