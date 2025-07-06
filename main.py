from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import openai
import os
from dotenv import load_dotenv
from uuid import UUID

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 🧠 Session memory store
session_memory = {}

@app.get("/")
async def root():
    return {"message": "Welcome to the ChatBot API"}

class ChatRequest(BaseModel):
    message: str
    lang: str = "en"
    session_id: UUID

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # If no session history, start new with system instructions
    if request.session_id not in session_memory:
        session_memory[request.session_id] = [
            {
                "role": "system",
                "content": """
You are a vacation assistant. ONLY answer questions about booking hotels or vacation stays.

Your job is to extract the city, check-in date, check-out date, and number of guests (if available) from the user's message.
Then return a response with an Airbnb link like this:

https://www.airbnb.com/s/{city}/homes?checkin={checkin}&checkout={checkout}&adults={adults}

🧠 Rules:
- If city, check-in, or check-out is missing, ask the user for clarification.
- If number of adults is missing, assume 1.
- Use YYYY-MM-DD date format.
- Make city URL-safe (e.g. "New York" → "New%20York").
- If the user asks unrelated things, respond:
❌ I'm sorry, I can only help with hotel bookings and vacation-related inquiries.
"""
            }
        ]

    session_messages = session_memory[request.session_id]
    session_messages.append({"role": "user", "content": request.message})

    try:
        chat_completion = client.chat.completions.create(
            model="gpt-4o",
            messages=session_messages
        )
        reply = chat_completion.choices[0].message.content
        session_messages.append({"role": "assistant", "content": reply})

        return {
            "response": reply,
            "session_id": str(request.session_id)
        }

    except Exception as e:
        return {
            "response": "❌ An error occurred while processing your request.",
            "error": str(e),
            "session_id": str(request.session_id)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
