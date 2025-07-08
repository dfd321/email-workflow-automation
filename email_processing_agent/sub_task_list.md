# Sub-Task List for Email Processing Agent

**Objective:** Implement the logic to fetch, normalize, and dispatch emails.

1.  **Load Configuration:**
    *   Read the `.env` file to load all necessary credentials and URLs (`EMAIL_PROVIDER`, `IMAP_SERVER`, `IMAP_USERNAME`, `IMAP_PASSWORD`, `CLASSIFICATION_AGENT_URL`, etc.).

2.  **Implement Email Fetching:**
    *   Create a function `connect_to_imap()` that establishes and authenticates a connection to the IMAP server.
    *   Create a function `fetch_unseen_emails_imap()` that searches for and retrieves all unseen emails.
    *   *(Optional/Future)* Create similar functions for the MS Graph API (`connect_to_msgraph()`, `fetch_unread_emails_msgraph()`).

3.  **Implement Email Normalization:**
    *   Create a function `normalize_email(raw_email)` that takes a raw email object as input.
    *   Inside this function, parse the email to extract the sender, subject, plain text body, and received date.
    *   Use `BeautifulSoup4` to convert any HTML body to plain text.
    *   Ensure the `received_time` is converted to a standard ISO 8601 string format.
    *   Return a `NormalizedEmail` Pydantic object (from `shared/models.py`).

4.  **Implement Dispatch Logic:**
    *   Create a function `dispatch_to_classifier(email: NormalizedEmail)` that takes the normalized email object.
    *   This function should make an HTTP POST request to the `CLASSIFICATION_AGENT_URL`, sending the email object's JSON representation as the payload.
    *   Add error handling for the request (e.g., network errors, non-200 status codes).

5.  **Create Main Loop:**
    *   In `main()`, create a `while True` loop that runs indefinitely.
    *   Inside the loop, call the functions to connect, fetch, normalize, and dispatch emails.
    *   Mark emails as "seen" or "read" after successful processing to avoid fetching them again.
    *   Use `time.sleep(30)` at the end of the loop to wait before the next poll.

6.  **Add Logging:**
    *   Configure Python's `logging` module.
    *   Add log messages for key events: starting the agent, fetching emails, successful normalization, dispatching to the classifier, and any errors encountered.
