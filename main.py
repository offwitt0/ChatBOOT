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

✅ If the user asks general questions like "What are the best places to stay in Egypt?", follow this strategy:

1. Suggest 2–3 top cities or areas in the destination (e.g., Egypt → Cairo, Sharm El Sheikh, Luxor).
2. Use bullet points to describe each area briefly (e.g., cultural, beach, historical).
3. For each area, generate a **clickable Markdown Airbnb link** using this format:
   [Explore Cairo](https://www.airbnb.com/s/Cairo/homes?checkin={checkin}&checkout={checkout}&adults={adults})

💡 Logic to follow:
- If no city is mentioned, use the country.
- If no date is mentioned, default to 5 and 7 days from today (check-in/check-out).
- If no number of guests is mentioned, assume 2 adults.
- Use Markdown formatting for all links.
- Only respond to hotel and vacation-related requests.

❌ If the user asks something unrelated (e.g., “What’s the capital of Japan?”), respond:
"I'm sorry, I can only help with hotel bookings and vacation-related stays."

---

📌 EXAMPLE:
User: "What are the best options to stay in Egypt in my vacation?"
Assistant:
Top destinations in Egypt:
- **Cairo** – perfect for cultural and historic experiences.
- **Sharm El Sheikh** – famous for its beaches and diving.
- **Luxor** – rich with ancient temples and monuments.

Here are some Airbnb options:
- [Explore Cairo](https://www.airbnb.com/s/Cairo/homes?checkin=2025-07-12&checkout=2025-07-15&adults=2)
- [Explore Sharm El Sheikh](https://www.airbnb.com/s/Sharm-El-Sheikh/homes?checkin=2025-07-12&checkout=2025-07-15&adults=2)
- [Explore Luxor](https://www.airbnb.com/s/Luxor/homes?checkin=2025-07-12&checkout=2025-07-15&adults=2)
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
