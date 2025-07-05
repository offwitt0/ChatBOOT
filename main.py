from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import openai


load_dotenv()

app = FastAPI()

# CORS setup (allow any origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ OpenAI client setup
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 👇 Add this route to fix "Not Found"
@app.get("/")
async def root():
    return {"message": "Welcome to the ChatBot API"}

# Input model
class ChatRequest(BaseModel):
    message: str
    lang: str = "en"

# Chat endpoint
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    system_prompt = {
        "en": "You are a helpful assistant who replies in English.",
        "ar": "أنت مساعد ذكي تجيب باللغة العربية فقط."
    }.get(request.lang, "You are a helpful assistant.")

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

# Start server
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
