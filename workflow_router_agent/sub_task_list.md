# Sub-Task List for Workflow Router Agent

**Objective:** Implement the logic to route classified emails to the correct handler.

1.  **Load Configuration:**
    *   Read the `.env` file to load the URLs for all handlers (`INVOICE_HANDLER_URL`, `SCHEDULER_URL`, etc.).

2.  **Update API Endpoint:**
    *   In `main.py`, import the `ClassifiedEmail` model from `shared/models.py`.
    *   Update the `/route` endpoint to ensure its request body is validated as a `ClassifiedEmail` object.

3.  **Implement Routing Logic:**
    *   Create a dictionary that maps the `workflow_type` string to the corresponding handler URL.
        ```python
        HANDLER_MAP = {
            "InvoiceRequest": os.getenv("INVOICE_HANDLER_URL"),
            "AppointmentBooking": os.getenv("SCHEDULER_URL"),
            "NewClientInquiry": os.getenv("INFO_RETRIEVAL_URL"),
            "HumanReview": os.getenv("HUMAN_REVIEW_URL")
        }
        ```
    *   In the `/route` endpoint, get the `workflow_type` from the incoming payload.
    *   Use the `HANDLER_MAP` to find the correct destination URL.

4.  **Implement Dispatch Logic:**
    *   Create a function `forward_payload(url: str, payload: ClassifiedEmail)` that takes the destination URL and the original payload.
    *   This function should make an HTTP POST request to the given URL, sending the `ClassifiedEmail` object's JSON as the payload.
    *   Add error handling for the request.

5.  **Add Logging and Fallback:**
    *   Configure Python's `logging` module.
    *   Log every incoming routing request, including the `workflow_type`.
    *   Log which handler the payload is being forwarded to.
    *   If a `workflow_type` does not exist in the `HANDLER_MAP`, log it as an error and implement a fallback (e.g., send it to the human review queue).
