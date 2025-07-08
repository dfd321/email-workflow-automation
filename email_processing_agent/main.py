# main.py for email_processing_agent
import os
import time
import logging
import imaplib
import email
from email.header import decode_header
from datetime import datetime
from typing import Optional, List
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.models import NormalizedEmail

# Load environment variables
load_dotenv()

# Configuration
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "IMAP")
IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_USERNAME = os.getenv("IMAP_USERNAME")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")
MS_GRAPH_CLIENT_ID = os.getenv("MS_GRAPH_CLIENT_ID")
MS_GRAPH_CLIENT_SECRET = os.getenv("MS_GRAPH_CLIENT_SECRET")
MS_GRAPH_TENANT_ID = os.getenv("MS_GRAPH_TENANT_ID")
CLASSIFICATION_AGENT_URL = os.getenv("CLASSIFICATION_AGENT_URL")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def connect_to_imap() -> Optional[imaplib.IMAP4_SSL]:
    """Establish and authenticate a connection to the IMAP server."""
    try:
        logger.info(f"Connecting to IMAP server: {IMAP_SERVER}")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(IMAP_USERNAME, IMAP_PASSWORD)
        logger.info("Successfully connected and authenticated to IMAP server")
        return mail
    except Exception as e:
        logger.error(f"Failed to connect to IMAP server: {e}")
        return None


def fetch_unseen_emails_imap(mail: imaplib.IMAP4_SSL) -> List[email.message.Message]:
    """Fetch all unseen emails from the IMAP server."""
    emails = []
    try:
        mail.select("INBOX")
        status, messages = mail.search(None, "UNSEEN")
        
        if status == "OK":
            email_ids = messages[0].split()
            logger.info(f"Found {len(email_ids)} unseen emails")
            
            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status == "OK":
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    emails.append(msg)
                    
        return emails
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        return []


def get_email_body(msg: email.message.Message) -> str:
    """Extract the body text from an email message."""
    body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode()
                    break
                except:
                    pass
            elif part.get_content_type() == "text/html":
                try:
                    html_body = part.get_payload(decode=True).decode()
                    soup = BeautifulSoup(html_body, 'html.parser')
                    body = soup.get_text(strip=True)
                except:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode()
                if msg.get_content_type() == "text/html":
                    soup = BeautifulSoup(body, 'html.parser')
                    body = soup.get_text(strip=True)
        except:
            pass
    
    return body.strip()


def decode_mime_header(header_value: str) -> str:
    """Decode MIME encoded header values."""
    if not header_value:
        return ""
    
    decoded_parts = []
    for part, encoding in decode_header(header_value):
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(encoding or 'utf-8', errors='ignore'))
        else:
            decoded_parts.append(part)
    
    return ' '.join(decoded_parts)


def normalize_email(raw_email: email.message.Message) -> Optional[NormalizedEmail]:
    """Normalize a raw email into the standard format."""
    try:
        # Extract sender
        sender = decode_mime_header(raw_email.get("From", ""))
        
        # Extract subject
        subject = decode_mime_header(raw_email.get("Subject", ""))
        
        # Extract body
        body = get_email_body(raw_email)
        
        # Extract and format received time
        date_str = raw_email.get("Date", "")
        try:
            # Parse the email date
            email_date = email.utils.parsedate_to_datetime(date_str)
            received_time = email_date.isoformat()
        except:
            # Fallback to current time if parsing fails
            received_time = datetime.utcnow().isoformat()
        
        normalized = NormalizedEmail(
            sender=sender,
            subject=subject,
            body=body,
            received_time=received_time
        )
        
        logger.info(f"Successfully normalized email from {sender} with subject: {subject}")
        return normalized
        
    except Exception as e:
        logger.error(f"Error normalizing email: {e}")
        return None


def dispatch_to_classifier(email: NormalizedEmail) -> bool:
    """Send the normalized email to the classification agent."""
    try:
        logger.info(f"Dispatching email to classifier: {CLASSIFICATION_AGENT_URL}")
        
        response = requests.post(
            CLASSIFICATION_AGENT_URL,
            json=email.model_dump(),
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info("Successfully dispatched email to classifier")
            return True
        else:
            logger.error(f"Classifier returned status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error dispatching to classifier: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error dispatching to classifier: {e}")
        return False


def mark_email_as_seen(mail: imaplib.IMAP4_SSL, email_id: bytes):
    """Mark an email as seen to avoid processing it again."""
    try:
        mail.store(email_id, '+FLAGS', '\\Seen')
        logger.debug(f"Marked email {email_id} as seen")
    except Exception as e:
        logger.error(f"Error marking email as seen: {e}")


def main():
    logger.info("Starting Email Processing Agent...")
    
    # Validate configuration
    if EMAIL_PROVIDER == "IMAP":
        if not all([IMAP_SERVER, IMAP_USERNAME, IMAP_PASSWORD]):
            logger.error("IMAP configuration incomplete. Please check .env file.")
            return
    elif EMAIL_PROVIDER == "MS_GRAPH":
        logger.error("MS Graph provider not implemented yet")
        return
    
    if not CLASSIFICATION_AGENT_URL:
        logger.error("CLASSIFICATION_AGENT_URL not configured. Please check .env file.")
        return
    
    # Main loop
    while True:
        try:
            logger.info("Starting email poll cycle")
            
            if EMAIL_PROVIDER == "IMAP":
                # Connect to IMAP
                mail = connect_to_imap()
                if not mail:
                    logger.error("Failed to connect to IMAP server, waiting before retry...")
                    time.sleep(30)
                    continue
                
                # Fetch unseen emails
                mail.select("INBOX")
                status, messages = mail.search(None, "UNSEEN")
                
                if status == "OK":
                    email_ids = messages[0].split()
                    logger.info(f"Found {len(email_ids)} unseen emails")
                    
                    for email_id in email_ids:
                        try:
                            # Fetch the email
                            status, msg_data = mail.fetch(email_id, "(RFC822)")
                            if status != "OK":
                                continue
                            
                            raw_email = msg_data[0][1]
                            msg = email.message_from_bytes(raw_email)
                            
                            # Normalize the email
                            normalized = normalize_email(msg)
                            if not normalized:
                                logger.error("Failed to normalize email, marking as seen anyway")
                                mark_email_as_seen(mail, email_id)
                                continue
                            
                            # Dispatch to classifier
                            if dispatch_to_classifier(normalized):
                                # Mark as seen only after successful processing
                                mark_email_as_seen(mail, email_id)
                            else:
                                logger.warning("Failed to dispatch email, will retry in next cycle")
                                
                        except Exception as e:
                            logger.error(f"Error processing email {email_id}: {e}")
                            # Mark as seen to avoid getting stuck
                            mark_email_as_seen(mail, email_id)
                
                # Close connection
                mail.logout()
                
            logger.info("Email poll cycle completed, waiting 30 seconds...")
            time.sleep(30)
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            time.sleep(30)


if __name__ == "__main__":
    main()
