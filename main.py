from fastapi import FastAPI
from fastapi import Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import re

import openai
import os
from dotenv import load_dotenv
from uuid import UUID
from datetime import date
from datetime import datetime
import requests
import json

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
    phone: str  # <-- new field for the user's phone number

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Example phone-to-chat_id mapping (you can later load this from a file/db)
def get_chat_id_by_phone(phone: str):
    phone = phone.lstrip("+")  # remove leading +
    try:
        with open("chat_id_store.json", "r") as f:
            mapping = json.load(f)
        return mapping.get(phone)
    except FileNotFoundError:
        return None

def send_to_telegram_by_phone(phone: str, text: str, request_contact: bool = False):
    chat_id = get_chat_id_by_phone(phone)
    if not chat_id:
        print(f"❌ Chat ID not found for phone: {phone}")
        return

    # Send plain text or send "Share Phone Number" button
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }

    if request_contact:
        keyboard = {
            "keyboard": [[{
                "text": "📱 Share Phone Number",
                "request_contact": True
            }]],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        payload["reply_markup"] = keyboard

    requests.post(url, json=payload)

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
                [Explore Zamalek](https://www.airbnb.com/s/Cairo--Zamalek/homes?checkin=2025-07-12&checkout=2025-07-15&adults=2&children=0&infants=0)

                Your task:
                - Extract:
                - plz this is so importand part take it carfully
                - **check-in and check-out** dates from the message, all the dates in the future — don't generate any past dates. 
                - This is useful information you can use. Today is {today_str}. Always generate check-in/check-out dates in the current year: {today.year}.
                - **adults**: anyone aged 13 and above (teens count as adults).
                - **children**: aged 2–12.
                - **infants**: under 2 years old.
                - **Pets**: any thing realted to pest like dogs or cat etc.

                - Include the full set of filters in every link: `checkin`, `checkout`, `adults`, `children`, `infants`, `pets`.
                
                If no guest count is provided:
                - Assume: adults=2, children=0, infants=0

                Airbnb Link Format:
                https://www.airbnb.com/s/{City}--{Area}/homes?checkin=YYYY-MM-DD&checkout=YYYY-MM-DD&adults=X&children=Y&infants=Z

                If user asks about anything non-travel related, respond:
                "I'm sorry, I can only help with hotel bookings and vacation stays. Let me know where you're planning to travel."
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
        if request.phone:  # If we received a phone number in the web chat
            print(f"📲 Prompting user {request.phone} for phone number sharing on Telegram.")
            send_to_telegram_by_phone(request.phone, "Please tap the button below to share your phone number with the bot.", True)
        send_to_telegram_by_phone(request.phone, reply)

        # Extract Markdown links like [Explore Zamalek](https://...)
        markdown_links = re.findall(r'\[(.*?)\]\((https?://[^\s]+)\)', reply)

        # Also fallback to raw links in case they exist without Markdown
        raw_links = re.findall(r'(https?://www\.airbnb\.com/s/[^\s)]+)', reply)

        # Combine unique links
        all_links = set([text + ": " + url for text, url in markdown_links]) | set(raw_links)

        # Send links to Telegram as individual messages
        for link in all_links:
            send_to_telegram_by_phone(request.phone, link)

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
    
@app.post("/telegram-webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    print("📥 Telegram webhook triggered!")
    print("📦 Incoming data:", json.dumps(data, indent=2))

    message = data.get("message", {})

    # Handle /start command
    if "text" in message and message["text"] == "/start":
        chat_id = message["chat"]["id"]

        print(f"🚀 /start command received from chat_id: {chat_id}")

        welcome_msg = (
            "👋 Welcome to the Vacation Assistant!\n\n"
            "Please tap the button below to share your phone number. Once you do, "
            "you’ll receive vacation suggestions via this chat whenever you search on our website."
        )

        keyboard = {
            "keyboard": [[{
                "text": "📱 Share Phone Number",
                "request_contact": True
            }]],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }

        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": welcome_msg,
                "reply_markup": keyboard
            }
        )

        print("📤 Sent /start reply:", resp.status_code, resp.text)
        return {"status": "start_sent"}

    # Handle contact sharing
    if "contact" in message:
        phone = message["contact"]["phone_number"].lstrip("+")
        chat_id = message["chat"]["id"]

        print(f"📲 Contact shared: phone={phone}, chat_id={chat_id}")

        try:
            with open("chat_id_store.json", "r") as f:
                mapping = json.load(f)
        except FileNotFoundError:
            mapping = {}

        mapping[phone] = chat_id

        with open("chat_id_store.json", "w") as f:
            json.dump(mapping, f)

        print(f"✅ Saved phone {phone} → chat_id {chat_id}")

        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
            "chat_id": chat_id,
            "text": "✅ You’re now linked! You’ll receive hotel links here when you use the assistant on the website.",
        })

        return {"status": "linked"}

    print("🤷 Message did not match any handled type")
    return {"status": "ignored"}

@app.post("/check-phone")
async def check_phone(request: Request):
    body = await request.json()
    phone = body.get("phone", "").lstrip("+")
    chat_id = get_chat_id_by_phone(phone)
    return {"linked": bool(chat_id)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))