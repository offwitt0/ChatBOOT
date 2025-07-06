from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from uuid import UUID
import openai
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 👇 In-memory conversation memory (simple demo version)
session_memory = {}

@app.get("/")
async def root():
    return {"message": "Welcome to the ChatBot API"}

# 🔄 Data model
class ChatRequest(BaseModel):
    message: str
    lang: str = "en"
    session_id: UUID

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # ❌ Reject unrelated questions
    keywords = ["hotel", "vacation", "stay", "book", "airbnb"]
    if not any(word in request.message.lower() for word in keywords):
        return {
            "response": "❌ I'm sorry, I can only help with hotel bookings and vacation-related inquiries.",
            "session_id": str(request.session_id)
        }

    # 🔁 Get session memory or start fresh
    history = session_memory.get(str(request.session_id), [])

    # 🔧 Build full message history
    messages = [
        {"role": "system", "content": "You are a hotel booking assistant. You ONLY answer vacation-related hotel booking questions. If user asks about destinations and dates, offer an Airbnb link."}
    ] + history + [
        {"role": "user", "content": request.message}
    ]

    # 💬 Generate response
    chat_completion = client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )

    reply = chat_completion.choices[0].message.content

    # 🧠 Save interaction to memory
    session_memory[str(request.session_id)] = history + [
        {"role": "user", "content": request.message},
        {"role": "assistant", "content": reply}
    ]

    return {
        "response": reply,
        "session_id": str(request.session_id)
    }
