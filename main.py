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

def send_to_telegram_by_phone(phone: str, text: str, image_url: str = None):
    phone = phone.lstrip("+")  # ✅ Normalize phone just in case
    print(f"📞 [send_to_telegram_by_phone] Looking up chat_id for phone: {phone}")

    chat_id = get_chat_id_by_phone(phone)
    if not chat_id:
        print("❌ [send_to_telegram_by_phone] Chat ID not found for phone:", phone)
        return

    print(f"✅ [send_to_telegram_by_phone] Sending to chat_id: {chat_id}")
    print(f"💬 [send_to_telegram_by_phone] Message: {text}")

    if image_url:
        print(f"🖼️ [send_to_telegram_by_phone] Sending with image: {image_url}")
        # Send image with caption
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "caption": text,
            "parse_mode": "Markdown"
        }
        try:
            files = {"photo": requests.get(image_url).content}
            requests.post(url, data=payload, files=files)
        except Exception as e:
            print(f"❌ [send_to_telegram_by_phone] Failed to send image: {e}")
    else:
        # Send plain text
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            response = requests.post(url, json=payload)
            print(f"📤 [send_to_telegram_by_phone] Telegram response: {response.status_code}")
        except Exception as e:
            print(f"❌ [send_to_telegram_by_phone] Failed to send message: {e}")

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

        # OPTIONAL: Get user's phone from somewhere (e.g., request payload or session)
        user_phone = request.phone  # <-- Replace with dynamic logic later

        # Extract Airbnb image URL if you have one
        # You could use regex or LLM tools to parse it, for now just assume none
        image_url = None  # or provide a real URL if generated

        # Send the reply to Telegram
        send_to_telegram_by_phone(user_phone, reply, image_url)

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
    message = data.get("message", {})

    # Handle /start command
    if "text" in message and message["text"] == "/start":
        chat_id = message["chat"]["id"]
        
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

        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
            "chat_id": chat_id,
            "text": welcome_msg,
            "reply_markup": keyboard
        })

        return {"status": "start_sent"}

    # ✅ Handle contact sharing and save phone → chat_id
    if "contact" in message:
        phone = message["contact"]["phone_number"].lstrip("+")  # normalize phone
        chat_id = message["chat"]["id"]

        try:
            with open("chat_id_store.json", "r") as f:
                mapping = json.load(f)
        except FileNotFoundError:
            mapping = {}

        mapping[phone] = chat_id

        with open("chat_id_store.json", "w") as f:
            json.dump(mapping, f)

        print(f"✅ Saved phone {phone} → chat_id {chat_id}")

        # Send confirmation
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
            "chat_id": chat_id,
            "text": "✅ You’re now linked! You’ll receive hotel links here when you use the assistant on the website.",
        })

        return {"status": "linked"}

    return {"status": "ignored"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))