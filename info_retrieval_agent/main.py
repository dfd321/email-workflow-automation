# main.py for info_retrieval_agent
from fastapi import FastAPI
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

class EmailData(BaseModel):
    # Define the structure of the email data
    pass

@app.post("/handle_inquiry")
async def handle_inquiry(email: EmailData):
    print("Handling info retrieval request...")
    # TODO: Implement info retrieval logic
    return {"status": "inquiry handled"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
