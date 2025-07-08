# main.py for invoice_handler_agent
from fastapi import FastAPI
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

class EmailData(BaseModel):
    # Define the structure of the email data
    pass

@app.post("/handle_invoice")
async def handle_invoice(email: EmailData):
    print("Handling invoice request...")
    # TODO: Implement invoice handling logic
    return {"status": "invoice handled"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
