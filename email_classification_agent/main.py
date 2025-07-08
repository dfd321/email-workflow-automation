# main.py for email_classification_agent
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import sys
import logging
import httpx
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

# Add parent directory to path to import shared models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.models import NormalizedEmail, ClassificationResult, ClassifiedEmail

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ROUTER_AGENT_URL = os.getenv("ROUTER_AGENT_URL", "http://localhost:8002/route")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.85"))

if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY not found in environment variables")
    raise ValueError("OPENAI_API_KEY is required")

app = FastAPI(title="Email Classification Agent")

# Initialize OpenAI LLM
llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model="gpt-3.5-turbo",
    temperature=0.1
)

# Create output parser for structured response
parser = PydanticOutputParser(pydantic_object=ClassificationResult)

# Create classification prompt template
classification_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an email classification expert. Analyze the email and classify it into one of these categories:
    - InvoiceRequest: Emails about invoices, billing, payments, or financial documents
    - AppointmentBooking: Emails about scheduling, meetings, appointments, or calendar events
    - NewClientInquiry: Emails from potential new clients asking about services or products
    - HumanReview: Emails that don't clearly fit into the above categories or are ambiguous
    
    Provide a confidence score between 0 and 1 indicating how confident you are in the classification.
    
    {format_instructions}"""),
    ("human", """Please classify this email:
    
    From: {sender}
    Subject: {subject}
    Body: {body}
    Received: {received_time}""")
])

@app.post("/classify")
async def classify_email(email: NormalizedEmail):
    """Classify an email and route it appropriately."""
    logger.info(f"Received email for classification from {email.sender}")
    
    try:
        # Prepare the prompt with format instructions
        formatted_prompt = classification_prompt.format_messages(
            sender=email.sender,
            subject=email.subject,
            body=email.body,
            received_time=email.received_time,
            format_instructions=parser.get_format_instructions()
        )
        
        # Get classification from LLM
        logger.info("Sending email to LLM for classification")
        response = llm.invoke(formatted_prompt)
        
        # Parse the response
        classification_result = parser.parse(response.content)
        logger.info(f"Classification result: {classification_result.workflow_type} "
                   f"with confidence {classification_result.confidence_score}")
        
        # Create classified email payload
        classified_email = ClassifiedEmail(
            original_email=email,
            classification=classification_result
        )
        
        # Determine routing based on confidence threshold
        if classification_result.confidence_score < CONFIDENCE_THRESHOLD:
            logger.warning(f"Low confidence score ({classification_result.confidence_score}), "
                          f"changing to HumanReview")
            classification_result.workflow_type = "HumanReview"
            classified_email.classification = classification_result
        
        # Send to router agent
        async with httpx.AsyncClient() as client:
            logger.info(f"Sending classified email to router at {ROUTER_AGENT_URL}")
            response = await client.post(
                ROUTER_AGENT_URL,
                json=classified_email.model_dump(),
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"Router returned error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to route email: {response.text}"
                )
            
            logger.info("Email successfully classified and routed")
            return {
                "status": "success",
                "classification": classification_result.model_dump(),
                "routed": True
            }
            
    except Exception as e:
        logger.error(f"Error classifying email: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "email_classification"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Email Classification Agent on port 8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
