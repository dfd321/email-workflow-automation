# Atomic Task Lists for Email Workflow Automation Agents

## Email Processing Agent

**Objective:** To fetch new emails from the email server, normalize them into a standard JSON format, and pass them to the Email Classification Agent.

*   **Task 1: Environment Setup**
    *   1.1: Create a directory named `email_processing_agent`.
    *   1.2: Initialize a Python virtual environment within the directory.
    *   1.3: Create a `requirements.txt` file with the following libraries: `imaplib2`, `msal`, `requests`, `python-dotenv`, `beautifulsoup4`.
    *   1.4: Create a `.env` file to store email credentials (IMAP/MS Graph), API endpoints, and other configuration.
    *   1.5: Create the main application file, `main.py`.

*   **Task 2: Implement Email Fetching**
    *   2.1: In `main.py`, create a function to connect to and authenticate with an IMAP server using credentials from `.env`.
    *   2.2: Implement a function to search for and fetch unseen emails from the IMAP server.
    *   2.3: Create a function to connect to and authenticate with the Microsoft Graph API for Outlook/Office 365 mailboxes using credentials from `.env`.
    *   2.4: Implement a function to fetch unread emails via the MS Graph API.
    *   2.5: Create a main polling loop that checks for new emails every 30 seconds, using either IMAP or MS Graph based on a setting in `.env`.

*   **Task 3: Implement Email Normalization**
    *   3.1: Create a function to parse a raw email and extract the sender, subject, plain text body, and received timestamp.
    *   3.2: If the body is HTML, use BeautifulSoup4 to convert it to plain text.
    *   3.3: Normalize the extracted data into a JSON object: `{ "sender": "...", "subject": "...", "body": "...", "received_time": "..." }`.
    *   3.4: Handle various email content types and decode any non-standard text encoding.

*   **Task 4: Implement Communication with Classification Agent**
    *   4.1: Create a function to send the normalized JSON payload to the Email Classification Agent's API endpoint (URL from `.env`) via an HTTP POST request.
    *   4.2: Implement error handling for network issues or non-successful responses from the classification agent.

*   **Task 5: Logging and Error Handling**
    *   5.1: Configure Python's `logging` module to log agent activities.
    *   5.2: Log successful email fetches, normalizations, and dispatches.
    *   5.3: Implement a retry mechanism with exponential backoff for transient network errors.

---

## Email Classification Agent

**Objective:** To receive a normalized email, classify its intent using an LLM, and pass the result to the Workflow Router Agent.

*   **Task 1: Environment Setup**
    *   1.1: Create a directory named `email_classification_agent`.
    *   1.2: Initialize a Python virtual environment.
    *   1.3: Create a `requirements.txt` file with: `fastapi`, `uvicorn`, `langchain`, `openai`, `python-dotenv`, `pydantic`.
    *   1.4: Create a `.env` file for the OpenAI API key and other settings.
    *   1.5: Create the main application file, `main.py`.

*   **Task 2: Implement API Endpoint**
    *   2.1: In `main.py`, set up a FastAPI application.
    *   2.2: Create a POST endpoint (e.g., `/classify`) that accepts the normalized email JSON.
    *   2.3: Define a Pydantic model to validate the structure of the incoming request body.

*   **Task 3: Implement Email Classification**
    *   3.1: Create a function that takes the email data and uses LangChain with the OpenAI API to classify the intent.
    *   3.2: Use OpenAI's "function calling" feature to ensure a structured output. Define functions for each workflow type (e.g., `invoice_request`, `new_client_inquiry`).
    *   3.3: The classification should return a `workflow_type` and a `confidence_score`.

*   **Task 4: Implement Communication with Workflow Router**
    *   4.1: Create a JSON payload containing the original email data and the classification result.
    *   4.2: If the confidence score is above the threshold defined in `.env`, send the payload to the Workflow Router Agent via an HTTP POST request.
    *   4.3: If the confidence is below the threshold, send the payload to a "human review" endpoint or queue.

*   **Task 5: Logging and Error Handling**
    *   5.1: Configure Python's `logging` module.
    *   5.2: Log all incoming requests, classification results, and routing decisions.
    *   5.3: Log any errors from the LLM or in communication with the router.

---

## Workflow Router Agent

**Objective:** To receive a classified email and route it to the appropriate handler based on its workflow type.

*   **Task 1: Environment Setup**
    *   1.1: Create a directory named `workflow_router_agent`.
    *   1.2: Initialize a Python virtual environment.
    *   1.3: Create a `requirements.txt` file with: `fastapi`, `uvicorn`, `requests`, `python-dotenv`, `pydantic`.
    *   1.4: Create a `.env` file to store the API endpoint URLs for the various handlers (Invoice, Scheduler, etc.).
    *   1.5: Create the main application file, `main.py`.

*   **Task 2: Implement API Endpoint**
    *   2.1: In `main.py`, set up a FastAPI application.
    *   2.2: Create a POST endpoint (e.g., `/route`) that accepts the classified email JSON.
    *   2.3: Define a Pydantic model to validate the incoming request body.

*   **Task 3: Implement Routing Logic**
    *   3.1: Create a function that takes the classified email data as input.
    *   3.2: Use a dictionary to map the `workflow_type` to the corresponding handler's URL, loaded from `.env`.
        *   `InvoiceRequest` -> `INVOICE_HANDLER_URL`
        *   `AppointmentBooking` -> `SCHEDULER_URL`
        *   `NewClientInquiry` -> `INFO_RETRIEVAL_URL`

*   **Task 4: Implement Communication with Handlers**
    *   4.1: Forward the JSON payload to the appropriate handler's endpoint via an HTTP POST request.
    *   4.2: Implement error handling for cases where a handler is unavailable or returns an error.

*   **Task 5: Logging and Error Handling**
    *   5.1: Configure Python's `logging` module.
    *   5.2: Log each routing decision, including the workflow type and the handler it was routed to.
    *   5.3: For un-routable workflows, implement a fallback mechanism that flags them for manual review.
