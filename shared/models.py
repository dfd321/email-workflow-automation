# /home/dfdan/projects/email_workflow_automation/shared/models.py
from pydantic import BaseModel
from typing import Literal

class NormalizedEmail(BaseModel):
    """The standard format for an email after processing."""
    sender: str
    subject: str
    body: str
    received_time: str  # ISO 8601 format

class ClassificationResult(BaseModel):
    """The output of the classification agent."""
    workflow_type: Literal[
        'InvoiceRequest',
        'AppointmentBooking',
        'NewClientInquiry',
        'HumanReview'
    ]
    confidence_score: float

class ClassifiedEmail(BaseModel):
    """The final payload sent to the Workflow Router."""
    original_email: NormalizedEmail
    classification: ClassificationResult
