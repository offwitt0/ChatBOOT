from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import openai
import re
from datetime import datetime

load_dotenv()
app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ChatRequest(BaseModel):
    message: str
    lang: str = "en"

@app.get("/")
async def root():
    return {"message": "Welcome to the ChatBot API"}

def extract_booking_info(message):
    # Try to find destination, check-in/out dates, and guest count
    location_match = re.search(r'in ([A-Za-z\s]+)', message)
    date_match = re.findall(r'(\d{4}-\d{2}-\d{2})', message)
    guests_match = re.search(r'(\d+) (?:guests?|adults?)', message)

    location = location_match.group(1).strip().replace(' ', '--') if location_match else None
    checkin = date_match[0] if len(date_match) > 0 else None
    checkout = date_match[1] if len(date_match) > 1 else None
    guests = guests_match.group(1) if guests_match else '1'

    if location and checkin and checkout:
        url = f"https://www.airbnb.com/s/{location}/homes?checkin={checkin}&checkout={checkout}&adults={guests}"
        return url
    return None

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    url = extract_booking_info(request.message)

    if url:
        return {
            "response": f"✅ Here are some options for you: [View on Airbnb]({url})"
        }

    system_prompt = (
        "You are a hotel booking assistant. Only respond to hotel or vacation-related questions. "
        "If the user asks anything outside this, say: ❌ 'I'm sorry, I can only help with hotel bookings and vacation-related inquiries.'"
    )

    chat_completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message}
        ]
    )

    return {
        "response": chat_completion.choices[0].message.content
    }