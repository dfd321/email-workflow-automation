# main.py for workflow_router_agent
from fastapi import FastAPI
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import sys
import logging
import httpx

# Add parent directory to path to import shared models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.models import ClassifiedEmail, NormalizedEmail, ClassificationResult

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Handler URL mapping
HANDLER_MAP = {
    "InvoiceRequest": os.getenv("INVOICE_HANDLER_URL"),
    "AppointmentBooking": os.getenv("SCHEDULER_URL"),
    "NewClientInquiry": os.getenv("INFO_RETRIEVAL_URL"),
    "HumanReview": os.getenv("HUMAN_REVIEW_URL")
}

async def forward_payload(url: str, payload: ClassifiedEmail) -> dict:
    """Forward the classified email payload to the appropriate handler."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload.model_dump(), timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP error occurred while forwarding to {url}: {e}")
            raise
        except httpx.RequestError as e:
            logging.error(f"Request error occurred while forwarding to {url}: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error occurred while forwarding to {url}: {e}")
            raise

@app.post("/route")
async def route_workflow(email: ClassifiedEmail):
    logger.info(f"Received classified email for routing with workflow_type: {email.classification.workflow_type}")
    
    # Get the destination URL from the handler map
    workflow_type = email.classification.workflow_type
    destination_url = HANDLER_MAP.get(workflow_type)
    
    if not destination_url:
        logger.error(f"Unknown workflow_type: {workflow_type}. Routing to human review.")
        destination_url = HANDLER_MAP.get("HumanReview")
        if not destination_url:
            logger.critical("Human review URL not configured!")
            return {"status": "error", "message": "No handler available for this workflow type"}
    
    logger.info(f"Forwarding payload to handler at: {destination_url}")
    
    try:
        # Forward the payload to the appropriate handler
        result = await forward_payload(destination_url, email)
        logger.info(f"Successfully routed email to {workflow_type} handler")
        return {"status": "routed", "handler": workflow_type, "result": result}
    except Exception as e:
        logger.error(f"Failed to route email: {str(e)}")
        # Fallback to human review on error
        if workflow_type != "HumanReview":
            logger.info("Attempting fallback to human review")
            try:
                human_review_url = HANDLER_MAP.get("HumanReview")
                if human_review_url:
                    result = await forward_payload(human_review_url, email)
                    return {"status": "routed", "handler": "HumanReview", "fallback": True, "result": result}
            except Exception as fallback_error:
                logger.error(f"Fallback to human review also failed: {str(fallback_error)}")
        
        return {"status": "error", "message": f"Failed to route email: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
