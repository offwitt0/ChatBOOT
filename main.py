from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import openai

load_dotenv()

app = FastAPI()

# CORS setup (so web or mobile can call it)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Set up the new OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Define expected body format
class ChatRequest(BaseModel):
    message: str
    lang: str = "en"

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    system_prompt = {
        "en": "You are a helpful assistant who replies in English.",
        "ar": "أنت مساعد ذكي تجيب باللغة العربية فقط."
    }.get(request.lang, "You are a helpful assistant.")

    # ✅ New API call syntax for openai>=1.0.0
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