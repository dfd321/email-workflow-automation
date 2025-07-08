# Email Workflow Automation

This project contains a set of AI agents to automate email-driven workflows for professional offices.

## Project Structure

- `email_processing_agent`: Fetches and normalizes emails.
- `email_classification_agent`: Classifies the intent of emails.
- `workflow_router_agent`: Routes classified emails to the appropriate handler.
- `invoice_handler_agent`: Handles invoice-related requests.
- `scheduler_agent`: Handles appointment scheduling.
- `info_retrieval_agent`: Handles new client inquiries.
- `shared`: Contains shared code, such as Pydantic models.
- `docs`: Contains project documentation.
- `tests`: Contains integration tests.

## Getting Started

1.  Navigate to each agent's directory.
2.  Create a `.env` file from the `.env.example`.
3.  Install dependencies: `pip install -r requirements.txt`.
4.  Run the agent: `python main.py`.

Alternatively, use the provided `docker-compose.yml` to run all agents.
