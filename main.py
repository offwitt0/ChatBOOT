from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import openai
import os
from dotenv import load_dotenv

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

@app.get("/")
async def root():
    return {"message": "Welcome to the ChatBot API"}

class ChatRequest(BaseModel):
    message: str
    lang: str = "en"

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if not request.message.lower().strip().startswith("book") and "hotel" not in request.message.lower():
        return {
            "response": "❌ I'm sorry, I can only help with hotel bookings and vacation-related inquiries."
        }

    chat_completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You help people with hotel bookings and vacation-related travel."},
            {"role": "user", "content": request.message},
        ]
    )

    return {
        "response": chat_completion.choices[0].message.content
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
