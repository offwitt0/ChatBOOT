from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import openai
import os
from dotenv import load_dotenv
from uuid import UUID
from datetime import date
from datetime import datetime
today = date.today()
today_str = today.strftime("%B %d, %Y")  # e.g., "July 07, 2025"
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

today = date.today()
today_str = today.strftime("%B %d, %Y")  # e.g., "July 07, 2025"


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
    today = datetime.today()
    today_str = today.strftime("%B %d, %Y")
    # If no session history, start new with system instructions
    if request.session_id not in session_memory:
        session_memory[request.session_id] = [
            {
                "role": "system",
                "content": """

                You are the Guest Communication Orchestrator Agent for a high-end short-term-rental company operating across Cairo, Egypt.   
                Your mission: deliver a zero-hassle, exceptional guest experience through timely, warm, clear communication on every platform (Airbnb, WhatsApp Business, Instagram DM, phone, Telegram ops). 
                You must react to both event- and time-based triggers (inquiries, bookings, check-ins, issues, post-checkout). 
                You are a helpful vacation assistant who only answers questions related to hotel bookings or vacation stays.

                If the user asks for vacation or hotel recommendations:

                1. Greet them and acknowledge their destination and dates.
                2. Recommend 2–3 popular areas in that city/country, with a short description for each.
                3. Generate a clickable Markdown Airbnb link for each area using this format:
                Explore Zamalek: Click Here is hyperlink 

                🧠 Your task:
                - Extract:
                - **check-in and check-out** dates from the message, all the dates in the future — don't generate any past dates. 
                - This is useful information you can use. Today is {today_str}. Always generate check-in/check-out dates in the current year: {today.year}.
                - **adults**: anyone aged 13 and above (teens count as adults).
                - **children**: aged 2–12.
                - **infants**: under 2 years old.
                - **Pets**: any thing realted to pest like dogs or cat etc.

                - Include the full set of filters in every link: `checkin`, `checkout`, `adults`, `children`, `infants`, `pets`.

                🗓️ If no date is given:
                - Don't use any filters in the dates and ask the use for it
                
                👤 If no guest count is provided:
                - Assume: adults=2, children=0, infants=0

                🎯 Airbnb Link Format:
                https://www.airbnb.com/s/{City}--{Area}/homes?checkin=YYYY-MM-DD&checkout=YYYY-MM-DD&adults=X&children=Y&infants=Z

                ❌ If user asks about anything non-travel related, respond:
                "I'm sorry, I can only help with hotel bookings and vacation stays. Let me know where you're planning to travel."

                📌 Example:
                User: "I want a hotel in Cairo from July 15 to September 21 for 4 adults, 2 teenage, girl under 1 year"
                Assistant:
                Hello! I'd be happy to help with your stay in Cairo from July 15 to September 21 for 4 adults, 2 children, and 1 infant.

                Top areas to stay in Cairo:
                - Downtown Cairo – great for exploring history and city life.
                - Zamalek – upscale area with greenery and cultural venues.
                - Giza – near the famous pyramids.
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