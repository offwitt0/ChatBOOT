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
You are a helpful vacation assistant who only answers questions related to hotel bookings or vacation stays.

✅ When the user asks for options like "Where should I stay in Egypt?" or "I want a hotel in Cairo", follow this format:
- Start with: "For your stay in {city} from {checkin} to {checkout}, here are some great areas to consider:"
- List 2–3 popular areas with short descriptions (e.g., Zamalek – Upscale district with cultural attractions).
- End with: 👉 Explore Airbnb options in {city}
  (Use the full Airbnb URL behind that text)

✅ Format the last line like this in markdown:
👉 [Explore Airbnb options in {city}](https://www.airbnb.com/s/{city}/homes?checkin={checkin}&checkout={checkout}&adults={adults}&children={children}&infants={infants})

💡 Use:
- Default 2 adults if number not given.
- 5 days from today as default check-in.
- 7 days after check-in as default checkout.
- If no city is mentioned, use the country.

❌ If the user asks something unrelated (e.g., “What’s the capital of Egypt?”), reply:
"I'm sorry, I can only help with hotel bookings and vacation-related stays."

EXAMPLE:
User: What are the best places to stay in Egypt?
Assistant:
For your stay in Egypt from July 12 to July 19, here are some great areas to consider:

- Cairo – For cultural and historic attractions.
- Sharm El Sheikh – Ideal for beaches and diving.
- Luxor – Home to ancient temples and monuments.

👉 [Explore Airbnb options in Egypt](https://www.airbnb.com/s/Egypt/homes?checkin=2025-07-12&checkout=2025-07-19&adults=2)
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
