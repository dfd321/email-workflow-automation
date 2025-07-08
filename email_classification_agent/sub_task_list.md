# Sub-Task List for Email Classification Agent

**Objective:** Implement the logic to classify emails and route them based on intent.

1.  **Load Configuration:**
    *   Read the `.env` file to load `OPENAI_API_KEY`, `ROUTER_AGENT_URL`, and `CONFIDENCE_THRESHOLD`.

2.  **Update API Endpoint:**
    *   In `main.py`, import the `NormalizedEmail` and `ClassifiedEmail` models from `shared/models.py`.
    *   Update the `/classify` endpoint to ensure its request body is validated as a `NormalizedEmail` object.

3.  **Implement Classification Logic:**
    *   Create a function `classify_intent(email: NormalizedEmail)` that takes the normalized email as input.
    *   Inside this function, initialize the LangChain client with the OpenAI API key.
    *   Construct a prompt that includes the email's subject and body.
    *   Use OpenAI's "function calling" or a similar structured output feature to force the LLM to return a JSON object with `workflow_type` and `confidence_score`. The possible `workflow_type` values should be `InvoiceRequest`, `AppointmentBooking`, `NewClientInquiry`, and `HumanReview`.
    *   Return the classification result.

4.  **Implement Routing Logic:**
    *   In the `/classify` endpoint, after getting the result from `classify_intent()`, check if the `confidence_score` is >= `CONFIDENCE_THRESHOLD`.
    *   If it is, create a `ClassifiedEmail` object containing the original email and the classification result.
    *   Make an HTTP POST request to the `ROUTER_AGENT_URL`, sending the `ClassifiedEmail` object's JSON as the payload.
    *   If confidence is below the threshold, the `workflow_type` should be set to `HumanReview`. Send this payload to the `HUMAN_REVIEW_URL` (you may need to add this to the `.env` file).

5.  **Add Logging:**
    *   Configure Python's `logging` module.
    *   Log all incoming classification requests.
    *   Log the classification result (workflow and confidence).
    *   Log the routing decision (to the main router or to human review).
    *   Log any errors from the LLM or network requests.
