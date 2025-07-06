from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import openai
import os
from dotenv import load_dotenv
from uuid import uuid4

load_dotenv()

app = FastAPI()

# In-memory store of session conversations
chat_sessions = {}

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/")
async def root():
    return {"message": "Welcome to the ChatBot API"}

# Request format
class ChatRequest(BaseModel):
    message: str
    lang: str = "en"
    session_id: str = None  # Optional

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # Session tracking
    session_id = request.session_id or str(uuid4())
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    # Add user message to history
    chat_sessions[session_id].append({"role": "user", "content": request.message})

    # System prompt
    system_prompt = {
        "role": "system",
        "content": """
        You are a vacation assistant. ONLY answer questions about booking hotels or vacation stays.
        If the question is not about travel or hotel booking, respond with:
        ❌ I'm sorry, I can only help with hotel bookings and vacation-related inquiries.

        If the user mentions a city and dates, respond with:
        ✅ Sure! Here's a link:
        https://www.airbnb.com/s/{city}/homes?checkin={checkin}&checkout={checkout}
        """
    }

    # Include system prompt once
    messages = [system_prompt] + chat_sessions[session_id]

    # Call OpenAI API
    try:
        chat_completion = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )
        reply = chat_completion.choices[0].message.content

        # Add assistant reply to history
        chat_sessions[session_id].append({"role": "assistant", "content": reply})

        return {"response": reply, "session_id": session_id}

    except Exception as e:
        return {"response": f"❌ Error: {str(e)}", "session_id": session_id}
