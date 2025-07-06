from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import openai

load_dotenv()

app = FastAPI()

# CORS for all origins (mobile + web)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/")
async def root():
    return {"message": "Welcome to the ChatBot API"}

class ChatRequest(BaseModel):
    message: str
    lang: str = "en"

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    system_prompt = (
        "You are a travel assistant specialized in hotel bookings and vacation planning. "
        "Answer questions related to booking hotels, vacation destinations, accommodations, travel tips, etc. "
        "If the question is clearly unrelated to travel or hotel bookings, politely respond with: "
        "'❌ I'm sorry, I can only help with hotel bookings and vacation-related inquiries.'"
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
